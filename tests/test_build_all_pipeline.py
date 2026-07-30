import unittest

import build_all


class BuildAllPipelineTests(unittest.TestCase):
    def test_root_points_to_project(self) -> None:
        self.assertTrue((build_all.ROOT / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
