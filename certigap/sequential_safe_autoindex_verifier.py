from __future__ import annotations

import hashlib
import json
import math

from .autoindex import (
    PORTFOLIO_ORDER,
    AutoIndexConstraints,
    TraceOperation,
    WorkloadTrace,
    analytical_candidate_costs,
    compile_autoindex,
)
from .autoindex_verifier import verify_autoindex_artifact
from .sequential_safe_autoindex import SequentialSafeSelectionPolicy


class SequentialSafeAutoIndexVerificationError(ValueError):
    pass


def _canonical_sha256(value: object) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SequentialSafeAutoIndexVerificationError(
            "certificate is not canonical JSON"
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def _row(artifact: dict, name: str) -> dict:
    matches = [
        row for row in artifact["candidates"] if row.get("name") == name
    ]
    if len(matches) != 1:
        raise SequentialSafeAutoIndexVerificationError(
            "candidate row is not unique"
        )
    return matches[0]


def _baseline(artifact: dict, policy: SequentialSafeSelectionPolicy) -> dict:
    feasible = [
        row
        for row in artifact["candidates"]
        if row["feasible"] and row["name"] in policy.safe_baselines
    ]
    if not feasible:
        raise SequentialSafeAutoIndexVerificationError(
            "no declared safe baseline satisfies constraints"
        )
    order = {name: index for index, name in enumerate(policy.safe_baselines)}
    return min(
        feasible,
        key=lambda row: (
            row["train"]["score"],
            row["resources"]["memory_slots"],
            order[row["name"]],
        ),
    )


def _unit_cost(name: str, constraints: AutoIndexConstraints) -> float:
    field = {
        "sorted_array": "array_unit_cost",
        "prefix_sum": "prefix_unit_cost",
        "fenwick": "fenwick_unit_cost",
        "sqrt_decomposition": "sqrt_unit_cost",
        "segment_tree": "segment_tree_unit_cost",
        "sparse_table": "sparse_unit_cost",
        "certirange_point": "certirange_unit_cost",
        "certirange_range": "certirange_unit_cost",
    }.get(name)
    if field is None or name not in PORTFOLIO_ORDER:
        raise SequentialSafeAutoIndexVerificationError(
            "unknown candidate unit cost"
        )
    return float(getattr(constraints, field))


def _cost_upper_bound(row: dict, constraints: AutoIndexConstraints) -> float:
    return (row["resources"]["build_units"] + 1) * _unit_cost(
        row["name"], constraints
    )


def _trace(raw: object, n: int, label: str) -> WorkloadTrace | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or raw.get("n") != n:
        raise SequentialSafeAutoIndexVerificationError(
            f"{label} universe is invalid"
        )
    operations = raw.get("operations")
    if not isinstance(operations, list) or not operations:
        raise SequentialSafeAutoIndexVerificationError(
            f"{label} must not be empty"
        )
    try:
        return WorkloadTrace(
            n, (TraceOperation(**operation) for operation in operations)
        )
    except (TypeError, ValueError) as exc:
        raise SequentialSafeAutoIndexVerificationError(
            f"{label} does not validate"
        ) from exc


def _checkpoint(
    operation: int,
    cumulative: float,
    width: float,
    transition: float,
    policy: SequentialSafeSelectionPolicy,
) -> dict:
    allocated_alpha = policy.confidence_alpha / (
        operation * (operation + 1)
    )
    mean = cumulative / operation
    radius = width * math.sqrt(
        math.log(1.0 / allocated_alpha) / (2.0 * operation)
    )
    return {
        "operation_count": operation,
        "allocated_alpha": allocated_alpha,
        "spent_alpha_through_operation": (
            policy.confidence_alpha * operation / (operation + 1)
        ),
        "mean_difference": mean,
        "difference_range_bound": width,
        "confidence_radius": radius,
        "amortized_transition_cost": transition,
        "upper_difference": mean + radius + transition,
    }


def _decision(
    base: dict,
    policy: SequentialSafeSelectionPolicy,
    validation: WorkloadTrace,
) -> dict:
    candidate = _row(base, base["selected"])
    baseline = _baseline(base, policy)
    same = candidate["name"] == baseline["name"]
    if same:
        return {
            "train_candidate": candidate["name"],
            "safe_baseline": baseline["name"],
            "deployed": baseline["name"],
            "candidate_approved": True,
            "reason": "training winner is already the declared safe baseline",
            "stopping_operation": 0,
            "selection_checkpoint": None,
            "final_audit": None,
            "monitoring": {
                "method": "alpha_spending_hoeffding",
                "allocation": "alpha_t=alpha/(t*(t+1))",
                "total_alpha_budget": policy.confidence_alpha,
                "validation_operations": len(validation.operations),
                "post_stop_operations": len(validation.operations),
            },
        }

    constraints = AutoIndexConstraints(**base["constraints"])
    width = _cost_upper_bound(
        candidate, constraints
    ) + _cost_upper_bound(baseline, constraints)
    transition = (
        policy.migration_cost_units
        + policy.build_cost_per_unit * candidate["resources"]["build_units"]
    ) / policy.horizon_operations
    candidate_costs = analytical_candidate_costs(
        base, candidate["name"], validation
    )
    baseline_costs = analytical_candidate_costs(
        base, baseline["name"], validation
    )
    cumulative = 0.0
    selected = None
    final = None
    for operation, costs in enumerate(
        zip(candidate_costs, baseline_costs), start=1
    ):
        cumulative += costs[0] - costs[1]
        current = _checkpoint(
            operation, cumulative, width, transition, policy
        )
        final = current
        if (
            selected is None
            and operation >= policy.minimum_observations
            and current["upper_difference"] < -policy.minimum_improvement
        ):
            selected = current
    approved = selected is not None
    stop = None if selected is None else selected["operation_count"]
    return {
        "train_candidate": candidate["name"],
        "safe_baseline": baseline["name"],
        "deployed": candidate["name"] if approved else baseline["name"],
        "candidate_approved": approved,
        "reason": (
            "anytime validation bound proves amortized improvement"
            if approved
            else "no validation prefix proved improvement; safe baseline retained"
        ),
        "stopping_operation": stop,
        "selection_checkpoint": selected,
        "final_audit": final,
        "monitoring": {
            "method": "alpha_spending_hoeffding",
            "allocation": "alpha_t=alpha/(t*(t+1))",
            "total_alpha_budget": policy.confidence_alpha,
            "validation_operations": len(validation.operations),
            "post_stop_operations": (
                0 if stop is None else len(validation.operations) - stop
            ),
        },
    }


def _test_scores(
    base: dict,
    test: WorkloadTrace | None,
    names: tuple[str, str, str],
) -> dict | None:
    if test is None:
        return None
    train = WorkloadTrace(
        base["n"],
        (
            TraceOperation(**operation)
            for operation in base["train_trace"]["operations"]
        ),
    )
    evaluated = compile_autoindex(
        [0.0] * base["n"],
        train,
        constraints=AutoIndexConstraints(**base["constraints"]),
        holdout_trace=test,
    ).artifact

    def score(name: str) -> float:
        holdout = _row(evaluated, name)["holdout"]
        if holdout is None:
            raise SequentialSafeAutoIndexVerificationError(
                "test score is missing"
            )
        return float(holdout["score"])

    candidate, baseline, deployed = names
    return {
        "operation_count": len(test.operations),
        "candidate_score": score(candidate),
        "baseline_score": score(baseline),
        "deployed_score": score(deployed),
        "selection_independent": True,
    }


def verify_sequential_safe_autoindex_certificate(
    certificate: dict,
) -> dict:
    if (
        not isinstance(certificate, dict)
        or certificate.get("schema")
        != "certigap-sequential-safe-autoindex-v1"
    ):
        raise SequentialSafeAutoIndexVerificationError(
            "unsupported certificate schema"
        )
    supplied = certificate.get("sha256")
    unsigned = dict(certificate)
    unsigned.pop("sha256", None)
    if supplied != _canonical_sha256(unsigned):
        raise SequentialSafeAutoIndexVerificationError(
            "certificate digest mismatch"
        )
    base = certificate.get("base_artifact")
    if not isinstance(base, dict):
        raise SequentialSafeAutoIndexVerificationError(
            "base artifact is missing"
        )
    try:
        verify_autoindex_artifact(base)
    except (TypeError, ValueError) as exc:
        raise SequentialSafeAutoIndexVerificationError(
            "base AutoIndex artifact does not verify"
        ) from exc

    raw_policy = certificate.get("policy")
    if not isinstance(raw_policy, dict):
        raise SequentialSafeAutoIndexVerificationError("policy is missing")
    try:
        policy = SequentialSafeSelectionPolicy(
            confidence_alpha=raw_policy["confidence_alpha"],
            minimum_observations=raw_policy["minimum_observations"],
            horizon_operations=raw_policy["horizon_operations"],
            migration_cost_units=raw_policy["migration_cost_units"],
            build_cost_per_unit=raw_policy["build_cost_per_unit"],
            minimum_improvement=raw_policy["minimum_improvement"],
            safe_baselines=tuple(raw_policy["safe_baselines"]),
        )
        policy.validate()
    except (KeyError, TypeError, ValueError) as exc:
        raise SequentialSafeAutoIndexVerificationError(
            "policy does not validate"
        ) from exc
    if policy.manifest() != raw_policy:
        raise SequentialSafeAutoIndexVerificationError(
            "policy is not canonical"
        )

    validation = _trace(
        base.get("holdout_trace"), base["n"], "validation trace"
    )
    if validation is None:
        raise SequentialSafeAutoIndexVerificationError(
            "validation trace is missing"
        )
    if policy.minimum_observations > len(validation.operations):
        raise SequentialSafeAutoIndexVerificationError(
            "minimum_observations exceeds validation length"
        )
    expected_decision = _decision(base, policy, validation)
    if certificate.get("decision") != expected_decision:
        raise SequentialSafeAutoIndexVerificationError(
            "sequential decision does not recompute"
        )

    test = _trace(certificate.get("test_trace"), base["n"], "test trace")
    names = (
        expected_decision["train_candidate"],
        expected_decision["safe_baseline"],
        expected_decision["deployed"],
    )
    test_scores = _test_scores(base, test, names)
    if certificate.get("test_evaluation") != test_scores:
        raise SequentialSafeAutoIndexVerificationError(
            "test evaluation does not recompute"
        )
    scope = (
        "one-sided alpha-spending Hoeffding confidence sequence valid "
        "under optional stopping conditional on independent IID bounded "
        "validation operations; post-stop observations and test are "
        "evaluation-only; future drift and wall-clock portability are "
        "not proven"
    )
    if certificate.get("scope") != scope:
        raise SequentialSafeAutoIndexVerificationError(
            "certificate scope is invalid"
        )
    checkpoint = (
        expected_decision["selection_checkpoint"]
        or expected_decision["final_audit"]
    )
    return {
        "verified": True,
        "selected": expected_decision["deployed"],
        "candidate_approved": expected_decision["candidate_approved"],
        "stopping_operation": expected_decision["stopping_operation"],
        "upper_difference": (
            None if checkpoint is None else checkpoint["upper_difference"]
        ),
        "confidence_alpha": policy.confidence_alpha,
        "test_score": (
            None if test_scores is None else test_scores["deployed_score"]
        ),
    }
