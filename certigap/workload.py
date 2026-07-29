from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Iterable

from .api import SolverName
from .dynamic_range import AggregateName, DynamicCertiRange


def _non_negative(value: float, name: str) -> float:
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{name} must be finite and non-negative")
    return numeric


@dataclass
class CertiRangeWorkload:
    """Declarative point/range/update workload used to compile an index."""

    n: int
    point_counts: list[float] = field(init=False)
    range_left_counts: list[float] = field(init=False)
    range_right_counts: list[float] = field(init=False)
    range_counts: dict[tuple[int, int], float] = field(default_factory=dict)
    update_counts: list[float] = field(init=False)
    point_events: int = 0
    range_events: int = 0
    update_events: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.n, int) or isinstance(self.n, bool) or self.n <= 0:
            raise ValueError("n must be a positive integer")
        self.point_counts = [0.0] * self.n
        self.range_left_counts = [0.0] * self.n
        self.range_right_counts = [0.0] * self.n
        self.update_counts = [0.0] * self.n

    def _key(self, key: int) -> int:
        if not isinstance(key, int) or isinstance(key, bool) or not 1 <= key <= self.n:
            raise ValueError("key rank out of range")
        return key - 1

    def add_point(self, key: int, count: float = 1.0) -> "CertiRangeWorkload":
        numeric = _non_negative(count, "count")
        self.point_counts[self._key(key)] += numeric
        self.point_events += 1
        return self

    def add_range(
        self, left: int, right: int, count: float = 1.0
    ) -> "CertiRangeWorkload":
        if (
            not isinstance(left, int)
            or isinstance(left, bool)
            or not isinstance(right, int)
            or isinstance(right, bool)
            or not 1 <= left <= right <= self.n
        ):
            raise ValueError("range must satisfy 1 <= left <= right <= n")
        numeric = _non_negative(count, "count")
        self.range_left_counts[left - 1] += numeric
        self.range_right_counts[right - 1] += numeric
        self.range_counts[(left, right)] = (
            self.range_counts.get((left, right), 0.0) + numeric
        )
        self.range_events += 1
        return self

    def add_update(self, key: int, count: float = 1.0) -> "CertiRangeWorkload":
        numeric = _non_negative(count, "count")
        self.update_counts[self._key(key)] += numeric
        self.update_events += 1
        return self

    def extend_points(self, keys: Iterable[int]) -> "CertiRangeWorkload":
        for key in keys:
            self.add_point(key)
        return self

    def extend_ranges(
        self, ranges: Iterable[tuple[int, int]]
    ) -> "CertiRangeWorkload":
        for left, right in ranges:
            self.add_range(left, right)
        return self

    def routing_weights(
        self,
        *,
        point_weight: float = 1.0,
        range_endpoint_weight: float = 1.0,
        update_weight: float = 1.0,
    ) -> list[float]:
        point_scale = _non_negative(point_weight, "point_weight")
        range_scale = _non_negative(
            range_endpoint_weight, "range_endpoint_weight"
        )
        update_scale = _non_negative(update_weight, "update_weight")
        weights = [
            point_scale * point
            + 0.5 * range_scale * (left + right)
            + update_scale * update
            for point, left, right, update in zip(
                self.point_counts,
                self.range_left_counts,
                self.range_right_counts,
                self.update_counts,
            )
        ]
        return weights if sum(weights) > 0 else [1.0] * self.n

    def manifest(self) -> dict:
        payload = {
            "schema": "certigap-workload-v1",
            "n": self.n,
            "point_counts": self.point_counts,
            "range_left_counts": self.range_left_counts,
            "range_right_counts": self.range_right_counts,
            "range_counts": [
                [left, right, count]
                for (left, right), count in sorted(self.range_counts.items())
            ],
            "update_counts": self.update_counts,
            "point_events": self.point_events,
            "range_events": self.range_events,
            "update_events": self.update_events,
            "range_model": (
                "range endpoints are a routing-cost proxy; aggregate correctness "
                "does not depend on this heuristic"
            ),
        }
        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
        return payload | {"sha256": hashlib.sha256(encoded).hexdigest()}

    def compile(
        self,
        values: Iterable[float],
        *,
        budget: int,
        eta: float = 0.15,
        solver: SolverName = "beam",
        aggregate: AggregateName = "sum",
        max_depth: int | None = None,
        drift_threshold: float = 0.10,
        min_rebuild_observations: float = 32.0,
        point_weight: float = 1.0,
        range_endpoint_weight: float = 1.0,
        update_weight: float = 1.0,
        routing: str = "point_proxy",
        range_beam_width: int = 8,
        range_candidate_limit: int = 12,
    ) -> DynamicCertiRange:
        value_list = list(values)
        if len(value_list) != self.n:
            raise ValueError("workload key count does not match values")
        weights = self.routing_weights(
            point_weight=point_weight,
            range_endpoint_weight=range_endpoint_weight,
            update_weight=update_weight,
        )
        routing_tree = None
        routing_label = None
        if routing == "range_aware":
            from .range_optimizer import range_aware_beam_search

            minimum_depth = 0 if self.n <= 1 else math.ceil(math.log2(self.n))
            chosen_depth = max_depth if max_depth is not None else 2 * minimum_depth + 1
            optimized = range_aware_beam_search(
                point_counts=[
                    point_weight * value for value in self.point_counts
                ],
                update_counts=[
                    update_weight * value for value in self.update_counts
                ],
                range_counts=[
                    (left, right, range_endpoint_weight * count)
                    for (left, right), count in self.range_counts.items()
                ],
                budget=budget,
                max_depth=chosen_depth,
                tail_weight=eta,
                beam_width=range_beam_width,
                candidate_limit=range_candidate_limit,
            )
            routing_tree = optimized["routing_tree"]
            routing_label = "range_aware_beam"
        elif routing != "point_proxy":
            raise ValueError("routing must be point_proxy or range_aware")
        return DynamicCertiRange().fit(
            value_list,
            weights=weights,
            budget=budget,
            eta=eta,
            solver=solver,
            aggregate=aggregate,
            max_depth=max_depth,
            drift_threshold=drift_threshold,
            min_rebuild_observations=min_rebuild_observations,
            range_endpoint_weight=range_endpoint_weight,
            routing_tree=routing_tree,
            routing_label=routing_label,
        )
