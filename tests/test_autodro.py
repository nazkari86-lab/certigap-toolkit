from __future__ import annotations

import copy
import hashlib
import json
import unittest

from certigap import (
    CertiGapAutoDRO,
    ExecutionCostModel,
    enumerate_partial_trees,
    evaluate_tree_with_fallback,
    fit_autodro,
    multinomial_uncertainty,
    verify_autodro_selection_artifact,
    worst_case_tv_expectation,
)
from certigap.autodro import AutoDROVerificationError, _deserialize_tree


class AutoDROTests(unittest.TestCase):
    def test_tv_zero_matches_nominal_expectation(self) -> None:
        result = worst_case_tv_expectation([0.25, 0.75], [1.0, 3.0], 0.0)
        self.assertAlmostEqual(result["robust_expectation"], 2.5)
        self.assertEqual(result["adversarial_distribution"], (0.25, 0.75))

    def test_tv_one_reaches_maximum_cost(self) -> None:
        result = worst_case_tv_expectation([0.6, 0.3, 0.1], [1.0, 2.0, 8.0], 1.0)
        self.assertAlmostEqual(result["robust_expectation"], 8.0)
        self.assertAlmostEqual(sum(result["adversarial_distribution"]), 1.0)

    def test_tv_transfer_matches_known_solution(self) -> None:
        result = worst_case_tv_expectation([0.5, 0.3, 0.2], [0.0, 2.0, 5.0], 0.25)
        self.assertAlmostEqual(result["robust_expectation"], 2.85)
        self.assertEqual(result["adversarial_distribution"], (0.25, 0.3, 0.45))

    def test_tv_solver_matches_grid_bruteforce(self) -> None:
        nominal = [0.5, 0.3, 0.2]
        costs = [0.0, 2.0, 5.0]
        radius = 0.2
        exact = worst_case_tv_expectation(nominal, costs, radius)["robust_expectation"]
        brute = max(
            p0 * costs[0] + p1 * costs[1] + p2 * costs[2]
            for p0 in (index / 10 for index in range(11))
            for p1 in (index / 10 for index in range(11))
            for p2 in [1.0 - p0 - p1]
            if p2 >= 0
            and 0.5 * (abs(p0 - nominal[0]) + abs(p1 - nominal[1]) + abs(p2 - nominal[2]))
            <= radius + 1e-12
        )
        self.assertAlmostEqual(exact, brute)

    def test_tv_solver_matches_multiple_exhaustive_grids(self) -> None:
        costs = [0.0, 1.0, 4.0]
        for nominal in ([0.5, 0.25, 0.25], [0.25, 0.5, 0.25], [0.25, 0.25, 0.5]):
            for radius in (0.25, 0.5):
                exact = worst_case_tv_expectation(nominal, costs, radius)["robust_expectation"]
                brute = max(
                    p0 * costs[0] + p1 * costs[1] + p2 * costs[2]
                    for p0 in (index / 4 for index in range(5))
                    for p1 in (index / 4 for index in range(5))
                    for p2 in [1.0 - p0 - p1]
                    if p2 >= 0
                    and 0.5
                    * (
                        abs(p0 - nominal[0])
                        + abs(p1 - nominal[1])
                        + abs(p2 - nominal[2])
                    )
                    <= radius + 1e-12
                )
                self.assertAlmostEqual(exact, brute)

    def test_statistical_radius_shrinks_with_more_observations(self) -> None:
        small = multinomial_uncertainty([10, 20, 30], pseudocount=0.0)
        large = multinomial_uncertainty([1000, 2000, 3000], pseudocount=0.0)
        self.assertLess(large.tv_radius, small.tv_radius)

    def test_smoothing_penalty_covers_zero_count_keys(self) -> None:
        uncertainty = multinomial_uncertainty([20, 0, 0], pseudocount=0.5)
        self.assertTrue(all(value > 0 for value in uncertainty.nominal))
        self.assertGreater(uncertainty.smoothing_tv_radius, 0)

    def test_inferred_radius_rejects_fractional_counts(self) -> None:
        with self.assertRaisesRegex(ValueError, "integer observation counts"):
            multinomial_uncertainty([1.5, 2.5])
        explicit = multinomial_uncertainty([1.5, 2.5], tv_radius=0.2)
        self.assertEqual(explicit.tv_radius, 0.2)

    def test_non_finite_inputs_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite"):
            multinomial_uncertainty([1.0, float("nan")], tv_radius=0.1)
        with self.assertRaisesRegex(ValueError, "finite"):
            worst_case_tv_expectation([0.5, 0.5], [1.0, float("inf")], 0.1)
        with self.assertRaisesRegex(ValueError, "finite"):
            ExecutionCostModel(routing_comparison_cost=float("nan")).validate()

    def test_cost_model_calibration_uses_medians(self) -> None:
        model = ExecutionCostModel.from_samples(
            [3.0, 1.0, 2.0],
            [9.0, 5.0, 7.0],
        )
        self.assertEqual(model.routing_comparison_cost, 2.0)
        self.assertEqual(model.fallback_comparison_cost, 7.0)
        self.assertEqual(model.cost_unit, "ns")

    def test_auto_selects_minimum_reported_score(self) -> None:
        result = fit_autodro(
            [100, 30, 10, 5, 2, 1],
            max_budget=3,
            tv_radius=0.15,
            training_etas=[0.0, 0.15],
            exact_limit=8,
        )
        self.assertEqual(result.selected["robust_score"], result.leaderboard[0]["robust_score"])
        self.assertLessEqual(result.selected["split_count"], 3)
        self.assertGreater(len(result.leaderboard), 1)

    def test_memory_limit_is_enforced(self) -> None:
        model = ExecutionCostModel(node_bytes=48, key_bytes=4)
        result = fit_autodro(
            [1, 2, 3, 4],
            max_budget=3,
            tv_radius=0.1,
            cost_model=model,
            memory_limit_bytes=64,
            solvers=["balanced"],
            fallbacks=["fixed_rounds"],
        )
        self.assertEqual(result.selected["split_count"], 0)
        self.assertLessEqual(result.selected["memory_bytes"], 64)

    def test_impossible_memory_limit_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "no portfolio candidate"):
            fit_autodro(
                [1, 2, 3],
                max_budget=1,
                tv_radius=0.1,
                memory_limit_bytes=1,
            )

    def test_cost_model_can_penalize_materialization(self) -> None:
        result = fit_autodro(
            [100, 1, 1, 1],
            max_budget=3,
            tv_radius=0.0,
            cost_model=ExecutionCostModel(build_cost_per_split=1000.0),
            solvers=["balanced", "weighted"],
            fallbacks=["fixed_rounds"],
        )
        self.assertEqual(result.selected["split_count"], 0)

    def test_public_wrapper_exports_auditable_selection(self) -> None:
        model = CertiGapAutoDRO().fit(
            [50, 10, 5, 1],
            max_budget=2,
            tv_radius=0.1,
            exact_limit=8,
        )
        summary = model.summary()
        artifact = model.export_selection_artifact()
        self.assertEqual(artifact["model"], "CertiGap-AutoDRO-v2")
        self.assertIn("globally optimal", summary["selection_scope"])
        self.assertNotIn("tree", artifact["selected"])
        self.assertGreaterEqual(model.query_cost(1), 0)
        verified = verify_autodro_selection_artifact(artifact)
        self.assertTrue(verified["verified"])
        self.assertTrue(verified["completeness_verified"])

    def test_direct_tv_solver_matches_independent_tree_enumeration(self) -> None:
        counts = [30, 7, 3, 2, 1]
        radius = 0.2
        result = fit_autodro(
            counts,
            2,
            tv_radius=radius,
            solvers=["balanced"],
            fallbacks=["fixed_rounds"],
            direct_tv_limit=5,
        )
        nominal = result.uncertainty.nominal
        brute = min(
            worst_case_tv_expectation(
                nominal,
                evaluate_tree_with_fallback(tree, list(nominal), 0.0, "fixed_rounds")[
                    "per_key_costs"
                ],
                radius,
            )["robust_expectation"]
            for tree in enumerate_partial_trees(5, 2)
        )
        self.assertAlmostEqual(result.selected["robust_score"], brute)
        self.assertIsNotNone(result.portfolio_manifest["direct_tree_space"])

    def test_direct_tv_has_strict_huber_portfolio_separation_witness(self) -> None:
        counts = [1134, 165, 7077, 2112, 1313, 1368, 8649]
        exact = fit_autodro(
            counts, 2, tv_radius=0.1, exact_limit=8, direct_tv_limit=7
        )
        heuristic = fit_autodro(
            counts, 2, tv_radius=0.1, exact_limit=8, direct_tv_limit=0
        )
        self.assertEqual(exact.selected["solver"], "direct_tv_exact")
        self.assertLess(
            exact.selected["robust_score"],
            heuristic.selected["robust_score"] - 0.06,
        )

    def test_v2_verifier_rejects_omitted_winner_even_with_rewritten_digest(self) -> None:
        result = fit_autodro([8, 4, 2, 1], 2, tv_radius=0.1, exact_limit=4)
        artifact = result.export_selection_artifact()
        tampered = copy.deepcopy(artifact)
        original = tampered["leaderboard"][0]["robust_score"]
        first_worse = next(
            index
            for index, row in enumerate(tampered["leaderboard"])
            if row["robust_score"] > original + 1e-9
        )
        tampered["leaderboard"] = tampered["leaderboard"][first_worse:]
        tampered["selected"] = tampered["leaderboard"][0]
        tampered["portfolio_manifest"]["candidate_count"] = len(tampered["leaderboard"])
        encoded = json.dumps(
            tampered["leaderboard"], sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        tampered["portfolio_manifest"]["leaderboard_sha256"] = hashlib.sha256(encoded).hexdigest()
        with self.assertRaisesRegex(ValueError, "incomplete"):
            verify_autodro_selection_artifact(tampered)

    def test_tree_deserializer_enforces_depth_limit(self) -> None:
        tree: dict = {"type": "leaf", "interval": [20, 20]}
        for left in range(19, 0, -1):
            tree = {
                "type": "split",
                "interval": [left, 20],
                "threshold": left,
                "left": {"type": "leaf", "interval": [left, left]},
                "right": tree,
            }
        with self.assertRaisesRegex(AutoDROVerificationError, "maximum depth"):
            _deserialize_tree(tree, 1, 20, max_depth=5)

    def test_selection_verifier_rejects_tampered_score(self) -> None:
        result = fit_autodro([8, 4, 2, 1], 2, tv_radius=0.1, exact_limit=4)
        artifact = result.export_selection_artifact()
        tampered = copy.deepcopy(artifact)
        tampered["leaderboard"][0]["robust_score"] -= 1.0
        tampered["selected"] = tampered["leaderboard"][0]
        with self.assertRaisesRegex(ValueError, "does not recompute"):
            verify_autodro_selection_artifact(tampered)

    def test_selection_verifier_rejects_selected_row_outside_leaderboard(self) -> None:
        result = fit_autodro([8, 4, 2, 1], 2, tv_radius=0.1, exact_limit=4)
        artifact = result.export_selection_artifact()
        tampered = copy.deepcopy(artifact)
        tampered["leaderboard"] = tampered["leaderboard"][1:]
        with self.assertRaisesRegex(ValueError, "leaderboard minimum"):
            verify_autodro_selection_artifact(tampered)

    def test_incremental_counts_trigger_new_audited_fit(self) -> None:
        model = CertiGapAutoDRO().fit(
            [20, 2, 1],
            max_budget=2,
            tv_radius=0.1,
            exact_limit=4,
        )
        model.update_counts([1, 2, 20])
        artifact = model.export_selection_artifact()
        self.assertEqual(artifact["uncertainty"]["total_count"], 46.0)

    def test_incremental_counts_preserve_key_universe(self) -> None:
        model = CertiGapAutoDRO().fit([2, 1], max_budget=1, tv_radius=0.1)
        with self.assertRaisesRegex(ValueError, "key universe"):
            model.update_counts([1, 2, 3])

    def test_sliding_window_refits_only_after_drift_threshold(self) -> None:
        model = CertiGapAutoDRO().fit([100, 10, 1], 2, tv_radius=0.1)
        before = model.export_tree()
        model.update_window([99, 10, 1], min_tv_drift=0.1)
        self.assertFalse(model.summary()["last_adaptation"]["refit"])
        self.assertEqual(model.export_tree(), before)
        model.update_window([1, 10, 100], min_tv_drift=0.1)
        self.assertTrue(model.summary()["last_adaptation"]["refit"])


if __name__ == "__main__":
    unittest.main()
