from __future__ import annotations

import hashlib
import json
import math

from .dynamic_range_verifier import _complete


EPS = 1e-9


class RangeOptimizerVerificationError(ValueError):
    pass


def _depths(tree: dict, depth: int = 0) -> list[int]:
    if tree["type"] == "leaf":
        return [depth]
    return _depths(tree["left"], depth + 1) + _depths(
        tree["right"], depth + 1
    )


def _range_visits(tree: dict, query_left: int, query_right: int) -> int:
    left, right = tree["interval"]
    if query_right < left or right < query_left:
        return 1
    if query_left <= left and right <= query_right:
        return 1
    if tree["type"] == "leaf":
        return 1
    return (
        1
        + _range_visits(tree["left"], query_left, query_right)
        + _range_visits(tree["right"], query_left, query_right)
    )


def _score(
    routing_tree: dict,
    points: list[float],
    updates: list[float],
    ranges: list[tuple[int, int, float]],
    max_depth: int,
    eta: float,
) -> dict:
    topology = _complete(routing_tree, 1, len(points), max_depth)
    depths = _depths(topology)
    point_contribution = sum(
        (point + update) * (depth + 1)
        for point, update, depth in zip(points, updates, depths)
    )
    range_contribution = sum(
        count * _range_visits(topology, left, right)
        for left, right, count in ranges
    )
    total = sum(points) + sum(updates) + sum(
        count for _, _, count in ranges
    )
    if total <= 0:
        total = 1.0
    mean = (point_contribution + range_contribution) / total
    maximum = max(depths)
    return {
        "objective": (1.0 - eta) * mean + eta * (maximum + 1),
        "mean_node_visits": mean,
        "max_point_depth": maximum,
        "point_contribution": point_contribution / total,
        "range_contribution": range_contribution / total,
        "complete_topology": topology,
    }


def _canonical_digest(value: object) -> str:
    try:
        encoded = json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise RangeOptimizerVerificationError(
            "artifact is not canonical JSON"
        ) from exc
    return hashlib.sha256(encoded).hexdigest()


def make_range_optimizer_artifact(
    *,
    point_counts: list[float],
    update_counts: list[float],
    range_counts: list[tuple[int, int, float]],
    max_depth: int,
    tail_weight: float,
    budget: int,
    result: dict,
) -> dict:
    workload = {
        "point_counts": list(point_counts),
        "update_counts": list(update_counts),
        "range_counts": [list(item) for item in range_counts],
    }
    settings = {
        "max_depth": max_depth,
        "tail_weight": tail_weight,
        "budget": budget,
    }
    reported = {
        field: result[field]
        for field in (
            "objective",
            "mean_node_visits",
            "max_point_depth",
            "point_contribution",
            "range_contribution",
            "used_splits",
            "expanded_candidates",
            "evaluated_candidates",
            "beam_width",
            "candidate_limit",
            "scope",
        )
    }
    signed = {
        "workload": workload,
        "settings": settings,
        "routing_tree": result["routing_tree"],
        "reported": reported,
    }
    artifact = {
        "schema": "certigap-range-optimizer-v1",
        **signed,
        "sha256": _canonical_digest(signed),
    }
    verify_range_optimizer_artifact(artifact)
    return artifact


def verify_range_optimizer_artifact(artifact: dict) -> dict:
    if not isinstance(artifact, dict) or artifact.get("schema") != "certigap-range-optimizer-v1":
        raise RangeOptimizerVerificationError("unsupported artifact schema")
    workload = artifact.get("workload")
    settings = artifact.get("settings")
    reported = artifact.get("reported")
    routing_tree = artifact.get("routing_tree")
    if not all(
        isinstance(value, dict)
        for value in (workload, settings, reported, routing_tree)
    ):
        raise RangeOptimizerVerificationError("artifact sections are missing")
    try:
        points = [float(value) for value in workload["point_counts"]]
        updates = [float(value) for value in workload["update_counts"]]
        ranges = [
            (int(left), int(right), float(count))
            for left, right, count in workload["range_counts"]
        ]
        max_depth = settings["max_depth"]
        eta = float(settings["tail_weight"])
        budget = settings["budget"]
    except (KeyError, TypeError, ValueError) as exc:
        raise RangeOptimizerVerificationError("artifact inputs are invalid") from exc
    if (
        not points
        or len(points) != len(updates)
        or any(not math.isfinite(value) or value < 0 for value in points + updates)
        or any(
            not 1 <= left <= right <= len(points)
            or not math.isfinite(count)
            or count < 0
            for left, right, count in ranges
        )
        or not isinstance(max_depth, int)
        or isinstance(max_depth, bool)
        or not isinstance(budget, int)
        or isinstance(budget, bool)
        or not 0 <= eta <= 1
        or budget < 0
    ):
        raise RangeOptimizerVerificationError("artifact workload is invalid")

    try:
        recomputed = _score(
            routing_tree, points, updates, ranges, max_depth, eta
        )
    except (TypeError, ValueError) as exc:
        raise RangeOptimizerVerificationError(
            "routing tree does not replay"
        ) from exc
    for field in (
        "objective",
        "mean_node_visits",
        "point_contribution",
        "range_contribution",
    ):
        try:
            supplied = float(reported[field])
        except (KeyError, TypeError, ValueError) as exc:
            raise RangeOptimizerVerificationError(
                f"reported {field} is invalid"
            ) from exc
        if not math.isfinite(supplied) or abs(supplied - recomputed[field]) > EPS:
            raise RangeOptimizerVerificationError(
                f"reported {field} does not replay"
            )
    if reported.get("max_point_depth") != recomputed["max_point_depth"]:
        raise RangeOptimizerVerificationError(
            "reported max_point_depth does not replay"
        )
    used_splits = int(reported.get("used_splits", -1))
    if not 0 <= used_splits <= min(budget, len(points) - 1):
        raise RangeOptimizerVerificationError("reported split count exceeds budget")

    try:
        balanced = _score(
            {"type": "leaf", "interval": [1, len(points)]},
            points,
            updates,
            ranges,
            max_depth,
            eta,
        )
    except (TypeError, ValueError) as exc:
        raise RangeOptimizerVerificationError(
            "balanced reference does not replay"
        ) from exc
    if recomputed["objective"] > balanced["objective"] + EPS:
        raise RangeOptimizerVerificationError(
            "selected routing is worse than the included balanced candidate"
        )
    signed = {
        "workload": workload,
        "settings": settings,
        "routing_tree": routing_tree,
        "reported": reported,
    }
    if artifact.get("sha256") != _canonical_digest(signed):
        raise RangeOptimizerVerificationError("artifact digest mismatch")
    return {
        "verified": True,
        "objective": recomputed["objective"],
        "balanced_objective": balanced["objective"],
        "improvement_over_balanced": (
            balanced["objective"] - recomputed["objective"]
        ),
        "max_point_depth": recomputed["max_point_depth"],
        "scope": reported.get("scope"),
    }
