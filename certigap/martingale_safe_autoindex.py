from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Iterable

from .autoindex import (
    PORTFOLIO_ORDER,
    AutoIndexConstraints,
    CandidateName,
    WorkloadTrace,
    analytical_candidate_costs,
    compile_autoindex,
    materialize_autoindex_candidate,
)
from .safe_autoindex import (
    DEFAULT_SAFE_BASELINES,
    SafeCompiledAutoIndex,
    _baseline,
    _cost_upper_bound,
    _test_evaluation,
)


DEFAULT_BETTING_FRACTIONS = (0.125, 0.25, 0.5, 1.0, 2.0)


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class MartingaleSafeSelectionPolicy:
    deployment_alpha: float = 0.05
    revocation_alpha: float = 0.05
    minimum_observations: int = 1
    minimum_post_deployment_observations: int = 1
    horizon_operations: int = 100_000
    migration_cost_units: float = 0.0
    build_cost_per_unit: float = 0.0
    minimum_improvement: float = 0.0
    revocation_tolerance: float = 0.0
    betting_fractions: tuple[float, ...] = DEFAULT_BETTING_FRACTIONS
    safe_baselines: tuple[CandidateName, ...] = DEFAULT_SAFE_BASELINES

    def validate(self) -> None:
        for label, value in (
            ("deployment_alpha", self.deployment_alpha),
            ("revocation_alpha", self.revocation_alpha),
        ):
            if not math.isfinite(value) or not 0.0 < value < 1.0:
                raise ValueError(f"{label} must lie in (0,1)")
        for label, value in (
            ("minimum_observations", self.minimum_observations),
            (
                "minimum_post_deployment_observations",
                self.minimum_post_deployment_observations,
            ),
            ("horizon_operations", self.horizon_operations),
        ):
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise ValueError(f"{label} must be positive")
        if any(
            not math.isfinite(value) or value < 0.0
            for value in (
                self.migration_cost_units,
                self.build_cost_per_unit,
                self.minimum_improvement,
                self.revocation_tolerance,
            )
        ):
            raise ValueError("policy costs and tolerances must be non-negative")
        if (
            not self.betting_fractions
            or len(set(self.betting_fractions))
            != len(self.betting_fractions)
            or any(
                not math.isfinite(value) or value <= 0.0
                for value in self.betting_fractions
            )
        ):
            raise ValueError("betting_fractions must be unique and positive")
        if (
            not self.safe_baselines
            or len(set(self.safe_baselines)) != len(self.safe_baselines)
            or any(name not in PORTFOLIO_ORDER for name in self.safe_baselines)
        ):
            raise ValueError("safe_baselines must be unique portfolio candidates")

    def manifest(self) -> dict:
        return {
            "deployment_alpha": self.deployment_alpha,
            "revocation_alpha": self.revocation_alpha,
            "minimum_observations": self.minimum_observations,
            "minimum_post_deployment_observations": (
                self.minimum_post_deployment_observations
            ),
            "horizon_operations": self.horizon_operations,
            "migration_cost_units": self.migration_cost_units,
            "build_cost_per_unit": self.build_cost_per_unit,
            "minimum_improvement": self.minimum_improvement,
            "revocation_tolerance": self.revocation_tolerance,
            "betting_fractions": list(self.betting_fractions),
            "safe_baselines": list(self.safe_baselines),
        }


def _log_mixture_e_value(
    cumulative_evidence: float,
    operation_count: int,
    width: float,
    betting_fractions: tuple[float, ...],
) -> float:
    log_weight = -math.log(len(betting_fractions))
    terms = [
        log_weight
        + (fraction / width) * cumulative_evidence
        - fraction * fraction * operation_count / 8.0
        for fraction in betting_fractions
    ]
    maximum = max(terms)
    return maximum + math.log(sum(math.exp(term - maximum) for term in terms))


def _checkpoint(
    *,
    operation_count: int,
    stream_operation: int,
    cumulative_evidence: float,
    width: float,
    alpha: float,
    betting_fractions: tuple[float, ...],
) -> dict:
    log_e_value = _log_mixture_e_value(
        cumulative_evidence,
        operation_count,
        width,
        betting_fractions,
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


def _martingale_decision(
    artifact: dict,
    monitoring_trace: WorkloadTrace,
    policy: MartingaleSafeSelectionPolicy,
) -> dict:
    candidate = next(
        row
        for row in artifact["candidates"]
        if row["name"] == artifact["selected"]
    )
    baseline = _baseline(artifact, policy)
    same = candidate["name"] == baseline["name"]
    if same:
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
            "monitoring_operations": len(monitoring_trace.operations),
        }

    constraints = AutoIndexConstraints(**artifact["constraints"])
    width = _cost_upper_bound(
        candidate, constraints
    ) + _cost_upper_bound(baseline, constraints)
    transition = (
        policy.migration_cost_units
        + policy.build_cost_per_unit * candidate["resources"]["build_units"]
    ) / policy.horizon_operations
    candidate_costs = analytical_candidate_costs(
        artifact, candidate["name"], monitoring_trace
    )
    baseline_costs = analytical_candidate_costs(
        artifact, baseline["name"], monitoring_trace
    )

    deployment_event = None
    revocation_event = None
    deployment_audit = None
    revocation_audit = None
    deployment_sum = 0.0
    revocation_sum = 0.0
    revocation_count = 0
    for stream_operation, (candidate_cost, baseline_cost) in enumerate(
        zip(candidate_costs, baseline_costs), start=1
    ):
        difference = candidate_cost - baseline_cost
        if deployment_event is None:
            # Positive evidence rejects the null that specialization has no
            # conditional expected advantage after transition costs.
            deployment_sum += -(
                difference + transition + policy.minimum_improvement
            )
            deployment_audit = _checkpoint(
                operation_count=stream_operation,
                stream_operation=stream_operation,
                cumulative_evidence=deployment_sum,
                width=width,
                alpha=policy.deployment_alpha,
                betting_fractions=policy.betting_fractions,
            )
            if (
                stream_operation >= policy.minimum_observations
                and deployment_audit["crossed"]
            ):
                deployment_event = deployment_audit
            continue

        if revocation_event is None:
            revocation_count += 1
            # Positive evidence rejects the null that the deployed candidate
            # is conditionally no worse than the declared tolerance.
            revocation_sum += difference - policy.revocation_tolerance
            revocation_audit = _checkpoint(
                operation_count=revocation_count,
                stream_operation=stream_operation,
                cumulative_evidence=revocation_sum,
                width=width,
                alpha=policy.revocation_alpha,
                betting_fractions=policy.betting_fractions,
            )
            if (
                revocation_count
                >= policy.minimum_post_deployment_observations
                and revocation_audit["crossed"]
            ):
                revocation_event = revocation_audit

    approved = deployment_event is not None
    revoked = revocation_event is not None
    deployed = (
        candidate["name"] if approved and not revoked else baseline["name"]
    )
    if not approved:
        reason = "deployment e-process did not cross; safe baseline retained"
    elif revoked:
        reason = "post-deployment harm e-process crossed; candidate revoked"
    else:
        reason = "deployment e-process crossed and no harm crossing followed"
    return {
        "train_candidate": candidate["name"],
        "safe_baseline": baseline["name"],
        "deployed": deployed,
        "candidate_approved": approved,
        "candidate_revoked": revoked,
        "reason": reason,
        "deployment_event": deployment_event,
        "revocation_event": revocation_event,
        "deployment_final_audit": deployment_audit,
        "revocation_final_audit": revocation_audit,
        "monitoring_operations": len(monitoring_trace.operations),
    }


@dataclass
class MartingaleSafeCompiledAutoIndex(SafeCompiledAutoIndex):
    def summary(self) -> dict:
        decision = self.artifact["decision"]
        return {
            "selected": self.selected_name,
            "train_candidate": decision["train_candidate"],
            "safe_baseline": decision["safe_baseline"],
            "candidate_approved": decision["candidate_approved"],
            "candidate_revoked": decision["candidate_revoked"],
            "reason": decision["reason"],
            "deployment_operation": (
                None
                if decision["deployment_event"] is None
                else decision["deployment_event"]["stream_operation"]
            ),
            "revocation_operation": (
                None
                if decision["revocation_event"] is None
                else decision["revocation_event"]["stream_operation"]
            ),
        }


def compile_martingale_safe_autoindex(
    values: Iterable[float],
    train_trace: WorkloadTrace,
    monitoring_trace: WorkloadTrace,
    *,
    test_trace: WorkloadTrace | None = None,
    constraints: AutoIndexConstraints = AutoIndexConstraints(),
    policy: MartingaleSafeSelectionPolicy = MartingaleSafeSelectionPolicy(),
) -> MartingaleSafeCompiledAutoIndex:
    if not all(
        isinstance(trace, WorkloadTrace)
        for trace in (train_trace, monitoring_trace)
    ):
        raise TypeError("train and monitoring traces must be WorkloadTrace")
    if test_trace is not None and not isinstance(test_trace, WorkloadTrace):
        raise TypeError("test_trace must be WorkloadTrace")
    if not monitoring_trace.operations:
        raise ValueError("monitoring trace must not be empty")
    if test_trace is not None and not test_trace.operations:
        raise ValueError("test trace must not be empty")
    if any(
        trace.n != train_trace.n
        for trace in (monitoring_trace, test_trace)
        if trace is not None
    ):
        raise ValueError("all traces must share one key universe")
    policy.validate()
    if policy.minimum_observations > len(monitoring_trace.operations):
        raise ValueError("minimum_observations exceeds monitoring length")
    value_list = [float(value) for value in values]
    model = compile_autoindex(
        value_list,
        train_trace,
        constraints=constraints,
        holdout_trace=monitoring_trace,
    )
    decision = _martingale_decision(
        model.artifact, monitoring_trace, policy
    )
    test_evaluation = _test_evaluation(
        train_trace,
        test_trace,
        constraints,
        decision["train_candidate"],
        decision["safe_baseline"],
        decision["deployed"],
    )
    unsigned = {
        "schema": "certigap-martingale-safe-autoindex-v1",
        "base_artifact": model.export_selection_artifact(),
        "policy": policy.manifest(),
        "decision": decision,
        "test_trace": None if test_trace is None else test_trace.to_dict(),
        "test_evaluation": test_evaluation,
        "scope": (
            "mixture Hoeffding e-process deployment and revocation gates for "
            "bounded adapted candidate-minus-baseline costs under their "
            "declared conditional-mean nulls; Ville optional-stopping control; "
            "does not guarantee future safety, unbounded drift, or portable "
            "wall-clock latency"
        ),
    }
    artifact = unsigned | {"sha256": _canonical_sha256(unsigned)}

    from .martingale_safe_autoindex_verifier import (
        verify_martingale_safe_autoindex_certificate,
    )

    verify_martingale_safe_autoindex_certificate(artifact)
    deployed = decision["deployed"]
    runtime = materialize_autoindex_candidate(
        value_list, model.artifact, deployed
    )
    return MartingaleSafeCompiledAutoIndex(
        selected_name=deployed,
        runtime=runtime,
        artifact=artifact,
    )
