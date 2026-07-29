from __future__ import annotations

import json
import hashlib
from dataclasses import asdict, dataclass
from math import isfinite, log, sqrt
from statistics import median
from typing import Iterable, Sequence

from .api import SolverName, solve_with
from .core import IntervalLeaf, SplitNode, Tree, _to_serializable, effective_budget, split_count
from .direct_tv import enumerate_partial_trees, exact_tree_space_manifest
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
    portfolio_manifest: dict

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
            "model": "CertiGap-AutoDRO-v2",
            "counts": self.counts,
            "uncertainty": asdict(self.uncertainty),
            "cost_model": asdict(self.cost_model),
            "memory_limit_bytes": self.memory_limit_bytes,
            "max_budget": self.max_budget,
            "selected": _public_candidate(self.selected),
            "leaderboard": [_public_candidate(row) for row in self.leaderboard],
            "portfolio_manifest": self.portfolio_manifest,
            "scope": self.portfolio_manifest["selection_scope"],
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
                "selection_scope": self.portfolio_manifest["selection_scope"],
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


def _deserialize_tree(
    serialized: dict,
    expected_left: int,
    expected_right: int,
    *,
    depth: int = 0,
    node_counter: list[int] | None = None,
    max_depth: int = 256,
    max_nodes: int = 20_000,
) -> Tree:
    if depth > max_depth:
        raise AutoDROVerificationError("serialized tree exceeds maximum depth")
    counter = node_counter if node_counter is not None else [0]
    counter[0] += 1
    if counter[0] > max_nodes:
        raise AutoDROVerificationError("serialized tree exceeds maximum node count")
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
        _deserialize_tree(
            serialized["left"],
            expected_left,
            threshold,
            depth=depth + 1,
            node_counter=counter,
            max_depth=max_depth,
            max_nodes=max_nodes,
        ),
        _deserialize_tree(
            serialized["right"],
            threshold + 1,
            expected_right,
            depth=depth + 1,
            node_counter=counter,
            max_depth=max_depth,
            max_nodes=max_nodes,
        ),
    )


def _close(left: float, right: float, tolerance: float = 1e-9) -> bool:
    return abs(float(left) - float(right)) <= tolerance * max(1.0, abs(float(left)), abs(float(right)))


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def verify_autodro_selection_artifact(
    artifact: dict,
    *,
    verify_completeness: bool = True,
    max_keys: int = 10_000,
    max_candidates: int = 5_000,
) -> dict:
    """Recompute candidate arithmetic and, for v2, regenerate the portfolio."""
    try:
        if not isinstance(artifact, dict):
            raise AutoDROVerificationError("artifact must be an object")
        model_version = artifact.get("model")
        if model_version not in {"CertiGap-AutoDRO-v1", "CertiGap-AutoDRO-v2"}:
            raise AutoDROVerificationError("unknown AutoDRO artifact model")
        counts = _validated_counts(artifact["counts"])
        if len(counts) > max_keys:
            raise AutoDROVerificationError("artifact exceeds maximum key count")
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
        if len(leaderboard) > max_candidates:
            raise AutoDROVerificationError("artifact exceeds maximum candidate count")
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
        completeness_verified = False
        if model_version == "CertiGap-AutoDRO-v2":
            manifest = artifact.get("portfolio_manifest")
            if not isinstance(manifest, dict):
                raise AutoDROVerificationError("v2 artifact requires a portfolio manifest")
            _validate_manifest_limits(manifest, max_budget, len(counts))
            if manifest.get("leaderboard_sha256") != _canonical_sha256(leaderboard):
                raise AutoDROVerificationError("leaderboard digest does not match manifest")
            if int(manifest.get("candidate_count", -1)) != len(leaderboard):
                raise AutoDROVerificationError("candidate count does not match manifest")
            if verify_completeness:
                _verify_portfolio_completeness(artifact, counts, cost_model, uncertainty)
                completeness_verified = True
        return {
            "verified": True,
            "candidate_count": len(leaderboard),
            "selected_robust_score": expected_order[0]["score"],
            "completeness_verified": completeness_verified,
            "scope": (
                "regenerated deterministic portfolio"
                if completeness_verified
                else "submitted portfolio arithmetic"
            ),
        }
    except AutoDROVerificationError:
        raise
    except (KeyError, TypeError, ValueError, RecursionError) as error:
        raise AutoDROVerificationError(f"malformed AutoDRO artifact: {error}") from error


def _validate_manifest_limits(manifest: dict, max_budget: int, key_count: int) -> None:
    budgets = manifest.get("budgets")
    etas = manifest.get("training_etas")
    solvers = manifest.get("solvers")
    fallbacks = manifest.get("fallbacks")
    if not all(isinstance(values, list) and values for values in (budgets, etas, solvers, fallbacks)):
        raise AutoDROVerificationError("manifest search grids must be non-empty lists")
    if len(budgets) > 65 or max_budget > 64:
        raise AutoDROVerificationError("manifest regeneration budget exceeds safety limit")
    if len(etas) > 64 or len(solvers) > 32 or len(fallbacks) > 8:
        raise AutoDROVerificationError("manifest search grid exceeds safety limit")
    if len(budgets) * len(etas) * len(solvers) * len(fallbacks) > 20_000:
        raise AutoDROVerificationError("manifest regeneration work exceeds safety limit")
    direct_limit = int(manifest.get("direct_tv_limit", -1))
    if direct_limit < 0 or direct_limit > 8:
        raise AutoDROVerificationError("direct TV verification limit exceeds safety limit")
    if key_count <= direct_limit and max_budget > 7:
        raise AutoDROVerificationError("direct tree-space budget exceeds safety limit")


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
    direct_tv_limit: int = 8,
) -> AutoDROFitResult:
    values = _validated_counts(counts)
    n = len(values)
    if max_budget < 0:
        raise ValueError("max_budget must be non-negative")
    if exact_limit < 1:
        raise ValueError("exact_limit must be positive")
    if not 0 <= direct_tv_limit <= 8:
        raise ValueError("direct_tv_limit must lie in [0, 8]")
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

    def add_candidate(
        tree: Tree,
        *,
        solver: str,
        budget: int,
        training_eta: float | None,
        fallback: FallbackName,
    ) -> None:
        evaluated = evaluate_tree_with_fallback(
            tree,
            normalized,
            0.0 if training_eta is None else training_eta,
            fallback,
        )
        serialized = evaluated["serialized_tree"]
        identity = (json.dumps(serialized, sort_keys=True), fallback)
        source = {
            "solver": solver,
            "budget": budget,
            "training_eta": training_eta,
            "fallback": fallback,
        }
        if identity in candidates:
            candidates[identity]["sources"].append(source)
            if solver == "direct_tv_exact":
                candidates[identity].update(
                    {
                        "solver": solver,
                        "budget": budget,
                        "training_eta": None,
                    }
                )
            return
        comparisons, execution_costs = _tree_execution_costs(
            tree,
            n,
            fallback,
            model,
        )
        splits = split_count(tree)
        memory_bytes = model.key_bytes * n + model.node_bytes * (2 * splits + 1)
        if memory_limit_bytes is not None and memory_bytes > memory_limit_bytes:
            return
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
            **source,
            "sources": [source],
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

    for budget in selected_budgets:
        for training_eta in eta_grid:
            for solver in portfolio:
                if solver == "binary_search":
                    base_tree: Tree = IntervalLeaf(1, n)
                else:
                    base_result = solve_with(normalized, budget, training_eta, solver)
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
                    add_candidate(
                        tree,
                        solver=solver,
                        budget=budget,
                        training_eta=training_eta,
                        fallback=fallback,
                    )

    direct_space: dict | None = None
    if n <= direct_tv_limit:
        direct_space = exact_tree_space_manifest(n, effective_max_budget)
        all_trees = enumerate_partial_trees(n, effective_max_budget)
        for budget in selected_budgets:
            eligible = tuple(tree for tree in all_trees if split_count(tree) <= budget)
            for fallback in fallbacks:
                best_tree: Tree | None = None
                best_key: tuple[float, int, str] | None = None
                for tree in eligible:
                    comparisons, execution_costs = _tree_execution_costs(
                        tree,
                        n,
                        fallback,
                        model,
                    )
                    del comparisons
                    splits = split_count(tree)
                    memory_bytes = model.key_bytes * n + model.node_bytes * (2 * splits + 1)
                    if memory_limit_bytes is not None and memory_bytes > memory_limit_bytes:
                        continue
                    robust = worst_case_tv_expectation(
                        uncertainty.nominal,
                        execution_costs,
                        uncertainty.tv_radius,
                    )
                    score = (
                        robust["robust_expectation"]
                        + model.tail_weight * max(execution_costs)
                        + model.memory_cost_per_byte * memory_bytes
                        + model.build_cost_per_split * splits
                    )
                    key = (
                        score,
                        memory_bytes,
                        json.dumps(_to_serializable(tree), sort_keys=True),
                    )
                    if best_key is None or key < best_key:
                        best_key = key
                        best_tree = tree
                if best_tree is not None:
                    add_candidate(
                        best_tree,
                        solver="direct_tv_exact",
                        budget=budget,
                        training_eta=None,
                        fallback=fallback,
                    )

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
    public_leaderboard = [_public_candidate(row) for row in leaderboard]
    full_direct_scope = direct_space is not None
    portfolio_manifest = {
        "generator": "certigap-autodro-deterministic-v2",
        "budgets": list(selected_budgets),
        "training_etas": list(eta_grid),
        "solvers": list(portfolio),
        "fallbacks": list(fallbacks),
        "exact_limit": exact_limit,
        "direct_tv_limit": direct_tv_limit,
        "candidate_count": len(leaderboard),
        "leaderboard_sha256": _canonical_sha256(public_leaderboard),
        "direct_tree_space": direct_space,
        "selection_scope": (
            "globally optimal over every partial tree and configured fallback"
            if full_direct_scope
            else "best candidate in the regenerated deterministic portfolio"
        ),
    }
    return AutoDROFitResult(
        counts=values,
        uncertainty=uncertainty,
        cost_model=model,
        selected=leaderboard[0],
        leaderboard=leaderboard,
        memory_limit_bytes=memory_limit_bytes,
        max_budget=effective_max_budget,
        portfolio_manifest=portfolio_manifest,
    )


def _verify_portfolio_completeness(
    artifact: dict,
    counts: tuple[float, ...],
    cost_model: ExecutionCostModel,
    uncertainty: UncertaintyModel,
) -> None:
    manifest = artifact["portfolio_manifest"]
    if manifest.get("generator") != "certigap-autodro-deterministic-v2":
        raise AutoDROVerificationError("unknown portfolio generator")
    regenerated = fit_autodro(
        counts,
        int(artifact["max_budget"]),
        budgets=manifest["budgets"],
        confidence=uncertainty.confidence,
        pseudocount=uncertainty.pseudocount,
        tv_radius=None if uncertainty.radius_source == "inferred" else uncertainty.tv_radius,
        training_etas=manifest["training_etas"],
        solvers=manifest["solvers"],
        fallbacks=manifest["fallbacks"],
        cost_model=cost_model,
        memory_limit_bytes=artifact["memory_limit_bytes"],
        exact_limit=int(manifest["exact_limit"]),
        direct_tv_limit=int(manifest["direct_tv_limit"]),
    )
    regenerated_leaderboard = [_public_candidate(row) for row in regenerated.leaderboard]
    if _canonical_sha256(regenerated_leaderboard) != _canonical_sha256(artifact["leaderboard"]):
        raise AutoDROVerificationError("submitted portfolio is incomplete or was not regenerated")
    if regenerated.portfolio_manifest != manifest:
        raise AutoDROVerificationError("portfolio manifest does not recompute")


class CertiGapAutoDRO:
    def __init__(self) -> None:
        self._fit: AutoDROFitResult | None = None
        self._max_budget: int | None = None
        self._fit_options: dict = {}
        self._last_adaptation: dict | None = None

    def fit(self, counts: Iterable[float], max_budget: int, **kwargs) -> "CertiGapAutoDRO":
        self._fit = fit_autodro(counts, max_budget, **kwargs)
        self._max_budget = max_budget
        self._fit_options = dict(kwargs)
        return self

    def update_counts(
        self,
        additional_counts: Iterable[float],
        *,
        decay: float = 1.0,
    ) -> "CertiGapAutoDRO":
        current = self._require_fit()
        additions = _validated_counts(additional_counts)
        if len(additions) != len(current.counts):
            raise ValueError("additional counts must preserve the key universe")
        if not isfinite(decay) or not 0 < decay <= 1:
            raise ValueError("decay must lie in (0, 1]")
        if decay != 1.0 and self._fit_options.get("tv_radius") is None:
            raise ValueError("decayed fractional counts require an explicit tv_radius")
        combined = tuple(decay * old + new for old, new in zip(current.counts, additions))
        previous = current.uncertainty.nominal
        self.fit(combined, int(self._max_budget), **self._fit_options)
        updated = self._require_fit().uncertainty.nominal
        self._last_adaptation = {
            "mode": "decayed_counts" if decay != 1.0 else "cumulative_counts",
            "decay": decay,
            "tv_drift": 0.5 * sum(abs(left - right) for left, right in zip(previous, updated)),
            "refit": True,
        }
        return self

    def update_window(
        self,
        window_counts: Iterable[float],
        *,
        min_tv_drift: float = 0.0,
        force: bool = False,
    ) -> "CertiGapAutoDRO":
        current = self._require_fit()
        window = _validated_counts(window_counts)
        if len(window) != len(current.counts):
            raise ValueError("window counts must preserve the key universe")
        if not isfinite(min_tv_drift) or not 0 <= min_tv_drift <= 1:
            raise ValueError("min_tv_drift must lie in [0, 1]")
        total = sum(window)
        empirical = tuple(value / total for value in window)
        drift = 0.5 * sum(
            abs(left - right)
            for left, right in zip(current.uncertainty.empirical, empirical)
        )
        should_refit = force or drift >= min_tv_drift
        if should_refit:
            self.fit(window, int(self._max_budget), **self._fit_options)
        self._last_adaptation = {
            "mode": "sliding_window",
            "tv_drift": drift,
            "threshold": min_tv_drift,
            "refit": should_refit,
        }
        return self

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
        result = self._require_fit().summary()
        if self._last_adaptation is not None:
            result["last_adaptation"] = dict(self._last_adaptation)
        return result

    def leaderboard(self) -> list[dict]:
        return [_public_candidate(row) for row in self._require_fit().leaderboard]
