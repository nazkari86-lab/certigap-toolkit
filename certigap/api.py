from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .core import (
    baseline_balanced,
    baseline_weighted_median,
    beam_search_best,
    certify_tree,
    frontier_dp_best,
    greedy_best,
    make_distribution,
    split_count,
)


SolverName = Literal["exact", "beam", "greedy", "balanced", "weighted", "binary_search", "learned_segment"]


@dataclass
class FitResult:
    weights: list[float]
    budget: int
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
            "eta": self.eta,
            "objective": self.result["objective"],
            "average_cost": self.result["average_cost"],
            "max_cost": self.result["max_cost"],
            "split_count": self.result["split_count"],
        }


def _normalize_weights(weights: list[float]) -> list[float]:
    total = float(sum(weights))
    if total <= 0:
        raise ValueError("weights must have positive total mass")
    return [float(weight) / total for weight in weights]


def _solver_dispatch(weights: list[float], budget: int, eta: float, solver: SolverName) -> dict:
    if solver == "exact":
        return frontier_dp_best(weights, budget, eta)
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
    n = len(weights)
    segment_count = min(budget + 1, n)
    cuts = []
    for i in range(1, segment_count):
        cuts.append((i * n) // segment_count)
    costs = [0] * n
    left = 1
    depth = 1 if cuts else 0
    for cut in cuts + [n]:
        segment_size = cut - left + 1
        cost = depth + (0 if segment_size <= 1 else (segment_size - 1).bit_length())
        for idx in range(left - 1, cut):
            costs[idx] = cost
        left = cut + 1
    average = sum(weight * cost for weight, cost in zip(weights, costs))
    max_cost = max(costs) if costs else 0
    return {
        "average_cost": average,
        "max_cost": max_cost,
        "objective": (1.0 - eta) * average + eta * max_cost,
        "per_key_costs": costs,
        "split_count": max(0, segment_count - 1),
        "tree": None,
        "serialized_tree": {
            "type": "learned_segment",
            "segments": segment_count,
            "cuts": cuts,
        },
    }


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
        result = _solver_dispatch(normalized, budget, eta, solver)
        self._fit = FitResult(
            weights=normalized,
            budget=budget,
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
