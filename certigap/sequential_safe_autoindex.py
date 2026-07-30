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


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class SequentialSafeSelectionPolicy:
    confidence_alpha: float = 0.05
    minimum_observations: int = 1
    horizon_operations: int = 100_000
    migration_cost_units: float = 0.0
    build_cost_per_unit: float = 0.0
    minimum_improvement: float = 0.0
    safe_baselines: tuple[CandidateName, ...] = DEFAULT_SAFE_BASELINES

    def validate(self) -> None:
        if (
            not math.isfinite(self.confidence_alpha)
            or not 0.0 < self.confidence_alpha < 1.0
        ):
            raise ValueError("confidence_alpha must lie in (0,1)")
        if (
            not isinstance(self.minimum_observations, int)
            or isinstance(self.minimum_observations, bool)
            or self.minimum_observations <= 0
        ):
            raise ValueError("minimum_observations must be positive")
        if (
            not isinstance(self.horizon_operations, int)
            or isinstance(self.horizon_operations, bool)
            or self.horizon_operations <= 0
        ):
            raise ValueError("horizon_operations must be positive")
        if any(
            not math.isfinite(value) or value < 0.0
            for value in (
                self.migration_cost_units,
                self.build_cost_per_unit,
                self.minimum_improvement,
            )
        ):
            raise ValueError("safe-selection costs must be finite and non-negative")
        if (
            not self.safe_baselines
            or len(set(self.safe_baselines)) != len(self.safe_baselines)
            or any(name not in PORTFOLIO_ORDER for name in self.safe_baselines)
        ):
            raise ValueError("safe_baselines must be unique portfolio candidates")

    def manifest(self) -> dict:
        return {
            "confidence_alpha": self.confidence_alpha,
            "minimum_observations": self.minimum_observations,
            "horizon_operations": self.horizon_operations,
            "migration_cost_units": self.migration_cost_units,
            "build_cost_per_unit": self.build_cost_per_unit,
            "minimum_improvement": self.minimum_improvement,
            "safe_baselines": list(self.safe_baselines),
        }


def _alpha_at(policy: SequentialSafeSelectionPolicy, operation: int) -> float:
    return policy.confidence_alpha / (operation * (operation + 1))


def _checkpoint(
    *,
    operation: int,
    cumulative_difference: float,
    difference_range_bound: float,
    transition: float,
    policy: SequentialSafeSelectionPolicy,
) -> dict:
    mean = cumulative_difference / operation
    allocated_alpha = _alpha_at(policy, operation)
    radius = difference_range_bound * math.sqrt(
        math.log(1.0 / allocated_alpha) / (2.0 * operation)
    )
    upper = mean + radius + transition
    return {
        "operation_count": operation,
        "allocated_alpha": allocated_alpha,
        "spent_alpha_through_operation": (
            policy.confidence_alpha * operation / (operation + 1)
        ),
        "mean_difference": mean,
        "difference_range_bound": difference_range_bound,
        "confidence_radius": radius,
        "amortized_transition_cost": transition,
        "upper_difference": upper,
    }


def _sequential_decision(
    artifact: dict,
    validation_trace: WorkloadTrace,
    policy: SequentialSafeSelectionPolicy,
) -> dict:
    candidate = next(
        row
        for row in artifact["candidates"]
        if row["name"] == artifact["selected"]
    )
    baseline = _baseline(artifact, policy)
    constraints = AutoIndexConstraints(**artifact["constraints"])
    transition = (
        policy.migration_cost_units
        + policy.build_cost_per_unit * candidate["resources"]["build_units"]
    ) / policy.horizon_operations
    difference_range_bound = _cost_upper_bound(
        candidate, constraints
    ) + _cost_upper_bound(baseline, constraints)
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
                "validation_operations": len(validation_trace.operations),
                "post_stop_operations": len(validation_trace.operations),
            },
        }

    candidate_costs = analytical_candidate_costs(
        artifact, candidate["name"], validation_trace
    )
    baseline_costs = analytical_candidate_costs(
        artifact, baseline["name"], validation_trace
    )
    cumulative = 0.0
    selected_checkpoint: dict | None = None
    final_checkpoint: dict | None = None
    for operation, (candidate_cost, baseline_cost) in enumerate(
        zip(candidate_costs, baseline_costs), start=1
    ):
        cumulative += candidate_cost - baseline_cost
        checkpoint = _checkpoint(
            operation=operation,
            cumulative_difference=cumulative,
            difference_range_bound=difference_range_bound,
            transition=transition,
            policy=policy,
        )
        final_checkpoint = checkpoint
        if (
            selected_checkpoint is None
            and operation >= policy.minimum_observations
            and checkpoint["upper_difference"] < -policy.minimum_improvement
        ):
            selected_checkpoint = checkpoint

    approved = selected_checkpoint is not None
    deployed = candidate["name"] if approved else baseline["name"]
    stopping_operation = (
        None
        if selected_checkpoint is None
        else selected_checkpoint["operation_count"]
    )
    return {
        "train_candidate": candidate["name"],
        "safe_baseline": baseline["name"],
        "deployed": deployed,
        "candidate_approved": approved,
        "reason": (
            "anytime validation bound proves amortized improvement"
            if approved
            else "no validation prefix proved improvement; safe baseline retained"
        ),
        "stopping_operation": stopping_operation,
        "selection_checkpoint": selected_checkpoint,
        "final_audit": final_checkpoint,
        "monitoring": {
            "method": "alpha_spending_hoeffding",
            "allocation": "alpha_t=alpha/(t*(t+1))",
            "total_alpha_budget": policy.confidence_alpha,
            "validation_operations": len(validation_trace.operations),
            "post_stop_operations": (
                0
                if stopping_operation is None
                else len(validation_trace.operations) - stopping_operation
            ),
        },
    }


@dataclass
class SequentialSafeCompiledAutoIndex(SafeCompiledAutoIndex):
    def summary(self) -> dict:
        decision = self.artifact["decision"]
        checkpoint = (
            decision["selection_checkpoint"] or decision["final_audit"]
        )
        return {
            "selected": self.selected_name,
            "train_candidate": decision["train_candidate"],
            "safe_baseline": decision["safe_baseline"],
            "candidate_approved": decision["candidate_approved"],
            "reason": decision["reason"],
            "stopping_operation": decision["stopping_operation"],
            "upper_difference": (
                None if checkpoint is None else checkpoint["upper_difference"]
            ),
        }


def compile_sequential_safe_autoindex(
    values: Iterable[float],
    train_trace: WorkloadTrace,
    validation_trace: WorkloadTrace,
    *,
    test_trace: WorkloadTrace | None = None,
    constraints: AutoIndexConstraints = AutoIndexConstraints(),
    policy: SequentialSafeSelectionPolicy = SequentialSafeSelectionPolicy(),
) -> SafeCompiledAutoIndex:
    if not all(
        isinstance(trace, WorkloadTrace)
        for trace in (train_trace, validation_trace)
    ):
        raise TypeError("train and validation traces must be WorkloadTrace")
    if test_trace is not None and not isinstance(test_trace, WorkloadTrace):
        raise TypeError("test_trace must be WorkloadTrace")
    if not validation_trace.operations:
        raise ValueError("validation trace must not be empty")
    if test_trace is not None and not test_trace.operations:
        raise ValueError("test trace must not be empty")
    if any(
        trace.n != train_trace.n
        for trace in (validation_trace, test_trace)
        if trace is not None
    ):
        raise ValueError("all traces must share one key universe")
    policy.validate()
    if policy.minimum_observations > len(validation_trace.operations):
        raise ValueError("minimum_observations exceeds validation length")
    value_list = [float(value) for value in values]
    model = compile_autoindex(
        value_list,
        train_trace,
        constraints=constraints,
        holdout_trace=validation_trace,
    )
    decision = _sequential_decision(
        model.artifact, validation_trace, policy
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
        "schema": "certigap-sequential-safe-autoindex-v1",
        "base_artifact": model.export_selection_artifact(),
        "policy": policy.manifest(),
        "decision": decision,
        "test_trace": None if test_trace is None else test_trace.to_dict(),
        "test_evaluation": test_evaluation,
        "scope": (
            "one-sided alpha-spending Hoeffding confidence sequence valid "
            "under optional stopping conditional on independent IID bounded "
            "validation operations; post-stop observations and test are "
            "evaluation-only; future drift and wall-clock portability are "
            "not proven"
        ),
    }
    artifact = unsigned | {"sha256": _canonical_sha256(unsigned)}

    from .sequential_safe_autoindex_verifier import (
        verify_sequential_safe_autoindex_certificate,
    )

    verify_sequential_safe_autoindex_certificate(artifact)
    deployed = decision["deployed"]
    runtime = materialize_autoindex_candidate(
        value_list, model.artifact, deployed
    )
    return SequentialSafeCompiledAutoIndex(
        selected_name=deployed,
        runtime=runtime,
        artifact=artifact,
    )
