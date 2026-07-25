from __future__ import annotations

from math import ceil, isfinite, log2
from typing import Any


EPS = 1e-9


class VerificationError(ValueError):
    """Raised when a submitted tree or certificate artifact is invalid."""


def _interval_cost(size: int) -> int:
    return 0 if size <= 1 else ceil(log2(size))


def _is_leaf(node: Any) -> bool:
    return type(node).__name__ == "IntervalLeaf"


def _validate_inputs(weights: list[float], budget: int, eta: float) -> None:
    if not weights:
        raise VerificationError("weights must be non-empty")
    if budget < 0:
        raise VerificationError("budget must be non-negative")
    if not isfinite(eta) or not 0.0 <= eta <= 1.0:
        raise VerificationError("eta must lie in [0, 1]")
    if any(not isfinite(weight) or weight < 0.0 for weight in weights):
        raise VerificationError("weights must be finite and non-negative")
    if sum(weights) <= EPS:
        raise VerificationError("weights must have positive total mass")


def verify_tree(tree: Any, weights: list[float], budget: int, eta: float) -> dict:
    """Validate a tree and recompute its search costs without using a solver."""
    _validate_inputs(weights, budget, eta)
    n = len(weights)
    per_key_costs = [0] * n
    covered = [False] * n
    leaves: list[list[int]] = []
    splits: list[dict[str, list[int] | int]] = []

    def walk(node: Any, depth: int) -> tuple[int, int]:
        if _is_leaf(node):
            left, right = node.left, node.right
            if not (1 <= left <= right <= n):
                raise VerificationError(f"invalid leaf interval [{left}, {right}]")
            cost = depth + _interval_cost(right - left + 1)
            for index in range(left - 1, right):
                if covered[index]:
                    raise VerificationError("leaves overlap")
                covered[index] = True
                per_key_costs[index] = cost
            leaves.append([left, right])
            return left, right

        required = ("left", "right", "threshold", "left_child", "right_child")
        if not all(hasattr(node, field) for field in required):
            raise VerificationError("node is neither a valid leaf nor a valid split")
        left, right, threshold = node.left, node.right, node.threshold
        if not (1 <= left <= threshold < right <= n):
            raise VerificationError("threshold is outside its interval")
        left_bounds = walk(node.left_child, depth + 1)
        right_bounds = walk(node.right_child, depth + 1)
        if left_bounds != (left, threshold):
            raise VerificationError("left child interval does not match threshold")
        if right_bounds != (threshold + 1, right):
            raise VerificationError("right child interval does not match threshold")
        splits.append({"interval": [left, right], "threshold": threshold})
        return left, right

    if walk(tree, 0) != (1, n):
        raise VerificationError("root interval does not cover all ranks")
    if not all(covered):
        raise VerificationError("leaves do not cover all ranks")
    if len(splits) > budget:
        raise VerificationError("tree exceeds split budget")

    average_cost = sum(weight * cost for weight, cost in zip(weights, per_key_costs))
    max_cost = max(per_key_costs)
    return {
        "average_cost": average_cost,
        "max_cost": max_cost,
        "objective": (1.0 - eta) * average_cost + eta * max_cost,
        "per_key_costs": per_key_costs,
        "split_count": len(splits),
        "splits": list(reversed(splits)),
        "leaves": sorted(leaves),
    }


def verify_certificate_artifact(
    tree: Any,
    weights: list[float],
    budget: int,
    eta: float,
    artifact: dict,
) -> dict:
    """Check certificate arithmetic supplied by a solver-produced witness artifact."""
    evaluation = verify_tree(tree, weights, budget, eta)
    upper_bound = float(artifact["upper_bound"])
    lower_bound = float(artifact["lower_bound"])
    if not isfinite(lower_bound) or lower_bound < -EPS:
        raise VerificationError("lower bound must be finite and non-negative")
    if abs(upper_bound - evaluation["objective"]) > EPS:
        raise VerificationError("upper bound does not match the submitted tree")
    if lower_bound > upper_bound + EPS:
        raise VerificationError("lower bound exceeds upper bound")
    expected_gap = None if lower_bound <= EPS else (upper_bound - lower_bound) / lower_bound
    supplied_gap = artifact.get("certified_gap")
    if expected_gap is None:
        if supplied_gap is not None:
            raise VerificationError("certificate gap must be null for a zero lower bound")
    elif supplied_gap is None or abs(float(supplied_gap) - expected_gap) > EPS:
        raise VerificationError("certificate gap does not match its bounds")
    return evaluation | {"certified_gap": expected_gap}
