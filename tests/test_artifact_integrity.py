import unittest

from verify_artifacts import validate_artifacts


class ArtifactIntegrityTests(unittest.TestCase):
    def test_published_artifacts_are_nonempty_and_consistent(self) -> None:
        rows = validate_artifacts()
        self.assertEqual(rows["scaling_benchmark.csv"], 450)


if __name__ == "__main__":
    unittest.main()
