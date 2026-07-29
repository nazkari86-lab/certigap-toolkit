from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from itertools import product

from .core import IntervalLeaf, SplitNode, Tree, _to_serializable, effective_budget


@lru_cache(maxsize=None)
def _trees_with_exact_splits(
    left: int,
    right: int,
    split_total: int,
) -> tuple[Tree, ...]:
    if split_total == 0:
        return (IntervalLeaf(left, right),)
    if left >= right or split_total > right - left:
        return ()

    trees: list[Tree] = []
    for threshold in range(left, right):
        left_capacity = threshold - left
        right_capacity = right - threshold - 1
        for left_splits in range(split_total):
            right_splits = split_total - 1 - left_splits
            if left_splits > left_capacity or right_splits > right_capacity:
                continue
            for left_tree, right_tree in product(
                _trees_with_exact_splits(left, threshold, left_splits),
                _trees_with_exact_splits(threshold + 1, right, right_splits),
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


def enumerate_partial_trees(n: int, max_budget: int) -> tuple[Tree, ...]:
    """Enumerate every ordered partial tree with at most ``max_budget`` splits."""
    if n <= 0:
        raise ValueError("n must be positive")
    if max_budget < 0:
        raise ValueError("max_budget must be non-negative")
    budget = effective_budget(max_budget, n)
    return tuple(
        tree
        for split_total in range(budget + 1)
        for tree in _trees_with_exact_splits(1, n, split_total)
    )


def exact_tree_space_manifest(n: int, max_budget: int) -> dict:
    trees = enumerate_partial_trees(n, max_budget)
    digest = hashlib.sha256()
    counts = [0] * (effective_budget(max_budget, n) + 1)
    for tree in trees:
        serialized = _to_serializable(tree)
        split_total = _serialized_split_count(serialized)
        counts[split_total] += 1
        digest.update(
            json.dumps(serialized, sort_keys=True, separators=(",", ":")).encode("utf-8")
        )
        digest.update(b"\n")
    return {
        "tree_count": len(trees),
        "counts_by_exact_splits": counts,
        "tree_space_sha256": digest.hexdigest(),
    }


def _serialized_split_count(tree: dict) -> int:
    if tree["type"] == "leaf":
        return 0
    return (
        1
        + _serialized_split_count(tree["left"])
        + _serialized_split_count(tree["right"])
    )
