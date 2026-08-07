from __future__ import annotations

import random
import unittest

from certigap import (
    CppCertiGap,
    brute_force_candidate_restricted_best,
    candidate_restricted_frontier_dp_best,
    combined_lower_bound,
    cost_cap_dp_best,
    frontier_dp_best,
    mass_quantile_thresholds,
    tree_respects_mass_quantile_grammar,
)
from certigap.autoindex import WorkloadTrace
from certigap.hybrid import HybridConstraints, synthesize_hybrid_partitions


class ScientificPropertyTests(unittest.TestCase):
    def test_complete_candidate_grammar_matches_unrestricted_dp(self) -> None:
        weights = [1, 7, 2, 11, 3, 5, 13, 1]
        exact = frontier_dp_best(weights, budget=3, eta=0.2)
        restricted = candidate_restricted_frontier_dp_best(
            weights, budget=3, eta=0.2, candidate_limit=len(weights)
        )
        self.assertAlmostEqual(restricted["objective"], exact["objective"], places=9)

    def test_candidate_thresholds_match_declared_boundary_grammar(self) -> None:
        thresholds = mass_quantile_thresholds(
            [1.0] * 20, left=3, right=18, candidate_limit=4
        )
        self.assertEqual(thresholds[0], 3)
        self.assertEqual(thresholds[-1], 17)
        self.assertIn(10, thresholds)

    def test_pruning_and_beam_gaps_have_a_nonnegative_decomposition(self) -> None:
        weights = [1, 1, 4, 14, 20, 13, 4, 1, 1, 1]
        exact = frontier_dp_best(weights, budget=3, eta=0.15)
        restricted = candidate_restricted_frontier_dp_best(
            weights, budget=3, eta=0.15, candidate_limit=4
        )
        beam = CppCertiGap().pruned_beam(
            weights, budget=3, eta=0.15, beam_width=2, candidate_limit=4
        )
        candidate_gap = restricted["objective"] - exact["objective"]
        beam_gap = beam["objective"] - restricted["objective"]
        total_gap = beam["objective"] - exact["objective"]
        self.assertGreaterEqual(candidate_gap, -1e-9)
        self.assertGreaterEqual(beam_gap, -1e-9)
        self.assertAlmostEqual(candidate_gap + beam_gap, total_gap, places=8)

    def test_candidate_restricted_dp_matches_independent_enumeration(self) -> None:
        cases = [
            ([1, 8, 1, 2, 11, 1], 3, 0.0, 4),
            ([3, 1, 7, 1, 2, 9, 1], 3, 0.15, 4),
            ([1, 2, 1, 13, 4, 1, 6], 4, 0.35, 5),
            ([2, 1, 5, 1, 11, 1, 3, 1], 3, 0.8, 4),
        ]
        for weights, budget, eta, candidate_limit in cases:
            dynamic_program = candidate_restricted_frontier_dp_best(
                weights, budget, eta, candidate_limit
            )
            exhaustive = brute_force_candidate_restricted_best(
                weights, budget, eta, candidate_limit
            )
            self.assertAlmostEqual(
                dynamic_program["objective"], exhaustive["objective"], places=9
            )
            self.assertTrue(
                tree_respects_mass_quantile_grammar(
                    dynamic_program["tree"], weights, candidate_limit
                )
            )

    def test_exact_optimum_never_worsens_with_more_budget(self) -> None:
        generator = random.Random(20260730)
        for n in range(2, 9):
            for _ in range(4):
                weights = [generator.randint(1, 50) for _ in range(n)]
                objectives = [
                    frontier_dp_best(weights, budget, 0.2)["objective"]
                    for budget in range(n)
                ]
                self.assertTrue(
                    all(
                        right <= left + 1e-9
                        for left, right in zip(objectives, objectives[1:])
                    )
                )

    def test_all_reported_lower_bounds_stay_below_exact_optimum(self) -> None:
        generator = random.Random(20260731)
        for n in range(2, 9):
            for budget in range(min(4, n)):
                weights = [generator.randint(1, 30) for _ in range(n)]
                exact = cost_cap_dp_best(weights, budget, 0.3)
                bound = combined_lower_bound(weights, budget, 0.3)
                self.assertLessEqual(
                    bound["lower_bound"], exact["objective"] + 1e-9
                )

    def test_expanding_hybrid_block_count_cannot_remove_old_candidates(
        self,
    ) -> None:
        trace = WorkloadTrace(12)
        for _ in range(20):
            trace.add_range(1, 8)
        for key in range(1, 13):
            trace.add_update(key, float(key))
        smaller = synthesize_hybrid_partitions(
            trace,
            constraints=HybridConstraints(
                max_blocks=3,
                max_block_width=6,
            ),
        )
        larger = synthesize_hybrid_partitions(
            trace,
            constraints=HybridConstraints(
                max_blocks=4,
                max_block_width=6,
            ),
        )
        self.assertEqual(larger[: len(smaller)], smaller)
        smaller_best = min(
            row["score"] for row in smaller if row["feasible"]
        )
        larger_best = min(row["score"] for row in larger if row["feasible"])
        self.assertLessEqual(
            larger_best, smaller_best + 1e-9
        )


if __name__ == "__main__":
    unittest.main()
