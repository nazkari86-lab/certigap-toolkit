import unittest

import generate_speed_quality


class SpeedQualityPipelineTests(unittest.TestCase):
    def test_build_summary_mentions_tradeoff(self) -> None:
        rows = [
            {"solver": "exact", "time_ms": 10.0, "absolute_objective_gap_vs_exact": 0.0, "relative_objective_gap_vs_exact": 0.0},
            {"solver": "beam", "time_ms": 1.0, "absolute_objective_gap_vs_exact": 0.0, "relative_objective_gap_vs_exact": 0.0},
            {"solver": "greedy", "time_ms": 0.5, "absolute_objective_gap_vs_exact": 0.2, "relative_objective_gap_vs_exact": 0.1},
            {"solver": "balanced", "time_ms": 0.4, "absolute_objective_gap_vs_exact": 0.3, "relative_objective_gap_vs_exact": 0.15},
            {"solver": "weighted", "time_ms": 0.6, "absolute_objective_gap_vs_exact": 0.1, "relative_objective_gap_vs_exact": 0.05},
            {"solver": "beam", "time_ms": 2.0, "absolute_objective_gap_vs_exact": None, "relative_objective_gap_vs_exact": None},
            {"solver": "greedy", "time_ms": 1.0, "absolute_objective_gap_vs_exact": None, "relative_objective_gap_vs_exact": None},
            {"solver": "balanced", "time_ms": 0.8, "absolute_objective_gap_vs_exact": None, "relative_objective_gap_vs_exact": None},
            {"solver": "weighted", "time_ms": 1.2, "absolute_objective_gap_vs_exact": None, "relative_objective_gap_vs_exact": None},
        ]
        summary = generate_speed_quality.build_summary(rows)
        self.assertIn("Small Cases With Exact Reference", summary)
        self.assertIn("Solver Tradeoff", summary)
        self.assertIn("mean relative objective gap", summary)


if __name__ == "__main__":
    unittest.main()
