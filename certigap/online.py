from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite, log2
from typing import Sequence

from .autodro import ExecutionCostModel
from .core import EPS, validate_problem


@dataclass(frozen=True)
class OnlineRegretCertificate:
    tv_drift: float
    optimization_gap: float
    per_query_regret_upper_bound: float
    horizon_regret_upper_bound: float
    rebuild_cost: float
    rebuild_recommended: bool
    cost_range_bound: float


def total_variation_distance(
    left: Sequence[float],
    right: Sequence[float],
) -> float:
    if len(left) != len(right) or not left:
        raise ValueError("distributions must be non-empty and have equal length")
    p = validate_problem(left, 0, 0.0)
    q = validate_problem(right, 0, 0.0)
    return 0.5 * sum(abs(a - b) for a, b in zip(p, q))


def expectation_shift_bound(
    reference: Sequence[float],
    current: Sequence[float],
    per_key_costs: Sequence[float],
) -> dict:
    """Certify |E_p[c] - E_q[c]| <= TV(p,q) * range(c)."""
    if len(reference) != len(current) or len(reference) != len(per_key_costs):
        raise ValueError("distributions and costs must have equal length")
    costs = tuple(float(value) for value in per_key_costs)
    if not costs or any(not isfinite(value) for value in costs):
        raise ValueError("per_key_costs must be finite and non-empty")
    drift = total_variation_distance(reference, current)
    cost_range = max(costs) - min(costs)
    return {
        "tv_drift": drift,
        "cost_range": cost_range,
        "expectation_shift_upper_bound": drift * cost_range,
    }


def online_regret_certificate(
    reference: Sequence[float],
    current: Sequence[float],
    *,
    budget: int,
    optimization_gap: float,
    horizon_queries: int,
    rebuild_cost: float,
    cost_model: ExecutionCostModel | None = None,
) -> OnlineRegretCertificate:
    """Bound stale-policy regret under distribution drift.

    If the reference solution is within ``optimization_gap`` of its optimum,
    then its mean-cost regret under the current distribution is at most
    ``optimization_gap + 2 * TV * R``, where ``R`` bounds every feasible
    tree's execution-cost range.
    """
    if budget < 0:
        raise ValueError("budget must be non-negative")
    if (
        not isfinite(optimization_gap)
        or optimization_gap < 0
        or not isfinite(rebuild_cost)
        or rebuild_cost < 0
        or horizon_queries < 0
    ):
        raise ValueError("gap, rebuild cost, and horizon must be non-negative")
    if len(reference) != len(current) or not reference:
        raise ValueError("distributions must be non-empty and have equal length")
    model = cost_model or ExecutionCostModel()
    model.validate()
    drift = total_variation_distance(reference, current)
    n = len(reference)
    fallback_rounds = 0 if n <= 1 else ceil(log2(n))
    cost_range = (
        min(budget, n - 1) * model.routing_comparison_cost
        + fallback_rounds * model.fallback_comparison_cost
    )
    per_query = optimization_gap + 2.0 * drift * cost_range
    horizon = per_query * horizon_queries
    return OnlineRegretCertificate(
        tv_drift=drift,
        optimization_gap=optimization_gap,
        per_query_regret_upper_bound=per_query,
        horizon_regret_upper_bound=horizon,
        rebuild_cost=rebuild_cost,
        rebuild_recommended=horizon > rebuild_cost + EPS,
        cost_range_bound=cost_range,
    )

