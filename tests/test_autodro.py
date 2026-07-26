from __future__ import annotations

import copy
import unittest

from certigap import (
    CertiGapAutoDRO,
    ExecutionCostModel,
    fit_autodro,
    multinomial_uncertainty,
    verify_autodro_selection_artifact,
    worst_case_tv_expectation,
)


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
        self.assertEqual(artifact["model"], "CertiGap-AutoDRO-v1")
        self.assertEqual(summary["selection_scope"], "portfolio")
        self.assertNotIn("tree", artifact["selected"])
        self.assertGreaterEqual(model.query_cost(1), 0)
        verified = verify_autodro_selection_artifact(artifact)
        self.assertTrue(verified["verified"])

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


if __name__ == "__main__":
    unittest.main()
