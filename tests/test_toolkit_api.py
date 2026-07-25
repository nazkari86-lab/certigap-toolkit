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
        result = baseline_learned_segment([0.125] * 8, budget=7, eta=0.0)
        self.assertIn("objective", result)
        self.assertEqual(result["split_count"], 7)
        self.assertEqual(result["max_cost"], 3)

    def test_cpp_library_path_suffix(self) -> None:
        suffix = library_path().suffix
        self.assertIn(suffix, {".dylib", ".so", ".dll"})

    def test_large_certificate_uses_fast_valid_bound(self) -> None:
        model = CertiGapToolkit().fit_distribution(
            kind="hot_tail",
            n=32,
            budget=6,
            eta=0.30,
            solver="beam",
        )
        certificate = model.export_certificate()
        self.assertEqual(certificate["bound_source"], "entropy_only")
        self.assertIsNotNone(certificate["certified_gap"])


if __name__ == "__main__":
    unittest.main()
