from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable, Sequence

from .autoindex import WorkloadTrace
from .synthesis import HardwareProfile


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class HybridConstraints:
    max_blocks: int = 16
    max_block_width: int = 64
    tail_weight: float = 0.15
    memory_limit_slots: int | None = None
    memory_weight_ns: float = 0.0

    def validate(self, n: int) -> None:
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
        if (
            not math.isfinite(self.memory_weight_ns)
            or self.memory_weight_ns < 0.0
        ):
            raise ValueError("memory_weight_ns must be finite and non-negative")


class PrefixBlockIndex:
    def __init__(
        self, values: Iterable[float], boundaries: Sequence[int]
    ) -> None:
        self.values = [float(value) for value in values]
        self.boundaries = tuple(int(value) for value in boundaries)
        if (
            not self.values
            or not self.boundaries
            or self.boundaries[-1] != len(self.values)
            or any(
                left >= right
                for left, right in zip(
                    (0, *self.boundaries[:-1]), self.boundaries
                )
            )
            or any(not math.isfinite(value) for value in self.values)
        ):
            raise ValueError("boundaries must strictly partition finite values")
        self.block_for_key = [0] * len(self.values)
        self.local_prefix = [0.0] * len(self.values)
        self.block_prefix = [0.0] * len(self.boundaries)
        left = 1
        blocks_total = 0.0
        for block, right in enumerate(self.boundaries):
            local_total = 0.0
            for key in range(left, right + 1):
                self.block_for_key[key - 1] = block
                local_total += self.values[key - 1]
                self.local_prefix[key - 1] = local_total
            blocks_total += local_total
            self.block_prefix[block] = blocks_total
            left = right + 1

    def _validate_key(self, key: int) -> None:
        if not isinstance(key, int) or isinstance(key, bool) or not 1 <= key <= len(
            self.values
        ):
            raise ValueError("key is outside the key universe")

    def _validate_range(self, left: int, right: int) -> None:
        if (
            not isinstance(left, int)
            or isinstance(left, bool)
            or not isinstance(right, int)
            or isinstance(right, bool)
            or not 1 <= left <= right <= len(self.values)
        ):
            raise ValueError("range is outside the key universe")

    def get(self, key: int) -> float:
        self._validate_key(key)
        return self.values[key - 1]

    def _local_range(self, block: int, left: int, right: int) -> float:
        block_start = 1 if block == 0 else self.boundaries[block - 1] + 1
        before = 0.0 if left == block_start else self.local_prefix[left - 2]
        return self.local_prefix[right - 1] - before

    def range_query(self, left: int, right: int) -> float:
        self._validate_range(left, right)
        left_block = self.block_for_key[left - 1]
        right_block = self.block_for_key[right - 1]
        if left_block == right_block:
            return self._local_range(left_block, left, right)
        result = self._local_range(
            left_block, left, self.boundaries[left_block]
        )
        if right_block > left_block + 1:
            result += (
                self.block_prefix[right_block - 1]
                - self.block_prefix[left_block]
            )
        right_start = (
            1
            if right_block == 0
            else self.boundaries[right_block - 1] + 1
        )
        return result + self._local_range(right_block, right_start, right)

    def point_update(self, key: int, value: float) -> None:
        self._validate_key(key)
        value = float(value)
        if not math.isfinite(value):
            raise ValueError("value must be finite")
        delta = value - self.values[key - 1]
        if delta == 0.0:
            return
        self.values[key - 1] = value
        block = self.block_for_key[key - 1]
        for index in range(key - 1, self.boundaries[block]):
            self.local_prefix[index] += delta
        for index in range(block, len(self.block_prefix)):
            self.block_prefix[index] += delta

    def memory_slots(self) -> int:
        return 3 * len(self.values) + 2 * len(self.boundaries)


def _statistics(trace: WorkloadTrace) -> dict:
    gets = [0] * (trace.n + 1)
    updates = [0] * (trace.n + 1)
    ranges = []
    for operation in trace.operations:
        if operation.kind == "get":
            gets[operation.left] += 1
        elif operation.kind == "update":
            updates[operation.left] += 1
        else:
            ranges.append(operation)
    get_prefix = [0] * (trace.n + 1)
    update_prefix = [0] * (trace.n + 1)
    weighted_update_prefix = [0] * (trace.n + 1)
    for key in range(1, trace.n + 1):
        get_prefix[key] = get_prefix[key - 1] + gets[key]
        update_prefix[key] = update_prefix[key - 1] + updates[key]
        weighted_update_prefix[key] = (
            weighted_update_prefix[key - 1] + key * updates[key]
        )
    crossing_prefix = [[0] * (trace.n + 1) for _ in range(trace.n + 1)]
    for right in range(1, trace.n + 1):
        starts = [0] * (trace.n + 1)
        for operation in ranges:
            if operation.right > right:
                starts[operation.left] += 1
        for key in range(1, trace.n + 1):
            crossing_prefix[right][key] = (
                crossing_prefix[right][key - 1] + starts[key]
            )
    next_update = [trace.n + 1] * (trace.n + 2)
    nearest = trace.n + 1
    for key in range(trace.n, 0, -1):
        if updates[key]:
            nearest = key
        next_update[key] = nearest
    return {
        "get_prefix": get_prefix,
        "update_prefix": update_prefix,
        "weighted_update_prefix": weighted_update_prefix,
        "crossing_prefix": crossing_prefix,
        "next_update": next_update,
    }


def _interval_score(
    trace: WorkloadTrace,
    left: int,
    right: int,
    block_index: int,
    total_blocks: int,
    constraints: HybridConstraints,
    hardware: HardwareProfile,
    statistics: dict | None = None,
) -> tuple[float, float, float]:
    stats = statistics or _statistics(trace)
    get_count = (
        stats["get_prefix"][right] - stats["get_prefix"][left - 1]
    )
    update_count = (
        stats["update_prefix"][right]
        - stats["update_prefix"][left - 1]
    )
    weighted_updates = (
        stats["weighted_update_prefix"][right]
        - stats["weighted_update_prefix"][left - 1]
    )
    crossing_count = (
        stats["crossing_prefix"][right][right]
        - stats["crossing_prefix"][right][left - 1]
    )
    top_suffix = total_blocks - block_index + 1
    crossing_cost = (
        4.0 * hardware.aggregate_read_ns + hardware.combine_ns
    )
    update_sum = (
        update_count
        * (
            hardware.value_write_ns
            + (right + 1 + top_suffix) * hardware.aggregate_write_ns
        )
        - weighted_updates * hardware.aggregate_write_ns
    )
    mean = (
        get_count * hardware.value_read_ns
        + update_sum
        + crossing_count * crossing_cost
    ) / len(trace.operations)
    first_update = stats["next_update"][left]
    maximum_update = (
        hardware.value_write_ns
        + (right - first_update + 1 + top_suffix)
        * hardware.aggregate_write_ns
        if first_update <= right
        else 0.0
    )
    local_maximum = max(
        hardware.value_read_ns if get_count else 0.0,
        maximum_update,
        crossing_cost if crossing_count else 0.0,
    )
    robust = (
        (1.0 - constraints.tail_weight) * mean
        + constraints.tail_weight * local_maximum
        + 2.0 * constraints.memory_weight_ns
    )
    return robust, mean, local_maximum


def _best_for_block_count(
    trace: WorkloadTrace,
    total_blocks: int,
    constraints: HybridConstraints,
    hardware: HardwareProfile,
) -> dict | None:
    n = trace.n
    statistics = _statistics(trace)
    infinity = math.inf
    scores = [[infinity] * (n + 1) for _ in range(total_blocks + 1)]
    paths: list[list[tuple[int, ...] | None]] = [
        [None] * (n + 1) for _ in range(total_blocks + 1)
    ]
    scores[0][0] = 0.0
    paths[0][0] = ()
    for block_index in range(1, total_blocks + 1):
        minimum_right = block_index
        maximum_right = min(
            n,
            block_index * constraints.max_block_width,
            n - (total_blocks - block_index),
        )
        for right in range(minimum_right, maximum_right + 1):
            minimum_left = max(
                block_index,
                right - constraints.max_block_width + 1,
            )
            for left in range(minimum_left, right + 1):
                previous = left - 1
                previous_path = paths[block_index - 1][previous]
                if previous_path is None:
                    continue
                interval = round(
                    _interval_score(
                        trace,
                        left,
                        right,
                        block_index,
                        total_blocks,
                        constraints,
                        hardware,
                        statistics,
                    )[0],
                    12,
                )
                candidate = round(
                    scores[block_index - 1][previous] + interval, 12
                )
                candidate_path = (*previous_path, right)
                if (
                    candidate < scores[block_index][right] - 1e-12
                    or (
                        abs(candidate - scores[block_index][right]) <= 1e-12
                        and (
                            paths[block_index][right] is None
                            or candidate_path < paths[block_index][right]
                        )
                    )
                ):
                    scores[block_index][right] = candidate
                    paths[block_index][right] = candidate_path
    path = paths[total_blocks][n]
    if path is None:
        return None
    memory_slots = 3 * n + 2 * total_blocks
    feasible = (
        constraints.memory_limit_slots is None
        or memory_slots <= constraints.memory_limit_slots
    )
    return {
        "blocks": total_blocks,
        "boundaries": list(path),
        "score": round(scores[total_blocks][n], 12),
        "memory_slots": memory_slots,
        "feasible": feasible,
    }


def synthesize_hybrid_partitions(
    trace: WorkloadTrace,
    constraints: HybridConstraints = HybridConstraints(),
    hardware: HardwareProfile = HardwareProfile(),
) -> list[dict]:
    if not trace.operations:
        raise ValueError("trace must contain at least one operation")
    constraints.validate(trace.n)
    hardware.validate()
    minimum_blocks = math.ceil(trace.n / constraints.max_block_width)
    return [
        candidate
        for blocks in range(minimum_blocks, constraints.max_blocks + 1)
        if (
            candidate := _best_for_block_count(
                trace, blocks, constraints, hardware
            )
        )
        is not None
    ]


class HybridIndex:
    def __init__(self, runtime: PrefixBlockIndex, artifact: dict) -> None:
        self.runtime = runtime
        self.artifact = artifact

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
        if (
            not namespace
            or not namespace.replace("_", "a").isalnum()
            or namespace[0].isdigit()
        ):
            raise ValueError("namespace must be a C++ identifier")
        boundaries = ", ".join(map(str, self.selected_boundaries))
        return (
            "#pragma once\n\n"
            '#include "certigap_synth.hpp"\n\n'
            f"namespace {namespace} {{\n\n"
            "inline certigap::PrefixBlockIndex make_index(\n"
            "    const std::vector<double>& values\n"
            ") {\n"
            f"    return certigap::PrefixBlockIndex(values, {{{boundaries}}});\n"
            "}\n\n"
            f"}}  // namespace {namespace}\n"
        )


def compile_hybrid_index(
    values: Iterable[float],
    trace: WorkloadTrace,
    *,
    constraints: HybridConstraints = HybridConstraints(),
    hardware: HardwareProfile = HardwareProfile(),
) -> HybridIndex:
    value_list = [float(value) for value in values]
    if len(value_list) != trace.n or any(
        not math.isfinite(value) for value in value_list
    ):
        raise ValueError("finite values must match the trace key universe")
    candidates = synthesize_hybrid_partitions(trace, constraints, hardware)
    feasible = [candidate for candidate in candidates if candidate["feasible"]]
    if not feasible:
        raise ValueError("no hybrid partition satisfies constraints")
    selected = min(
        feasible,
        key=lambda row: (
            row["score"],
            row["memory_slots"],
            row["boundaries"],
        ),
    )
    unsigned = {
        "schema": "certigap-hybrid-v1",
        "n": trace.n,
        "trace": trace.to_dict(),
        "constraints": asdict(constraints),
        "hardware": hardware.manifest(),
        "grammar": {
            "layout": "two_level_prefix_sum",
            "partition_space": "all contiguous partitions within declared limits",
            "objective": (
                "exact additive partition-dependent prefix work plus a "
                "certified sum-of-local-maxima tail upper bound; interval "
                "and DP scores use canonical 12-decimal rounding"
            ),
        },
        "candidates": candidates,
        "selected": {
            "blocks": selected["blocks"],
            "boundaries": selected["boundaries"],
        },
        "scope": (
            "exact minimum certified prefix-layout score over every legal "
            "partition in the declared grammar; wall-clock latency is not proven"
        ),
    }
    artifact = unsigned | {"sha256": _canonical_sha256(unsigned)}
    return HybridIndex(
        PrefixBlockIndex(value_list, selected["boundaries"]), artifact
    )
