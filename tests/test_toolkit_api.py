import unittest

from certigap.api import CertiGapToolkit, baseline_learned_segment
from certigap.cpp_bindings import library_path


class ToolkitApiTests(unittest.TestCase):
    def test_toolkit_fit_and_query(self) -> None:
        model = CertiGapToolkit().fit([0.1, 0.2, 0.3, 0.4], budget=2, eta=0.15, solver="beam")
        self.assertGreaterEqual(model.query_cost(1), 0)
        self.assertIn("objective", model.summary())

    def test_compare_baselines(self) -> None:
        model = CertiGapToolkit().fit([0.1, 0.2, 0.3, 0.4], budget=2, eta=0.15, solver="beam")
        rows = model.compare_baselines(["beam", "greedy", "balanced", "learned_segment"])
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[0]["objective"], min(row["objective"] for row in rows))

    def test_learned_segment_baseline(self) -> None:
        result = baseline_learned_segment([0.25, 0.25, 0.25, 0.25], budget=1, eta=0.0)
        self.assertIn("objective", result)
        self.assertEqual(result["split_count"], 1)

    def test_cpp_library_path_suffix(self) -> None:
        suffix = library_path().suffix
        self.assertIn(suffix, {".dylib", ".so", ".dll"})


if __name__ == "__main__":
    unittest.main()
