from __future__ import annotations

import hashlib
import heapq
import json
from math import ceil, isfinite, log2

from .autodro import ExecutionCostModel, worst_case_tv_expectation
from .core import EPS, IntervalLeaf, SplitNode, Tree
from .generalized import resolve_fallback


MAX_KEYS = 512
MAX_EVENTS = 200_000


class AnytimeVerificationError(ValueError):
    pass


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


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


def _deserialize(value: dict, left: int, right: int) -> Tree:
    if not isinstance(value, dict) or value.get("interval") != [left, right]:
        raise AnytimeVerificationError("tree interval mismatch")
    if value.get("type") == "leaf":
        if set(value) != {"type", "interval"}:
            raise AnytimeVerificationError("malformed leaf")
        return IntervalLeaf(left, right)
    if value.get("type") != "split":
        raise AnytimeVerificationError("unknown tree node")
    threshold = value.get("threshold")
    if not isinstance(threshold, int) or not left <= threshold < right:
        raise AnytimeVerificationError("invalid threshold")
    if set(value) != {"type", "interval", "threshold", "left", "right"}:
        raise AnytimeVerificationError("malformed split")
    return SplitNode(
        left,
        right,
        threshold,
        _deserialize(value["left"], left, threshold),
        _deserialize(value["right"], threshold + 1, right),
    )


def _split_count(tree: Tree) -> int:
    if isinstance(tree, IntervalLeaf):
        return 0
    return 1 + _split_count(tree.left_child) + _split_count(tree.right_child)


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


def _leaf_depths(tree: Tree, depth: int = 0) -> list[tuple[int, int, int]]:
    if isinstance(tree, IntervalLeaf):
        return [(tree.left, tree.right, depth)]
    return _leaf_depths(tree.left_child, depth + 1) + _leaf_depths(
        tree.right_child, depth + 1
    )


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


def _memory(tree: Tree, n: int, model: ExecutionCostModel) -> int:
    return model.key_bytes * n + model.node_bytes * (2 * _split_count(tree) + 1)


def _costs(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    n: int,
    fallback: str,
    model: ExecutionCostModel,
) -> list[float]:
    open_set = set(open_leaves)
    profile = resolve_fallback(fallback)
    result = [0.0] * n
    for left, right, depth in _leaf_depths(tree):
        residual = (
            (0,) * (right - left + 1)
            if (left, right) in open_set
            else profile(left, right)
        )
        for key, fallback_cost in zip(range(left, right + 1), residual):
            result[key - 1] = (
                depth * model.routing_comparison_cost
                + fallback_cost * model.fallback_comparison_cost
            )
    return result


def _score(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    nominal: list[float],
    radius: float,
    fallback: str,
    model: ExecutionCostModel,
) -> float:
    costs = _costs(tree, open_leaves, len(nominal), fallback, model)
    robust = worst_case_tv_expectation(nominal, costs, radius)
    return (
        robust["robust_expectation"]
        + model.tail_weight * max(costs)
        + model.memory_cost_per_byte * _memory(tree, len(nominal), model)
        + model.build_cost_per_split * _split_count(tree)
    )


def _structural_floor(
    tree: Tree,
    open_leaves: tuple[tuple[int, int], ...],
    nominal: list[float],
    fallback: str,
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
                entropy = -sum(
                    (probability / mass) * log2(probability / mass)
                    for probability in probabilities
                    if probability > EPS
                )
                expected += mass * minimum_comparison_cost * entropy
        else:
            expected += sum(
                probability * fallback_cost * model.fallback_comparison_cost
                for probability, fallback_cost in zip(
                    probabilities,
                    profile(left, right),
                )
            )
    maximum_depth_floor = (
        0 if len(nominal) <= 1 else ceil(log2(len(nominal)))
    )
    return (
        expected
        + model.tail_weight
        * minimum_comparison_cost
        * maximum_depth_floor
        + model.memory_cost_per_byte * _memory(tree, len(nominal), model)
        + model.build_cost_per_split * _split_count(tree)
    )


def _information_floor(nominal: list[float], model: ExecutionCostModel) -> float:
    entropy = -sum(
        probability * log2(probability)
        for probability in nominal
        if probability > 0
    )
    comparison_floor = min(
        model.routing_comparison_cost,
        model.fallback_comparison_cost,
    )
    maximum_depth_floor = 0 if len(nominal) <= 1 else ceil(log2(len(nominal)))
    minimum_memory = model.key_bytes * len(nominal) + model.node_bytes
    return (
        comparison_floor * entropy
        + model.tail_weight * comparison_floor * maximum_depth_floor
        + model.memory_cost_per_byte * minimum_memory
    )


def _frontier_digest(frontier: list[tuple[float, str, tuple]]) -> str:
    identities = sorted(identity for _, identity, _ in frontier)
    return hashlib.sha256(_canonical(identities).encode("utf-8")).hexdigest()


def verify_anytime_tv_certificate(artifact: dict) -> dict:
    """Replay every deterministic search transition and certify the final gap."""
    if not isinstance(artifact, dict) or artifact.get("version") != 1:
        raise AnytimeVerificationError("unsupported anytime certificate")
    nominal = artifact.get("nominal")
    if (
        not isinstance(nominal, list)
        or not nominal
        or any(not isinstance(value, (int, float)) or not isfinite(value) or value < 0 for value in nominal)
        or abs(sum(nominal) - 1.0) > 1e-9
    ):
        raise AnytimeVerificationError("invalid nominal distribution")
    n = len(nominal)
    if n > MAX_KEYS:
        raise AnytimeVerificationError("certificate exceeds maximum key count")
    budget = artifact.get("budget")
    radius = artifact.get("tv_radius")
    if not isinstance(budget, int) or not 0 <= budget <= n - 1:
        raise AnytimeVerificationError("invalid budget")
    if not isinstance(radius, (int, float)) or not isfinite(radius) or not 0 <= radius <= 1:
        raise AnytimeVerificationError("invalid TV radius")
    fallback = artifact.get("fallback")
    resolve_fallback(fallback)
    try:
        model = ExecutionCostModel(**artifact["cost_model"])
        model.validate()
    except (KeyError, TypeError, ValueError) as exc:
        raise AnytimeVerificationError("invalid cost model") from exc
    memory_limit = artifact.get("memory_limit_bytes")
    if memory_limit is not None and (
        not isinstance(memory_limit, int) or memory_limit < 0
    ):
        raise AnytimeVerificationError("invalid memory limit")
    information_floor = _information_floor(nominal, model)
    if (
        abs(
            float(artifact.get("information_theoretic_floor"))
            - information_floor
        )
        > EPS
    ):
        raise AnytimeVerificationError("information-theoretic floor mismatch")

    initial_data = artifact.get("initial_incumbent")
    final_data = artifact.get("final_incumbent")
    if not isinstance(initial_data, dict) or not isinstance(final_data, dict):
        raise AnytimeVerificationError("missing incumbents")
    initial_tree = _deserialize(initial_data.get("tree"), 1, n)
    if memory_limit is not None and _memory(initial_tree, n, model) > memory_limit:
        raise AnytimeVerificationError("initial incumbent violates memory limit")
    initial_score = _score(initial_tree, (), nominal, radius, fallback, model)
    if abs(initial_score - float(initial_data.get("score"))) > EPS:
        raise AnytimeVerificationError("initial incumbent score mismatch")
    incumbent_tree = initial_tree
    incumbent_score = initial_score

    root = IntervalLeaf(1, n)
    root_open = ((1, n),)
    root_bound = max(
        _score(root, root_open, nominal, radius, fallback, model),
        information_floor,
        _structural_floor(
            root,
            root_open,
            nominal,
            fallback,
            model,
        ),
    )
    root_id = _identity(root, root_open, 0)
    frontier: list[tuple[float, str, tuple]] = [
        (root_bound, root_id, (root, root_open, 0))
    ]

    events = artifact.get("events")
    max_expansions = artifact.get("max_expansions")
    target_gap = artifact.get("target_relative_gap")
    if (
        not isinstance(events, list)
        or len(events) > MAX_EVENTS
        or not isinstance(max_expansions, int)
        or max_expansions < 0
        or len(events) > max_expansions
        or not isinstance(target_gap, (int, float))
        or not isfinite(target_gap)
        or target_gap < 0
    ):
        raise AnytimeVerificationError("invalid search limits")

    pruned = completed = generated = 0

    def push(tree: Tree, open_leaves: tuple[tuple[int, int], ...], used: int) -> None:
        nonlocal generated
        if memory_limit is not None and _memory(tree, n, model) > memory_limit:
            return
        bound = max(
            _score(tree, open_leaves, nominal, radius, fallback, model),
            information_floor,
            _structural_floor(
                tree,
                open_leaves,
                nominal,
                fallback,
                model,
            ),
        )
        identity = _identity(tree, open_leaves, used)
        heapq.heappush(frontier, (bound, identity, (tree, open_leaves, used)))
        generated += 1

    for event in events:
        if not frontier:
            raise AnytimeVerificationError("event exists after frontier exhaustion")
        bound, identity, state = heapq.heappop(frontier)
        tree, open_leaves, used = state
        if not isinstance(event, dict) or event.get("identity") != identity:
            raise AnytimeVerificationError("event does not match best-first frontier")
        if bound >= incumbent_score - EPS:
            expected_action = "pruned"
            pruned += 1
        elif not open_leaves:
            expected_action = "complete"
            completed += 1
            candidate_score = _score(tree, (), nominal, radius, fallback, model)
            if abs(candidate_score - float(event.get("score"))) > EPS:
                raise AnytimeVerificationError("completed score mismatch")
            candidate_key = (
                candidate_score,
                _memory(tree, n, model),
                _split_count(tree),
                _canonical(_serialize(tree)),
            )
            incumbent_key = (
                incumbent_score,
                _memory(incumbent_tree, n, model),
                _split_count(incumbent_tree),
                _canonical(_serialize(incumbent_tree)),
            )
            if candidate_key < incumbent_key:
                incumbent_tree = tree
                incumbent_score = candidate_score
        else:
            expected_action = "expanded"
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
        if event.get("action") != expected_action:
            raise AnytimeVerificationError("event action is invalid")

    global_lower = (
        incumbent_score
        if not frontier
        else min(incumbent_score, frontier[0][0])
    )
    absolute_gap = max(0.0, incumbent_score - global_lower)
    relative_gap = absolute_gap / max(abs(incumbent_score), EPS)
    stop_reason = artifact.get("stop_reason")
    valid_stop = (
        (stop_reason == "frontier_exhausted" and not frontier)
        or (
            stop_reason == "target_gap"
            and relative_gap <= float(target_gap) + EPS
        )
        or (
            stop_reason == "expansion_limit"
            and len(events) == max_expansions
            and bool(frontier)
        )
    )
    if not valid_stop:
        raise AnytimeVerificationError("stop reason is not justified")
    final_tree = _deserialize(final_data.get("tree"), 1, n)
    if _serialize(final_tree) != _serialize(incumbent_tree):
        raise AnytimeVerificationError("final incumbent tree mismatch")
    reported = (
        ("score", incumbent_score),
        ("global_lower_bound", global_lower),
        ("absolute_gap", absolute_gap),
        ("relative_gap", relative_gap),
    )
    for field, expected in reported:
        source = final_data if field == "score" else artifact
        if abs(float(source.get(field)) - expected) > EPS:
            raise AnytimeVerificationError(f"{field} mismatch")
    if artifact.get("frontier_count") != len(frontier):
        raise AnytimeVerificationError("frontier count mismatch")
    if artifact.get("frontier_sha256") != _frontier_digest(frontier):
        raise AnytimeVerificationError("frontier digest mismatch")
    exact = not frontier or relative_gap <= EPS
    if artifact.get("exact") is not exact:
        raise AnytimeVerificationError("exact flag mismatch")
    return {
        "verified": True,
        "processed_states": len(events),
        "generated_states": generated + 1,
        "pruned_states": pruned,
        "completed_states": completed,
        "frontier_states": len(frontier),
        "objective": incumbent_score,
        "global_lower_bound": global_lower,
        "relative_gap": relative_gap,
        "exact": exact,
    }
