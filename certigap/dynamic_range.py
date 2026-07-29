from __future__ import annotations

import hashlib
import json
import math
import threading
from dataclasses import dataclass
from typing import Iterable, Literal, Sequence

from .api import SolverName, solve_with
from .core import normalize_weights


AggregateName = Literal["sum", "min", "max"]


@dataclass(frozen=True)
class RangeNode:
    left: int
    right: int
    aggregate: float
    left_child: "RangeNode | None" = None
    right_child: "RangeNode | None" = None

    @property
    def is_leaf(self) -> bool:
        return self.left == self.right

    @property
    def threshold(self) -> int:
        if self.left_child is None:
            return self.left
        return self.left_child.right


@dataclass(frozen=True)
class RangeSnapshot:
    root: RangeNode
    aggregate: AggregateName
    data_version: int
    structure_version: int
    height: int

    def get(self, key: int) -> float:
        _validate_key(key, self.root.right)
        node = self.root
        while not node.is_leaf:
            if node.left_child is None or node.right_child is None:
                raise RuntimeError("corrupt range tree")
            node = node.left_child if key <= node.threshold else node.right_child
        return node.aggregate

    def range_query(self, left: int, right: int) -> float:
        _validate_range(left, right, self.root.right)
        value, _ = _range_query(self.root, left, right, self.aggregate)
        if value is None:
            raise RuntimeError("range query produced an empty result")
        return value


def _validate_values(values: Iterable[float]) -> list[float]:
    result = [float(value) for value in values]
    if not result:
        raise ValueError("values must be non-empty")
    if any(not math.isfinite(value) for value in result):
        raise ValueError("values must be finite")
    return result


def _validate_key(key: int, n: int) -> None:
    if not isinstance(key, int) or isinstance(key, bool) or not 1 <= key <= n:
        raise ValueError("key rank out of range")


def _validate_range(left: int, right: int, n: int) -> None:
    if (
        not isinstance(left, int)
        or isinstance(left, bool)
        or not isinstance(right, int)
        or isinstance(right, bool)
        or not 1 <= left <= right <= n
    ):
        raise ValueError("range must satisfy 1 <= left <= right <= n")


def _combine(left: float, right: float, aggregate: AggregateName) -> float:
    if aggregate == "sum":
        return left + right
    if aggregate == "min":
        return min(left, right)
    if aggregate == "max":
        return max(left, right)
    raise ValueError(f"unknown aggregate: {aggregate}")


def _minimum_height(size: int) -> int:
    return 0 if size <= 1 else math.ceil(math.log2(size))


def _build_balanced_topology(left: int, right: int) -> dict:
    if left == right:
        return {"type": "leaf", "interval": [left, right]}
    threshold = (left + right) // 2
    return {
        "type": "split",
        "interval": [left, right],
        "threshold": threshold,
        "left": _build_balanced_topology(left, threshold),
        "right": _build_balanced_topology(threshold + 1, right),
    }


def _complete_topology(spec: dict, left: int, right: int, remaining_depth: int) -> dict:
    if not isinstance(spec, dict) or spec.get("interval") != [left, right]:
        raise ValueError("routing tree interval does not match its parent")
    if left == right:
        if spec.get("type") != "leaf":
            raise ValueError("singleton routing node must be a leaf")
        return {"type": "leaf", "interval": [left, right]}
    if remaining_depth < _minimum_height(right - left + 1):
        raise ValueError("max_depth is too small for the key count")
    if spec.get("type") == "leaf":
        return _build_balanced_topology(left, right)
    if spec.get("type") != "split":
        raise ValueError("routing tree node type is invalid")
    threshold = spec.get("threshold")
    if not isinstance(threshold, int) or isinstance(threshold, bool) or not left <= threshold < right:
        raise ValueError("routing split threshold is invalid")
    left_size = threshold - left + 1
    right_size = right - threshold
    split_fits = (
        remaining_depth > 0
        and _minimum_height(left_size) <= remaining_depth - 1
        and _minimum_height(right_size) <= remaining_depth - 1
    )
    if not split_fits:
        return _build_balanced_topology(left, right)
    return {
        "type": "split",
        "interval": [left, right],
        "threshold": threshold,
        "left": _complete_topology(spec.get("left"), left, threshold, remaining_depth - 1),
        "right": _complete_topology(
            spec.get("right"), threshold + 1, right, remaining_depth - 1
        ),
    }


def _materialize(topology: dict, values: Sequence[float], aggregate: AggregateName) -> RangeNode:
    left, right = topology["interval"]
    if topology["type"] == "leaf":
        return RangeNode(left=left, right=right, aggregate=float(values[left - 1]))
    left_child = _materialize(topology["left"], values, aggregate)
    right_child = _materialize(topology["right"], values, aggregate)
    return RangeNode(
        left=left,
        right=right,
        aggregate=_combine(left_child.aggregate, right_child.aggregate, aggregate),
        left_child=left_child,
        right_child=right_child,
    )


def _serialize_topology(node: RangeNode) -> dict:
    if node.is_leaf:
        return {"type": "leaf", "interval": [node.left, node.right]}
    if node.left_child is None or node.right_child is None:
        raise RuntimeError("corrupt range tree")
    return {
        "type": "split",
        "interval": [node.left, node.right],
        "threshold": node.threshold,
        "left": _serialize_topology(node.left_child),
        "right": _serialize_topology(node.right_child),
    }


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _height(node: RangeNode) -> int:
    if node.is_leaf:
        return 0
    if node.left_child is None or node.right_child is None:
        raise RuntimeError("corrupt range tree")
    return 1 + max(_height(node.left_child), _height(node.right_child))


def _node_count(node: RangeNode) -> int:
    if node.is_leaf:
        return 1
    if node.left_child is None or node.right_child is None:
        raise RuntimeError("corrupt range tree")
    return 1 + _node_count(node.left_child) + _node_count(node.right_child)


def _leaf_depths(node: RangeNode, depth: int = 0) -> list[int]:
    if node.is_leaf:
        return [depth]
    if node.left_child is None or node.right_child is None:
        raise RuntimeError("corrupt range tree")
    return _leaf_depths(node.left_child, depth + 1) + _leaf_depths(
        node.right_child, depth + 1
    )


def _point_update(
    node: RangeNode, key: int, value: float, aggregate: AggregateName
) -> RangeNode:
    if node.is_leaf:
        return RangeNode(left=key, right=key, aggregate=value)
    if node.left_child is None or node.right_child is None:
        raise RuntimeError("corrupt range tree")
    if key <= node.threshold:
        left_child = _point_update(node.left_child, key, value, aggregate)
        right_child = node.right_child
    else:
        left_child = node.left_child
        right_child = _point_update(node.right_child, key, value, aggregate)
    return RangeNode(
        left=node.left,
        right=node.right,
        aggregate=_combine(left_child.aggregate, right_child.aggregate, aggregate),
        left_child=left_child,
        right_child=right_child,
    )


def _range_query(
    node: RangeNode, query_left: int, query_right: int, aggregate: AggregateName
) -> tuple[float | None, int]:
    if query_right < node.left or node.right < query_left:
        return None, 1
    if query_left <= node.left and node.right <= query_right:
        return node.aggregate, 1
    if node.left_child is None or node.right_child is None:
        return node.aggregate, 1
    left_value, left_visits = _range_query(
        node.left_child, query_left, query_right, aggregate
    )
    right_value, right_visits = _range_query(
        node.right_child, query_left, query_right, aggregate
    )
    if left_value is None:
        return right_value, 1 + left_visits + right_visits
    if right_value is None:
        return left_value, 1 + left_visits + right_visits
    return (
        _combine(left_value, right_value, aggregate),
        1 + left_visits + right_visits,
    )


def _total_variation(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        raise ValueError("distributions must have equal length")
    left_normalized = normalize_weights(left)
    right_normalized = normalize_weights(right)
    return 0.5 * sum(
        abs(a - b) for a, b in zip(left_normalized, right_normalized)
    )


class DynamicCertiRange:
    """Persistent workload-adaptive ordered range index.

    The CertiGap solver chooses a partial routing tree. Every unresolved leaf is
    completed with a midpoint tree, yielding exact point and range operations.
    Updates path-copy immutable nodes, so previously acquired snapshots remain
    consistent while a new root is published atomically.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._root: RangeNode | None = None
        self._values: list[float] = []
        self._fit_weights: list[float] = []
        self._observed_counts: list[float] = []
        self._routing_tree: dict | None = None
        self._solver_result: dict | None = None
        self._aggregate: AggregateName = "sum"
        self._solver: SolverName = "beam"
        self._routing_label = "beam"
        self._budget = 0
        self._requested_budget = 0
        self._eta = 0.0
        self._max_depth = 0
        self._drift_threshold = 0.10
        self._min_rebuild_observations = 32.0
        self._range_endpoint_weight = 1.0
        self._data_version = 0
        self._structure_version = 0
        self._rebuild_count = 0
        self._point_queries = 0
        self._range_queries = 0
        self._updates = 0
        self._last_range_node_visits = 0

    def fit(
        self,
        values: Iterable[float],
        *,
        weights: Iterable[float] | None = None,
        budget: int,
        eta: float = 0.15,
        solver: SolverName = "beam",
        aggregate: AggregateName = "sum",
        max_depth: int | None = None,
        drift_threshold: float = 0.10,
        min_rebuild_observations: float = 32.0,
        range_endpoint_weight: float = 1.0,
        routing_tree: dict | None = None,
        routing_label: str | None = None,
    ) -> "DynamicCertiRange":
        value_list = _validate_values(values)
        n = len(value_list)
        weight_list = (
            [1.0] * n if weights is None else [float(weight) for weight in weights]
        )
        normalized = normalize_weights(weight_list)
        if aggregate not in {"sum", "min", "max"}:
            raise ValueError("aggregate must be one of: sum, min, max")
        if not isinstance(budget, int) or isinstance(budget, bool) or budget < 0:
            raise ValueError("budget must be a non-negative integer")
        if not math.isfinite(drift_threshold) or not 0 <= drift_threshold <= 1:
            raise ValueError("drift_threshold must lie in [0, 1]")
        if (
            not math.isfinite(min_rebuild_observations)
            or min_rebuild_observations <= 0
        ):
            raise ValueError("min_rebuild_observations must be positive")
        if not math.isfinite(range_endpoint_weight) or range_endpoint_weight < 0:
            raise ValueError("range_endpoint_weight must be non-negative")
        minimum_depth = _minimum_height(n)
        chosen_max_depth = max_depth if max_depth is not None else max(
            minimum_depth, 2 * minimum_depth + 1
        )
        if (
            not isinstance(chosen_max_depth, int)
            or isinstance(chosen_max_depth, bool)
            or chosen_max_depth < minimum_depth
        ):
            raise ValueError(
                f"max_depth must be an integer >= ceil(log2(n))={minimum_depth}"
            )

        solver_result = solve_with(normalized, budget, eta, solver)
        routing_tree = (
            solver_result["serialized_tree"]
            if routing_tree is None
            else routing_tree
        )
        topology = _complete_topology(
            routing_tree, 1, n, chosen_max_depth
        )
        root = _materialize(topology, value_list, aggregate)
        with self._lock:
            self._root = root
            self._values = value_list
            self._fit_weights = normalized
            self._observed_counts = [0.0] * n
            self._routing_tree = routing_tree
            self._solver_result = solver_result
            self._aggregate = aggregate
            self._solver = solver
            self._routing_label = routing_label or solver
            self._budget = int(solver_result.get("budget", min(budget, n - 1)))
            self._requested_budget = budget
            self._eta = eta
            self._max_depth = chosen_max_depth
            self._drift_threshold = drift_threshold
            self._min_rebuild_observations = min_rebuild_observations
            self._range_endpoint_weight = range_endpoint_weight
            self._data_version = 0
            self._structure_version = 0
            self._rebuild_count = 0
            self._point_queries = 0
            self._range_queries = 0
            self._updates = 0
            self._last_range_node_visits = 0
        return self

    def _require_root(self) -> RangeNode:
        if self._root is None:
            raise RuntimeError("fit() must be called before using the index")
        return self._root

    def snapshot(self) -> RangeSnapshot:
        with self._lock:
            root = self._require_root()
            return RangeSnapshot(
                root=root,
                aggregate=self._aggregate,
                data_version=self._data_version,
                structure_version=self._structure_version,
                height=_height(root),
            )

    def get(self, key: int, *, track: bool = True) -> float:
        with self._lock:
            root = self._require_root()
            _validate_key(key, len(self._values))
            node = root
            while not node.is_leaf:
                if node.left_child is None or node.right_child is None:
                    raise RuntimeError("corrupt range tree")
                node = node.left_child if key <= node.threshold else node.right_child
            if track:
                self._observed_counts[key - 1] += 1.0
                self._point_queries += 1
            return node.aggregate

    def query_cost(self, key: int) -> int:
        with self._lock:
            node = self._require_root()
            _validate_key(key, len(self._values))
            depth = 0
            while not node.is_leaf:
                if node.left_child is None or node.right_child is None:
                    raise RuntimeError("corrupt range tree")
                node = node.left_child if key <= node.threshold else node.right_child
                depth += 1
            return depth

    def range_query(self, left: int, right: int, *, track: bool = True) -> float:
        with self._lock:
            root = self._require_root()
            _validate_range(left, right, len(self._values))
            value, visits = _range_query(root, left, right, self._aggregate)
            if value is None:
                raise RuntimeError("range query produced an empty result")
            self._last_range_node_visits = visits
            if track:
                endpoint_mass = self._range_endpoint_weight * 0.5
                self._observed_counts[left - 1] += endpoint_mass
                self._observed_counts[right - 1] += endpoint_mass
                self._range_queries += 1
            return value

    def point_update(self, key: int, value: float) -> None:
        numeric = float(value)
        if not math.isfinite(numeric):
            raise ValueError("value must be finite")
        with self._lock:
            root = self._require_root()
            _validate_key(key, len(self._values))
            self._root = _point_update(root, key, numeric, self._aggregate)
            self._values[key - 1] = numeric
            self._data_version += 1
            self._updates += 1

    def observe(self, key: int, count: float = 1.0) -> None:
        numeric = float(count)
        if not math.isfinite(numeric) or numeric <= 0:
            raise ValueError("count must be finite and positive")
        with self._lock:
            self._require_root()
            _validate_key(key, len(self._values))
            self._observed_counts[key - 1] += numeric

    def observed_drift(self) -> float:
        with self._lock:
            self._require_root()
            if sum(self._observed_counts) <= 0:
                return 0.0
            return _total_variation(self._fit_weights, self._observed_counts)

    def maybe_rebuild(self, *, force: bool = False) -> bool:
        with self._lock:
            self._require_root()
            observed_total = sum(self._observed_counts)
            if observed_total <= 0:
                return False
            drift = _total_variation(self._fit_weights, self._observed_counts)
            if not force and (
                observed_total < self._min_rebuild_observations
                or drift < self._drift_threshold
            ):
                return False
            new_weights = normalize_weights(self._observed_counts)
            solver_result = solve_with(
                new_weights, self._requested_budget, self._eta, self._solver
            )
            routing_tree = solver_result["serialized_tree"]
            topology = _complete_topology(
                routing_tree, 1, len(self._values), self._max_depth
            )
            root = _materialize(topology, self._values, self._aggregate)
            self._root = root
            self._fit_weights = new_weights
            self._observed_counts = [0.0] * len(self._values)
            self._routing_tree = routing_tree
            self._solver_result = solver_result
            self._routing_label = self._solver
            self._budget = int(
                solver_result.get(
                    "budget", min(self._requested_budget, len(self._values) - 1)
                )
            )
            self._structure_version += 1
            self._rebuild_count += 1
            return True

    def summary(self) -> dict:
        with self._lock:
            root = self._require_root()
            depths = _leaf_depths(root)
            mean_depth = sum(
                weight * depth for weight, depth in zip(self._fit_weights, depths)
            )
            return {
                "aggregate": self._aggregate,
                "n": len(self._values),
                "solver": self._solver,
                "routing_label": self._routing_label,
                "budget": self._budget,
                "requested_budget": self._requested_budget,
                "eta": self._eta,
                "height": max(depths),
                "mean_point_depth": mean_depth,
                "max_depth_limit": self._max_depth,
                "node_count": _node_count(root),
                "data_version": self._data_version,
                "structure_version": self._structure_version,
                "rebuild_count": self._rebuild_count,
                "observed_queries": self._point_queries + self._range_queries,
                "point_queries": self._point_queries,
                "range_queries": self._range_queries,
                "updates": self._updates,
                "observed_drift": (
                    0.0
                    if sum(self._observed_counts) <= 0
                    else _total_variation(
                        self._fit_weights, self._observed_counts
                    )
                ),
                "last_range_node_visits": self._last_range_node_visits,
                "range_node_visit_bound": 4 * max(depths) + 1,
                "root_aggregate": root.aggregate,
            }

    def export_certificate(self) -> dict:
        with self._lock:
            root = self._require_root()
            if self._routing_tree is None or self._solver_result is None:
                raise RuntimeError("fit() must be called before export_certificate()")
            topology = _serialize_topology(root)
            depths = _leaf_depths(root)
            realized_average = sum(
                weight * depth for weight, depth in zip(self._fit_weights, depths)
            )
            artifact = {
                "schema": "certigap-dynamic-range-v1",
                "scope": (
                    "independently verifies topology completion, depth cap, "
                    "point values, aggregate state, and structural cost; it does "
                    "not claim global latency optimality"
                ),
                "aggregate": self._aggregate,
                "values": list(self._values),
                "fit_weights": list(self._fit_weights),
                "routing_tree": self._routing_tree,
                "complete_topology": topology,
                "settings": {
                    "solver": self._solver,
                    "routing_label": self._routing_label,
                    "budget": self._budget,
                    "requested_budget": self._requested_budget,
                    "eta": self._eta,
                    "max_depth": self._max_depth,
                    "drift_threshold": self._drift_threshold,
                    "min_rebuild_observations": self._min_rebuild_observations,
                    "range_endpoint_weight": self._range_endpoint_weight,
                },
                "state": {
                    "data_version": self._data_version,
                    "structure_version": self._structure_version,
                    "rebuild_count": self._rebuild_count,
                    "root_aggregate": root.aggregate,
                    "height": max(depths),
                    "node_count": _node_count(root),
                    "leaf_count": len(depths),
                    "per_key_depths": depths,
                    "realized_average_point_depth": realized_average,
                    "realized_max_point_depth": max(depths),
                    "realized_objective": (
                        (1.0 - self._eta) * realized_average
                        + self._eta * max(depths)
                    ),
                },
                "digests": {
                    "topology_sha256": _canonical_sha256(topology),
                    "values_sha256": _canonical_sha256(self._values),
                    "fit_weights_sha256": _canonical_sha256(self._fit_weights),
                },
            }
        from .dynamic_range_verifier import verify_dynamic_range_certificate

        verify_dynamic_range_certificate(artifact)
        return artifact
