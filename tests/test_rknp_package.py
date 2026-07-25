import unittest

import build_rknp_package


class RknpPackageTests(unittest.TestCase):
    def test_parse_global_summary(self) -> None:
        summary = """# S

## Global Summary

- Rows analyzed: `10`
- Mean beam absolute objective gap vs exact: `0.1`

## By Distribution
"""
        metrics = build_rknp_package.parse_global_summary(summary)
        self.assertEqual(len(metrics), 2)
        self.assertIn("Rows analyzed", metrics[0])

    def test_build_abstract_ru_contains_metrics(self) -> None:
        summary = """# S

## Global Summary

- Rows analyzed: `10`
- Mean beam absolute objective gap vs exact: `0.1`

## By Distribution
"""
        abstract = build_rknp_package.build_abstract_ru(summary)
        self.assertIn("Аннотация", abstract)
        self.assertIn("Rows analyzed", abstract)


if __name__ == "__main__":
    unittest.main()
