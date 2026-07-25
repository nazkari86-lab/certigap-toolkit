import subprocess
import sys
import unittest
from pathlib import Path

from certigap import CppCertiGap, frontier_dp_best, normalize_weights
from certigap.cpp_bindings import library_path


ROOT = Path(__file__).resolve().parents[1]


class CppEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if not library_path().exists():
            subprocess.run([sys.executable, "build_cpp_core.py"], cwd=ROOT, check=True)
        cls.cpp = CppCertiGap()

    def test_cpp_matches_python_exact_on_reference_cases(self) -> None:
        cases = [
            ([1, 1], 1, 0.0),
            ([1, 4, 2, 7, 3], 2, 0.15),
            ([9, 1, 1, 1, 1, 1, 4], 3, 0.50),
            ([1, 0, 3, 0, 6, 2, 1], 3, 1.0),
        ]
        for raw_weights, budget, eta in cases:
            weights = normalize_weights(raw_weights)
            python_result = frontier_dp_best(weights, budget, eta)
            cpp_result = self.cpp.fit(weights, budget, eta)
            self.assertAlmostEqual(cpp_result["objective"], python_result["objective"], places=5)
            self.assertAlmostEqual(cpp_result["average_cost"], python_result["average_cost"], places=5)
            self.assertEqual(cpp_result["max_cost"], python_result["max_cost"])

    def test_cpp_pruned_beam_matches_full_candidates_on_small_case(self) -> None:
        weights = normalize_weights([1, 4, 2, 7, 3, 5, 1, 9])
        result = self.cpp.pruned_beam(weights, budget=3, eta=0.15, beam_width=16, candidate_limit=32)
        python_result = frontier_dp_best(weights, budget=3, eta=0.15)
        self.assertLessEqual(python_result["objective"], result["objective"] + 1e-5)
        self.assertEqual(len(result["per_key_costs"]), len(weights))
