from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .core import (
    baseline_balanced,
    baseline_weighted_median,
    beam_search_best,
    certify_tree,
    cost_cap_dp_best,
    evaluate_tree,
    effective_budget,
    frontier_dp_best,
    greedy_best,
    IntervalLeaf,
    make_distribution,
    SplitNode,
    validate_problem,
)


SolverName = Literal["exact", "cost_cap", "beam", "greedy", "balanced", "weighted", "binary_search", "learned_segment"]


@dataclass
class FitResult:
    weights: list[float]
    budget: int
    requested_budget: int
    eta: float
    solver: str
    result: dict

    def query_cost(self, key: int) -> int:
        if key < 1 or key > len(self.weights):
            raise ValueError("key rank out of range")
        return int(self.result["per_key_costs"][key - 1])

    def export_certificate(self) -> dict:
        return certify_tree(self.result["tree"], self.weights, self.budget, self.eta)

    def export_tree(self) -> dict:
        return self.result["serialized_tree"]

    def summary(self) -> dict:
        return {
            "solver": self.solver,
            "budget": self.budget,
            "requested_budget": self.requested_budget,
            "eta": self.eta,
            "objective": self.result["objective"],
            "average_cost": self.result["average_cost"],
            "max_cost": self.result["max_cost"],
            "split_count": self.result["split_count"],
        }


def _normalize_weights(weights: list[float]) -> list[float]:
    values = validate_problem(weights, budget=0, eta=0.0)
    total = float(sum(values))
    return [weight / total for weight in values]


def _solver_dispatch(weights: list[float], budget: int, eta: float, solver: SolverName) -> dict:
    if solver == "exact":
        return frontier_dp_best(weights, budget, eta)
    if solver == "cost_cap":
        return cost_cap_dp_best(weights, budget, eta)
    if solver == "beam":
        return beam_search_best(weights, budget, eta)
    if solver == "greedy":
        return greedy_best(weights, budget, eta)
    if solver == "balanced":
        return baseline_balanced(weights, budget, eta)
    if solver == "weighted":
        return baseline_weighted_median(weights, budget, eta)
    if solver == "binary_search":
        return baseline_balanced(weights, len(weights) - 1, eta)
    if solver == "learned_segment":
        return baseline_learned_segment(weights, budget, eta)
    raise ValueError(f"unknown solver: {solver}")


def baseline_learned_segment(weights: list[float], budget: int, eta: float) -> dict:
    weights = validate_problem(weights, budget, eta)
    n = len(weights)
    segment_count = min(budget + 1, n)
    endpoints = [(index * n) // segment_count for index in range(1, segment_count)]
    ranges: list[tuple[int, int]] = []
    left = 1
    for right in endpoints + [n]:
        ranges.append((left, right))
        left = right + 1

    def build(first: int, last: int):
        if first == last:
            left_bound, right_bound = ranges[first]
            return IntervalLeaf(left_bound, right_bound)
        middle = (first + last) // 2
        left_child = build(first, middle)
        right_child = build(middle + 1, last)
        return SplitNode(
            left=left_child.left,
            right=right_child.right,
            threshold=left_child.right,
            left_child=left_child,
            right_child=right_child,
        )

    result = evaluate_tree(build(0, len(ranges) - 1), weights, eta)
    result["budget"] = budget
    result["eta"] = eta
    result["segments"] = segment_count
    result["segment_endpoints"] = endpoints
    return result


class CertiGapToolkit:
    def __init__(self) -> None:
        self._fit: FitResult | None = None

    def fit(
        self,
        weights: list[float],
        budget: int,
        eta: float,
        solver: SolverName = "beam",
    ) -> "CertiGapToolkit":
        normalized = _normalize_weights(weights)
        effective = effective_budget(budget, len(normalized))
        result = _solver_dispatch(normalized, effective, eta, solver)
        self._fit = FitResult(
            weights=normalized,
            budget=effective,
            requested_budget=budget,
            eta=eta,
            solver=solver,
            result=result,
        )
        return self

    def fit_distribution(
        self,
        kind: str,
        n: int,
        budget: int,
        eta: float,
        solver: SolverName = "beam",
    ) -> "CertiGapToolkit":
        return self.fit(make_distribution(kind, n), budget, eta, solver=solver)

    def query_cost(self, key: int) -> int:
        if self._fit is None:
            raise RuntimeError("fit() must be called before query_cost()")
        return self._fit.query_cost(key)

    def export_certificate(self) -> dict:
        if self._fit is None:
            raise RuntimeError("fit() must be called before export_certificate()")
        return self._fit.export_certificate()

    def export_tree(self) -> dict:
        if self._fit is None:
            raise RuntimeError("fit() must be called before export_tree()")
        return self._fit.export_tree()

    def summary(self) -> dict:
        if self._fit is None:
            raise RuntimeError("fit() must be called before summary()")
        return self._fit.summary()

    def compare_baselines(self, solvers: list[SolverName] | None = None) -> list[dict]:
        if self._fit is None:
            raise RuntimeError("fit() must be called before compare_baselines()")
        solvers = solvers or ["exact", "beam", "greedy", "balanced", "weighted", "binary_search", "learned_segment"]
        rows = []
        for solver in solvers:
            result = _solver_dispatch(self._fit.weights, self._fit.budget, self._fit.eta, solver)
            rows.append(
                {
                    "solver": solver,
                    "objective": result["objective"],
                    "average_cost": result["average_cost"],
                    "max_cost": result["max_cost"],
                    "split_count": result["split_count"],
                }
            )
        rows.sort(key=lambda row: row["objective"])
        return rows
