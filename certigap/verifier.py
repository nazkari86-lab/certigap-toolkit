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


def _serialized_leaf_depths(tree: dict, n: int, depth: int = 0) -> list[tuple[int, int, int]]:
    node_type = tree.get("type")
    interval = tree.get("interval")
    if not isinstance(interval, list) or len(interval) != 2:
        raise VerificationError("serialized node has no valid interval")
    left, right = interval
    if not isinstance(left, int) or not isinstance(right, int) or not (1 <= left <= right <= n):
        raise VerificationError("serialized node interval is invalid")
    if node_type == "leaf":
        return [(left, right, depth)]
    if node_type != "split":
        raise VerificationError("serialized node type is invalid")
    threshold = tree.get("threshold")
    if not isinstance(threshold, int) or not (left <= threshold < right):
        raise VerificationError("serialized split threshold is invalid")
    left_leaves = _serialized_leaf_depths(tree.get("left"), n, depth + 1)
    right_leaves = _serialized_leaf_depths(tree.get("right"), n, depth + 1)
    if left_leaves[0][:2] != (left, left_leaves[0][1]) or left_leaves[-1][1] != threshold:
        raise VerificationError("serialized left child does not match its parent")
    if right_leaves[0][0] != threshold + 1 or right_leaves[-1][1] != right:
        raise VerificationError("serialized right child does not match its parent")
    return left_leaves + right_leaves


def _serialized_evaluation(tree: dict, weights: list[float], eta: float, open_leaves: tuple[tuple[int, int], ...] = ()) -> dict:
    n = len(weights)
    leaves = _serialized_leaf_depths(tree, n)
    if leaves[0][:2] != (1, leaves[0][1]) or leaves[-1][1] != n:
        raise VerificationError("serialized tree does not cover all ranks")
    expected = 1
    for left, right, _ in leaves:
        if left != expected:
            raise VerificationError("serialized leaves do not form a partition")
        expected = right + 1
    open_set = set(open_leaves)
    if not open_set.issubset({(left, right) for left, right, _ in leaves}):
        raise VerificationError("open leaves are not leaves of the serialized tree")
    average = 0.0
    max_cost = 0
    for left, right, depth in leaves:
        cost = depth if (left, right) in open_set else depth + _interval_cost(right - left + 1)
        average += sum(weights[left - 1:right]) * cost
        max_cost = max(max_cost, cost)
    return {
        "average_cost": average,
        "max_cost": max_cost,
        "objective": (1.0 - eta) * average + eta * max_cost,
        "leaves": leaves,
    }


def _replace_serialized_leaf(tree: dict, target: tuple[int, int], replacement: dict) -> dict:
    if tree["type"] == "leaf":
        return replacement if tuple(tree["interval"]) == target else tree
    return {
        "type": "split",
        "interval": list(tree["interval"]),
        "threshold": tree["threshold"],
        "left": _replace_serialized_leaf(tree["left"], target, replacement),
        "right": _replace_serialized_leaf(tree["right"], target, replacement),
    }


def verify_branch_and_bound_certificate(weights: list[float], budget: int, eta: float, artifact: dict) -> dict:
    """Verify a complete branch-and-bound trace without importing a solver.

    Every expanded node must list its terminal child and every legal split of
    its selected open leaf. Every pruned node must have a valid local lower
    bound at least as large as the submitted incumbent.
    """
    _validate_inputs(weights, budget, eta)
    n = len(weights)
    incumbent = artifact.get("incumbent")
    if not isinstance(incumbent, dict) or not isinstance(incumbent.get("tree"), dict):
        raise VerificationError("branch-and-bound artifact has no incumbent tree")
    incumbent_eval = _serialized_evaluation(incumbent["tree"], weights, eta)
    incumbent_objective = float(incumbent.get("objective"))
    if abs(incumbent_objective - incumbent_eval["objective"]) > EPS:
        raise VerificationError("incumbent objective does not match incumbent tree")

    root_tree = {"type": "leaf", "interval": [1, n]}
    visited = 0
    pruned = 0
    completed = 0

    def visit(node: dict, expected_tree: dict, expected_open: tuple[tuple[int, int], ...], used_budget: int) -> None:
        nonlocal visited, pruned, completed
        visited += 1
        if node.get("tree") != expected_tree:
            raise VerificationError("trace tree differs from the required branch state")
        encoded_open = tuple(tuple(item) for item in node.get("open_leaves", []))
        if encoded_open != expected_open:
            raise VerificationError("trace open leaves differ from the required branch state")
        if node.get("used_budget") != used_budget:
            raise VerificationError("trace budget differs from the required branch state")
        lower = _serialized_evaluation(expected_tree, weights, eta, expected_open)
        if abs(float(node.get("lower_bound")) - lower["objective"]) > EPS:
            raise VerificationError("trace lower bound is invalid")
        status = node.get("status")
        if status == "pruned":
            if lower["objective"] < incumbent_objective - EPS:
                raise VerificationError("pruned state could still beat the incumbent")
            pruned += 1
            return
        if status == "complete":
            if expected_open:
                raise VerificationError("complete state still has unresolved leaves")
            if lower["objective"] < incumbent_objective - EPS:
                raise VerificationError("complete state beats the claimed incumbent")
            completed += 1
            return
        if status != "expanded" or not expected_open:
            raise VerificationError("trace state is neither pruned, complete, nor a valid expansion")
        decision = tuple(node.get("decision", []))
        if decision != expected_open[0]:
            raise VerificationError("trace expands a noncanonical open leaf")
        children = node.get("children")
        if not isinstance(children, list):
            raise VerificationError("expanded state has no child list")
        terminal_open = expected_open[1:]
        expected_children: list[tuple[dict, tuple[tuple[int, int], ...], int]] = [(expected_tree, terminal_open, used_budget)]
        left, right = decision
        if used_budget < budget and left < right:
            for threshold in range(left, right):
                replacement = {
                    "type": "split",
                    "interval": [left, right],
                    "threshold": threshold,
                    "left": {"type": "leaf", "interval": [left, threshold]},
                    "right": {"type": "leaf", "interval": [threshold + 1, right]},
                }
                child_tree = _replace_serialized_leaf(expected_tree, decision, replacement)
                child_open = tuple(sorted(terminal_open + ((left, threshold), (threshold + 1, right))))
                expected_children.append((child_tree, child_open, used_budget + 1))
        if len(children) != len(expected_children):
            raise VerificationError("expanded state omits or adds legal branches")
        for child, expected in zip(children, expected_children):
            visit(child, *expected)

    search = artifact.get("search")
    if not isinstance(search, dict):
        raise VerificationError("branch-and-bound artifact has no search trace")
    visit(search, root_tree, ((1, n),), 0)
    return {"visited_nodes": visited, "pruned_nodes": pruned, "complete_nodes": completed, "objective": incumbent_objective}
