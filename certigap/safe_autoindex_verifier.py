from __future__ import annotations

import hashlib
import json
import math

from .autoindex import (
    PORTFOLIO_ORDER,
    AutoIndexConstraints,
    TraceOperation,
    WorkloadTrace,
)
from .autoindex_verifier import verify_autoindex_artifact
from .safe_autoindex import SafeSelectionPolicy


class SafeAutoIndexVerificationError(ValueError):
    pass


def _row(artifact: dict, name: str) -> dict:
    matches = [
        row for row in artifact["candidates"] if row.get("name") == name
    ]
    if len(matches) != 1:
        raise SafeAutoIndexVerificationError("candidate row is not unique")
    return matches[0]


def _baseline(artifact: dict, policy: SafeSelectionPolicy) -> dict:
    feasible = [
        row
        for row in artifact["candidates"]
        if row["feasible"] and row["name"] in policy.safe_baselines
    ]
    if not feasible:
        raise SafeAutoIndexVerificationError(
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
        raise SafeAutoIndexVerificationError("unknown candidate unit cost")
    return float(getattr(constraints, field))


def _cost_upper_bound(row: dict, constraints: AutoIndexConstraints) -> float:
    return (row["resources"]["build_units"] + 1) * _unit_cost(
        row["name"], constraints
    )


def _canonical_sha256(value: object) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise SafeAutoIndexVerificationError(
            "certificate is not canonical JSON"
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def _trace(raw: object, n: int) -> WorkloadTrace | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or raw.get("n") != n:
        raise SafeAutoIndexVerificationError("test trace universe is invalid")
    operations = raw.get("operations")
    if not isinstance(operations, list) or not operations:
        raise SafeAutoIndexVerificationError("test trace must not be empty")
    try:
        return WorkloadTrace(
            n,
            (TraceOperation(**operation) for operation in operations),
        )
    except (TypeError, ValueError) as exc:
        raise SafeAutoIndexVerificationError(
            "test trace does not validate"
        ) from exc


def _test_scores(
    base: dict,
    test: WorkloadTrace | None,
    names: tuple[str, str, str],
) -> dict | None:
    if test is None:
        return None
    from .autoindex import compile_autoindex

    train = WorkloadTrace(
        base["n"],
        (
            TraceOperation(**operation)
            for operation in base["train_trace"]["operations"]
        ),
    )
    constraints = AutoIndexConstraints(**base["constraints"])
    evaluated = compile_autoindex(
        [0.0] * base["n"],
        train,
        constraints=constraints,
        holdout_trace=test,
    ).artifact

    def score(name: str) -> float:
        holdout = _row(evaluated, name)["holdout"]
        if holdout is None:
            raise SafeAutoIndexVerificationError("test score is missing")
        return float(holdout["score"])

    candidate, baseline, deployed = names
    return {
        "operation_count": len(test.operations),
        "candidate_score": score(candidate),
        "baseline_score": score(baseline),
        "deployed_score": score(deployed),
        "selection_independent": True,
    }


def verify_safe_autoindex_certificate(certificate: dict) -> dict:
    if (
        not isinstance(certificate, dict)
        or certificate.get("schema") != "certigap-safe-autoindex-v1"
    ):
        raise SafeAutoIndexVerificationError("unsupported certificate schema")
    supplied = certificate.get("sha256")
    unsigned = dict(certificate)
    unsigned.pop("sha256", None)
    if supplied != _canonical_sha256(unsigned):
        raise SafeAutoIndexVerificationError("certificate digest mismatch")
    base = certificate.get("base_artifact")
    if not isinstance(base, dict):
        raise SafeAutoIndexVerificationError("base artifact is missing")
    try:
        verify_autoindex_artifact(base)
    except (TypeError, ValueError) as exc:
        raise SafeAutoIndexVerificationError(
            "base AutoIndex artifact does not verify"
        ) from exc
    raw_policy = certificate.get("policy")
    if not isinstance(raw_policy, dict):
        raise SafeAutoIndexVerificationError("policy is missing")
    try:
        policy = SafeSelectionPolicy(
            confidence_alpha=raw_policy["confidence_alpha"],
            horizon_operations=raw_policy["horizon_operations"],
            migration_cost_units=raw_policy["migration_cost_units"],
            build_cost_per_unit=raw_policy["build_cost_per_unit"],
            minimum_improvement=raw_policy["minimum_improvement"],
            safe_baselines=tuple(raw_policy["safe_baselines"]),
        )
        policy.validate()
    except (KeyError, TypeError, ValueError) as exc:
        raise SafeAutoIndexVerificationError("policy does not validate") from exc
    if policy.manifest() != raw_policy:
        raise SafeAutoIndexVerificationError("policy is not canonical")

    candidate = _row(base, base["selected"])
    baseline = _baseline(base, policy)
    candidate_validation = candidate["holdout"]
    baseline_validation = baseline["holdout"]
    if candidate_validation is None or baseline_validation is None:
        raise SafeAutoIndexVerificationError("validation evaluation is missing")
    operation_count = int(candidate_validation["operation_count"])
    constraints = AutoIndexConstraints(**base["constraints"])
    mean_difference = (
        float(candidate_validation["mean_primitive_visits"])
        - float(baseline_validation["mean_primitive_visits"])
    )
    difference_range_bound = _cost_upper_bound(
        candidate, constraints
    ) + _cost_upper_bound(baseline, constraints)
    confidence_radius = difference_range_bound * math.sqrt(
        math.log(1.0 / policy.confidence_alpha) / (2.0 * operation_count)
    )
    transition = (
        policy.migration_cost_units
        + policy.build_cost_per_unit * candidate["resources"]["build_units"]
    ) / policy.horizon_operations
    upper = mean_difference + confidence_radius + transition
    same = candidate["name"] == baseline["name"]
    approved = same or upper < -policy.minimum_improvement
    deployed = candidate["name"] if approved else baseline["name"]
    reason = (
        "training winner is already the declared safe baseline"
        if same
        else (
            "validation upper bound proves amortized improvement"
            if approved
            else "insufficient validation evidence; safe baseline retained"
        )
    )
    expected_decision = {
        "train_candidate": candidate["name"],
        "safe_baseline": baseline["name"],
        "deployed": deployed,
        "candidate_approved": approved,
        "reason": reason,
        "validation": {
            "operation_count": operation_count,
            "candidate_mean_work": float(
                candidate_validation["mean_primitive_visits"]
            ),
            "baseline_mean_work": float(
                baseline_validation["mean_primitive_visits"]
            ),
            "mean_difference": mean_difference,
            "difference_range_bound": difference_range_bound,
            "confidence_radius": confidence_radius,
            "amortized_transition_cost": transition,
            "upper_difference": upper,
        },
    }
    if certificate.get("decision") != expected_decision:
        raise SafeAutoIndexVerificationError("decision does not recompute")
    test = _trace(certificate.get("test_trace"), base["n"])
    expected_test = _test_scores(
        base,
        test,
        (candidate["name"], baseline["name"], deployed),
    )
    if certificate.get("test_evaluation") != expected_test:
        raise SafeAutoIndexVerificationError("test evaluation does not recompute")
    expected_scope = (
        "one-sided Hoeffding no-regression gate conditional on independent "
        "IID bounded validation operations; test is evaluation-only; "
        "wall-clock portability and arbitrary temporal drift are not proven"
    )
    if certificate.get("scope") != expected_scope:
        raise SafeAutoIndexVerificationError("certificate scope is invalid")
    return {
        "verified": True,
        "selected": deployed,
        "train_candidate": candidate["name"],
        "safe_baseline": baseline["name"],
        "candidate_approved": approved,
        "validation_upper_difference": upper,
        "confidence_alpha": policy.confidence_alpha,
        "test_score": (
            None if expected_test is None else expected_test["deployed_score"]
        ),
    }
