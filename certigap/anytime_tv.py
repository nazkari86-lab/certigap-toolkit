from __future__ import annotations

import hashlib
import heapq
import json
from dataclasses import asdict, dataclass
from math import ceil, isfinite, log2
from typing import Sequence

from .autodro import ExecutionCostModel, worst_case_tv_expectation
from .core import (
    EPS,
    IntervalLeaf,
    SplitNode,
    Tree,
    _leaf_depths,
    _replace_leaf,
    _to_serializable,
    baseline_balanced,
    baseline_weighted_median,
    beam_search_best,
    entropy_lower_bound,
    effective_budget,
    split_count,
    validate_problem,
)
from .generalized import FallbackName, resolve_fallback


MAX_KEYS = 512
MAX_EXPANSIONS = 200_000


@dataclass(frozen=True)
class _SearchState:
    tree: Tree
    open_leaves: tuple[tuple[int, int], ...]
    used_budget: int
    lower_bound: float
    identity: str


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _state_identity(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    used_budget: int,
) -> str:
    payload = {
        "tree": _to_serializable(tree),
        "open_leaves": [list(item) for item in open_leaves],
        "used_budget": used_budget,
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _memory_bytes(tree: Tree, n: int, model: ExecutionCostModel) -> int:
    splits = split_count(tree)
    return model.key_bytes * n + model.node_bytes * (2 * splits + 1)


def _partial_execution_costs(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    n: int,
    fallback: FallbackName,
    model: ExecutionCostModel,
) -> list[float]:
    open_set = set(open_leaves)
    fallback_profile = resolve_fallback(fallback)
    costs = [0.0] * n
    for left, right, depth in _leaf_depths(tree):
        if (left, right) in open_set:
            leaf_costs = (0,) * (right - left + 1)
        else:
            leaf_costs = fallback_profile(left, right)
        for key, fallback_cost in zip(range(left, right + 1), leaf_costs):
            costs[key - 1] = (
                depth * model.routing_comparison_cost
                + fallback_cost * model.fallback_comparison_cost
            )
    return costs


def _score_costs(
    nominal: Sequence[float],
    costs: Sequence[float],
    tv_radius: float,
    memory_bytes: int,
    splits: int,
    model: ExecutionCostModel,
) -> dict:
    robust = worst_case_tv_expectation(nominal, costs, tv_radius)
    maximum = max(costs)
    score = (
        robust["robust_expectation"]
        + model.tail_weight * maximum
        + model.memory_cost_per_byte * memory_bytes
        + model.build_cost_per_split * splits
    )
    return {
        "score": score,
        "robust_mean_cost": robust["robust_expectation"],
        "nominal_mean_cost": robust["nominal_expectation"],
        "max_execution_cost": maximum,
        "adversarial_distribution": robust["adversarial_distribution"],
    }


def _complete_candidate(
    tree: Tree,
    nominal: Sequence[float],
    tv_radius: float,
    fallback: FallbackName,
    model: ExecutionCostModel,
) -> dict:
    n = len(nominal)
    costs = _partial_execution_costs(tree, (), n, fallback, model)
    memory = _memory_bytes(tree, n, model)
    scored = _score_costs(
        nominal,
        costs,
        tv_radius,
        memory,
        split_count(tree),
        model,
    )
    return {
        **scored,
        "tree": tree,
        "serialized_tree": _to_serializable(tree),
        "per_key_execution_costs": costs,
        "split_count": split_count(tree),
        "memory_bytes": memory,
    }


def _state_lower_bound(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    nominal: Sequence[float],
    tv_radius: float,
    fallback: FallbackName,
    model: ExecutionCostModel,
    information_floor: float,
) -> float:
    costs = _partial_execution_costs(
        tree,
        open_leaves,
        len(nominal),
        fallback,
        model,
    )
    local_bound = _score_costs(
        nominal,
        costs,
        tv_radius,
        _memory_bytes(tree, len(nominal), model),
        split_count(tree),
        model,
    )["score"]
    structural_bound = _structural_nominal_floor(
        tree,
        open_leaves,
        nominal,
        fallback,
        model,
    )
    return max(local_bound, information_floor, structural_bound)


def _structural_nominal_floor(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    nominal: Sequence[float],
    fallback: FallbackName,
    model: ExecutionCostModel,
) -> float:
    open_set = set(open_leaves)
    profile = resolve_fallback(fallback)
    minimum_comparison_cost = min(
        model.routing_comparison_cost,
        model.fallback_comparison_cost,
    )
    expected = 0.0
    for left, right, depth in _leaf_depths(tree):
        probabilities = nominal[left - 1 : right]
        mass = sum(probabilities)
        expected += mass * depth * model.routing_comparison_cost
        if (left, right) in open_set:
            if mass > EPS:
                conditional_entropy = -sum(
                    (probability / mass) * log2(probability / mass)
                    for probability in probabilities
                    if probability > EPS
                )
                expected += (
                    mass
                    * minimum_comparison_cost
                    * conditional_entropy
                )
        else:
            expected += sum(
                probability * fallback_cost * model.fallback_comparison_cost
                for probability, fallback_cost in zip(
                    probabilities,
                    profile(left, right),
                )
            )
    splits = split_count(tree)
    maximum_depth_floor = (
        0 if len(nominal) <= 1 else ceil(log2(len(nominal)))
    )
    return (
        expected
        + model.tail_weight
        * minimum_comparison_cost
        * maximum_depth_floor
        + model.memory_cost_per_byte
        * _memory_bytes(tree, len(nominal), model)
        + model.build_cost_per_split * splits
    )


def _information_theoretic_floor(
    nominal: list[float],
    model: ExecutionCostModel,
) -> float:
    comparison_floor = min(
        model.routing_comparison_cost,
        model.fallback_comparison_cost,
    )
    maximum_depth_floor = 0 if len(nominal) <= 1 else ceil(log2(len(nominal)))
    minimum_memory = model.key_bytes * len(nominal) + model.node_bytes
    return (
        comparison_floor * entropy_lower_bound(nominal)
        + model.tail_weight * comparison_floor * maximum_depth_floor
        + model.memory_cost_per_byte * minimum_memory
    )


def _initial_incumbent(
    nominal: list[float],
    budget: int,
    tv_radius: float,
    fallback: FallbackName,
    model: ExecutionCostModel,
    memory_limit_bytes: int | None,
) -> dict:
    trees: dict[str, Tree] = {}
    for tree in (
        IntervalLeaf(1, len(nominal)),
        baseline_balanced(nominal, budget, 0.0)["tree"],
        baseline_weighted_median(nominal, budget, 0.0)["tree"],
    ):
        trees[_canonical(_to_serializable(tree))] = tree
    for eta in (0.0, min(tv_radius, 1.0), 0.5, 1.0):
        tree = beam_search_best(nominal, budget, eta, beam_width=32)["tree"]
        trees[_canonical(_to_serializable(tree))] = tree

    candidates = [
        _complete_candidate(tree, nominal, tv_radius, fallback, model)
        for tree in trees.values()
        if memory_limit_bytes is None
        or _memory_bytes(tree, len(nominal), model) <= memory_limit_bytes
    ]
    if not candidates:
        raise ValueError("memory_limit_bytes excludes every feasible tree")
    return min(
        candidates,
        key=lambda row: (
            row["score"],
            row["memory_bytes"],
            row["split_count"],
            _canonical(row["serialized_tree"]),
        ),
    )


def _frontier_digest(frontier: list[tuple[float, str, _SearchState]]) -> str:
    identities = sorted(identity for _, identity, _ in frontier)
    return hashlib.sha256(_canonical(identities).encode("utf-8")).hexdigest()


def anytime_tv_branch_and_bound(
    weights: Sequence[float],
    budget: int,
    tv_radius: float,
    *,
    fallback: FallbackName = "fixed_rounds",
    cost_model: ExecutionCostModel | None = None,
    memory_limit_bytes: int | None = None,
    max_expansions: int = 10_000,
    target_relative_gap: float = 0.0,
) -> dict:
    """Best-first TV-DRO search with an independently replayable gap certificate."""
    nominal = validate_problem(weights, budget, 0.0)
    if len(nominal) > MAX_KEYS:
        raise ValueError(f"anytime solver supports at most {MAX_KEYS} keys")
    if not isfinite(tv_radius) or not 0.0 <= tv_radius <= 1.0:
        raise ValueError("tv_radius must lie in [0, 1]")
    if not 0 <= max_expansions <= MAX_EXPANSIONS:
        raise ValueError(
            f"max_expansions must lie in [0, {MAX_EXPANSIONS}]"
        )
    if not isfinite(target_relative_gap) or target_relative_gap < 0.0:
        raise ValueError("target_relative_gap must be finite and non-negative")
    if memory_limit_bytes is not None and memory_limit_bytes < 0:
        raise ValueError("memory_limit_bytes must be non-negative")
    resolve_fallback(fallback)
    model = cost_model or ExecutionCostModel()
    model.validate()
    effective = effective_budget(budget, len(nominal))
    information_floor = _information_theoretic_floor(nominal, model)
    root = IntervalLeaf(1, len(nominal))
    if (
        memory_limit_bytes is not None
        and _memory_bytes(root, len(nominal), model) > memory_limit_bytes
    ):
        raise ValueError("memory_limit_bytes excludes the root tree")

    initial = _initial_incumbent(
        nominal,
        effective,
        tv_radius,
        fallback,
        model,
        memory_limit_bytes,
    )
    incumbent = initial
    root_open = ((1, len(nominal)),)
    root_state = _SearchState(
        tree=root,
        open_leaves=root_open,
        used_budget=0,
        lower_bound=_state_lower_bound(
            root,
            root_open,
            nominal,
            tv_radius,
            fallback,
            model,
            information_floor,
        ),
        identity=_state_identity(root, root_open, 0),
    )
    frontier: list[tuple[float, str, _SearchState]] = [
        (root_state.lower_bound, root_state.identity, root_state)
    ]
    events: list[dict] = []
    pruned = completed = generated = 0
    stop_reason = "frontier_exhausted"

    def push(tree: Tree, open_leaves: tuple[tuple[int, int], ...], used: int) -> None:
        nonlocal generated
        if (
            memory_limit_bytes is not None
            and _memory_bytes(tree, len(nominal), model) > memory_limit_bytes
        ):
            return
        state = _SearchState(
            tree=tree,
            open_leaves=open_leaves,
            used_budget=used,
            lower_bound=_state_lower_bound(
                tree,
                open_leaves,
                nominal,
                tv_radius,
                fallback,
                model,
                information_floor,
            ),
            identity=_state_identity(tree, open_leaves, used),
        )
        heapq.heappush(frontier, (state.lower_bound, state.identity, state))
        generated += 1

    while frontier:
        global_lower = min(incumbent["score"], frontier[0][0])
        relative_gap = (incumbent["score"] - global_lower) / max(
            abs(incumbent["score"]), EPS
        )
        if relative_gap <= target_relative_gap + EPS:
            stop_reason = "target_gap"
            break
        if len(events) >= max_expansions:
            stop_reason = "expansion_limit"
            break

        _, _, state = heapq.heappop(frontier)
        event = {"identity": state.identity}
        if state.lower_bound >= incumbent["score"] - EPS:
            event["action"] = "pruned"
            pruned += 1
        elif not state.open_leaves:
            candidate = _complete_candidate(
                state.tree,
                nominal,
                tv_radius,
                fallback,
                model,
            )
            event["action"] = "complete"
            event["score"] = candidate["score"]
            completed += 1
            if (
                candidate["score"],
                candidate["memory_bytes"],
                candidate["split_count"],
                _canonical(candidate["serialized_tree"]),
            ) < (
                incumbent["score"],
                incumbent["memory_bytes"],
                incumbent["split_count"],
                _canonical(incumbent["serialized_tree"]),
            ):
                incumbent = candidate
        else:
            event["action"] = "expanded"
            decision = state.open_leaves[0]
            remaining = state.open_leaves[1:]
            push(state.tree, remaining, state.used_budget)
            left, right = decision
            if state.used_budget < effective and left < right:
                for threshold in range(left, right):
                    replacement = SplitNode(
                        left,
                        right,
                        threshold,
                        IntervalLeaf(left, threshold),
                        IntervalLeaf(threshold + 1, right),
                    )
                    child_tree = _replace_leaf(state.tree, decision, replacement)
                    child_open = tuple(
                        sorted(
                            remaining
                            + ((left, threshold), (threshold + 1, right))
                        )
                    )
                    push(child_tree, child_open, state.used_budget + 1)
        events.append(event)

    global_lower = (
        incumbent["score"]
        if not frontier
        else min(incumbent["score"], frontier[0][0])
    )
    absolute_gap = max(0.0, incumbent["score"] - global_lower)
    relative_gap = absolute_gap / max(abs(incumbent["score"]), EPS)
    exact = not frontier or relative_gap <= EPS
    certificate = {
        "version": 1,
        "nominal": nominal,
        "budget": effective,
        "tv_radius": tv_radius,
        "fallback": fallback,
        "cost_model": asdict(model),
        "memory_limit_bytes": memory_limit_bytes,
        "max_expansions": max_expansions,
        "target_relative_gap": target_relative_gap,
        "information_theoretic_floor": information_floor,
        "initial_incumbent": {
            "tree": initial["serialized_tree"],
            "score": initial["score"],
        },
        "events": events,
        "stop_reason": stop_reason,
        "final_incumbent": {
            "tree": incumbent["serialized_tree"],
            "score": incumbent["score"],
        },
        "frontier_count": len(frontier),
        "frontier_sha256": _frontier_digest(frontier),
        "global_lower_bound": global_lower,
        "absolute_gap": absolute_gap,
        "relative_gap": relative_gap,
        "exact": exact,
    }
    return {
        **incumbent,
        "solver": "anytime_tv_branch_and_bound",
        "global_lower_bound": global_lower,
        "absolute_gap": absolute_gap,
        "relative_gap": relative_gap,
        "exact": exact,
        "stop_reason": stop_reason,
        "search_stats": {
            "processed_states": len(events),
            "generated_states": generated + 1,
            "pruned_states": pruned,
            "completed_states": completed,
            "frontier_states": len(frontier),
        },
        "certificate": certificate,
    }
