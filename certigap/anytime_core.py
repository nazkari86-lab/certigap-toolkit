from __future__ import annotations

import hashlib
import heapq
import json
from dataclasses import dataclass
from math import isfinite

from .core import (
    EPS,
    IntervalLeaf,
    SplitNode,
    Tree,
    _leaf_depths,
    _replace_leaf,
    _to_serializable,
    beam_search_best,
    entropy_lower_bound,
    evaluate_tree,
    interval_cost,
    max_cost_lower_bound,
    validate_problem,
)
from .anytime_core_verifier import verify_anytime_core_certificate


MAX_KEYS = 128
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


def _partial_lower_bound(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    weights: list[float],
    eta: float,
    global_floor: float,
) -> float:
    """Use routing depth alone for unresolved leaves.

    Every completion adds a non-negative fallback/search cost to each open
    leaf, so this componentwise relaxation is admissible for both objective
    coordinates.
    """
    open_set = set(open_leaves)
    average = 0.0
    maximum = 0
    for left, right, depth in _leaf_depths(tree):
        cost = depth if (left, right) in open_set else depth + interval_cost(
            right - left + 1
        )
        average += sum(weights[left - 1 : right]) * cost
        maximum = max(maximum, cost)
    return max(global_floor, (1.0 - eta) * average + eta * maximum)


def _frontier_digest(frontier: list[tuple[float, str, _SearchState]]) -> str:
    identities = sorted(identity for _, identity, _ in frontier)
    return hashlib.sha256(_canonical(identities).encode("utf-8")).hexdigest()


def anytime_branch_and_bound(
    weights: list[float],
    budget: int,
    eta: float,
    *,
    max_expansions: int = 10_000,
    target_relative_gap: float = 0.0,
) -> dict:
    """Return a certified interval for the ordinary CertiGap objective.

    The solver searches the full threshold grammar.  It may stop early, but
    the returned certificate always proves `lower_bound <= OPT <= objective`.
    It is intentionally bounded to proof-sized/moderate instances because the
    certificate replays every explored transition independently.
    """
    normalized = validate_problem(weights, budget, eta)
    n = len(normalized)
    if n > MAX_KEYS:
        raise ValueError(f"anytime solver supports at most {MAX_KEYS} keys")
    if not isinstance(max_expansions, int) or not 0 <= max_expansions <= MAX_EXPANSIONS:
        raise ValueError(
            f"max_expansions must be an integer in [0, {MAX_EXPANSIONS}]"
        )
    if not isfinite(target_relative_gap) or target_relative_gap < 0.0:
        raise ValueError("target_relative_gap must be finite and non-negative")

    effective_budget = min(budget, n - 1)
    global_floor = (
        (1.0 - eta) * entropy_lower_bound(normalized)
        + eta * max_cost_lower_bound(n, effective_budget)
    )
    initial = beam_search_best(normalized, effective_budget, eta, beam_width=32)
    incumbent = initial
    root = IntervalLeaf(1, n)
    root_open = ((1, n),)
    root_state = _SearchState(
        tree=root,
        open_leaves=root_open,
        used_budget=0,
        lower_bound=_partial_lower_bound(
            root, root_open, normalized, eta, global_floor
        ),
        identity=_state_identity(root, root_open, 0),
    )
    frontier: list[tuple[float, str, _SearchState]] = [
        (root_state.lower_bound, root_state.identity, root_state)
    ]
    events: list[dict] = []
    generated = 1
    pruned = 0
    completed = 0
    stop_reason = "frontier_exhausted"

    def push(
        tree: Tree,
        open_leaves: tuple[tuple[int, int], ...],
        used_budget: int,
    ) -> None:
        nonlocal generated
        state = _SearchState(
            tree=tree,
            open_leaves=open_leaves,
            used_budget=used_budget,
            lower_bound=_partial_lower_bound(
                tree, open_leaves, normalized, eta, global_floor
            ),
            identity=_state_identity(tree, open_leaves, used_budget),
        )
        heapq.heappush(frontier, (state.lower_bound, state.identity, state))
        generated += 1

    while frontier:
        lower = min(incumbent["objective"], frontier[0][0])
        relative_gap = (incumbent["objective"] - lower) / max(
            abs(incumbent["objective"]), EPS
        )
        if relative_gap <= target_relative_gap + EPS:
            stop_reason = "target_gap"
            break
        if len(events) >= max_expansions:
            stop_reason = "expansion_limit"
            break

        _, _, state = heapq.heappop(frontier)
        event = {"identity": state.identity}
        if state.lower_bound >= incumbent["objective"] - EPS:
            event["action"] = "pruned"
            pruned += 1
        elif not state.open_leaves:
            evaluation = evaluate_tree(state.tree, normalized, eta)
            event["action"] = "complete"
            event["objective"] = evaluation["objective"]
            completed += 1
            if evaluation["objective"] < incumbent["objective"] - EPS:
                incumbent = evaluation
        else:
            event["action"] = "expanded"
            decision = state.open_leaves[0]
            remaining = state.open_leaves[1:]
            push(state.tree, remaining, state.used_budget)
            left, right = decision
            if state.used_budget < effective_budget and left < right:
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

    lower_bound = (
        incumbent["objective"]
        if not frontier
        else min(incumbent["objective"], frontier[0][0])
    )
    absolute_gap = max(0.0, incumbent["objective"] - lower_bound)
    relative_gap = absolute_gap / max(abs(incumbent["objective"]), EPS)
    exact = absolute_gap <= EPS
    certificate = {
        "schema": "certigap-anytime-core-v1",
        "weights": normalized,
        "budget": effective_budget,
        "eta": eta,
        "max_expansions": max_expansions,
        "target_relative_gap": target_relative_gap,
        "global_floor": global_floor,
        "initial_incumbent": {
            "tree": initial["serialized_tree"],
            "objective": initial["objective"],
        },
        "events": events,
        "stop_reason": stop_reason,
        "final_incumbent": {
            "tree": incumbent["serialized_tree"],
            "objective": incumbent["objective"],
        },
        "frontier_count": len(frontier),
        "frontier_sha256": _frontier_digest(frontier),
        "lower_bound": lower_bound,
        "upper_bound": incumbent["objective"],
        "absolute_gap": absolute_gap,
        "relative_gap": relative_gap,
        "exact": exact,
    }
    verification = verify_anytime_core_certificate(certificate)
    return {
        **incumbent,
        "solver": "anytime_branch_and_bound",
        "lower_bound": lower_bound,
        "upper_bound": incumbent["objective"],
        "absolute_gap": absolute_gap,
        "relative_gap": relative_gap,
        "exact": exact,
        "stop_reason": stop_reason,
        "search_stats": {
            "processed_states": len(events),
            "generated_states": generated,
            "pruned_states": pruned,
            "completed_states": completed,
            "frontier_states": len(frontier),
        },
        "certificate": certificate,
        "verification": verification,
    }
