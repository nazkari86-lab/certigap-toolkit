from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from .autoindex import TraceOperation, WorkloadTrace
from .dynamic_range import AggregateName


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class HardwareProfile:
    """Measured primitive costs used conditionally by the verifier."""

    name: str = "structural-unit-profile"
    value_read_ns: float = 1.0
    aggregate_read_ns: float = 1.0
    combine_ns: float = 1.0
    value_write_ns: float = 1.0
    aggregate_write_ns: float = 1.0
    sample_count: int = 1

    def validate(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise ValueError("hardware profile name must not be empty")
        costs = (
            self.value_read_ns,
            self.aggregate_read_ns,
            self.combine_ns,
            self.value_write_ns,
            self.aggregate_write_ns,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in costs):
            raise ValueError("hardware primitive costs must be finite and positive")
        if (
            not isinstance(self.sample_count, int)
            or isinstance(self.sample_count, bool)
            or self.sample_count <= 0
        ):
            raise ValueError("sample_count must be a positive integer")

    def manifest(self) -> dict:
        self.validate()
        payload = asdict(self)
        return payload | {"sha256": _canonical_sha256(payload)}


@dataclass(frozen=True)
class SynthesisConstraints:
    aggregate: AggregateName = "sum"
    max_blocks: int = 8
    max_block_width: int = 64
    tail_weight: float = 0.10
    memory_limit_slots: int | None = None
    memory_weight_ns: float = 0.0
    build_weight_ns: float = 0.0

    def validate(self, n: int) -> None:
        if self.aggregate not in {"sum", "min", "max"}:
            raise ValueError("aggregate must be sum, min, or max")
        for name, value in (
            ("max_blocks", self.max_blocks),
            ("max_block_width", self.max_block_width),
        ):
            if (
                not isinstance(value, int)
                or isinstance(value, bool)
                or value <= 0
            ):
                raise ValueError(f"{name} must be a positive integer")
        if self.max_blocks * self.max_block_width < n:
            raise ValueError("grammar cannot cover the key universe")
        if (
            not math.isfinite(self.tail_weight)
            or not 0.0 <= self.tail_weight <= 1.0
        ):
            raise ValueError("tail_weight must lie in [0,1]")
        if self.memory_limit_slots is not None and (
            not isinstance(self.memory_limit_slots, int)
            or isinstance(self.memory_limit_slots, bool)
            or self.memory_limit_slots <= 0
        ):
            raise ValueError("memory_limit_slots must be positive")
        if any(
            not math.isfinite(value) or value < 0.0
            for value in (self.memory_weight_ns, self.build_weight_ns)
        ):
            raise ValueError("resource weights must be finite and non-negative")


def _combine(left: float, right: float, aggregate: AggregateName) -> float:
    if aggregate == "sum":
        return left + right
    if aggregate == "min":
        return min(left, right)
    return max(left, right)


def _identity(aggregate: AggregateName) -> float:
    if aggregate == "sum":
        return 0.0
    if aggregate == "min":
        return math.inf
    return -math.inf


def _block_contribution(
    operation: TraceOperation,
    left: int,
    right: int,
    aggregate: AggregateName,
    profile: HardwareProfile,
) -> float:
    if operation.right < left or right < operation.left:
        return 0.0
    width = right - left + 1
    if operation.kind == "get":
        return profile.value_read_ns
    if operation.kind == "update":
        if aggregate == "sum":
            return (
                profile.value_read_ns
                + profile.value_write_ns
                + profile.aggregate_write_ns
            )
        return (
            profile.value_write_ns
            + width * (profile.value_read_ns + profile.combine_ns)
            + profile.aggregate_write_ns
        )
    if operation.left <= left and right <= operation.right:
        return profile.aggregate_read_ns + profile.combine_ns
    overlap = min(right, operation.right) - max(left, operation.left) + 1
    return overlap * (profile.value_read_ns + profile.combine_ns)


def _interval_score(
    trace: WorkloadTrace,
    left: int,
    right: int,
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> tuple[float, float, float]:
    costs = [
        _block_contribution(
            operation,
            left,
            right,
            constraints.aggregate,
            profile,
        )
        for operation in trace.operations
    ]
    mean = sum(costs) / len(costs)
    local_maximum = max(costs)
    robust = (
        (1.0 - constraints.tail_weight) * mean
        + constraints.tail_weight * local_maximum
        + 2.0 * constraints.memory_weight_ns
        + (right - left + 2) * constraints.build_weight_ns
    )
    return robust, mean, local_maximum


def _partition_operation_costs(
    trace: WorkloadTrace,
    boundaries: Sequence[int],
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> list[float]:
    result: list[float] = []
    for operation in trace.operations:
        total = 0.0
        left = 1
        for right in boundaries:
            total += _block_contribution(
                operation,
                left,
                right,
                constraints.aggregate,
                profile,
            )
            left = right + 1
        result.append(total)
    return result


def _candidate_row(
    trace: WorkloadTrace,
    boundaries: Sequence[int],
    certified_score: float,
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> dict:
    costs = _partition_operation_costs(
        trace, boundaries, constraints, profile
    )
    blocks = len(boundaries)
    memory_slots = 2 * trace.n + 2 * blocks
    build_units = trace.n + blocks
    feasible = (
        constraints.memory_limit_slots is None
        or memory_slots <= constraints.memory_limit_slots
    )
    return {
        "blocks": blocks,
        "boundaries": list(boundaries),
        "feasible": feasible,
        "reason": "feasible" if feasible else "memory limit exceeded",
        "resources": {
            "memory_slots": memory_slots,
            "build_units": build_units,
            "max_block_width": max(
                right - left + 1
                for left, right in zip(
                    (1, *(boundary + 1 for boundary in boundaries[:-1])),
                    boundaries,
                )
            ),
        },
        "train": {
            "mean_ns": round(sum(costs) / len(costs), 12),
            "max_ns": round(max(costs), 12),
            "certified_robust_upper_ns": round(certified_score, 12),
            "operation_count": len(costs),
        },
    }


def synthesize_partitions(
    trace: WorkloadTrace,
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> list[dict]:
    """Return the exact DP optimum for every feasible block count."""

    if not isinstance(trace, WorkloadTrace) or not trace.operations:
        raise ValueError("a nonempty WorkloadTrace is required")
    constraints.validate(trace.n)
    profile.validate()
    n = trace.n
    max_blocks = min(constraints.max_blocks, n)
    interval: dict[tuple[int, int], float] = {}
    for right in range(1, n + 1):
        for left in range(
            max(1, right - constraints.max_block_width + 1), right + 1
        ):
            interval[(left, right)] = _interval_score(
                trace, left, right, constraints, profile
            )[0]

    infinity = float("inf")
    dp = [[infinity] * (n + 1) for _ in range(max_blocks + 1)]
    paths: list[list[tuple[int, ...] | None]] = [
        [None] * (n + 1) for _ in range(max_blocks + 1)
    ]
    dp[0][0] = 0.0
    paths[0][0] = ()
    rows: list[dict] = []
    for blocks in range(1, max_blocks + 1):
        for right in range(1, n + 1):
            lower = max(blocks - 1, right - constraints.max_block_width)
            for previous in range(lower, right):
                prior_path = paths[blocks - 1][previous]
                if prior_path is None:
                    continue
                score = dp[blocks - 1][previous] + interval[
                    (previous + 1, right)
                ]
                path = prior_path + (right,)
                if (
                    score < dp[blocks][right] - 1e-12
                    or (
                        abs(score - dp[blocks][right]) <= 1e-12
                        and (paths[blocks][right] is None or path < paths[blocks][right])
                    )
                ):
                    dp[blocks][right] = score
                    paths[blocks][right] = path
        if paths[blocks][n] is not None:
            rows.append(
                _candidate_row(
                    trace,
                    paths[blocks][n] or (),
                    dp[blocks][n],
                    constraints,
                    profile,
                )
            )
    return rows


class VariableBlockIndex:
    supports_snapshots = False

    def __init__(
        self,
        values: Sequence[float],
        boundaries: Sequence[int],
        aggregate: AggregateName,
    ) -> None:
        self.values = [float(value) for value in values]
        self.boundaries = list(boundaries)
        self.aggregate = aggregate
        if (
            not self.values
            or any(not math.isfinite(value) for value in self.values)
            or not self.boundaries
            or any(
                not isinstance(boundary, int)
                or isinstance(boundary, bool)
                for boundary in self.boundaries
            )
            or self.boundaries[0] < 1
            or self.boundaries[-1] != len(self.values)
            or any(
                left >= right
                for left, right in zip(self.boundaries, self.boundaries[1:])
            )
        ):
            raise ValueError("boundaries must strictly partition all values")
        self.block_for_key = [0] * len(self.values)
        self.aggregates: list[float] = []
        left = 1
        for block, right in enumerate(self.boundaries):
            for key in range(left, right + 1):
                self.block_for_key[key - 1] = block
            self.aggregates.append(self._aggregate(left, right))
            left = right + 1

    def _aggregate(self, left: int, right: int) -> float:
        result = _identity(self.aggregate)
        for value in self.values[left - 1 : right]:
            result = _combine(result, value, self.aggregate)
        return result

    def get(self, key: int) -> float:
        if (
            not isinstance(key, int)
            or isinstance(key, bool)
            or not 1 <= key <= len(self.values)
        ):
            raise ValueError("key out of range")
        return self.values[key - 1]

    def range_query(self, left: int, right: int) -> float:
        if (
            not isinstance(left, int)
            or isinstance(left, bool)
            or not isinstance(right, int)
            or isinstance(right, bool)
            or not 1 <= left <= right <= len(self.values)
        ):
            raise ValueError("invalid range")
        result = _identity(self.aggregate)
        block = self.block_for_key[left - 1]
        block_left = 1 if block == 0 else self.boundaries[block - 1] + 1
        while block < len(self.boundaries) and block_left <= right:
            block_right = self.boundaries[block]
            if left <= block_left and block_right <= right:
                result = _combine(
                    result, self.aggregates[block], self.aggregate
                )
            else:
                for key in range(max(left, block_left), min(right, block_right) + 1):
                    result = _combine(
                        result, self.values[key - 1], self.aggregate
                    )
            block += 1
            block_left = block_right + 1
        return result

    def point_update(self, key: int, value: float) -> None:
        if (
            not isinstance(key, int)
            or isinstance(key, bool)
            or not 1 <= key <= len(self.values)
        ):
            raise ValueError("key out of range")
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("value must be finite")
        block = self.block_for_key[key - 1]
        old = self.values[key - 1]
        self.values[key - 1] = numeric
        if self.aggregate == "sum":
            self.aggregates[block] += numeric - old
        else:
            left = 1 if block == 0 else self.boundaries[block - 1] + 1
            self.aggregates[block] = self._aggregate(
                left, self.boundaries[block]
            )


@dataclass
class SynthesizedIndex:
    runtime: VariableBlockIndex
    artifact: dict

    @property
    def selected_boundaries(self) -> tuple[int, ...]:
        return tuple(self.artifact["selected"]["boundaries"])

    def get(self, key: int) -> float:
        return self.runtime.get(key)

    def range_query(self, left: int, right: int) -> float:
        return self.runtime.range_query(left, right)

    def point_update(self, key: int, value: float) -> None:
        self.runtime.point_update(key, value)

    def export_certificate(self) -> dict:
        return json.loads(json.dumps(self.artifact))

    def render_cpp_header(self, namespace: str = "certigap_generated") -> str:
        from .synthesis_verifier import verify_synthesis_certificate

        verify_synthesis_certificate(self.artifact)
        if (
            not namespace
            or not namespace.replace("_", "a").isalnum()
            or namespace[0].isdigit()
        ):
            raise ValueError("namespace must be a C++ identifier")
        aggregate = {
            "sum": "Sum",
            "min": "Min",
            "max": "Max",
        }[self.artifact["constraints"]["aggregate"]]
        boundaries = ", ".join(
            str(value) for value in self.artifact["selected"]["boundaries"]
        )
        return (
            "#pragma once\n\n"
            '#include "certigap_synth.hpp"\n\n'
            f"namespace {namespace} {{\n\n"
            "inline certigap::VariableBlockIndex make_index(\n"
            "    const std::vector<double>& values\n"
            ") {\n"
            "    return certigap::VariableBlockIndex(\n"
            f"        values, {{{boundaries}}}, "
            f"certigap::Aggregate::{aggregate}\n"
            "    );\n"
            "}\n\n"
            "inline constexpr std::string_view certificate_sha256() {\n"
            f'    return "{self.artifact["sha256"]}";\n'
            "}\n\n"
            f"}}  // namespace {namespace}\n"
        )


def compile_synthesized_index(
    values: Iterable[float],
    trace: WorkloadTrace,
    *,
    constraints: SynthesisConstraints = SynthesisConstraints(),
    hardware: HardwareProfile = HardwareProfile(),
) -> SynthesizedIndex:
    value_list = [float(value) for value in values]
    if len(value_list) != trace.n or any(
        not math.isfinite(value) for value in value_list
    ):
        raise ValueError("finite values must match the trace key universe")
    candidates = synthesize_partitions(trace, constraints, hardware)
    feasible = [row for row in candidates if row["feasible"]]
    if not feasible:
        raise ValueError("no synthesized partition satisfies constraints")
    selected = min(
        feasible,
        key=lambda row: (
            row["train"]["certified_robust_upper_ns"],
            row["resources"]["memory_slots"],
            row["boundaries"],
        ),
    )
    unsigned = {
        "schema": "certigap-synthesis-v1",
        "n": trace.n,
        "trace": trace.to_dict(),
        "constraints": asdict(constraints),
        "hardware": hardware.manifest(),
        "grammar": {
            "family": "variable_block_aggregate",
            "partition_space": "all contiguous partitions within declared limits",
            "objective": (
                "sum of per-block ((1-tail)*mean + tail*local-max) "
                "plus declared resource penalties"
            ),
            "actual_max_relation": (
                "sum of local maxima upper-bounds maximum whole-operation cost"
            ),
        },
        "candidates": candidates,
        "selected": {
            "blocks": selected["blocks"],
            "boundaries": selected["boundaries"],
        },
        "scope": (
            "exact minimum certified robust upper score over every legal "
            "variable-block partition in the declared grammar; hardware "
            "measurements are treated as supplied conditions"
        ),
    }
    artifact = unsigned | {"sha256": _canonical_sha256(unsigned)}
    return SynthesizedIndex(
        runtime=VariableBlockIndex(
            value_list, selected["boundaries"], constraints.aggregate
        ),
        artifact=artifact,
    )


def migration_decision(
    *,
    current_ns_per_operation: float,
    proposed_ns_per_operation: float,
    rebuild_ns: float,
    horizon_operations: int,
    confidence_margin_ns: float = 0.0,
) -> dict:
    values = (
        current_ns_per_operation,
        proposed_ns_per_operation,
        rebuild_ns,
        confidence_margin_ns,
    )
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("migration costs must be finite and non-negative")
    if (
        not isinstance(horizon_operations, int)
        or isinstance(horizon_operations, bool)
        or horizon_operations <= 0
    ):
        raise ValueError("horizon_operations must be positive")
    gross_savings = (
        current_ns_per_operation - proposed_ns_per_operation
    ) * horizon_operations
    required = rebuild_ns + confidence_margin_ns
    payload = {
        "schema": "certigap-migration-v1",
        "gross_savings_ns": gross_savings,
        "required_savings_ns": required,
        "migrate": gross_savings > required,
        "horizon_operations": horizon_operations,
    }
    return payload | {"sha256": _canonical_sha256(payload)}
