import csv
import tempfile
import unittest
from pathlib import Path

import analyze_experiments


class ResultsPipelineTests(unittest.TestCase):
    def test_summary_generation(self) -> None:
        rows = [
            {
                "distribution": "zipf",
                "n": "8",
                "budget": "2",
                "eta": "0.15",
                "exact": "2.000000",
                "greedy": "2.200000",
                "beam": "2.000000",
                "balanced": "2.300000",
                "weighted": "2.250000",
                "greedy_gap": "0.200000",
                "beam_gap": "0.000000",
            },
            {
                "distribution": "uniform",
                "n": "8",
                "budget": "2",
                "eta": "0.15",
                "exact": "3.000000",
                "greedy": "3.000000",
                "beam": "3.000000",
                "balanced": "3.100000",
                "weighted": "3.100000",
                "greedy_gap": "0.000000",
                "beam_gap": "0.000000",
            },
        ]
        summary = analyze_experiments.summarize(rows)
        self.assertIn("Mean greedy gap vs exact", summary)
        self.assertIn("zipf", summary)
        self.assertIn("Top Beam Improvements", summary)


if __name__ == "__main__":
    unittest.main()
