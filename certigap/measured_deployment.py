from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import time
from copy import deepcopy
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from .autoindex import (
    CompiledAutoIndex,
    WorkloadTrace,
    materialize_autoindex_candidate,
)
from .dynamic_range import DynamicCertiRange
from .measured_deployment_verifier import verify_measured_deployment_artifact
from .spec import AdaptiveSpec, compile_from_spec


@dataclass(frozen=True)
class MeasuredDeploymentPolicy:
    alpha: float = 0.05
    minimum_normalized_improvement: float = 0.0
    repetitions: int = 64
    warmup_repetitions: int = 3
    amortization_operations: int = 100_000
    baseline: str = "sorted_array"

    def validate(self) -> None:
        if not math.isfinite(self.alpha) or not 0.0 < self.alpha < 1.0:
            raise ValueError("alpha must lie in (0,1)")
        if (
            not math.isfinite(self.minimum_normalized_improvement)
            or not 0.0 <= self.minimum_normalized_improvement < 1.0
        ):
            raise ValueError("minimum improvement must lie in [0,1)")
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0
            for value in (self.repetitions, self.amortization_operations)
        ):
            raise ValueError("measurement counts must be positive integers")
        if (
            not isinstance(self.warmup_repetitions, int)
            or isinstance(self.warmup_repetitions, bool)
            or self.warmup_repetitions < 0
        ):
            raise ValueError("warmup_repetitions must be a non-negative integer")
        if not isinstance(self.baseline, str) or not self.baseline:
            raise ValueError("baseline must be a candidate name")


@dataclass
class MeasuredCompiledAutoIndex:
    selected_name: str
    candidate_name: str
    baseline_name: str
    runtime: object
    artifact: dict

    def _key(self, key: int) -> None:
        if (
            not isinstance(key, int)
            or isinstance(key, bool)
            or not 1 <= key <= int(self.artifact["n"])
        ):
            raise ValueError("key rank out of range")

    def get(self, key: int) -> float:
        self._key(key)
        return float(_runtime_get(self.runtime, key))

    def range_query(self, left: int, right: int) -> float:
        self._key(left)
        self._key(right)
        if left > right:
            raise ValueError("range must satisfy left <= right")
        return float(_runtime_range_query(self.runtime, left, right))

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

    @property
    def candidate_deployed(self) -> bool:
        return bool(self.artifact["decision"]["candidate_deployed"])

    def explain(self) -> dict:
        return json.loads(json.dumps(self.artifact["decision"]))

    def export_certificate(self) -> dict:
        return json.loads(json.dumps(self.artifact))


def paired_latency_decision(
    pairs_ns: Sequence[tuple[int, int]],
    policy: MeasuredDeploymentPolicy,
) -> dict:
    policy.validate()
    if len(pairs_ns) != policy.repetitions:
        raise ValueError("paired latency count differs from policy")
    harms: list[float] = []
    for baseline_ns, candidate_ns in pairs_ns:
        if (
            not isinstance(baseline_ns, int)
            or isinstance(baseline_ns, bool)
            or not isinstance(candidate_ns, int)
            or isinstance(candidate_ns, bool)
            or baseline_ns <= 0
            or candidate_ns <= 0
        ):
            raise ValueError("paired latencies must be positive integer nanoseconds")
        harms.append(
            (candidate_ns - baseline_ns) / max(candidate_ns, baseline_ns)
        )
    mean_harm = sum(harms) / len(harms)
    radius = math.sqrt(2.0 * math.log(1.0 / policy.alpha) / len(harms))
    upper_bound = min(1.0, mean_harm + radius)
    deployed = (
        upper_bound
        <= -policy.minimum_normalized_improvement + 1e-15
    )
    return {
        "candidate_deployed": deployed,
        "sample_count": len(harms),
        "mean_normalized_harm": mean_harm,
        "hoeffding_radius": radius,
        "upper_normalized_harm": upper_bound,
        "required_upper_bound": -policy.minimum_normalized_improvement,
        "reason": (
            "paired measured upper bound passed"
            if deployed
            else "paired measured upper bound did not pass"
        ),
    }


def _runtime_get(runtime: object, key: int) -> float:
    if isinstance(runtime, DynamicCertiRange):
        return float(runtime.get(key, track=False))
    return float(runtime.get(key))


def _runtime_range_query(runtime: object, left: int, right: int) -> float:
    if isinstance(runtime, DynamicCertiRange):
        return float(runtime.range_query(left, right, track=False))
    return float(runtime.range_query(left, right))


def _replay(runtime: object, trace: WorkloadTrace) -> float:
    checksum = 0.0
    for operation in trace.operations:
        if operation.kind == "get":
            checksum += _runtime_get(runtime, operation.left)
        elif operation.kind == "range":
            checksum += _runtime_range_query(
                runtime, operation.left, operation.right
            )
        else:
            runtime.point_update(operation.left, operation.value)
            checksum += _runtime_get(runtime, operation.left)
    return checksum


def _measure_pairs(
    baseline_prototype: object,
    candidate_prototype: object,
    trace: WorkloadTrace,
    policy: MeasuredDeploymentPolicy,
    migration_penalty_ns: int,
) -> list[tuple[int, int]]:
    pairs: list[tuple[int, int]] = []
    total_repetitions = policy.warmup_repetitions + policy.repetitions
    per_batch_penalty = math.ceil(
        migration_penalty_ns
        * len(trace.operations)
        / policy.amortization_operations
    )
    for repetition in range(total_repetitions):
        baseline_runtime = deepcopy(baseline_prototype)
        candidate_runtime = deepcopy(candidate_prototype)
        runtimes = (
            (("baseline", baseline_runtime), ("candidate", candidate_runtime))
            if repetition % 2 == 0
            else (("candidate", candidate_runtime), ("baseline", baseline_runtime))
        )
        elapsed: dict[str, int] = {}
        checksums: dict[str, float] = {}
        for name, runtime in runtimes:
            started = time.perf_counter_ns()
            checksums[name] = _replay(runtime, trace)
            elapsed[name] = max(1, time.perf_counter_ns() - started)
        if not math.isclose(
            checksums["baseline"],
            checksums["candidate"],
            rel_tol=1e-10,
            abs_tol=1e-8,
        ):
            raise RuntimeError("candidate differs from baseline during shadow replay")
        if repetition >= policy.warmup_repetitions:
            pairs.append(
                (
                    elapsed["baseline"],
                    elapsed["candidate"] + per_batch_penalty,
                )
            )
    return pairs


def _build_latency(
    values: list[float], artifact: dict, candidate: str
) -> tuple[object, int]:
    started = time.perf_counter_ns()
    runtime = materialize_autoindex_candidate(values, artifact, candidate)
    return runtime, max(1, time.perf_counter_ns() - started)


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def compile_measured_autoindex(
    values: Iterable[float],
    train_trace: WorkloadTrace,
    validation_trace: WorkloadTrace,
    spec: AdaptiveSpec,
    *,
    policy: MeasuredDeploymentPolicy = MeasuredDeploymentPolicy(),
) -> MeasuredCompiledAutoIndex:
    if not isinstance(spec, AdaptiveSpec):
        raise TypeError("spec must be AdaptiveSpec")
    if not isinstance(policy, MeasuredDeploymentPolicy):
        raise TypeError("policy must be MeasuredDeploymentPolicy")
    policy.validate()
    value_list = [float(value) for value in values]
    spec.validate_trace(validation_trace, role="validation")
    if validation_trace.n != train_trace.n or not validation_trace.operations:
        raise ValueError("validation trace must be non-empty and match training")
    compiled: CompiledAutoIndex = compile_from_spec(
        value_list, train_trace, spec
    )
    autoindex_artifact = compiled.export_selection_artifact()
    candidate = compiled.selected_name
    baseline_row = next(
        (
            row
            for row in autoindex_artifact["candidates"]
            if row["name"] == policy.baseline
        ),
        None,
    )
    if baseline_row is None or not baseline_row["feasible"]:
        raise ValueError("declared measured baseline is absent or infeasible")

    baseline_runtime, baseline_build_ns = _build_latency(
        value_list, autoindex_artifact, policy.baseline
    )
    candidate_runtime, candidate_build_ns = _build_latency(
        value_list, autoindex_artifact, candidate
    )
    migration_penalty_ns = max(0, candidate_build_ns - baseline_build_ns)
    pairs: list[tuple[int, int]] = []
    if candidate == policy.baseline:
        decision = {
            "candidate_deployed": False,
            "sample_count": 0,
            "mean_normalized_harm": 0.0,
            "hoeffding_radius": 0.0,
            "upper_normalized_harm": 0.0,
            "required_upper_bound": -policy.minimum_normalized_improvement,
            "reason": "structural winner is the measured baseline",
        }
    else:
        pairs = _measure_pairs(
            baseline_runtime,
            candidate_runtime,
            validation_trace,
            policy,
            migration_penalty_ns,
        )
        decision = paired_latency_decision(pairs, policy)

    selected = candidate if decision["candidate_deployed"] else policy.baseline
    runtime = candidate_runtime if selected == candidate else baseline_runtime
    artifact = {
        "schema": "certigap-measured-deployment-v1",
        "n": len(value_list),
        "candidate": candidate,
        "baseline": policy.baseline,
        "selected": selected,
        "spec": spec.to_dict(),
        "policy": asdict(policy),
        "validation_trace": validation_trace.to_dict(),
        "build_latency_ns": {
            "baseline": baseline_build_ns,
            "candidate": candidate_build_ns,
            "migration_penalty": migration_penalty_ns,
        },
        "paired_batch_latency_ns": [
            {"baseline": baseline, "candidate": candidate_ns}
            for baseline, candidate_ns in pairs
        ],
        "decision": decision,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "processor": platform.processor(),
            "pid": os.getpid(),
            "timer": "time.perf_counter_ns",
        },
        "autoindex_artifact": autoindex_artifact,
        "claim_boundary": (
            "The Hoeffding gate controls mean bounded normalized paired harm "
            "under the declared independent representative-repetition model. "
            "It does not certify p99 latency, future drift, or other hardware."
        ),
    }
    artifact["sha256"] = _canonical_sha256(artifact)
    verify_measured_deployment_artifact(artifact)
    return MeasuredCompiledAutoIndex(
        selected_name=selected,
        candidate_name=candidate,
        baseline_name=policy.baseline,
        runtime=runtime,
        artifact=artifact,
    )
