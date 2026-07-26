from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from math import isfinite, log, sqrt
from statistics import median
from typing import Iterable, Sequence

from .api import SolverName, _solver_dispatch
from .core import IntervalLeaf, SplitNode, Tree, effective_budget, split_count
from .generalized import (
    FallbackName,
    evaluate_tree_with_fallback,
    generalized_frontier_dp_best,
    resolve_fallback,
)


@dataclass(frozen=True)
class ExecutionCostModel:
    """Portable analytical cost model; nanoseconds require user calibration."""

    routing_comparison_cost: float = 1.0
    fallback_comparison_cost: float = 1.0
    node_bytes: int = 48
    key_bytes: int = 4
    memory_cost_per_byte: float = 0.0
    tail_weight: float = 0.0
    build_cost_per_split: float = 0.0
    cost_unit: str = "comparison_equivalent"

    def validate(self) -> None:
        numeric = (
            self.routing_comparison_cost,
            self.fallback_comparison_cost,
            self.memory_cost_per_byte,
            self.tail_weight,
            self.build_cost_per_split,
        )
        if any(not isfinite(value) or value < 0 for value in numeric):
            raise ValueError("execution cost parameters must be finite and non-negative")
        if self.node_bytes < 0 or self.key_bytes < 0:
            raise ValueError("byte sizes must be non-negative")
        if not self.cost_unit.strip():
            raise ValueError("cost_unit must not be empty")

    @classmethod
    def from_samples(
        cls,
        routing_samples: Iterable[float],
        fallback_samples: Iterable[float],
        *,
        cost_unit: str = "ns",
        **kwargs,
    ) -> "ExecutionCostModel":
        routing = tuple(float(value) for value in routing_samples)
        fallback = tuple(float(value) for value in fallback_samples)
        if not routing or not fallback:
            raise ValueError("calibration sample sets must not be empty")
        if any(not isfinite(value) or value < 0 for value in routing + fallback):
            raise ValueError("calibration samples must be finite and non-negative")
        model = cls(
            routing_comparison_cost=median(routing),
            fallback_comparison_cost=median(fallback),
            cost_unit=cost_unit,
            **kwargs,
        )
        model.validate()
        return model


@dataclass(frozen=True)
class UncertaintyModel:
    nominal: tuple[float, ...]
    empirical: tuple[float, ...]
    total_count: float
    confidence: float
    sampling_tv_radius: float
    smoothing_tv_radius: float
    tv_radius: float
    pseudocount: float
    radius_source: str


class AutoDROVerificationError(ValueError):
    pass


@dataclass
class AutoDROFitResult:
    counts: tuple[float, ...]
    uncertainty: UncertaintyModel
    cost_model: ExecutionCostModel
    selected: dict
    leaderboard: list[dict]
    memory_limit_bytes: int | None
    max_budget: int

    def query_cost(self, key: int) -> int:
        if key < 1 or key > len(self.counts):
            raise ValueError("key rank out of range")
        return int(self.selected["per_key_comparisons"][key - 1])

    def estimated_query_cost(self, key: int) -> float:
        if key < 1 or key > len(self.counts):
            raise ValueError("key rank out of range")
        return float(self.selected["per_key_execution_costs"][key - 1])

    def export_tree(self) -> dict:
        return self.selected["serialized_tree"]

    def export_selection_artifact(self) -> dict:
        artifact = {
            "model": "CertiGap-AutoDRO-v1",
            "counts": self.counts,
            "uncertainty": asdict(self.uncertainty),
            "cost_model": asdict(self.cost_model),
            "memory_limit_bytes": self.memory_limit_bytes,
            "max_budget": self.max_budget,
            "selected": _public_candidate(self.selected),
            "leaderboard": [_public_candidate(row) for row in self.leaderboard],
            "scope": "best candidate in the enumerated portfolio; not a global optimality certificate",
        }
        verify_autodro_selection_artifact(artifact)
        return artifact

    def summary(self) -> dict:
        fields = (
            "solver",
            "budget",
            "training_eta",
            "fallback",
            "robust_score",
            "robust_mean_cost",
            "nominal_mean_cost",
            "max_execution_cost",
            "split_count",
            "memory_bytes",
        )
        result = {field: self.selected[field] for field in fields}
        result.update(
            {
                "tv_radius": self.uncertainty.tv_radius,
                "portfolio_candidates": len(self.leaderboard),
                "selection_scope": "portfolio",
            }
        )
        return result


def _validated_counts(counts: Iterable[float]) -> tuple[float, ...]:
    values = tuple(float(value) for value in counts)
    if not values:
        raise ValueError("counts must not be empty")
    if any(not isfinite(value) or value < 0 for value in values):
        raise ValueError("counts must be finite and non-negative")
    if sum(values) <= 0:
        raise ValueError("counts must have positive total mass")
    return values


def multinomial_uncertainty(
    counts: Iterable[float],
    confidence: float = 0.95,
    pseudocount: float = 0.5,
    tv_radius: float | None = None,
) -> UncertaintyModel:
    """Build a conservative multinomial TV radius using the Weissman bound."""
    values = _validated_counts(counts)
    if not isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("confidence must lie strictly between 0 and 1")
    if not isfinite(pseudocount) or pseudocount < 0:
        raise ValueError("pseudocount must be non-negative")
    if tv_radius is not None and (not isfinite(tv_radius) or not 0 <= tv_radius <= 1):
        raise ValueError("tv_radius must lie in [0, 1]")
    if tv_radius is None and any(not value.is_integer() for value in values):
        raise ValueError("inferred statistical radius requires integer observation counts")

    total = sum(values)
    empirical = tuple(value / total for value in values)
    smoothed_total = total + pseudocount * len(values)
    nominal = tuple((value + pseudocount) / smoothed_total for value in values)
    smoothing_radius = 0.5 * sum(
        abs(empirical_value - nominal_value)
        for empirical_value, nominal_value in zip(empirical, nominal)
    )
    failure_probability = 1.0 - confidence
    sampling_radius = min(
        1.0,
        0.5 * sqrt(2.0 * (len(values) * log(2.0) + log(1.0 / failure_probability)) / total),
    )
    radius = (
        min(1.0, sampling_radius + smoothing_radius)
        if tv_radius is None
        else float(tv_radius)
    )
    return UncertaintyModel(
        nominal=nominal,
        empirical=empirical,
        total_count=total,
        confidence=confidence,
        sampling_tv_radius=sampling_radius,
        smoothing_tv_radius=smoothing_radius,
        tv_radius=radius,
        pseudocount=pseudocount,
        radius_source="inferred" if tv_radius is None else "explicit",
    )


def worst_case_tv_expectation(
    nominal: Sequence[float],
    costs: Sequence[float],
    tv_radius: float,
) -> dict:
    """Exactly maximize expected cost over a total-variation ball."""
    probabilities = tuple(float(value) for value in nominal)
    values = tuple(float(value) for value in costs)
    if not probabilities or len(probabilities) != len(values):
        raise ValueError("nominal and costs must be non-empty and have equal length")
    if (
        any(not isfinite(value) or value < 0 for value in probabilities)
        or abs(sum(probabilities) - 1.0) > 1e-9
    ):
        raise ValueError("nominal must be a finite probability distribution")
    if not all(isfinite(value) for value in values):
        raise ValueError("costs must be finite")
    if not isfinite(tv_radius) or not 0 <= tv_radius <= 1:
        raise ValueError("tv_radius must lie in [0, 1]")

    adversarial = list(probabilities)
    low_order = sorted(range(len(values)), key=lambda index: (values[index], index))
    high_order = sorted(range(len(values)), key=lambda index: (-values[index], index))
    low_index = high_index = 0
    remaining = float(tv_radius)
    while remaining > 1e-15 and low_index < len(values) and high_index < len(values):
        source = low_order[low_index]
        target = high_order[high_index]
        if values[source] >= values[target]:
            break
        if source == target:
            if adversarial[source] <= 1e-15:
                low_index += 1
            else:
                high_index += 1
            continue
        removable = adversarial[source]
        capacity = 1.0 - adversarial[target]
        moved = min(remaining, removable, capacity)
        if moved <= 1e-15:
            if removable <= 1e-15:
                low_index += 1
            if capacity <= 1e-15:
                high_index += 1
            continue
        adversarial[source] -= moved
        adversarial[target] += moved
        remaining -= moved
        if adversarial[source] <= 1e-15:
            low_index += 1
        if 1.0 - adversarial[target] <= 1e-15:
            high_index += 1

    nominal_expectation = sum(p * cost for p, cost in zip(probabilities, values))
    robust_expectation = sum(p * cost for p, cost in zip(adversarial, values))
    return {
        "nominal_expectation": nominal_expectation,
        "robust_expectation": robust_expectation,
        "adversarial_distribution": tuple(adversarial),
        "used_tv_radius": tv_radius - remaining,
    }


def _tree_execution_costs(
    tree: Tree,
    n: int,
    fallback: FallbackName,
    cost_model: ExecutionCostModel,
) -> tuple[list[int], list[float]]:
    fallback_profile = resolve_fallback(fallback)
    comparisons = [0] * n
    execution_costs = [0.0] * n

    def walk(node: Tree, depth: int, left: int, right: int) -> None:
        if node.left != left or node.right != right:
            raise ValueError("tree node interval disagrees with its parent")
        if isinstance(node, IntervalLeaf):
            fallback_costs = fallback_profile(node.left, node.right)
            for key, fallback_cost in zip(range(node.left, node.right + 1), fallback_costs):
                comparisons[key - 1] = depth + fallback_cost
                execution_costs[key - 1] = (
                    depth * cost_model.routing_comparison_cost
                    + fallback_cost * cost_model.fallback_comparison_cost
                )
            return
        walk(node.left_child, depth + 1, left, node.threshold)
        walk(node.right_child, depth + 1, node.threshold + 1, right)

    walk(tree, 0, 1, n)
    return comparisons, execution_costs


def _public_candidate(candidate: dict) -> dict:
    private = {"tree", "per_key_comparisons", "per_key_execution_costs"}
    return {key: value for key, value in candidate.items() if key not in private}


def _deserialize_tree(serialized: dict, expected_left: int, expected_right: int) -> Tree:
    if not isinstance(serialized, dict) or serialized.get("interval") != [expected_left, expected_right]:
        raise AutoDROVerificationError("serialized tree interval mismatch")
    if serialized.get("type") == "leaf":
        if set(serialized) != {"type", "interval"}:
            raise AutoDROVerificationError("leaf contains unsupported fields")
        return IntervalLeaf(expected_left, expected_right)
    if serialized.get("type") != "split":
        raise AutoDROVerificationError("unknown serialized tree node type")
    if set(serialized) != {"type", "interval", "threshold", "left", "right"}:
        raise AutoDROVerificationError("split contains unsupported fields")
    threshold = serialized["threshold"]
    if not isinstance(threshold, int) or not expected_left <= threshold < expected_right:
        raise AutoDROVerificationError("invalid split threshold")
    return SplitNode(
        expected_left,
        expected_right,
        threshold,
        _deserialize_tree(serialized["left"], expected_left, threshold),
        _deserialize_tree(serialized["right"], threshold + 1, expected_right),
    )


def _close(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return abs(float(left) - float(right)) <= tolerance * max(1.0, abs(float(left)), abs(float(right)))


def verify_autodro_selection_artifact(artifact: dict) -> dict:
    """Independently recompute arithmetic for every submitted portfolio candidate."""
    try:
        if artifact.get("model") != "CertiGap-AutoDRO-v1":
            raise AutoDROVerificationError("unknown AutoDRO artifact model")
        counts = _validated_counts(artifact["counts"])
        claimed_uncertainty = artifact["uncertainty"]
        source = claimed_uncertainty["radius_source"]
        if source not in {"inferred", "explicit"}:
            raise AutoDROVerificationError("unknown uncertainty radius source")
        uncertainty = multinomial_uncertainty(
            counts,
            confidence=float(claimed_uncertainty["confidence"]),
            pseudocount=float(claimed_uncertainty["pseudocount"]),
            tv_radius=(
                None if source == "inferred" else float(claimed_uncertainty["tv_radius"])
            ),
        )
        for field, expected in asdict(uncertainty).items():
            claimed = claimed_uncertainty[field]
            if isinstance(expected, tuple):
                if len(claimed) != len(expected) or any(
                    not _close(left, right) for left, right in zip(claimed, expected)
                ):
                    raise AutoDROVerificationError(f"uncertainty field {field} does not recompute")
            elif isinstance(expected, float):
                if not _close(claimed, expected):
                    raise AutoDROVerificationError(f"uncertainty field {field} does not recompute")
            elif claimed != expected:
                raise AutoDROVerificationError(f"uncertainty field {field} does not recompute")

        cost_model = ExecutionCostModel(**artifact["cost_model"])
        cost_model.validate()
        max_budget = int(artifact["max_budget"])
        memory_limit = artifact["memory_limit_bytes"]
        leaderboard = artifact["leaderboard"]
        if not isinstance(leaderboard, list) or not leaderboard:
            raise AutoDROVerificationError("leaderboard must not be empty")
        recomputed: list[dict] = []
        for candidate in leaderboard:
            fallback = candidate["fallback"]
            if fallback not in ("fixed_rounds", "midpoint_binary"):
                raise AutoDROVerificationError("unsupported fallback in leaderboard")
            tree = _deserialize_tree(candidate["serialized_tree"], 1, len(counts))
            splits = split_count(tree)
            if splits > int(candidate["budget"]) or int(candidate["budget"]) > max_budget:
                raise AutoDROVerificationError("candidate violates its split budget")
            comparisons, execution_costs = _tree_execution_costs(
                tree,
                len(counts),
                fallback,
                cost_model,
            )
            del comparisons
            memory_bytes = (
                cost_model.key_bytes * len(counts)
                + cost_model.node_bytes * (2 * splits + 1)
            )
            if memory_limit is not None and memory_bytes > int(memory_limit):
                raise AutoDROVerificationError("candidate violates memory limit")
            robust = worst_case_tv_expectation(
                uncertainty.nominal,
                execution_costs,
                uncertainty.tv_radius,
            )
            score = (
                robust["robust_expectation"]
                + cost_model.tail_weight * max(execution_costs)
                + cost_model.memory_cost_per_byte * memory_bytes
                + cost_model.build_cost_per_split * splits
            )
            scalar_fields = {
                "robust_score": score,
                "robust_mean_cost": robust["robust_expectation"],
                "nominal_mean_cost": robust["nominal_expectation"],
                "max_execution_cost": max(execution_costs),
                "used_tv_radius": robust["used_tv_radius"],
            }
            for field, expected in scalar_fields.items():
                if not _close(candidate[field], expected):
                    raise AutoDROVerificationError(f"candidate field {field} does not recompute")
            if candidate["split_count"] != splits or candidate["memory_bytes"] != memory_bytes:
                raise AutoDROVerificationError("candidate structural accounting does not recompute")
            adversarial = candidate["adversarial_distribution"]
            if len(adversarial) != len(counts) or any(
                not _close(left, right)
                for left, right in zip(adversarial, robust["adversarial_distribution"])
            ):
                raise AutoDROVerificationError("adversarial distribution does not recompute")
            recomputed.append({"score": score, "candidate": candidate})

        expected_order = sorted(
            recomputed,
            key=lambda row: (
                row["score"],
                row["candidate"]["memory_bytes"],
                row["candidate"]["split_count"],
                row["candidate"]["solver"],
                row["candidate"]["fallback"],
            ),
        )
        if [row["candidate"] for row in expected_order] != leaderboard:
            raise AutoDROVerificationError("leaderboard is not sorted by the declared objective")
        if artifact["selected"] != leaderboard[0]:
            raise AutoDROVerificationError("selected candidate is not the leaderboard minimum")
        return {
            "verified": True,
            "candidate_count": len(leaderboard),
            "selected_robust_score": expected_order[0]["score"],
            "scope": "submitted portfolio arithmetic",
        }
    except AutoDROVerificationError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise AutoDROVerificationError(f"malformed AutoDRO artifact: {error}") from error


def _training_eta_grid(radius: float, requested: Sequence[float] | None) -> tuple[float, ...]:
    values = requested if requested is not None else (0.0, min(0.15, radius), radius)
    result = sorted({float(value) for value in values})
    if any(value < 0 or value > 1 for value in result):
        raise ValueError("training eta values must lie in [0, 1]")
    return tuple(result)


def fit_autodro(
    counts: Iterable[float],
    max_budget: int,
    *,
    budgets: Sequence[int] | None = None,
    confidence: float = 0.95,
    pseudocount: float = 0.5,
    tv_radius: float | None = None,
    training_etas: Sequence[float] | None = None,
    solvers: Sequence[SolverName] | None = None,
    fallbacks: Sequence[FallbackName] = ("fixed_rounds", "midpoint_binary"),
    cost_model: ExecutionCostModel | None = None,
    memory_limit_bytes: int | None = None,
    exact_limit: int = 16,
) -> AutoDROFitResult:
    values = _validated_counts(counts)
    n = len(values)
    if max_budget < 0:
        raise ValueError("max_budget must be non-negative")
    if exact_limit < 1:
        raise ValueError("exact_limit must be positive")
    effective_max_budget = effective_budget(max_budget, n)
    selected_budgets = (
        tuple(range(effective_max_budget + 1))
        if budgets is None
        else tuple(sorted(set(int(value) for value in budgets)))
    )
    if not selected_budgets or any(value < 0 or value > effective_max_budget for value in selected_budgets):
        raise ValueError("budgets must lie in [0, max_budget]")
    if not fallbacks or any(value not in ("fixed_rounds", "midpoint_binary") for value in fallbacks):
        raise ValueError("at least one supported fallback is required")
    if memory_limit_bytes is not None and memory_limit_bytes < 0:
        raise ValueError("memory_limit_bytes must be non-negative")

    model = cost_model or ExecutionCostModel()
    model.validate()
    uncertainty = multinomial_uncertainty(
        values,
        confidence=confidence,
        pseudocount=pseudocount,
        tv_radius=tv_radius,
    )
    eta_grid = _training_eta_grid(uncertainty.tv_radius, training_etas)
    portfolio = tuple(solvers or ("beam", "greedy", "balanced", "weighted", "learned_segment"))
    if n <= exact_limit and "exact" not in portfolio:
        portfolio += ("exact",)

    candidates: dict[tuple[str, str], dict] = {}
    normalized = list(uncertainty.nominal)
    for budget in selected_budgets:
        for training_eta in eta_grid:
            for solver in portfolio:
                if solver == "binary_search":
                    base_tree: Tree = IntervalLeaf(1, n)
                else:
                    base_result = _solver_dispatch(normalized, budget, training_eta, solver)
                    base_tree = base_result["tree"]
                for fallback in fallbacks:
                    tree = base_tree
                    if solver == "exact" and fallback != "fixed_rounds":
                        tree = generalized_frontier_dp_best(
                            normalized,
                            budget,
                            training_eta,
                            fallback,
                        )["tree"]
                    evaluated = evaluate_tree_with_fallback(
                        tree,
                        normalized,
                        training_eta,
                        fallback,
                    )
                    serialized = evaluated["serialized_tree"]
                    identity = (json.dumps(serialized, sort_keys=True), fallback)
                    if identity in candidates:
                        continue
                    comparisons, execution_costs = _tree_execution_costs(
                        tree,
                        n,
                        fallback,
                        model,
                    )
                    splits = split_count(tree)
                    memory_bytes = model.key_bytes * n + model.node_bytes * (2 * splits + 1)
                    if memory_limit_bytes is not None and memory_bytes > memory_limit_bytes:
                        continue
                    robust = worst_case_tv_expectation(
                        uncertainty.nominal,
                        execution_costs,
                        uncertainty.tv_radius,
                    )
                    maximum = max(execution_costs)
                    score = (
                        robust["robust_expectation"]
                        + model.tail_weight * maximum
                        + model.memory_cost_per_byte * memory_bytes
                        + model.build_cost_per_split * splits
                    )
                    candidates[identity] = {
                        "solver": solver,
                        "budget": budget,
                        "training_eta": training_eta,
                        "fallback": fallback,
                        "robust_score": score,
                        "robust_mean_cost": robust["robust_expectation"],
                        "nominal_mean_cost": robust["nominal_expectation"],
                        "max_execution_cost": maximum,
                        "split_count": splits,
                        "memory_bytes": memory_bytes,
                        "used_tv_radius": robust["used_tv_radius"],
                        "adversarial_distribution": robust["adversarial_distribution"],
                        "per_key_comparisons": comparisons,
                        "per_key_execution_costs": execution_costs,
                        "serialized_tree": serialized,
                        "tree": tree,
                    }

    if not candidates:
        raise ValueError("no portfolio candidate satisfies the supplied constraints")
    leaderboard = sorted(
        candidates.values(),
        key=lambda row: (
            row["robust_score"],
            row["memory_bytes"],
            row["split_count"],
            row["solver"],
            row["fallback"],
        ),
    )
    return AutoDROFitResult(
        counts=values,
        uncertainty=uncertainty,
        cost_model=model,
        selected=leaderboard[0],
        leaderboard=leaderboard,
        memory_limit_bytes=memory_limit_bytes,
        max_budget=effective_max_budget,
    )


class CertiGapAutoDRO:
    def __init__(self) -> None:
        self._fit: AutoDROFitResult | None = None
        self._max_budget: int | None = None
        self._fit_options: dict = {}

    def fit(self, counts: Iterable[float], max_budget: int, **kwargs) -> "CertiGapAutoDRO":
        self._fit = fit_autodro(counts, max_budget, **kwargs)
        self._max_budget = max_budget
        self._fit_options = dict(kwargs)
        return self

    def update_counts(self, additional_counts: Iterable[float]) -> "CertiGapAutoDRO":
        current = self._require_fit()
        additions = _validated_counts(additional_counts)
        if len(additions) != len(current.counts):
            raise ValueError("additional counts must preserve the key universe")
        combined = tuple(old + new for old, new in zip(current.counts, additions))
        return self.fit(combined, int(self._max_budget), **self._fit_options)

    def _require_fit(self) -> AutoDROFitResult:
        if self._fit is None:
            raise RuntimeError("fit() must be called first")
        return self._fit

    def query_cost(self, key: int) -> int:
        return self._require_fit().query_cost(key)

    def estimated_query_cost(self, key: int) -> float:
        return self._require_fit().estimated_query_cost(key)

    def export_tree(self) -> dict:
        return self._require_fit().export_tree()

    def export_selection_artifact(self) -> dict:
        return self._require_fit().export_selection_artifact()

    def summary(self) -> dict:
        return self._require_fit().summary()

    def leaderboard(self) -> list[dict]:
        return [_public_candidate(row) for row in self._require_fit().leaderboard]
