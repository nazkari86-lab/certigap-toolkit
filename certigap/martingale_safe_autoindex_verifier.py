from __future__ import annotations

import hashlib
import json
import math

from .autoindex import (
    AutoIndexConstraints,
    WorkloadTrace,
    analytical_candidate_costs,
)
from .autoindex_verifier import verify_autoindex_artifact
from .martingale_safe_autoindex import MartingaleSafeSelectionPolicy
from .sequential_safe_autoindex_verifier import (
    _baseline,
    _cost_upper_bound,
    _row,
    _test_scores,
    _trace,
)


class MartingaleSafeAutoIndexVerificationError(ValueError):
    pass


def _canonical_sha256(value: object) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MartingaleSafeAutoIndexVerificationError(
            "certificate is not canonical JSON"
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def _checkpoint(
    *,
    operation_count: int,
    stream_operation: int,
    cumulative_evidence: float,
    width: float,
    alpha: float,
    fractions: tuple[float, ...],
) -> dict:
    log_weight = -math.log(len(fractions))
    terms = [
        log_weight
        + (fraction / width) * cumulative_evidence
        - fraction * fraction * operation_count / 8.0
        for fraction in fractions
    ]
    maximum = max(terms)
    log_e_value = maximum + math.log(
        sum(math.exp(term - maximum) for term in terms)
    )
    return {
        "operation_count": operation_count,
        "stream_operation": stream_operation,
        "cumulative_evidence": cumulative_evidence,
        "mean_evidence": cumulative_evidence / operation_count,
        "difference_range_bound": width,
        "log_e_value": log_e_value,
        "e_value": math.exp(min(log_e_value, 700.0)),
        "log_threshold": math.log(1.0 / alpha),
        "crossed": log_e_value >= math.log(1.0 / alpha),
    }


def _expected_decision(
    base: dict,
    monitoring: WorkloadTrace,
    policy: MartingaleSafeSelectionPolicy,
) -> dict:
    candidate = _row(base, base["selected"])
    baseline = _baseline(base, policy)
    if candidate["name"] == baseline["name"]:
        return {
            "train_candidate": candidate["name"],
            "safe_baseline": baseline["name"],
            "deployed": baseline["name"],
            "candidate_approved": True,
            "candidate_revoked": False,
            "reason": "training winner is already the declared safe baseline",
            "deployment_event": None,
            "revocation_event": None,
            "deployment_final_audit": None,
            "revocation_final_audit": None,
            "monitoring_operations": len(monitoring.operations),
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
        base, candidate["name"], monitoring
    )
    baseline_costs = analytical_candidate_costs(
        base, baseline["name"], monitoring
    )
    deployment_event = None
    revocation_event = None
    deployment_audit = None
    revocation_audit = None
    deployment_sum = 0.0
    revocation_sum = 0.0
    revocation_count = 0
    for stream_operation, costs in enumerate(
        zip(candidate_costs, baseline_costs), start=1
    ):
        difference = costs[0] - costs[1]
        if deployment_event is None:
            deployment_sum += -(
                difference + transition + policy.minimum_improvement
            )
            deployment_audit = _checkpoint(
                operation_count=stream_operation,
                stream_operation=stream_operation,
                cumulative_evidence=deployment_sum,
                width=width,
                alpha=policy.deployment_alpha,
                fractions=policy.betting_fractions,
            )
            if (
                stream_operation >= policy.minimum_observations
                and deployment_audit["crossed"]
            ):
                deployment_event = deployment_audit
            continue
        if revocation_event is None:
            revocation_count += 1
            revocation_sum += difference - policy.revocation_tolerance
            revocation_audit = _checkpoint(
                operation_count=revocation_count,
                stream_operation=stream_operation,
                cumulative_evidence=revocation_sum,
                width=width,
                alpha=policy.revocation_alpha,
                fractions=policy.betting_fractions,
            )
            if (
                revocation_count
                >= policy.minimum_post_deployment_observations
                and revocation_audit["crossed"]
            ):
                revocation_event = revocation_audit

    approved = deployment_event is not None
    revoked = revocation_event is not None
    if not approved:
        reason = "deployment e-process did not cross; safe baseline retained"
    elif revoked:
        reason = "post-deployment harm e-process crossed; candidate revoked"
    else:
        reason = "deployment e-process crossed and no harm crossing followed"
    return {
        "train_candidate": candidate["name"],
        "safe_baseline": baseline["name"],
        "deployed": (
            candidate["name"] if approved and not revoked else baseline["name"]
        ),
        "candidate_approved": approved,
        "candidate_revoked": revoked,
        "reason": reason,
        "deployment_event": deployment_event,
        "revocation_event": revocation_event,
        "deployment_final_audit": deployment_audit,
        "revocation_final_audit": revocation_audit,
        "monitoring_operations": len(monitoring.operations),
    }


def verify_martingale_safe_autoindex_certificate(certificate: dict) -> dict:
    if (
        not isinstance(certificate, dict)
        or certificate.get("schema")
        != "certigap-martingale-safe-autoindex-v1"
    ):
        raise MartingaleSafeAutoIndexVerificationError(
            "unsupported certificate schema"
        )
    supplied = certificate.get("sha256")
    unsigned = dict(certificate)
    unsigned.pop("sha256", None)
    if supplied != _canonical_sha256(unsigned):
        raise MartingaleSafeAutoIndexVerificationError(
            "certificate digest mismatch"
        )
    base = certificate.get("base_artifact")
    if not isinstance(base, dict):
        raise MartingaleSafeAutoIndexVerificationError(
            "base artifact is missing"
        )
    try:
        verify_autoindex_artifact(base)
    except (TypeError, ValueError) as exc:
        raise MartingaleSafeAutoIndexVerificationError(
            "base AutoIndex artifact does not verify"
        ) from exc

    raw_policy = certificate.get("policy")
    if not isinstance(raw_policy, dict):
        raise MartingaleSafeAutoIndexVerificationError("policy is missing")
    try:
        policy = MartingaleSafeSelectionPolicy(
            deployment_alpha=raw_policy["deployment_alpha"],
            revocation_alpha=raw_policy["revocation_alpha"],
            minimum_observations=raw_policy["minimum_observations"],
            minimum_post_deployment_observations=raw_policy[
                "minimum_post_deployment_observations"
            ],
            horizon_operations=raw_policy["horizon_operations"],
            migration_cost_units=raw_policy["migration_cost_units"],
            build_cost_per_unit=raw_policy["build_cost_per_unit"],
            minimum_improvement=raw_policy["minimum_improvement"],
            revocation_tolerance=raw_policy["revocation_tolerance"],
            betting_fractions=tuple(raw_policy["betting_fractions"]),
            safe_baselines=tuple(raw_policy["safe_baselines"]),
        )
        policy.validate()
    except (KeyError, TypeError, ValueError) as exc:
        raise MartingaleSafeAutoIndexVerificationError(
            "policy does not validate"
        ) from exc
    if policy.manifest() != raw_policy:
        raise MartingaleSafeAutoIndexVerificationError(
            "policy is not canonical"
        )
    try:
        monitoring = _trace(
            base.get("holdout_trace"), base["n"], "monitoring trace"
        )
    except ValueError as exc:
        raise MartingaleSafeAutoIndexVerificationError(
            "monitoring trace does not validate"
        ) from exc
    if monitoring is None:
        raise MartingaleSafeAutoIndexVerificationError(
            "monitoring trace is missing"
        )
    if policy.minimum_observations > len(monitoring.operations):
        raise MartingaleSafeAutoIndexVerificationError(
            "minimum_observations exceeds monitoring length"
        )
    try:
        expected = _expected_decision(base, monitoring, policy)
    except ValueError as exc:
        raise MartingaleSafeAutoIndexVerificationError(
            "decision inputs do not replay"
        ) from exc
    if certificate.get("decision") != expected:
        raise MartingaleSafeAutoIndexVerificationError(
            "martingale decision does not recompute"
        )
    try:
        test = _trace(certificate.get("test_trace"), base["n"], "test trace")
        scores = _test_scores(
            base,
            test,
            (
                expected["train_candidate"],
                expected["safe_baseline"],
                expected["deployed"],
            ),
        )
    except ValueError as exc:
        raise MartingaleSafeAutoIndexVerificationError(
            "test evaluation does not replay"
        ) from exc
    if certificate.get("test_evaluation") != scores:
        raise MartingaleSafeAutoIndexVerificationError(
            "test evaluation does not recompute"
        )
    scope = (
        "mixture Hoeffding e-process deployment and revocation gates for "
        "bounded adapted candidate-minus-baseline costs under their "
        "declared conditional-mean nulls; Ville optional-stopping control; "
        "does not guarantee future safety, unbounded drift, or portable "
        "wall-clock latency"
    )
    if certificate.get("scope") != scope:
        raise MartingaleSafeAutoIndexVerificationError(
            "certificate scope is invalid"
        )
    return {
        "verified": True,
        "selected": expected["deployed"],
        "candidate_approved": expected["candidate_approved"],
        "candidate_revoked": expected["candidate_revoked"],
        "deployment_operation": (
            None
            if expected["deployment_event"] is None
            else expected["deployment_event"]["stream_operation"]
        ),
        "revocation_operation": (
            None
            if expected["revocation_event"] is None
            else expected["revocation_event"]["stream_operation"]
        ),
        "test_score": None if scores is None else scores["deployed_score"],
    }
