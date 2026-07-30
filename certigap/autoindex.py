from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Iterable, Literal, Sequence

from .api import solve_with
from .dynamic_range import (
    AggregateName,
    DynamicCertiRange,
    _complete_topology,
)
from .range_optimizer import range_aware_beam_search
from .workload import CertiRangeWorkload


OperationName = Literal["get", "range", "update"]
CandidateName = Literal[
    "sorted_array",
    "prefix_sum",
    "fenwick",
    "sqrt_decomposition",
    "segment_tree",
    "sparse_table",
    "certirange_point",
    "certirange_range",
]

PORTFOLIO_ORDER: tuple[CandidateName, ...] = (
    "sorted_array",
    "prefix_sum",
    "fenwick",
    "sqrt_decomposition",
    "segment_tree",
    "sparse_table",
    "certirange_point",
    "certirange_range",
)


@dataclass(frozen=True)
class TraceOperation:
    kind: OperationName
    left: int
    right: int
    value: float = 0.0

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "left": self.left,
            "right": self.right,
            "value": self.value,
        }


class WorkloadTrace:
    def __init__(self, n: int, operations: Iterable[TraceOperation] = ()) -> None:
        if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
            raise ValueError("n must be a positive integer")
        self.n = n
        self._operations: list[TraceOperation] = []
        for operation in operations:
            self._append(operation)

    @property
    def operations(self) -> tuple[TraceOperation, ...]:
        return tuple(self._operations)

    def _append(self, operation: TraceOperation) -> None:
        if not isinstance(operation, TraceOperation):
            raise TypeError("operation must be a TraceOperation")
        if operation.kind not in {"get", "range", "update"}:
            raise ValueError("unsupported operation kind")
        if not 1 <= operation.left <= operation.right <= self.n:
            raise ValueError("operation interval is outside the key universe")
        if operation.kind in {"get", "update"} and operation.left != operation.right:
            raise ValueError("get/update operations must target one key")
        if not math.isfinite(operation.value):
            raise ValueError("operation value must be finite")
        self._operations.append(operation)

    def add_get(self, key: int) -> "WorkloadTrace":
        self._append(TraceOperation("get", key, key))
        return self

    def add_range(self, left: int, right: int) -> "WorkloadTrace":
        self._append(TraceOperation("range", left, right))
        return self

    def add_update(self, key: int, value: float = 0.0) -> "WorkloadTrace":
        self._append(TraceOperation("update", key, key, float(value)))
        return self

    def chronological_split(
        self, train_fraction: float = 0.75
    ) -> tuple["WorkloadTrace", "WorkloadTrace"]:
        if (
            not math.isfinite(train_fraction)
            or not 0 < train_fraction < 1
            or len(self._operations) < 2
        ):
            raise ValueError(
                "split requires at least two operations and fraction in (0,1)"
            )
        cut = min(
            len(self._operations) - 1,
            max(1, int(len(self._operations) * train_fraction)),
        )
        return (
            WorkloadTrace(self.n, self._operations[:cut]),
            WorkloadTrace(self.n, self._operations[cut:]),
        )

    def aggregate(self) -> CertiRangeWorkload:
        workload = CertiRangeWorkload(self.n)
        for operation in self._operations:
            if operation.kind == "get":
                workload.add_point(operation.left)
            elif operation.kind == "range":
                workload.add_range(operation.left, operation.right)
            else:
                workload.add_update(operation.left)
        return workload

    def to_dict(self) -> dict:
        return {
            "n": self.n,
            "operations": [operation.to_dict() for operation in self._operations],
        }


@dataclass(frozen=True)
class AutoIndexConstraints:
    aggregate: AggregateName = "sum"
    budget: int = 6
    tail_weight: float = 0.10
    memory_limit_slots: int | None = None
    max_depth: int | None = None
    require_persistent_snapshots: bool = False
    memory_weight: float = 0.0
    build_weight: float = 0.0
    array_unit_cost: float = 1.0
    prefix_unit_cost: float = 1.0
    fenwick_unit_cost: float = 1.0
    sqrt_unit_cost: float = 1.0
    segment_tree_unit_cost: float = 1.0
    sparse_unit_cost: float = 1.0
    certirange_unit_cost: float = 1.0
    range_beam_width: int = 8
    range_candidate_limit: int = 12

    def validate(self, n: int) -> None:
        if self.aggregate not in {"sum", "min", "max"}:
            raise ValueError("aggregate must be sum, min, or max")
        if not isinstance(self.budget, int) or isinstance(self.budget, bool) or self.budget < 0:
            raise ValueError("budget must be a non-negative integer")
        if not math.isfinite(self.tail_weight) or not 0 <= self.tail_weight <= 1:
            raise ValueError("tail_weight must lie in [0,1]")
        if self.memory_limit_slots is not None and (
            not isinstance(self.memory_limit_slots, int)
            or isinstance(self.memory_limit_slots, bool)
            or self.memory_limit_slots <= 0
        ):
            raise ValueError("memory_limit_slots must be a positive integer")
        if self.max_depth is not None and (
            not isinstance(self.max_depth, int)
            or isinstance(self.max_depth, bool)
            or self.max_depth < math.ceil(math.log2(n))
        ):
            raise ValueError("max_depth is infeasible")
        if any(
            not math.isfinite(value) or value < 0
            for value in (self.memory_weight, self.build_weight)
        ):
            raise ValueError("cost weights must be finite and non-negative")
        if any(
            not math.isfinite(value) or value <= 0
            for value in (
                self.array_unit_cost,
                self.prefix_unit_cost,
                self.fenwick_unit_cost,
                self.sqrt_unit_cost,
                self.segment_tree_unit_cost,
                self.sparse_unit_cost,
                self.certirange_unit_cost,
            )
        ):
            raise ValueError("candidate unit costs must be finite and positive")
        if self.range_beam_width <= 0 or self.range_candidate_limit < 3:
            raise ValueError("range search limits are invalid")


def _combine(left: float, right: float, aggregate: AggregateName) -> float:
    if aggregate == "sum":
        return left + right
    if aggregate == "min":
        return min(left, right)
    return max(left, right)


class _ArrayIndex:
    supports_snapshots = False

    def __init__(self, values: Sequence[float], aggregate: AggregateName) -> None:
        self.values = list(values)
        self.aggregate = aggregate

    def get(self, key: int) -> float:
        return self.values[key - 1]

    def range_query(self, left: int, right: int) -> float:
        selected = self.values[left - 1 : right]
        if self.aggregate == "sum":
            return sum(selected)
        if self.aggregate == "min":
            return min(selected)
        return max(selected)

    def point_update(self, key: int, value: float) -> None:
        self.values[key - 1] = float(value)


class _FenwickIndex:
    supports_snapshots = False

    def __init__(self, values: Sequence[float]) -> None:
        self.values = list(values)
        self.tree = [0.0] * (len(values) + 1)
        for key, value in enumerate(values, start=1):
            self._add(key, value)

    def _add(self, key: int, delta: float) -> None:
        while key < len(self.tree):
            self.tree[key] += delta
            key += key & -key

    def _prefix(self, key: int) -> float:
        result = 0.0
        while key > 0:
            result += self.tree[key]
            key -= key & -key
        return result

    def get(self, key: int) -> float:
        return self.values[key - 1]

    def range_query(self, left: int, right: int) -> float:
        return self._prefix(right) - self._prefix(left - 1)

    def point_update(self, key: int, value: float) -> None:
        numeric = float(value)
        delta = numeric - self.values[key - 1]
        self.values[key - 1] = numeric
        self._add(key, delta)


class _PrefixSumIndex:
    supports_snapshots = False

    def __init__(self, values: Sequence[float]) -> None:
        self.values = list(values)
        self.prefix = [0.0]
        for value in self.values:
            self.prefix.append(self.prefix[-1] + value)

    def get(self, key: int) -> float:
        return self.values[key - 1]

    def range_query(self, left: int, right: int) -> float:
        return self.prefix[right] - self.prefix[left - 1]

    def point_update(self, key: int, value: float) -> None:
        numeric = float(value)
        delta = numeric - self.values[key - 1]
        self.values[key - 1] = numeric
        for index in range(key, len(self.prefix)):
            self.prefix[index] += delta


class _SqrtIndex:
    supports_snapshots = False

    def __init__(self, values: Sequence[float], aggregate: AggregateName) -> None:
        self.values = list(values)
        self.aggregate = aggregate
        self.block_size = max(1, math.ceil(math.sqrt(len(values))))
        self.blocks = [self._identity()] * math.ceil(
            len(values) / self.block_size
        )
        for block in range(len(self.blocks)):
            self._rebuild_block(block)

    def _identity(self) -> float:
        if self.aggregate == "sum":
            return 0.0
        if self.aggregate == "min":
            return float("inf")
        return float("-inf")

    def _rebuild_block(self, block: int) -> None:
        left = block * self.block_size
        right = min(len(self.values), left + self.block_size)
        result = self._identity()
        for value in self.values[left:right]:
            result = _combine(result, value, self.aggregate)
        self.blocks[block] = result

    def get(self, key: int) -> float:
        return self.values[key - 1]

    def range_query(self, left: int, right: int) -> float:
        index = left - 1
        stop = right
        result = self._identity()
        while index < stop and index % self.block_size:
            result = _combine(result, self.values[index], self.aggregate)
            index += 1
        while index + self.block_size <= stop:
            result = _combine(
                result, self.blocks[index // self.block_size], self.aggregate
            )
            index += self.block_size
        while index < stop:
            result = _combine(result, self.values[index], self.aggregate)
            index += 1
        return result

    def point_update(self, key: int, value: float) -> None:
        self.values[key - 1] = float(value)
        self._rebuild_block((key - 1) // self.block_size)


class _SparseTableIndex:
    supports_snapshots = False

    def __init__(self, values: Sequence[float], aggregate: AggregateName) -> None:
        self.values = list(values)
        self.aggregate = aggregate
        self.logs: list[int] = []
        self.table: list[list[float]] = []
        self._rebuild()

    def _rebuild(self) -> None:
        n = len(self.values)
        self.logs = [0] * (n + 1)
        for length in range(2, n + 1):
            self.logs[length] = self.logs[length // 2] + 1
        self.table = [self.values.copy()]
        level = 1
        while 1 << level <= n:
            width = 1 << level
            half = width >> 1
            previous = self.table[-1]
            self.table.append(
                [
                    _combine(
                        previous[left],
                        previous[left + half],
                        self.aggregate,
                    )
                    for left in range(n - width + 1)
                ]
            )
            level += 1

    def get(self, key: int) -> float:
        return self.values[key - 1]

    def range_query(self, left: int, right: int) -> float:
        level = self.logs[right - left + 1]
        width = 1 << level
        return _combine(
            self.table[level][left - 1],
            self.table[level][right - width],
            self.aggregate,
        )

    def point_update(self, key: int, value: float) -> None:
        self.values[key - 1] = float(value)
        self._rebuild()


class _SegmentIndex:
    supports_snapshots = False

    def __init__(self, values: Sequence[float], aggregate: AggregateName) -> None:
        size = 1
        while size < len(values):
            size *= 2
        identity = 0.0 if aggregate == "sum" else (
            float("inf") if aggregate == "min" else float("-inf")
        )
        self.n = len(values)
        self.size = size
        self.aggregate = aggregate
        self.identity = identity
        self.tree = [identity] * (2 * size)
        self.tree[size : size + len(values)] = values
        for index in range(size - 1, 0, -1):
            self.tree[index] = _combine(
                self.tree[2 * index], self.tree[2 * index + 1], aggregate
            )

    def get(self, key: int) -> float:
        return self.tree[self.size + key - 1]

    def range_query(self, left: int, right: int) -> float:
        left = self.size + left - 1
        right = self.size + right
        result_left = self.identity
        result_right = self.identity
        while left < right:
            if left & 1:
                result_left = _combine(
                    result_left, self.tree[left], self.aggregate
                )
                left += 1
            if right & 1:
                right -= 1
                result_right = _combine(
                    self.tree[right], result_right, self.aggregate
                )
            left //= 2
            right //= 2
        return _combine(result_left, result_right, self.aggregate)

    def point_update(self, key: int, value: float) -> None:
        index = self.size + key - 1
        self.tree[index] = float(value)
        index //= 2
        while index:
            self.tree[index] = _combine(
                self.tree[2 * index],
                self.tree[2 * index + 1],
                self.aggregate,
            )
            index //= 2


def _topology_depths(topology: dict, depth: int = 0) -> list[int]:
    if topology["type"] == "leaf":
        return [depth]
    return _topology_depths(topology["left"], depth + 1) + _topology_depths(
        topology["right"], depth + 1
    )


def _topology_range_visits(topology: dict, left: int, right: int) -> int:
    node_left, node_right = topology["interval"]
    if right < node_left or node_right < left:
        return 1
    if left <= node_left and node_right <= right:
        return 1
    if topology["type"] == "leaf":
        return 1
    return (
        1
        + _topology_range_visits(topology["left"], left, right)
        + _topology_range_visits(topology["right"], left, right)
    )


def _fenwick_prefix_steps(key: int) -> int:
    steps = 0
    while key > 0:
        steps += 1
        key -= key & -key
    return steps


def _fenwick_update_steps(key: int, n: int) -> int:
    steps = 0
    while key <= n:
        steps += 1
        key += key & -key
    return steps


def _segment_range_steps(left: int, right: int, size: int) -> int:
    left = size + left - 1
    right = size + right
    steps = 0
    while left < right:
        if left & 1:
            steps += 1
            left += 1
        if right & 1:
            right -= 1
            steps += 1
        left //= 2
        right //= 2
    return max(1, steps)


def _sqrt_range_steps(left: int, right: int, block_size: int) -> int:
    index = left - 1
    stop = right
    steps = 0
    while index < stop and index % block_size:
        steps += 1
        index += 1
    while index + block_size <= stop:
        steps += 1
        index += block_size
    return steps + stop - index


def _sparse_table_entries(n: int) -> int:
    return sum(n - (1 << level) + 1 for level in range(n.bit_length()))


def _analytical_costs(
    name: CandidateName,
    trace: WorkloadTrace,
    topology: dict | None,
    constraints: AutoIndexConstraints,
) -> list[float]:
    n = trace.n
    size = 1 << math.ceil(math.log2(n)) if n > 1 else 1
    depths = _topology_depths(topology) if topology is not None else []
    unit_cost = {
        "sorted_array": constraints.array_unit_cost,
        "prefix_sum": constraints.prefix_unit_cost,
        "fenwick": constraints.fenwick_unit_cost,
        "sqrt_decomposition": constraints.sqrt_unit_cost,
        "segment_tree": constraints.segment_tree_unit_cost,
        "sparse_table": constraints.sparse_unit_cost,
        "certirange_point": constraints.certirange_unit_cost,
        "certirange_range": constraints.certirange_unit_cost,
    }[name]
    costs: list[float] = []
    for operation in trace.operations:
        if name == "sorted_array":
            cost = (
                1
                if operation.kind in {"get", "update"}
                else operation.right - operation.left + 1
            )
        elif name == "prefix_sum":
            if operation.kind == "get":
                cost = 1
            elif operation.kind == "update":
                cost = n - operation.left + 2
            else:
                cost = 1 if operation.left == 1 else 2
        elif name == "fenwick":
            if operation.kind == "get":
                cost = 1
            elif operation.kind == "update":
                cost = _fenwick_update_steps(operation.left, n)
            else:
                cost = _fenwick_prefix_steps(
                    operation.right
                ) + _fenwick_prefix_steps(operation.left - 1)
                cost = max(1, cost)
        elif name == "sqrt_decomposition":
            block_size = max(1, math.ceil(math.sqrt(n)))
            if operation.kind == "get":
                cost = 1
            elif operation.kind == "update":
                block_start = ((operation.left - 1) // block_size) * block_size
                cost = min(block_size, n - block_start) + 1
            else:
                cost = _sqrt_range_steps(
                    operation.left, operation.right, block_size
                )
        elif name == "segment_tree":
            if operation.kind == "get":
                cost = 1
            elif operation.kind == "update":
                cost = int(math.log2(size)) + 1
            else:
                cost = _segment_range_steps(
                    operation.left, operation.right, size
                )
        elif name == "sparse_table":
            if operation.kind == "get":
                cost = 1
            elif operation.kind == "update":
                cost = _sparse_table_entries(n) + 1
            else:
                cost = 2
        else:
            if topology is None:
                raise RuntimeError("CertiRange candidate has no topology")
            if operation.kind in {"get", "update"}:
                cost = depths[operation.left - 1] + 1
            else:
                cost = _topology_range_visits(
                    topology, operation.left, operation.right
                )
        costs.append(cost * unit_cost)
    return costs


def _candidate_resources(
    name: CandidateName, n: int, topology: dict | None
) -> tuple[int, int, int]:
    size = 1 << math.ceil(math.log2(n)) if n > 1 else 1
    if name == "sorted_array":
        return n, 0, n
    if name == "prefix_sum":
        return 2 * n + 1, 1, n
    if name == "fenwick":
        return 2 * n + 1, int(math.log2(size)), n * int(math.log2(size) + 1)
    if name == "sqrt_decomposition":
        block_size = max(1, math.ceil(math.sqrt(n)))
        blocks = math.ceil(n / block_size)
        return n + blocks, 1, n + blocks
    if name == "segment_tree":
        return 2 * size, int(math.log2(size)), 2 * size
    if name == "sparse_table":
        entries = _sparse_table_entries(n)
        return n + entries, 1, entries
    if topology is None:
        raise RuntimeError("CertiRange candidate has no topology")
    depth = max(_topology_depths(topology))
    return 3 * n - 1, depth, 2 * n - 1


def _score_costs(
    costs: Sequence[float],
    resources: tuple[int, int, int],
    constraints: AutoIndexConstraints,
) -> dict:
    if not costs:
        raise ValueError("trace must contain at least one operation")
    memory_slots, height, build_units = resources
    mean = sum(costs) / len(costs)
    maximum = max(costs)
    structural = (
        (1.0 - constraints.tail_weight) * mean
        + constraints.tail_weight * maximum
    )
    score = (
        structural
        + constraints.memory_weight * memory_slots
        + constraints.build_weight * build_units
    )
    return {
        "mean_primitive_visits": mean,
        "max_primitive_visits": maximum,
        "structural_score": structural,
        "score": score,
        "memory_slots": memory_slots,
        "height": height,
        "build_units": build_units,
        "operation_count": len(costs),
    }


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def _workload_routing(
    trace: WorkloadTrace,
    constraints: AutoIndexConstraints,
) -> tuple[dict, dict]:
    workload = trace.aggregate()
    weights = workload.routing_weights()
    point_result = solve_with(
        weights, constraints.budget, constraints.tail_weight, "beam"
    )
    point_tree = point_result["serialized_tree"]
    minimum = 0 if trace.n <= 1 else math.ceil(math.log2(trace.n))
    max_depth = constraints.max_depth or (2 * minimum + 1)
    range_result = range_aware_beam_search(
        point_counts=workload.point_counts,
        update_counts=workload.update_counts,
        range_counts=[
            (left, right, count)
            for (left, right), count in workload.range_counts.items()
        ],
        budget=constraints.budget,
        max_depth=max_depth,
        tail_weight=constraints.tail_weight,
        beam_width=constraints.range_beam_width,
        candidate_limit=constraints.range_candidate_limit,
    )
    return point_tree, range_result["routing_tree"]


def _candidate_feasibility(
    name: CandidateName,
    resources: tuple[int, int, int],
    constraints: AutoIndexConstraints,
) -> tuple[bool, str]:
    memory_slots, height, _ = resources
    reasons: list[str] = []
    if name in {"fenwick", "prefix_sum"} and constraints.aggregate != "sum":
        reasons.append(f"{name} supports sum only")
    if name == "sparse_table" and constraints.aggregate == "sum":
        reasons.append("sparse_table supports idempotent min/max only")
    if constraints.require_persistent_snapshots and not name.startswith(
        "certirange"
    ):
        reasons.append("persistent snapshots required")
    if (
        constraints.memory_limit_slots is not None
        and memory_slots > constraints.memory_limit_slots
    ):
        reasons.append("memory limit exceeded")
    if constraints.max_depth is not None and height > constraints.max_depth:
        reasons.append("depth limit exceeded")
    return (not reasons, "feasible" if not reasons else "; ".join(reasons))


@dataclass
class CompiledAutoIndex:
    selected_name: CandidateName
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
        selected = next(
            row
            for row in self.artifact["candidates"]
            if row["name"] == self.selected_name
        )
        return {
            "selected": self.selected_name,
            "train_score": selected["train"]["score"],
            "holdout_score": (
                None
                if selected["holdout"] is None
                else selected["holdout"]["score"]
            ),
            "memory_slots": selected["resources"]["memory_slots"],
            "height": selected["resources"]["height"],
            "selection_scope": self.artifact["scope"],
        }

    def export_selection_artifact(self) -> dict:
        return json.loads(json.dumps(self.artifact))


def _runtime_for_candidate(
    values: Sequence[float],
    name: CandidateName,
    artifact: dict,
) -> object:
    constraints = AutoIndexConstraints(**artifact["constraints"])
    if name == "sorted_array":
        return _ArrayIndex(values, constraints.aggregate)
    if name == "prefix_sum":
        return _PrefixSumIndex(values)
    if name == "fenwick":
        return _FenwickIndex(values)
    if name == "sqrt_decomposition":
        return _SqrtIndex(values, constraints.aggregate)
    if name == "segment_tree":
        return _SegmentIndex(values, constraints.aggregate)
    if name == "sparse_table":
        return _SparseTableIndex(values, constraints.aggregate)

    selected = next(
        row for row in artifact["candidates"] if row["name"] == name
    )
    minimum = 0 if artifact["n"] <= 1 else math.ceil(math.log2(artifact["n"]))
    max_depth = constraints.max_depth or (2 * minimum + 1)
    trace = WorkloadTrace(
        artifact["n"],
        (
            TraceOperation(**operation)
            for operation in artifact["train_trace"]["operations"]
        ),
    )
    workload = trace.aggregate()
    return DynamicCertiRange().fit(
        values,
        weights=workload.routing_weights(),
        budget=constraints.budget,
        eta=constraints.tail_weight,
        aggregate=constraints.aggregate,
        max_depth=max_depth,
        routing_tree=selected["routing_tree"],
        routing_label=name,
    )


def materialize_autoindex_candidate(
    values: Iterable[float],
    artifact: dict,
    name: CandidateName,
) -> object:
    """Build one feasible candidate from a verified AutoIndex artifact."""
    from .autoindex_verifier import verify_autoindex_artifact

    verify_autoindex_artifact(artifact)
    if name not in PORTFOLIO_ORDER:
        raise ValueError("candidate is outside the verified portfolio")
    candidate = next(
        row for row in artifact["candidates"] if row["name"] == name
    )
    if not candidate["feasible"]:
        raise ValueError(f"candidate is infeasible: {candidate['reason']}")
    value_list = [float(value) for value in values]
    if len(value_list) != artifact["n"] or any(
        not math.isfinite(value) for value in value_list
    ):
        raise ValueError("finite values must match the artifact key universe")
    return _runtime_for_candidate(value_list, name, artifact)


def analytical_candidate_costs(
    artifact: dict,
    name: CandidateName,
    trace: WorkloadTrace,
) -> tuple[float, ...]:
    """Replay per-operation structural costs for one verified candidate."""
    from .autoindex_verifier import verify_autoindex_artifact

    verify_autoindex_artifact(artifact)
    if not isinstance(trace, WorkloadTrace):
        raise TypeError("trace must be WorkloadTrace")
    if trace.n != artifact["n"] or not trace.operations:
        raise ValueError("trace must be non-empty and match the key universe")
    if name not in PORTFOLIO_ORDER:
        raise ValueError("candidate is outside the verified portfolio")
    row = next(
        candidate for candidate in artifact["candidates"]
        if candidate["name"] == name
    )
    if not row["feasible"]:
        raise ValueError(f"candidate is infeasible: {row['reason']}")
    constraints = AutoIndexConstraints(**artifact["constraints"])
    topology = None
    if name.startswith("certirange"):
        minimum = 0 if trace.n <= 1 else math.ceil(math.log2(trace.n))
        max_depth = constraints.max_depth or (2 * minimum + 1)
        topology = _complete_topology(
            row["routing_tree"], 1, trace.n, max_depth
        )
    return tuple(_analytical_costs(name, trace, topology, constraints))


def compile_autoindex(
    values: Iterable[float],
    train_trace: WorkloadTrace,
    *,
    constraints: AutoIndexConstraints = AutoIndexConstraints(),
    holdout_trace: WorkloadTrace | None = None,
) -> CompiledAutoIndex:
    if not isinstance(train_trace, WorkloadTrace):
        raise TypeError("train_trace must be a WorkloadTrace")
    if holdout_trace is not None and not isinstance(
        holdout_trace, WorkloadTrace
    ):
        raise TypeError("holdout_trace must be a WorkloadTrace")
    if not isinstance(constraints, AutoIndexConstraints):
        raise TypeError("constraints must be AutoIndexConstraints")
    value_list = [float(value) for value in values]
    if len(value_list) != train_trace.n or not value_list:
        raise ValueError("values and trace key universe must match")
    if any(not math.isfinite(value) for value in value_list):
        raise ValueError("values must be finite")
    if not train_trace.operations:
        raise ValueError("training trace must not be empty")
    if holdout_trace is not None and holdout_trace.n != train_trace.n:
        raise ValueError("holdout key universe differs from training")
    constraints.validate(train_trace.n)
    point_tree, range_tree = _workload_routing(train_trace, constraints)
    minimum = 0 if train_trace.n <= 1 else math.ceil(math.log2(train_trace.n))
    max_depth = constraints.max_depth or (2 * minimum + 1)
    topologies = {
        "certirange_point": _complete_topology(
            point_tree, 1, train_trace.n, max_depth
        ),
        "certirange_range": _complete_topology(
            range_tree, 1, train_trace.n, max_depth
        ),
    }
    routing_trees = {
        "certirange_point": point_tree,
        "certirange_range": range_tree,
    }
    candidates: list[dict] = []
    for name in PORTFOLIO_ORDER:
        topology = topologies.get(name)
        resources = _candidate_resources(name, train_trace.n, topology)
        feasible, reason = _candidate_feasibility(
            name, resources, constraints
        )
        train = _score_costs(
            _analytical_costs(name, train_trace, topology, constraints),
            resources,
            constraints,
        )
        holdout = (
            None
            if holdout_trace is None or not holdout_trace.operations
            else _score_costs(
                _analytical_costs(
                    name, holdout_trace, topology, constraints
                ),
                resources,
                constraints,
            )
        )
        candidates.append(
            {
                "name": name,
                "feasible": feasible,
                "reason": reason,
                "capabilities": {
                    "aggregates": (
                        ["sum"]
                        if name in {"fenwick", "prefix_sum"}
                        else (
                            ["min", "max"]
                            if name == "sparse_table"
                            else ["sum", "min", "max"]
                        )
                    ),
                    "persistent_snapshots": name.startswith("certirange"),
                },
                "resources": {
                    "memory_slots": resources[0],
                    "height": resources[1],
                    "build_units": resources[2],
                },
                "train": train,
                "holdout": holdout,
                "routing_tree": routing_trees.get(name),
                "topology_sha256": (
                    None
                    if topology is None
                    else _canonical_sha256(topology)
                ),
            }
        )
    feasible_rows = [row for row in candidates if row["feasible"]]
    if not feasible_rows:
        raise ValueError("no portfolio candidate satisfies the constraints")
    selected = min(
        feasible_rows,
        key=lambda row: (
            row["train"]["score"],
            row["resources"]["memory_slots"],
            PORTFOLIO_ORDER.index(row["name"]),
        ),
    )
    manifest = {
        "schema": "certigap-autoindex-v2",
        "scope": (
            "minimum declared analytical score over the complete deterministic "
            "eight-candidate portfolio; holdout is evaluation-only"
        ),
        "metric": {
            "unit": "declared_weighted_primitive_work",
            "warning": (
                "defaults are uncalibrated structural visits, not nanoseconds; "
                "set candidate unit costs from target-system measurements"
            ),
        },
        "n": train_trace.n,
        "constraints": asdict(constraints),
        "train_trace": train_trace.to_dict(),
        "holdout_trace": (
            None if holdout_trace is None else holdout_trace.to_dict()
        ),
        "portfolio_order": list(PORTFOLIO_ORDER),
        "candidates": candidates,
        "selected": selected["name"],
    }
    manifest["sha256"] = _canonical_sha256(manifest)

    runtime = _runtime_for_candidate(value_list, selected["name"], manifest)

    from .autoindex_verifier import verify_autoindex_artifact

    verify_autoindex_artifact(manifest)
    return CompiledAutoIndex(
        selected_name=selected["name"],
        runtime=runtime,
        artifact=manifest,
    )
