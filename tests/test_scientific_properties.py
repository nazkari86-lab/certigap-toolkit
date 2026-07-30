from __future__ import annotations

import random
import unittest

from certigap import (
    combined_lower_bound,
    cost_cap_dp_best,
    frontier_dp_best,
)
from certigap.autoindex import WorkloadTrace
from certigap.hybrid import HybridConstraints, synthesize_hybrid_partitions


class ScientificPropertyTests(unittest.TestCase):
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
