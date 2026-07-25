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
