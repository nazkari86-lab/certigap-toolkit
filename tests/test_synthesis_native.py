from __future__ import annotations

import csv
import subprocess
import unittest
from pathlib import Path


class SynthesisNativeBenchmarkTests(unittest.TestCase):
    def test_native_holdout_harness_compiles_and_matches_oracle(self) -> None:
        root = Path(__file__).resolve().parents[1]
        build = root / "build"
        build.mkdir(exist_ok=True)
        binary = build / "synthesis_native_benchmark_test"
        subprocess.run(
            [
                "c++",
                "-std=c++17",
                "-O3",
                "-DNDEBUG",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                "-Icpp",
                "cpp/synthesis_native_benchmark.cpp",
                "-o",
                str(binary),
            ],
            cwd=root,
            check=True,
        )
        output = subprocess.check_output([str(binary)], cwd=root, text=True)
        rows = list(csv.DictReader(output.splitlines()))
        self.assertEqual(len(rows), 110)
        self.assertTrue(all(row["correct"] == "true" for row in rows))
        self.assertEqual(len({row["scenario"] for row in rows}), 11)
        self.assertEqual(
            {row["method"] for row in rows},
            {
                "array",
                "global_prefix",
                "fenwick",
                "segment_tree",
                "uniform_block",
                "certigap_x",
                "uniform_prefix",
                "certigap_x_prefix",
                "certigap_hybrid",
                "certigap_auto",
            },
        )
        for scenario in {row["scenario"] for row in rows}:
            checksums = {
                row["checksum"] for row in rows if row["scenario"] == scenario
            }
            self.assertEqual(len(checksums), 1)


if __name__ == "__main__":
    unittest.main()
