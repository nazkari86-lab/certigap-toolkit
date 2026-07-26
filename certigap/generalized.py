from __future__ import annotations

from functools import lru_cache
from math import ceil, log2
from numbers import Integral
from typing import Callable, Literal

from .core import (
    FrontierState,
    IntervalLeaf,
    SplitNode,
    Tree,
    _compress,
    _mass,
    _prefix,
    _to_serializable,
    effective_budget,
    split_count,
    validate_problem,
)


FallbackName = Literal["fixed_rounds", "midpoint_binary"]
FallbackProfile = Callable[[int, int], tuple[int, ...]]


def _validated_profile_costs(
    profile: FallbackProfile,
    left: int,
    right: int,
) -> tuple[int, ...]:
    raw_costs = tuple(profile(left, right))
    if (
        len(raw_costs) != right - left + 1
        or any(isinstance(cost, bool) or not isinstance(cost, Integral) or cost < 0 for cost in raw_costs)
    ):
        raise ValueError("fallback profile must return one non-negative integer cost per key")
    return tuple(int(cost) for cost in raw_costs)


def fixed_rounds_profile(left: int, right: int) -> tuple[int, ...]:
    size = right - left + 1
    cost = 0 if size <= 1 else ceil(log2(size))
    return (cost,) * size


def midpoint_binary_profile(left: int, right: int) -> tuple[int, ...]:
    """Exact comparison counts of the executable lower-bound fallback."""
    costs: list[int] = []
    for key in range(left, right + 1):
        lo, hi, comparisons = left, right, 0
        while lo < hi:
            comparisons += 1
            middle = lo + (hi - lo) // 2
            if key <= middle:
                hi = middle
            else:
                lo = middle + 1
        costs.append(comparisons)
    return tuple(costs)


def resolve_fallback(fallback: FallbackName | FallbackProfile) -> FallbackProfile:
    if fallback == "fixed_rounds":
        return fixed_rounds_profile
    if fallback == "midpoint_binary":
        return midpoint_binary_profile
    if callable(fallback):
        return fallback
    raise ValueError(f"unknown fallback policy: {fallback}")


def evaluate_tree_with_fallback(
    tree: Tree,
    weights: list[float],
    eta: float,
    fallback: FallbackName | FallbackProfile = "midpoint_binary",
) -> dict:
    probabilities = validate_problem(weights, budget=0, eta=eta)
    profile = resolve_fallback(fallback)
    per_key = [0] * len(probabilities)
    covered = [False] * len(probabilities)

    def walk(node: Tree, depth: int, expected_left: int, expected_right: int) -> None:
        if node.left != expected_left or node.right != expected_right:
            raise ValueError("tree node interval disagrees with its parent")
        if isinstance(node, IntervalLeaf):
            costs = _validated_profile_costs(profile, node.left, node.right)
            for key, fallback_cost in zip(range(node.left, node.right + 1), costs):
                if not 1 <= key <= len(probabilities) or covered[key - 1]:
                    raise ValueError("tree leaves must form a non-overlapping partition")
                covered[key - 1] = True
                per_key[key - 1] = depth + fallback_cost
            return
        if not (node.left <= node.threshold < node.right):
            raise ValueError("split threshold is outside its interval")
        walk(node.left_child, depth + 1, node.left, node.threshold)
        walk(node.right_child, depth + 1, node.threshold + 1, node.right)

    walk(tree, 0, 1, len(probabilities))
    if not all(covered):
        raise ValueError("tree leaves do not cover every key")
    average = sum(weight * cost for weight, cost in zip(probabilities, per_key))
    maximum = max(per_key)
    return {
        "average_cost": average,
        "max_cost": maximum,
        "objective": (1.0 - eta) * average + eta * maximum,
        "per_key_costs": per_key,
        "split_count": split_count(tree),
        "tree": tree,
        "serialized_tree": _to_serializable(tree),
    }


def generalized_frontier_dp_best(
    weights: list[float],
    budget: int,
    eta: float,
    fallback: FallbackName | FallbackProfile = "midpoint_binary",
) -> dict:
    """Exact CertiGap DP for any deterministic contiguous-interval fallback."""
    probabilities = validate_problem(weights, budget, eta)
    n = len(probabilities)
    requested_budget, budget = budget, effective_budget(budget, n)
    prefix = _prefix(probabilities)
    profile = resolve_fallback(fallback)

    @lru_cache(maxsize=None)
    def leaf_costs(left: int, right: int) -> tuple[int, ...]:
        return _validated_profile_costs(profile, left, right)

    @lru_cache(maxsize=None)
    def solve(left: int, right: int, remaining_budget: int) -> tuple[FrontierState, ...]:
        fallback_costs = leaf_costs(left, right)
        leaf_average = sum(
            probabilities[key - 1] * fallback_cost
            for key, fallback_cost in zip(range(left, right + 1), fallback_costs)
        )
        states = [
            FrontierState(
                average_cost=leaf_average,
                max_cost=max(fallback_costs, default=0),
                tree=IntervalLeaf(left, right),
            )
        ]
        if remaining_budget <= 0 or left == right:
            return tuple(states)
        total_mass = _mass(prefix, left, right)
        for threshold in range(left, right):
            for left_budget in range(remaining_budget):
                right_budget = remaining_budget - 1 - left_budget
                for left_state in solve(left, threshold, left_budget):
                    for right_state in solve(threshold + 1, right, right_budget):
                        states.append(
                            FrontierState(
                                average_cost=total_mass + left_state.average_cost + right_state.average_cost,
                                max_cost=1 + max(left_state.max_cost, right_state.max_cost),
                                tree=SplitNode(
                                    left,
                                    right,
                                    threshold,
                                    left_state.tree,
                                    right_state.tree,
                                ),
                            )
                        )
        return tuple(_compress(states))

    frontier = solve(1, n, budget)
    best = min(
        frontier,
        key=lambda state: (
            (1.0 - eta) * state.average_cost + eta * state.max_cost,
            state.max_cost,
        ),
    )
    result = evaluate_tree_with_fallback(best.tree, probabilities, eta, fallback)
    result.update(
        {
            "budget": budget,
            "requested_budget": requested_budget,
            "eta": eta,
            "fallback": fallback if isinstance(fallback, str) else getattr(fallback, "__name__", "custom"),
            "frontier_size": len(frontier),
        }
    )
    return result
