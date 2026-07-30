from __future__ import annotations

import math
from typing import Any


class PrunedBeamVerificationError(ValueError):
    pass


def _close(left: float, right: float, tolerance: float = 2e-9) -> bool:
    return abs(left - right) <= tolerance * max(1.0, abs(left), abs(right))


def _interval_cost(width: int) -> int:
    return 0 if width <= 1 else math.ceil(math.log2(width))


def _tree_costs(
    node: Any,
    left: int,
    right: int,
    depth: int,
) -> tuple[list[int], int]:
    if not isinstance(node, dict) or node.get("interval") != [left, right]:
        raise PrunedBeamVerificationError("tree interval mismatch")
    if node.get("type") == "leaf":
        if set(node) != {"type", "interval"}:
            raise PrunedBeamVerificationError("malformed leaf")
        cost = depth + _interval_cost(right - left + 1)
        return [cost] * (right - left + 1), 0
    if node.get("type") != "split":
        raise PrunedBeamVerificationError("unknown tree node")
    if set(node) != {
        "type",
        "interval",
        "threshold",
        "left",
        "right",
    }:
        raise PrunedBeamVerificationError("malformed split")
    threshold = node["threshold"]
    if (
        not isinstance(threshold, int)
        or isinstance(threshold, bool)
        or not left <= threshold < right
    ):
        raise PrunedBeamVerificationError("invalid threshold")
    left_costs, left_splits = _tree_costs(
        node["left"], left, threshold, depth + 1
    )
    right_costs, right_splits = _tree_costs(
        node["right"], threshold + 1, right, depth + 1
    )
    return left_costs + right_costs, 1 + left_splits + right_splits


def verify_pruned_beam_certificate(
    weights: list[float],
    artifact: dict,
) -> dict:
    """Replay a scalable C++ heuristic result without importing a solver."""
    if (
        not isinstance(artifact, dict)
        or artifact.get("schema") != "certigap-pruned-beam-v1"
    ):
        raise PrunedBeamVerificationError("unsupported pruned-beam schema")
    n = artifact.get("n")
    budget = artifact.get("budget")
    requested_budget = artifact.get("requested_budget")
    eta = artifact.get("eta")
    if (
        not isinstance(n, int)
        or isinstance(n, bool)
        or n <= 0
        or len(weights) != n
    ):
        raise PrunedBeamVerificationError("invalid key universe")
    if (
        not isinstance(budget, int)
        or isinstance(budget, bool)
        or not 0 <= budget <= n - 1
        or not isinstance(requested_budget, int)
        or isinstance(requested_budget, bool)
        or requested_budget < budget
    ):
        raise PrunedBeamVerificationError("invalid budget")
    try:
        numeric_weights = [float(weight) for weight in weights]
        eta_value = float(eta)
    except (TypeError, ValueError) as exc:
        raise PrunedBeamVerificationError("non-numeric input") from exc
    if (
        any(
            not math.isfinite(weight) or weight < 0.0
            for weight in numeric_weights
        )
        or sum(numeric_weights) <= 0.0
        or not math.isfinite(eta_value)
        or not 0.0 <= eta_value <= 1.0
    ):
        raise PrunedBeamVerificationError("invalid weights or eta")
    total = sum(numeric_weights)
    normalized = [weight / total for weight in numeric_weights]
    costs, split_count = _tree_costs(artifact.get("tree"), 1, n, 0)
    if split_count > budget:
        raise PrunedBeamVerificationError("tree exceeds budget")
    if artifact.get("per_key_costs") != costs:
        raise PrunedBeamVerificationError("per-key costs do not replay")
    average = sum(weight * cost for weight, cost in zip(normalized, costs))
    maximum = max(costs)
    objective = (1.0 - eta_value) * average + eta_value * maximum
    entropy = -sum(
        weight * math.log2(weight) for weight in normalized if weight > 0.0
    )
    largest_leaf = math.ceil(n / (budget + 1))
    recomputed_lower = (
        (1.0 - eta_value) * entropy
        + eta_value * _interval_cost(largest_leaf)
    )
    recomputed_lower = min(recomputed_lower, objective)
    absolute_gap = max(0.0, objective - recomputed_lower)
    relative_gap = absolute_gap / max(abs(objective), 1e-12)
    expected = {
        "average_cost": average,
        "max_cost": maximum,
        "objective": objective,
        "lower_bound": recomputed_lower,
        "absolute_gap": absolute_gap,
        "relative_gap_to_upper": relative_gap,
    }
    for field, value in expected.items():
        supplied = artifact.get(field)
        if (
            isinstance(supplied, bool)
            or not isinstance(supplied, (int, float))
            or not math.isfinite(float(supplied))
            or not _close(float(supplied), float(value))
        ):
            raise PrunedBeamVerificationError(
                f"{field} does not replay"
            )
    if artifact.get("bound_type") != "entropy_maxcost":
        raise PrunedBeamVerificationError("unknown lower-bound type")
    return {
        "verified": True,
        "split_count": split_count,
        **expected,
        "exact": absolute_gap <= 2e-9,
        "scope": (
            "feasible heuristic upper bound and information-theoretic lower "
            "bound; no approximation ratio is claimed"
        ),
    }
