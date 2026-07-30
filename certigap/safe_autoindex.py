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
    compile_autoindex,
    materialize_autoindex_candidate,
)
from .dynamic_range import DynamicCertiRange


DEFAULT_SAFE_BASELINES: tuple[CandidateName, ...] = (
    "sorted_array",
    "fenwick",
    "segment_tree",
)


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class SafeSelectionPolicy:
    confidence_alpha: float = 0.05
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
            "horizon_operations": self.horizon_operations,
            "migration_cost_units": self.migration_cost_units,
            "build_cost_per_unit": self.build_cost_per_unit,
            "minimum_improvement": self.minimum_improvement,
            "safe_baselines": list(self.safe_baselines),
        }


def _row(artifact: dict, name: str) -> dict:
    return next(row for row in artifact["candidates"] if row["name"] == name)


def _baseline(artifact: dict, policy: SafeSelectionPolicy) -> dict:
    feasible = [
        row
        for row in artifact["candidates"]
        if row["feasible"] and row["name"] in policy.safe_baselines
    ]
    if not feasible:
        raise ValueError("no declared safe baseline satisfies the constraints")
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
    }[name]
    return float(getattr(constraints, field))


def _cost_upper_bound(row: dict, constraints: AutoIndexConstraints) -> float:
    # Every current backend performs at most build_units + 1 primitive actions
    # for one supported operation. This deliberately loose bound keeps the
    # statistical gate valid across all eight implementations.
    return (row["resources"]["build_units"] + 1) * _unit_cost(
        row["name"], constraints
    )


def _test_evaluation(
    train_trace: WorkloadTrace,
    test_trace: WorkloadTrace | None,
    constraints: AutoIndexConstraints,
    candidate_name: str,
    baseline_name: str,
    deployed_name: str,
) -> dict | None:
    if test_trace is None:
        return None
    evaluated = compile_autoindex(
        [0.0] * train_trace.n,
        train_trace,
        constraints=constraints,
        holdout_trace=test_trace,
    ).artifact

    def score(name: str) -> float:
        holdout = _row(evaluated, name)["holdout"]
        if holdout is None:
            raise RuntimeError("test evaluation is missing")
        return float(holdout["score"])

    return {
        "operation_count": len(test_trace.operations),
        "candidate_score": score(candidate_name),
        "baseline_score": score(baseline_name),
        "deployed_score": score(deployed_name),
        "selection_independent": True,
    }


def _selection_decision(
    artifact: dict,
    policy: SafeSelectionPolicy,
) -> dict:
    candidate = _row(artifact, artifact["selected"])
    baseline = _baseline(artifact, policy)
    candidate_validation = candidate["holdout"]
    baseline_validation = baseline["holdout"]
    if candidate_validation is None or baseline_validation is None:
        raise ValueError("validation trace must not be empty")
    operation_count = int(candidate_validation["operation_count"])
    constraints = AutoIndexConstraints(**artifact["constraints"])
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
    amortized_transition = (
        policy.migration_cost_units
        + policy.build_cost_per_unit * candidate["resources"]["build_units"]
    ) / policy.horizon_operations
    upper_difference = (
        mean_difference + confidence_radius + amortized_transition
    )
    same_as_baseline = candidate["name"] == baseline["name"]
    approved = same_as_baseline or (
        upper_difference < -policy.minimum_improvement
    )
    deployed = candidate["name"] if approved else baseline["name"]
    if same_as_baseline:
        reason = "training winner is already the declared safe baseline"
    elif approved:
        reason = "validation upper bound proves amortized improvement"
    else:
        reason = "insufficient validation evidence; safe baseline retained"
    return {
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
            "amortized_transition_cost": amortized_transition,
            "upper_difference": upper_difference,
        },
    }


@dataclass
class SafeCompiledAutoIndex:
    selected_name: CandidateName
    runtime: object
    artifact: dict

    def _key(self, key: int) -> None:
        n = int(self.artifact["base_artifact"]["n"])
        if (
            not isinstance(key, int)
            or isinstance(key, bool)
            or not 1 <= key <= n
        ):
            raise ValueError("key rank out of range")

    def get(self, key: int) -> float:
        self._key(key)
        if isinstance(self.runtime, DynamicCertiRange):
            return self.runtime.get(key, track=False)
        return self.runtime.get(key)

    def range_query(self, left: int, right: int) -> float:
        self._key(left)
        self._key(right)
        if left > right:
            raise ValueError("range must satisfy left <= right")
        if isinstance(self.runtime, DynamicCertiRange):
            return self.runtime.range_query(left, right, track=False)
        return self.runtime.range_query(left, right)

    def point_update(self, key: int, value: float) -> None:
        self._key(key)
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("value must be finite")
        self.runtime.point_update(key, numeric)

    def snapshot(self):
        if not isinstance(self.runtime, DynamicCertiRange):
            raise RuntimeError(
                f"{self.selected_name} does not provide persistent snapshots"
            )
        return self.runtime.snapshot()

    def summary(self) -> dict:
        decision = self.artifact["decision"]
        return {
            "selected": self.selected_name,
            "train_candidate": decision["train_candidate"],
            "safe_baseline": decision["safe_baseline"],
            "candidate_approved": decision["candidate_approved"],
            "reason": decision["reason"],
            "validation_upper_difference": decision["validation"][
                "upper_difference"
            ],
        }

    def export_certificate(self) -> dict:
        return json.loads(json.dumps(self.artifact))


def compile_safe_autoindex(
    values: Iterable[float],
    train_trace: WorkloadTrace,
    validation_trace: WorkloadTrace,
    *,
    test_trace: WorkloadTrace | None = None,
    constraints: AutoIndexConstraints = AutoIndexConstraints(),
    policy: SafeSelectionPolicy = SafeSelectionPolicy(),
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
    value_list = [float(value) for value in values]
    model = compile_autoindex(
        value_list,
        train_trace,
        constraints=constraints,
        holdout_trace=validation_trace,
    )
    decision = _selection_decision(model.artifact, policy)
    test_evaluation = _test_evaluation(
        train_trace,
        test_trace,
        constraints,
        decision["train_candidate"],
        decision["safe_baseline"],
        decision["deployed"],
    )
    unsigned = {
        "schema": "certigap-safe-autoindex-v1",
        "base_artifact": model.export_selection_artifact(),
        "policy": policy.manifest(),
        "decision": decision,
        "test_trace": None if test_trace is None else test_trace.to_dict(),
        "test_evaluation": test_evaluation,
        "scope": (
            "one-sided Hoeffding no-regression gate conditional on independent "
            "IID bounded validation operations; test is evaluation-only; "
            "wall-clock portability and arbitrary temporal drift are not proven"
        ),
    }
    artifact = unsigned | {"sha256": _canonical_sha256(unsigned)}

    from .safe_autoindex_verifier import verify_safe_autoindex_certificate

    verify_safe_autoindex_certificate(artifact)
    deployed = decision["deployed"]
    runtime = materialize_autoindex_candidate(
        value_list, model.artifact, deployed
    )
    return SafeCompiledAutoIndex(
        selected_name=deployed,
        runtime=runtime,
        artifact=artifact,
    )
