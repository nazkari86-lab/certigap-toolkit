from __future__ import annotations

import hashlib
import heapq
import json
from math import ceil, isfinite, log2

from .core import EPS, IntervalLeaf, SplitNode, Tree


MAX_KEYS = 128
MAX_EVENTS = 200_000


class AnytimeCoreVerificationError(ValueError):
    pass


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _interval_cost(size: int) -> int:
    return 0 if size <= 1 else ceil(log2(size))


def _serialize(tree: Tree) -> dict:
    if isinstance(tree, IntervalLeaf):
        return {"type": "leaf", "interval": [tree.left, tree.right]}
    return {
        "type": "split",
        "interval": [tree.left, tree.right],
        "threshold": tree.threshold,
        "left": _serialize(tree.left_child),
        "right": _serialize(tree.right_child),
    }


def _deserialize(value: object, left: int, right: int) -> Tree:
    if not isinstance(value, dict) or value.get("interval") != [left, right]:
        raise AnytimeCoreVerificationError("tree interval mismatch")
    if value.get("type") == "leaf":
        if set(value) != {"type", "interval"}:
            raise AnytimeCoreVerificationError("malformed leaf")
        return IntervalLeaf(left, right)
    if value.get("type") != "split":
        raise AnytimeCoreVerificationError("unknown tree node")
    threshold = value.get("threshold")
    if (
        not isinstance(threshold, int)
        or isinstance(threshold, bool)
        or not left <= threshold < right
        or set(value) != {"type", "interval", "threshold", "left", "right"}
    ):
        raise AnytimeCoreVerificationError("malformed split")
    return SplitNode(
        left,
        right,
        threshold,
        _deserialize(value["left"], left, threshold),
        _deserialize(value["right"], threshold + 1, right),
    )


def _leaf_depths(tree: Tree, depth: int = 0) -> list[tuple[int, int, int]]:
    if isinstance(tree, IntervalLeaf):
        return [(tree.left, tree.right, depth)]
    return _leaf_depths(tree.left_child, depth + 1) + _leaf_depths(
        tree.right_child, depth + 1
    )


def _replace(tree: Tree, target: tuple[int, int], replacement: Tree) -> Tree:
    if isinstance(tree, IntervalLeaf):
        return replacement if (tree.left, tree.right) == target else tree
    return SplitNode(
        tree.left,
        tree.right,
        tree.threshold,
        _replace(tree.left_child, target, replacement),
        _replace(tree.right_child, target, replacement),
    )


def _split_count(tree: Tree) -> int:
    if isinstance(tree, IntervalLeaf):
        return 0
    return 1 + _split_count(tree.left_child) + _split_count(tree.right_child)


def _identity(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    used_budget: int,
) -> str:
    payload = {
        "tree": _serialize(tree),
        "open_leaves": [list(item) for item in open_leaves],
        "used_budget": used_budget,
    }
    return hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _evaluate(tree: Tree, weights: list[float], eta: float) -> dict:
    costs = [0] * len(weights)
    for left, right, depth in _leaf_depths(tree):
        cost = depth + _interval_cost(right - left + 1)
        for key in range(left - 1, right):
            costs[key] = cost
    average = sum(weight * cost for weight, cost in zip(weights, costs))
    maximum = max(costs)
    return {
        "average_cost": average,
        "max_cost": maximum,
        "objective": (1.0 - eta) * average + eta * maximum,
        "split_count": _split_count(tree),
    }


def _global_floor(weights: list[float], budget: int, eta: float) -> float:
    entropy = -sum(weight * log2(weight) for weight in weights if weight > 0.0)
    largest_leaf = ceil(len(weights) / (budget + 1))
    return (1.0 - eta) * entropy + eta * _interval_cost(largest_leaf)


def _partial_lower_bound(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    weights: list[float],
    eta: float,
    global_floor: float,
) -> float:
    open_set = set(open_leaves)
    average = 0.0
    maximum = 0
    for left, right, depth in _leaf_depths(tree):
        cost = depth if (left, right) in open_set else depth + _interval_cost(right - left + 1)
        average += sum(weights[left - 1 : right]) * cost
        maximum = max(maximum, cost)
    return max(global_floor, (1.0 - eta) * average + eta * maximum)


def _frontier_digest(frontier: list[tuple[float, str, tuple]]) -> str:
    return hashlib.sha256(
        _canonical(sorted(identity for _, identity, _ in frontier)).encode("utf-8")
    ).hexdigest()


def verify_anytime_core_certificate(artifact: dict) -> dict:
    """Replay a full-grammar ordinary-CertiGap anytime search certificate."""
    if (
        not isinstance(artifact, dict)
        or artifact.get("schema") != "certigap-anytime-core-v1"
    ):
        raise AnytimeCoreVerificationError("unsupported anytime-core certificate")
    weights = artifact.get("weights")
    if (
        not isinstance(weights, list)
        or not weights
        or len(weights) > MAX_KEYS
        or any(
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not isfinite(float(weight))
            or float(weight) < 0.0
            for weight in weights
        )
        or abs(sum(weights) - 1.0) > EPS
    ):
        raise AnytimeCoreVerificationError("invalid normalized weights")
    normalized = [float(weight) for weight in weights]
    n = len(normalized)
    budget = artifact.get("budget")
    eta = artifact.get("eta")
    if (
        not isinstance(budget, int)
        or isinstance(budget, bool)
        or not 0 <= budget <= n - 1
        or isinstance(eta, bool)
        or not isinstance(eta, (int, float))
        or not isfinite(float(eta))
        or not 0.0 <= float(eta) <= 1.0
    ):
        raise AnytimeCoreVerificationError("invalid budget or eta")
    eta_value = float(eta)
    global_floor = _global_floor(normalized, budget, eta_value)
    if abs(float(artifact.get("global_floor")) - global_floor) > EPS:
        raise AnytimeCoreVerificationError("global floor mismatch")

    max_expansions = artifact.get("max_expansions")
    target_gap = artifact.get("target_relative_gap")
    events = artifact.get("events")
    if (
        not isinstance(max_expansions, int)
        or not 0 <= max_expansions <= MAX_EVENTS
        or isinstance(target_gap, bool)
        or not isinstance(target_gap, (int, float))
        or not isfinite(float(target_gap))
        or float(target_gap) < 0.0
        or not isinstance(events, list)
        or len(events) > max_expansions
    ):
        raise AnytimeCoreVerificationError("invalid search limits")

    initial = artifact.get("initial_incumbent")
    final = artifact.get("final_incumbent")
    if not isinstance(initial, dict) or not isinstance(final, dict):
        raise AnytimeCoreVerificationError("certificate omits an incumbent")
    incumbent_tree = _deserialize(initial.get("tree"), 1, n)
    incumbent = _evaluate(incumbent_tree, normalized, eta_value)
    if incumbent["split_count"] > budget or abs(
        incumbent["objective"] - float(initial.get("objective"))
    ) > EPS:
        raise AnytimeCoreVerificationError("initial incumbent does not replay")

    root = IntervalLeaf(1, n)
    root_open = ((1, n),)
    root_bound = _partial_lower_bound(
        root, root_open, normalized, eta_value, global_floor
    )
    frontier: list[tuple[float, str, tuple]] = [
        (root_bound, _identity(root, root_open, 0), (root, root_open, 0))
    ]
    generated = 1
    pruned = 0
    completed = 0

    def push(
        tree: Tree, open_leaves: tuple[tuple[int, int], ...], used_budget: int
    ) -> None:
        nonlocal generated
        bound = _partial_lower_bound(
            tree, open_leaves, normalized, eta_value, global_floor
        )
        identity = _identity(tree, open_leaves, used_budget)
        heapq.heappush(frontier, (bound, identity, (tree, open_leaves, used_budget)))
        generated += 1

    for event in events:
        if not frontier:
            raise AnytimeCoreVerificationError("event follows an empty frontier")
        bound, identity, state = heapq.heappop(frontier)
        tree, open_leaves, used = state
        if not isinstance(event, dict) or event.get("identity") != identity:
            raise AnytimeCoreVerificationError("event is not the best-first state")
        if bound >= incumbent["objective"] - EPS:
            action = "pruned"
            pruned += 1
        elif not open_leaves:
            action = "complete"
            candidate = _evaluate(tree, normalized, eta_value)
            if abs(candidate["objective"] - float(event.get("objective"))) > EPS:
                raise AnytimeCoreVerificationError("completed objective mismatch")
            completed += 1
            if candidate["objective"] < incumbent["objective"] - EPS:
                incumbent_tree = tree
                incumbent = candidate
        else:
            action = "expanded"
            decision = open_leaves[0]
            remaining = open_leaves[1:]
            push(tree, remaining, used)
            left, right = decision
            if used < budget and left < right:
                for threshold in range(left, right):
                    replacement = SplitNode(
                        left,
                        right,
                        threshold,
                        IntervalLeaf(left, threshold),
                        IntervalLeaf(threshold + 1, right),
                    )
                    child = _replace(tree, decision, replacement)
                    child_open = tuple(
                        sorted(
                            remaining
                            + ((left, threshold), (threshold + 1, right))
                        )
                    )
                    push(child, child_open, used + 1)
        if event.get("action") != action:
            raise AnytimeCoreVerificationError("event action mismatch")

    lower_bound = (
        incumbent["objective"]
        if not frontier
        else min(incumbent["objective"], frontier[0][0])
    )
    absolute_gap = max(0.0, incumbent["objective"] - lower_bound)
    relative_gap = absolute_gap / max(abs(incumbent["objective"]), EPS)
    exact = absolute_gap <= EPS
    final_tree = _deserialize(final.get("tree"), 1, n)
    if _serialize(final_tree) != _serialize(incumbent_tree) or abs(
        float(final.get("objective")) - incumbent["objective"]
    ) > EPS:
        raise AnytimeCoreVerificationError("final incumbent does not replay")
    expected = {
        "frontier_count": len(frontier),
        "frontier_sha256": _frontier_digest(frontier),
        "lower_bound": lower_bound,
        "upper_bound": incumbent["objective"],
        "absolute_gap": absolute_gap,
        "relative_gap": relative_gap,
        "exact": exact,
    }
    for field, value in expected.items():
        supplied = artifact.get(field)
        if isinstance(value, bool):
            if supplied is not value:
                raise AnytimeCoreVerificationError(f"{field} does not replay")
        elif isinstance(value, int):
            if supplied != value:
                raise AnytimeCoreVerificationError(f"{field} does not replay")
        elif isinstance(value, str):
            if supplied != value:
                raise AnytimeCoreVerificationError(f"{field} does not replay")
        elif (
            isinstance(supplied, bool)
            or not isinstance(supplied, (int, float))
            or not isfinite(float(supplied))
            or abs(float(supplied) - value) > EPS
        ):
            raise AnytimeCoreVerificationError(f"{field} does not replay")
    stop_reason = artifact.get("stop_reason")
    if stop_reason not in {"frontier_exhausted", "target_gap", "expansion_limit"}:
        raise AnytimeCoreVerificationError("invalid stop reason")
    if stop_reason == "frontier_exhausted" and frontier:
        raise AnytimeCoreVerificationError("frontier-exhausted certificate has pending states")
    if stop_reason == "expansion_limit" and len(events) != max_expansions:
        raise AnytimeCoreVerificationError("expansion-limit certificate stopped early")
    if stop_reason == "target_gap" and relative_gap > float(target_gap) + EPS:
        raise AnytimeCoreVerificationError("target-gap certificate did not reach target")
    return {
        "verified": True,
        **expected,
        "processed_states": len(events),
        "generated_states": generated,
        "pruned_states": pruned,
        "completed_states": completed,
        "scope": (
            "full threshold grammar; replay-verified additive optimality "
            "interval, not a fixed multiplicative approximation ratio"
        ),
    }
