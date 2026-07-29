import copy
import unittest

from certigap import (
    AnytimeVerificationError,
    ExecutionCostModel,
    anytime_tv_branch_and_bound,
    fit_autodro,
    verify_anytime_tv_certificate,
)


class AnytimeTvTests(unittest.TestCase):
    def test_matches_complete_tree_space_oracle(self) -> None:
        cases = (
            ([30, 7, 3, 2, 1], 2, 0.2),
            ([1, 2, 3, 8, 21, 3], 3, 0.1),
            ([5, 5, 5, 5], 2, 0.35),
        )
        for weights, budget, radius in cases:
            anytime = anytime_tv_branch_and_bound(
                weights,
                budget,
                radius,
                max_expansions=200_000,
            )
            oracle = fit_autodro(
                weights,
                budget,
                tv_radius=radius,
                pseudocount=0.0,
                solvers=["balanced"],
                fallbacks=["fixed_rounds"],
                direct_tv_limit=len(weights),
            )
            self.assertTrue(anytime["exact"])
            self.assertAlmostEqual(
                anytime["score"],
                oracle.selected["robust_score"],
                places=9,
            )
            self.assertAlmostEqual(anytime["relative_gap"], 0.0)

    def test_replay_verifier_accepts_valid_certificate(self) -> None:
        result = anytime_tv_branch_and_bound(
            [100, 30, 8, 4, 2, 1],
            3,
            0.15,
            max_expansions=80,
        )
        verified = verify_anytime_tv_certificate(result["certificate"])
        self.assertTrue(verified["verified"])
        self.assertAlmostEqual(verified["objective"], result["score"])
        self.assertAlmostEqual(
            verified["global_lower_bound"],
            result["global_lower_bound"],
        )

    def test_midpoint_fallback_matches_complete_oracle(self) -> None:
        weights = [21, 8, 3, 2, 1]
        anytime = anytime_tv_branch_and_bound(
            weights,
            3,
            0.2,
            fallback="midpoint_binary",
            max_expansions=200_000,
        )
        oracle = fit_autodro(
            weights,
            3,
            tv_radius=0.2,
            pseudocount=0.0,
            solvers=["balanced"],
            fallbacks=["midpoint_binary"],
            direct_tv_limit=5,
        )
        self.assertTrue(anytime["exact"])
        self.assertAlmostEqual(
            anytime["score"],
            oracle.selected["robust_score"],
            places=9,
        )
        self.assertTrue(
            verify_anytime_tv_certificate(anytime["certificate"])["verified"]
        )

    def test_target_gap_stop_is_replay_verified(self) -> None:
        result = anytime_tv_branch_and_bound(
            [1] * 16,
            4,
            0.1,
            max_expansions=100,
            target_relative_gap=0.01,
        )
        self.assertEqual(result["stop_reason"], "target_gap")
        self.assertEqual(result["search_stats"]["processed_states"], 0)
        self.assertTrue(result["exact"])
        self.assertTrue(
            verify_anytime_tv_certificate(result["certificate"])["verified"]
        )

    def test_replay_verifier_rejects_tampering(self) -> None:
        result = anytime_tv_branch_and_bound(
            [20, 7, 3, 1],
            2,
            0.1,
            max_expansions=10,
        )
        artifact = copy.deepcopy(result["certificate"])
        artifact["events"][0]["identity"] = "0" * 64
        with self.assertRaisesRegex(
            AnytimeVerificationError,
            "best-first frontier",
        ):
            verify_anytime_tv_certificate(artifact)

    def test_more_work_never_worsens_certified_interval(self) -> None:
        weights = [1.0 / (index + 1) for index in range(24)]
        runs = [
            anytime_tv_branch_and_bound(
                weights,
                5,
                0.1,
                max_expansions=limit,
            )
            for limit in (0, 25, 100, 400)
        ]
        for earlier, later in zip(runs, runs[1:]):
            self.assertLessEqual(later["score"], earlier["score"] + 1e-9)
            self.assertGreaterEqual(
                later["global_lower_bound"],
                earlier["global_lower_bound"] - 1e-9,
            )
            self.assertLessEqual(
                later["relative_gap"],
                earlier["relative_gap"] + 1e-9,
            )

    def test_memory_and_multicomponent_costs_are_certified(self) -> None:
        model = ExecutionCostModel(
            routing_comparison_cost=2.0,
            fallback_comparison_cost=3.0,
            node_bytes=16,
            key_bytes=8,
            memory_cost_per_byte=0.001,
            tail_weight=0.2,
            build_cost_per_split=0.05,
        )
        result = anytime_tv_branch_and_bound(
            [9, 5, 3, 2, 1],
            3,
            0.2,
            cost_model=model,
            memory_limit_bytes=5 * 8 + 16 * 5,
            max_expansions=1_000,
        )
        verified = verify_anytime_tv_certificate(result["certificate"])
        self.assertTrue(verified["verified"])
        self.assertLessEqual(result["memory_bytes"], 5 * 8 + 16 * 5)

    def test_input_limits(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_expansions"):
            anytime_tv_branch_and_bound([1, 1], 1, 0.1, max_expansions=-1)
        with self.assertRaisesRegex(ValueError, "at most"):
            anytime_tv_branch_and_bound([1] * 513, 1, 0.1)


if __name__ == "__main__":
    unittest.main()
