import unittest

import build_report


class ReportPipelineTests(unittest.TestCase):
    def test_build_abstract_includes_summary_metrics(self) -> None:
        summary = """# CertiGap Experiment Summary

## Global Summary

- Rows analyzed: `240`
- Mean greedy gap vs exact: `0.0986`
- Mean beam gap vs exact: `0.0006`
- Beam strictly improves on greedy in `104` rows
- Beam matches exact in `237` rows

## By Distribution
"""
        abstract = build_report.build_abstract(summary)
        self.assertIn("Mean beam gap vs exact", abstract)
        self.assertIn("CertiGap studies", abstract)

    def test_build_report_includes_current_results(self) -> None:
        report = build_report.build_report(
            "# T\n## Final Topic\nTopic\n## One-Sentence Contribution\nContribution\n## Central Research Question\nQuestion\n## Main Claim To Build Toward\nClaim\n## What Must Stay Out Of Scope\nOut",
            "# Theorems",
            "# Experiments",
            "# Positioning",
            "# Summary",
        )
        self.assertIn("## Current Results", report)
        self.assertIn("# Summary", report)


if __name__ == "__main__":
    unittest.main()
