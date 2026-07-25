from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from math import ceil, log2
from typing import Iterable


EPS = 1e-9


@dataclass(frozen=True)
class IntervalLeaf:
    left: int
    right: int


@dataclass(frozen=True)
class SplitNode:
    left: int
    right: int
    threshold: int
    left_child: "Tree"
    right_child: "Tree"


Tree = IntervalLeaf | SplitNode


@dataclass(frozen=True)
class FrontierState:
    average_cost: float
    max_cost: int
    tree: Tree


@dataclass(frozen=True)
class SearchCandidate:
    objective: float
    average_cost: float
    max_cost: int
    used_budget: int
    tree: Tree


class CertificateError(ValueError):
    pass


def interval_cost(size: int) -> int:
    if size <= 1:
        return 0
    return ceil(log2(size))


def _prefix(weights: Iterable[float]) -> tuple[float, ...]:
    acc = [0.0]
    for value in weights:
        acc.append(acc[-1] + float(value))
    return tuple(acc)


def _mass(prefix: tuple[float, ...], left: int, right: int) -> float:
    return prefix[right] - prefix[left - 1]


def make_distribution(kind: str, n: int) -> list[float]:
    if kind == "uniform":
        base = [1.0] * n
    elif kind == "zipf":
        base = [1.0 / (i + 1) for i in range(n)]
    elif kind == "hot_tail":
        base = [1.0] * n
        for i in range(max(0, n - max(2, n // 4)), n):
            base[i] *= 8.0
    elif kind == "hot_middle":
        base = [1.0] * n
        start = max(0, n // 2 - max(1, n // 6))
        end = min(n, n // 2 + max(1, n // 6))
        for i in range(start, end):
            base[i] *= 10.0
    else:
        raise ValueError(f"unknown distribution kind: {kind}")
    total = sum(base)
    return [value / total for value in base]


def normalize_weights(weights: Iterable[float]) -> list[float]:
    values = [float(weight) for weight in weights]
    total = sum(values)
    if total <= EPS:
        raise ValueError("weights must have positive total mass")
    return [value / total for value in values]


def hot_block_distribution(n: int, start: int, width: int, hot_weight: float, cold_weight: float = 1.0) -> list[float]:
    if not (1 <= start <= n):
        raise ValueError("start must lie inside the key range")
    if width <= 0 or start + width - 1 > n:
        raise ValueError("invalid hot block width")
    base = [cold_weight] * n
    for idx in range(start - 1, start - 1 + width):
        base[idx] = hot_weight
    return normalize_weights(base)


def _compress(states: list[FrontierState]) -> list[FrontierState]:
    by_max: dict[int, FrontierState] = {}
    for state in states:
        prev = by_max.get(state.max_cost)
        if prev is None or state.average_cost < prev.average_cost - EPS:
            by_max[state.max_cost] = state
    ordered = sorted(by_max.values(), key=lambda item: (item.max_cost, item.average_cost))
    compressed: list[FrontierState] = []
    best_average = float("inf")
    for state in ordered:
        if state.average_cost < best_average - EPS:
            compressed.append(state)
            best_average = state.average_cost
    return compressed


def _to_serializable(tree: Tree) -> dict:
    if isinstance(tree, IntervalLeaf):
        return {"type": "leaf", "interval": [tree.left, tree.right]}
    return {
        "type": "split",
        "interval": [tree.left, tree.right],
        "threshold": tree.threshold,
        "left": _to_serializable(tree.left_child),
        "right": _to_serializable(tree.right_child),
    }


def _collect_splits(tree: Tree) -> list[tuple[int, int, int]]:
    if isinstance(tree, IntervalLeaf):
        return []
    return (
        [(tree.left, tree.right, tree.threshold)]
        + _collect_splits(tree.left_child)
        + _collect_splits(tree.right_child)
    )


def split_count(tree: Tree) -> int:
    return len(_collect_splits(tree))


def _collect_leaves(tree: Tree) -> list[tuple[int, int]]:
    if isinstance(tree, IntervalLeaf):
        return [(tree.left, tree.right)]
    return _collect_leaves(tree.left_child) + _collect_leaves(tree.right_child)


def evaluate_tree(tree: Tree, weights: list[float], eta: float) -> dict:
    per_key = [0] * len(weights)

    def walk(node: Tree, depth: int) -> None:
        if isinstance(node, IntervalLeaf):
            cost = depth + interval_cost(node.right - node.left + 1)
            for idx in range(node.left - 1, node.right):
                per_key[idx] = cost
            return
        walk(node.left_child, depth + 1)
        walk(node.right_child, depth + 1)

    walk(tree, 0)
    average = sum(weight * cost for weight, cost in zip(weights, per_key))
    worst = max(per_key) if per_key else 0
    objective = (1.0 - eta) * average + eta * worst
    return {
        "average_cost": average,
        "max_cost": worst,
        "objective": objective,
        "per_key_costs": per_key,
        "split_count": split_count(tree),
        "tree": tree,
        "serialized_tree": _to_serializable(tree),
    }


def frontier_dp_best(weights: list[float], budget: int, eta: float) -> dict:
    prefix = _prefix(weights)
    n = len(weights)

    @lru_cache(maxsize=None)
    def solve(left: int, right: int, remaining_budget: int) -> tuple[FrontierState, ...]:
        size = right - left + 1
        states = [
            FrontierState(
                average_cost=_mass(prefix, left, right) * interval_cost(size),
                max_cost=interval_cost(size),
                tree=IntervalLeaf(left, right),
            )
        ]
        if remaining_budget <= 0 or size <= 1:
            return tuple(_compress(states))

        total_mass = _mass(prefix, left, right)
        for threshold in range(left, right):
            for left_budget in range(remaining_budget):
                right_budget = remaining_budget - 1 - left_budget
                left_states = solve(left, threshold, left_budget)
                right_states = solve(threshold + 1, right, right_budget)
                for left_state, right_state in product(left_states, right_states):
                    states.append(
                        FrontierState(
                            average_cost=total_mass + left_state.average_cost + right_state.average_cost,
                            max_cost=1 + max(left_state.max_cost, right_state.max_cost),
                            tree=SplitNode(
                                left=left,
                                right=right,
                                threshold=threshold,
                                left_child=left_state.tree,
                                right_child=right_state.tree,
                            ),
                        )
                    )
        return tuple(_compress(states))

    frontier = solve(1, n, budget)
    best = min(frontier, key=lambda item: ((1.0 - eta) * item.average_cost + eta * item.max_cost, item.max_cost))
    result = evaluate_tree(best.tree, weights, eta)
    result["budget"] = budget
    result["eta"] = eta
    result["frontier_size"] = len(frontier)
    return result


def brute_force_best(weights: list[float], budget: int, eta: float) -> dict:
    n = len(weights)

    @lru_cache(maxsize=None)
    def build(left: int, right: int, remaining_budget: int) -> tuple[Tree, ...]:
        leaf: Tree = IntervalLeaf(left, right)
        trees: list[Tree] = [leaf]
        if remaining_budget <= 0 or left >= right:
            return tuple(trees)
        for threshold in range(left, right):
            for left_budget in range(remaining_budget):
                right_budget = remaining_budget - 1 - left_budget
                for left_tree, right_tree in product(
                    build(left, threshold, left_budget),
                    build(threshold + 1, right, right_budget),
                ):
                    trees.append(
                        SplitNode(
                            left=left,
                            right=right,
                            threshold=threshold,
                            left_child=left_tree,
                            right_child=right_tree,
                        )
                    )
        return tuple(trees)

    best_eval = None
    for tree in build(1, n, budget):
        current = evaluate_tree(tree, weights, eta)
        if best_eval is None or current["objective"] < best_eval["objective"] - EPS:
            best_eval = current
    assert best_eval is not None
    best_eval["budget"] = budget
    best_eval["eta"] = eta
    return best_eval


def baseline_balanced(weights: list[float], budget: int, eta: float) -> dict:
    n = len(weights)

    def build(left: int, right: int, remaining_budget: int) -> Tree:
        if remaining_budget <= 0 or left >= right:
            return IntervalLeaf(left, right)
        threshold = (left + right) // 2
        left_budget = (remaining_budget - 1) // 2
        right_budget = remaining_budget - 1 - left_budget
        return SplitNode(
            left=left,
            right=right,
            threshold=threshold,
            left_child=build(left, threshold, left_budget),
            right_child=build(threshold + 1, right, right_budget),
        )

    return evaluate_tree(build(1, n, budget), weights, eta) | {"budget": budget, "eta": eta}


def baseline_weighted_median(weights: list[float], budget: int, eta: float) -> dict:
    prefix = _prefix(weights)
    n = len(weights)

    def choose_threshold(left: int, right: int) -> int:
        total = _mass(prefix, left, right)
        target = total / 2.0
        best_threshold = left
        best_gap = float("inf")
        for threshold in range(left, right):
            left_mass = _mass(prefix, left, threshold)
            gap = abs(left_mass - target)
            if gap < best_gap:
                best_gap = gap
                best_threshold = threshold
        return best_threshold

    def build(left: int, right: int, remaining_budget: int) -> Tree:
        if remaining_budget <= 0 or left >= right:
            return IntervalLeaf(left, right)
        threshold = choose_threshold(left, right)
        left_mass = _mass(prefix, left, threshold)
        right_mass = _mass(prefix, threshold + 1, right)
        share = 0.0 if left_mass + right_mass <= EPS else left_mass / (left_mass + right_mass)
        left_budget = min(remaining_budget - 1, int(round((remaining_budget - 1) * share)))
        right_budget = remaining_budget - 1 - left_budget
        return SplitNode(
            left=left,
            right=right,
            threshold=threshold,
            left_child=build(left, threshold, left_budget),
            right_child=build(threshold + 1, right, right_budget),
        )

    return evaluate_tree(build(1, n, budget), weights, eta) | {"budget": budget, "eta": eta}


def entropy_lower_bound(weights: list[float]) -> float:
    total = 0.0
    for weight in weights:
        if weight > EPS:
            total -= weight * log2(weight)
    return total


def max_cost_lower_bound(n: int, budget: int) -> int:
    largest_leaf = ceil(n / (budget + 1))
    return interval_cost(largest_leaf)


def all_budget_optima(weights: list[float], eta: float, max_budget: int | None = None) -> list[dict]:
    n = len(weights)
    upper_budget = min(n - 1, max_budget if max_budget is not None else n - 1)
    return [frontier_dp_best(weights, budget, eta) for budget in range(upper_budget + 1)]


def lagrangian_lower_bound(
    weights: list[float],
    budget: int,
    eta: float,
    max_budget: int | None = None,
    lambda_grid: Iterable[float] | None = None,
) -> dict:
    optima = all_budget_optima(weights, eta, max_budget=max_budget)
    if lambda_grid is None:
        lambda_grid = [step / 8.0 for step in range(0, 49)]

    best_lower = float("-inf")
    best_lambda = 0.0
    best_budget = 0
    for lambda_value in lambda_grid:
        adjusted = [
            optimum["objective"] + lambda_value * optimum["budget"]
            for optimum in optima
        ]
        min_index, min_value = min(enumerate(adjusted), key=lambda item: item[1])
        lower = min_value - lambda_value * budget
        if lower > best_lower + EPS:
            best_lower = lower
            best_lambda = lambda_value
            best_budget = min_index
    return {
        "lower_bound": best_lower,
        "dual_lambda": best_lambda,
        "best_unconstrained_budget": best_budget,
    }


def combined_lower_bound(
    weights: list[float],
    budget: int,
    eta: float,
    max_budget: int | None = None,
) -> dict:
    entropy_bound = (1.0 - eta) * entropy_lower_bound(weights) + eta * max_cost_lower_bound(len(weights), budget)
    lagrangian = lagrangian_lower_bound(weights, budget, eta, max_budget=max_budget)
    lower_bound = max(entropy_bound, lagrangian["lower_bound"])
    source = "entropy" if entropy_bound >= lagrangian["lower_bound"] - EPS else "lagrangian"
    return {
        "lower_bound": lower_bound,
        "entropy_bound": entropy_bound,
        "lagrangian_bound": lagrangian["lower_bound"],
        "dual_lambda": lagrangian["dual_lambda"],
        "best_unconstrained_budget": lagrangian["best_unconstrained_budget"],
        "source": source,
    }


def _leaf_cost_at_depth(left: int, right: int, depth: int) -> int:
    return depth + interval_cost(right - left + 1)


def _replace_leaf(node: Tree, target: tuple[int, int], replacement: Tree) -> Tree:
    if isinstance(node, IntervalLeaf):
        if (node.left, node.right) == target:
            return replacement
        return node
    return SplitNode(
        left=node.left,
        right=node.right,
        threshold=node.threshold,
        left_child=_replace_leaf(node.left_child, target, replacement),
        right_child=_replace_leaf(node.right_child, target, replacement),
    )


def _leaf_depths(tree: Tree, depth: int = 0) -> list[tuple[int, int, int]]:
    if isinstance(tree, IntervalLeaf):
        return [(tree.left, tree.right, depth)]
    return _leaf_depths(tree.left_child, depth + 1) + _leaf_depths(tree.right_child, depth + 1)


def _candidate_key(tree: Tree) -> tuple:
    if isinstance(tree, IntervalLeaf):
        return ("leaf", tree.left, tree.right)
    return (
        "split",
        tree.left,
        tree.right,
        tree.threshold,
        _candidate_key(tree.left_child),
        _candidate_key(tree.right_child),
    )


def _single_split_expansions(tree: Tree, weights: list[float], eta: float, used_budget: int) -> list[dict]:
    prefix = _prefix(weights)
    expansions: list[dict] = []
    for left, right, depth in _leaf_depths(tree):
        if left >= right:
            continue
        leaf_cost = _leaf_cost_at_depth(left, right, depth)
        leaf_mass = _mass(prefix, left, right)
        for threshold in range(left, right):
            left_mass = _mass(prefix, left, threshold)
            right_mass = leaf_mass - left_mass
            left_cost = _leaf_cost_at_depth(left, threshold, depth + 1)
            right_cost = _leaf_cost_at_depth(threshold + 1, right, depth + 1)
            local_average_before = leaf_mass * leaf_cost
            local_average_after = left_mass * left_cost + right_mass * right_cost
            average_gain = local_average_before - local_average_after
            replacement = SplitNode(
                left=left,
                right=right,
                threshold=threshold,
                left_child=IntervalLeaf(left, threshold),
                right_child=IntervalLeaf(threshold + 1, right),
            )
            candidate_tree = _replace_leaf(tree, (left, right), replacement)
            candidate_eval = evaluate_tree(candidate_tree, weights, eta)
            candidate_eval["budget"] = used_budget + 1
            candidate_eval["eta"] = eta
            candidate_eval["average_gain"] = average_gain
            expansions.append(candidate_eval)
    return expansions


def greedy_best(weights: list[float], budget: int, eta: float) -> dict:
    n = len(weights)
    tree: Tree = IntervalLeaf(1, n)
    current = evaluate_tree(tree, weights, eta) | {"budget": 0, "eta": eta}

    for used_budget in range(budget):
        best_candidate = None
        for candidate_eval in _single_split_expansions(tree, weights, eta, used_budget):
            score = current["objective"] - candidate_eval["objective"]
            average_gain = candidate_eval["average_gain"]
            if best_candidate is None or score > best_candidate["score"] + EPS or (
                abs(score - best_candidate["score"]) <= EPS and average_gain > best_candidate["average_gain"] + EPS
            ):
                best_candidate = {
                    "score": score,
                    "average_gain": average_gain,
                    "evaluation": candidate_eval,
                    "tree": candidate_eval["tree"],
                }
        if best_candidate is None or best_candidate["score"] <= EPS:
            break
        tree = best_candidate["tree"]
        current = best_candidate["evaluation"]
    current["budget"] = budget
    current["eta"] = eta
    return current


def beam_search_best(weights: list[float], budget: int, eta: float, beam_width: int = 16) -> dict:
    n = len(weights)
    start = evaluate_tree(IntervalLeaf(1, n), weights, eta)
    start_candidate = SearchCandidate(
        objective=start["objective"],
        average_cost=start["average_cost"],
        max_cost=start["max_cost"],
        used_budget=0,
        tree=start["tree"],
    )
    beam = [start_candidate]
    best_overall = start_candidate

    for used_budget in range(budget):
        expanded: dict[tuple, SearchCandidate] = {}
        for candidate in beam:
            for expansion in _single_split_expansions(candidate.tree, weights, eta, used_budget):
                next_candidate = SearchCandidate(
                    objective=expansion["objective"],
                    average_cost=expansion["average_cost"],
                    max_cost=expansion["max_cost"],
                    used_budget=used_budget + 1,
                    tree=expansion["tree"],
                )
                key = _candidate_key(next_candidate.tree)
                previous = expanded.get(key)
                if previous is None or next_candidate.objective < previous.objective - EPS:
                    expanded[key] = next_candidate
        if not expanded:
            break
        beam = sorted(
            expanded.values(),
            key=lambda item: (item.objective, item.max_cost, item.average_cost),
        )[:beam_width]
        local_best = beam[0]
        if local_best.objective < best_overall.objective - EPS:
            best_overall = local_best

    result = evaluate_tree(best_overall.tree, weights, eta)
    result["budget"] = budget
    result["eta"] = eta
    result["used_budget"] = best_overall.used_budget
    result["beam_width"] = beam_width
    return result


def heuristic_best(weights: list[float], budget: int, eta: float, beam_width: int = 16) -> dict:
    exact_budget_threshold = 24
    if len(weights) <= exact_budget_threshold:
        result = frontier_dp_best(weights, budget, eta)
        result["solver"] = "exact"
        return result
    result = beam_search_best(weights, budget, eta, beam_width=beam_width)
    result["solver"] = "beam"
    return result


def counterexample_search(
    n_values: Iterable[int] = (8, 10, 12, 16, 20, 24),
    budgets: Iterable[int] = (2, 3, 4),
    etas: Iterable[float] = (0.0, 0.15, 0.30),
    widths: Iterable[int] = (2, 3, 4, 5, 6),
    hot_weights: Iterable[float] = (4.0, 8.0, 12.0, 16.0, 24.0),
) -> list[dict]:
    findings: list[dict] = []
    for n in n_values:
        for budget in budgets:
            if budget >= n:
                continue
            for eta in etas:
                for width in widths:
                    if width > n:
                        continue
                    for start in range(1, n - width + 2):
                        for hot_weight in hot_weights:
                            weights = hot_block_distribution(n, start, width, hot_weight)
                            exact = frontier_dp_best(weights, budget, eta)
                            greedy = greedy_best(weights, budget, eta)
                            beam = beam_search_best(weights, budget, eta, beam_width=16)
                            greedy_gap = greedy["objective"] - exact["objective"]
                            beam_gap = beam["objective"] - exact["objective"]
                            findings.append(
                                {
                                    "n": n,
                                    "budget": budget,
                                    "eta": eta,
                                    "start": start,
                                    "width": width,
                                    "hot_weight": hot_weight,
                                    "greedy_gap": greedy_gap,
                                    "beam_gap": beam_gap,
                                    "exact_objective": exact["objective"],
                                    "greedy_objective": greedy["objective"],
                                    "beam_objective": beam["objective"],
                                    "weights": weights,
                                    "exact_tree": exact["serialized_tree"],
                                    "greedy_tree": greedy["serialized_tree"],
                                    "beam_tree": beam["serialized_tree"],
                                }
                            )
    findings.sort(key=lambda row: (row["greedy_gap"] - row["beam_gap"], row["greedy_gap"]), reverse=True)
    return findings


def certify_tree(tree: Tree, weights: list[float], budget: int, eta: float) -> dict:
    n = len(weights)
    leaves = sorted(_collect_leaves(tree))
    if not leaves:
        raise CertificateError("tree has no leaves")
    expected_left = 1
    for left, right in leaves:
        if left > right:
            raise CertificateError(f"invalid leaf interval [{left}, {right}]")
        if left != expected_left:
            raise CertificateError("leaves do not form a contiguous partition")
        expected_left = right + 1
    if expected_left != n + 1:
        raise CertificateError("leaves do not cover all ranks")

    split_count = len(_collect_splits(tree))
    if split_count > budget:
        raise CertificateError("tree exceeds split budget")

    def validate(node: Tree) -> tuple[int, int]:
        if isinstance(node, IntervalLeaf):
            return node.left, node.right
        if not (node.left <= node.threshold < node.right):
            raise CertificateError("threshold is outside its interval")
        left_bounds = validate(node.left_child)
        right_bounds = validate(node.right_child)
        if left_bounds != (node.left, node.threshold):
            raise CertificateError("left child interval does not match threshold")
        if right_bounds != (node.threshold + 1, node.right):
            raise CertificateError("right child interval does not match threshold")
        return node.left, node.right

    root_bounds = validate(tree)
    if root_bounds != (1, n):
        raise CertificateError("root interval does not cover all ranks")

    evaluation = evaluate_tree(tree, weights, eta)
    lower_bounds = combined_lower_bound(weights, budget, eta)
    exact_optimum = None
    exact_gap = None
    if len(weights) <= 18:
        exact_optimum = frontier_dp_best(weights, budget, eta)["objective"]
        exact_gap = 0.0 if exact_optimum <= EPS else (evaluation["objective"] - exact_optimum) / exact_optimum
    certified_gap = None
    if lower_bounds["lower_bound"] > EPS:
        certified_gap = (evaluation["objective"] - lower_bounds["lower_bound"]) / lower_bounds["lower_bound"]
    return {
        "n": n,
        "budget": budget,
        "eta": eta,
        "splits": [
            {"interval": [left, right], "threshold": threshold}
            for left, right, threshold in _collect_splits(tree)
        ],
        "leaves": [[left, right] for left, right in leaves],
        "upper_bound": evaluation["objective"],
        "lower_bound": lower_bounds["lower_bound"],
        "entropy_bound": lower_bounds["entropy_bound"],
        "lagrangian_bound": lower_bounds["lagrangian_bound"],
        "dual_lambda": lower_bounds["dual_lambda"],
        "best_unconstrained_budget": lower_bounds["best_unconstrained_budget"],
        "bound_source": lower_bounds["source"],
        "certified_gap": certified_gap,
        "exact_optimum": exact_optimum,
        "exact_gap": exact_gap,
        "average_cost": evaluation["average_cost"],
        "max_cost": evaluation["max_cost"],
        "per_key_costs": evaluation["per_key_costs"],
    }


def benchmark_case(
    kind: str,
    n: int,
    budget: int,
    eta: float,
    include_certificate: bool = True,
) -> dict:
    weights = make_distribution(kind, n)
    exact = frontier_dp_best(weights, budget, eta)
    greedy = greedy_best(weights, budget, eta)
    beam = beam_search_best(weights, budget, eta)
    balanced = baseline_balanced(weights, budget, eta)
    weighted = baseline_weighted_median(weights, budget, eta)
    result = {
        "distribution": kind,
        "n": n,
        "budget": budget,
        "eta": eta,
        "exact_objective": exact["objective"],
        "greedy_objective": greedy["objective"],
        "beam_objective": beam["objective"],
        "balanced_objective": balanced["objective"],
        "weighted_objective": weighted["objective"],
        "greedy_gap_vs_exact": greedy["objective"] - exact["objective"],
        "beam_gap_vs_exact": beam["objective"] - exact["objective"],
        "exact_gain_vs_balanced": balanced["objective"] - exact["objective"],
        "exact_gain_vs_weighted": weighted["objective"] - exact["objective"],
    }
    if include_certificate:
        certificate = certify_tree(beam["tree"], weights, budget, eta)
        result["beam_certified_gap"] = certificate["certified_gap"]
        result["beam_lower_bound"] = certificate["lower_bound"]
    return result
