from __future__ import annotations

from .core import EPS, IntervalLeaf, SplitNode, Tree, _leaf_depths, _replace_leaf, _to_serializable, beam_search_best, evaluate_tree, interval_cost, validate_problem
from .verifier import verify_branch_and_bound_certificate


def branch_and_bound_exact(weights: list[float], budget: int, eta: float, max_nodes: int = 200_000) -> dict:
    """Exact exhaustive search with local admissible bounds and a proof trace.

    The trace is deliberately verbose: an independent verifier can reconstruct
    every terminal/split branch and confirm that each pruning decision was safe.
    It is therefore intended for small proof instances, not large benchmarks.
    """
    weights = validate_problem(weights, budget, eta)
    if max_nodes <= 0:
        raise ValueError("max_nodes must be positive")
    n = len(weights)
    incumbent = beam_search_best(weights, budget, eta)
    nodes_visited = 0

    def lower_bound(tree: Tree, open_leaves: tuple[tuple[int, int], ...]) -> float:
        open_set = set(open_leaves)
        average = 0.0
        worst = 0
        for left, right, depth in _leaf_depths(tree):
            cost = depth if (left, right) in open_set else depth + interval_cost(right - left + 1)
            average += sum(weights[left - 1:right]) * cost
            worst = max(worst, cost)
        return (1.0 - eta) * average + eta * worst

    def search(tree: Tree, open_leaves: tuple[tuple[int, int], ...], used_budget: int) -> dict:
        nonlocal incumbent, nodes_visited
        nodes_visited += 1
        if nodes_visited > max_nodes:
            raise RuntimeError(f"branch-and-bound exceeded max_nodes={max_nodes}; no certificate was produced")
        bound = lower_bound(tree, open_leaves)
        trace = {
            "tree": _to_serializable(tree),
            "open_leaves": [list(item) for item in open_leaves],
            "used_budget": used_budget,
            "lower_bound": bound,
        }
        if bound >= incumbent["objective"] - EPS:
            trace["status"] = "pruned"
            return trace
        if not open_leaves:
            evaluation = evaluate_tree(tree, weights, eta)
            if evaluation["objective"] < incumbent["objective"] - EPS:
                incumbent = evaluation | {"budget": budget, "eta": eta}
            trace["status"] = "complete"
            return trace

        decision = open_leaves[0]
        left, right = decision
        remaining_open = open_leaves[1:]
        children = [search(tree, remaining_open, used_budget)]
        if used_budget < budget and left < right:
            for threshold in range(left, right):
                replacement = SplitNode(
                    left=left,
                    right=right,
                    threshold=threshold,
                    left_child=IntervalLeaf(left, threshold),
                    right_child=IntervalLeaf(threshold + 1, right),
                )
                child_tree = _replace_leaf(tree, decision, replacement)
                child_open = tuple(sorted(remaining_open + ((left, threshold), (threshold + 1, right))))
                children.append(search(child_tree, child_open, used_budget + 1))
        trace["status"] = "expanded"
        trace["decision"] = list(decision)
        trace["children"] = children
        return trace

    trace = search(IntervalLeaf(1, n), ((1, n),), 0)
    certificate = {
        "version": 1,
        "incumbent": {"tree": incumbent["serialized_tree"], "objective": incumbent["objective"]},
        "search": trace,
    }
    verification = verify_branch_and_bound_certificate(weights, budget, eta, certificate)
    result = incumbent | {
        "budget": budget,
        "eta": eta,
        "solver": "branch_and_bound",
        "certificate": certificate,
        "proof_stats": verification,
    }
    return result
