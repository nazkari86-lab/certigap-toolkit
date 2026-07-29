from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from .dynamic_range import _complete_topology


@dataclass(frozen=True)
class RangeWorkloadScore:
    mean_node_visits: float
    max_point_depth: int
    objective: float
    point_contribution: float
    range_contribution: float


def _leaves(tree: dict) -> list[tuple[int, int]]:
    if tree["type"] == "leaf":
        return [tuple(tree["interval"])]
    return _leaves(tree["left"]) + _leaves(tree["right"])


def _replace_leaf(
    tree: dict, target: tuple[int, int], threshold: int
) -> dict:
    left, right = tree["interval"]
    if tree["type"] == "leaf":
        if (left, right) != target:
            return tree
        return {
            "type": "split",
            "interval": [left, right],
            "threshold": threshold,
            "left": {"type": "leaf", "interval": [left, threshold]},
            "right": {
                "type": "leaf",
                "interval": [threshold + 1, right],
            },
        }
    return {
        "type": "split",
        "interval": [left, right],
        "threshold": tree["threshold"],
        "left": _replace_leaf(tree["left"], target, threshold),
        "right": _replace_leaf(tree["right"], target, threshold),
    }


def _depths(topology: dict, depth: int = 0) -> list[int]:
    if topology["type"] == "leaf":
        return [depth]
    return _depths(topology["left"], depth + 1) + _depths(
        topology["right"], depth + 1
    )


def _range_visits(topology: dict, query_left: int, query_right: int) -> int:
    left, right = topology["interval"]
    if query_right < left or right < query_left:
        return 1
    if query_left <= left and right <= query_right:
        return 1
    if topology["type"] == "leaf":
        return 1
    return (
        1
        + _range_visits(topology["left"], query_left, query_right)
        + _range_visits(topology["right"], query_left, query_right)
    )


def score_range_workload(
    routing_tree: dict,
    *,
    point_counts: Sequence[float],
    update_counts: Sequence[float],
    range_counts: Sequence[tuple[int, int, float]],
    max_depth: int,
    tail_weight: float = 0.0,
) -> RangeWorkloadScore:
    if len(point_counts) != len(update_counts) or not point_counts:
        raise ValueError("point and update counts must have equal non-zero length")
    n = len(point_counts)
    topology = _complete_topology(routing_tree, 1, n, max_depth)
    depths = _depths(topology)
    point_contribution = sum(
        (float(point) + float(update)) * (depth + 1)
        for point, update, depth in zip(point_counts, update_counts, depths)
    )
    range_contribution = sum(
        float(count) * _range_visits(topology, left, right)
        for left, right, count in range_counts
    )
    total = (
        sum(float(value) for value in point_counts)
        + sum(float(value) for value in update_counts)
        + sum(float(count) for _, _, count in range_counts)
    )
    if total <= 0:
        total = 1.0
    mean = (point_contribution + range_contribution) / total
    maximum = max(depths)
    return RangeWorkloadScore(
        mean_node_visits=mean,
        max_point_depth=maximum,
        objective=(1.0 - tail_weight) * mean
        + tail_weight * (maximum + 1),
        point_contribution=point_contribution / total,
        range_contribution=range_contribution / total,
    )


def _candidate_thresholds(
    left: int,
    right: int,
    point_mass: Sequence[float],
    range_counts: Sequence[tuple[int, int, float]],
    candidate_limit: int,
) -> list[int]:
    if right <= left:
        return []
    points = {
        left,
        right - 1,
        (left + right) // 2,
        left + (right - left) // 3,
        left + 2 * (right - left) // 3,
    }
    total = sum(point_mass[left - 1 : right])
    if total > 0:
        target = total / 2
        cumulative = 0.0
        for key in range(left, right):
            cumulative += point_mass[key - 1]
            if cumulative >= target:
                points.add(key)
                break
    endpoint_mass: dict[int, float] = {}
    for query_left, query_right, count in range_counts:
        if left <= query_left < right:
            endpoint_mass[query_left] = endpoint_mass.get(query_left, 0.0) + count
        if left <= query_right < right:
            endpoint_mass[query_right] = endpoint_mass.get(query_right, 0.0) + count
    for key, _ in sorted(
        endpoint_mass.items(), key=lambda item: (-item[1], item[0])
    )[:candidate_limit]:
        points.add(key)
    valid = sorted(point for point in points if left <= point < right)
    if len(valid) <= candidate_limit:
        return valid
    midpoint = (left + right - 1) / 2
    return sorted(
        sorted(
            valid,
            key=lambda point: (
                -endpoint_mass.get(point, 0.0),
                abs(point - midpoint),
                point,
            ),
        )[:candidate_limit]
    )


def range_aware_beam_search(
    *,
    point_counts: Iterable[float],
    update_counts: Iterable[float],
    range_counts: Iterable[tuple[int, int, float]],
    budget: int,
    max_depth: int,
    tail_weight: float = 0.10,
    beam_width: int = 8,
    candidate_limit: int = 12,
) -> dict:
    points = [float(value) for value in point_counts]
    updates = [float(value) for value in update_counts]
    ranges = [(int(left), int(right), float(count)) for left, right, count in range_counts]
    if (
        not points
        or len(points) != len(updates)
        or any(not math.isfinite(value) or value < 0 for value in points + updates)
    ):
        raise ValueError("point/update counts must be finite, non-negative, and aligned")
    n = len(points)
    if any(
        not 1 <= left <= right <= n
        or not math.isfinite(count)
        or count < 0
        for left, right, count in ranges
    ):
        raise ValueError("range workload is invalid")
    if budget < 0 or beam_width <= 0 or candidate_limit < 3:
        raise ValueError("invalid search limits")
    if not 0 <= tail_weight <= 1:
        raise ValueError("tail_weight must lie in [0, 1]")

    root = {"type": "leaf", "interval": [1, n]}
    cache: dict[str, RangeWorkloadScore] = {}

    def evaluate(tree: dict) -> RangeWorkloadScore:
        key = json.dumps(tree, sort_keys=True, separators=(",", ":"))
        if key not in cache:
            cache[key] = score_range_workload(
                tree,
                point_counts=points,
                update_counts=updates,
                range_counts=ranges,
                max_depth=max_depth,
                tail_weight=tail_weight,
            )
        return cache[key]

    beam = [root]
    best_tree = root
    best_score = evaluate(root)
    point_mass = [
        point + update for point, update in zip(points, updates)
    ]
    expanded = 0
    for _ in range(min(budget, n - 1)):
        candidates: dict[str, dict] = {}
        for tree in beam:
            for leaf in _leaves(tree):
                left, right = leaf
                for threshold in _candidate_thresholds(
                    left,
                    right,
                    point_mass,
                    ranges,
                    candidate_limit,
                ):
                    child = _replace_leaf(tree, leaf, threshold)
                    key = json.dumps(
                        child, sort_keys=True, separators=(",", ":")
                    )
                    candidates[key] = child
                    expanded += 1
        if not candidates:
            break
        ordered = sorted(
            candidates.values(),
            key=lambda tree: (
                evaluate(tree).objective,
                evaluate(tree).max_point_depth,
                json.dumps(tree, sort_keys=True, separators=(",", ":")),
            ),
        )
        beam = ordered[:beam_width]
        candidate_score = evaluate(beam[0])
        if candidate_score.objective < best_score.objective - 1e-12:
            best_tree = beam[0]
            best_score = candidate_score

    topology = _complete_topology(best_tree, 1, n, max_depth)
    return {
        "routing_tree": best_tree,
        "complete_topology": topology,
        "objective": best_score.objective,
        "mean_node_visits": best_score.mean_node_visits,
        "max_point_depth": best_score.max_point_depth,
        "point_contribution": best_score.point_contribution,
        "range_contribution": best_score.range_contribution,
        "used_splits": len(_leaves(best_tree)) - 1,
        "expanded_candidates": expanded,
        "evaluated_candidates": len(cache),
        "beam_width": beam_width,
        "candidate_limit": candidate_limit,
        "scope": (
            "best candidate found by bounded range-aware beam search; "
            "not a global optimum certificate"
        ),
    }
