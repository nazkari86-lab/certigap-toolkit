from __future__ import annotations

from fractions import Fraction
from math import ceil, log2
from typing import Iterable


def _fixed_rounds(size: int) -> int:
    return 0 if size <= 1 else ceil(log2(size))


def verify_serialized_tree_exact(
    tree: dict,
    counts: Iterable[int],
    budget: int,
    eta: Fraction | tuple[int, int] = Fraction(0),
) -> dict:
    """Verify a fixed-round CertiGap tree using rational arithmetic only."""
    values = tuple(int(value) for value in counts)
    if not values or any(value < 0 for value in values) or sum(values) <= 0:
        raise ValueError("counts must be non-negative integers with positive total")
    if budget < 0:
        raise ValueError("budget must be non-negative")
    eta_fraction = Fraction(*eta) if isinstance(eta, tuple) else Fraction(eta)
    if not 0 <= eta_fraction <= 1:
        raise ValueError("eta must lie in [0, 1]")

    n = len(values)
    costs = [None] * n
    split_total = 0

    def walk(node: dict, expected_left: int, expected_right: int, depth: int) -> None:
        nonlocal split_total
        if node.get("interval") != [expected_left, expected_right]:
            raise ValueError("node interval does not match its parent")
        if node.get("type") == "leaf":
            cost = depth + _fixed_rounds(expected_right - expected_left + 1)
            for index in range(expected_left - 1, expected_right):
                if costs[index] is not None:
                    raise ValueError("tree leaves overlap")
                costs[index] = cost
            return
        if node.get("type") != "split":
            raise ValueError("unknown node type")
        threshold = node.get("threshold")
        if not isinstance(threshold, int) or not expected_left <= threshold < expected_right:
            raise ValueError("invalid threshold")
        split_total += 1
        walk(node.get("left", {}), expected_left, threshold, depth + 1)
        walk(node.get("right", {}), threshold + 1, expected_right, depth + 1)

    walk(tree, 1, n, 0)
    if split_total > min(budget, n - 1) or any(cost is None for cost in costs):
        raise ValueError("tree is incomplete or exceeds its split budget")
    total = sum(values)
    average = sum(Fraction(weight * int(cost), total) for weight, cost in zip(values, costs))
    maximum = max(int(cost) for cost in costs)
    objective = (1 - eta_fraction) * average + eta_fraction * maximum
    return {
        "average_cost": average,
        "max_cost": maximum,
        "objective": objective,
        "split_count": split_total,
        "per_key_costs": tuple(int(cost) for cost in costs),
    }
