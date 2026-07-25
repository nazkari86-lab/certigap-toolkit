import unittest

import generate_counterexamples


class CounterexamplePipelineTests(unittest.TestCase):
    def test_module_exports_paths(self) -> None:
        self.assertTrue(str(generate_counterexamples.CSV_PATH).endswith("counterexamples.csv"))
        self.assertTrue(str(generate_counterexamples.MD_PATH).endswith("counterexamples.md"))


if __name__ == "__main__":
    unittest.main()
