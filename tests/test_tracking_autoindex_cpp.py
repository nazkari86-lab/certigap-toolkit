from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from certigap import AdaptiveSpec, WorkloadTrace
from certigap.autoindex import _PreparedAnalyticalPortfolio
from certigap.spec import compile_from_spec
from generate_single_header import generated_text


ROOT = Path(__file__).resolve().parents[1]


class TrackingAutoIndexCppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.compiler = shutil.which("c++") or shutil.which("g++")
        if cls.compiler is None:
            raise unittest.SkipTest("C++ compiler is unavailable")

    def compile_and_run(self, source: Path, include: Path, *, sanitize: bool) -> str:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "validation"
            command = [
                self.compiler,
                "-std=c++17",
                "-O1",
                "-Wall",
                "-Wextra",
                "-Wpedantic",
                "-Werror",
                f"-I{include}",
                str(source),
                "-o",
                str(executable),
            ]
            if sanitize:
                command[2:2] = [
                    "-g",
                    "-fno-omit-frame-pointer",
                    "-fsanitize=address,undefined",
                ]
            subprocess.run(command, check=True, cwd=ROOT)
            environment = os.environ.copy()
            # Apple Clang aborts when leak detection is explicitly enabled.
            environment.setdefault("ASAN_OPTIONS", "detect_leaks=0")
            completed = subprocess.run(
                [str(executable)],
                check=True,
                cwd=ROOT,
                env=environment,
                text=True,
                capture_output=True,
            )
            return completed.stdout

    def test_native_validation_with_sanitizers(self) -> None:
        output = self.compile_and_run(
            ROOT / "cpp" / "tracking_autoindex_validation.cpp",
            ROOT / "cpp",
            sanitize=True,
        )
        self.assertIn("48000_random_operations", output)

    def test_single_header_compiles_and_executes_tracking_api(self) -> None:
        self.assertEqual(
            (ROOT / "cpp" / "certigap.hpp").read_text(encoding="utf-8"),
            generated_text(),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copy(ROOT / "cpp" / "certigap.hpp", root)
            source = root / "main.cpp"
            source.write_text(
                """
#include <certigap.hpp>
#include <cassert>
int main() {
    certigap::TrackingAutoIndex index({1, 2, 3, 4});
    assert(index.range_query(1, 4) == 10.0);
    index.point_update(2, 10.0);
    assert(index.get(2) == 10.0);
    certigap::FastTrackingAutoIndex fast({1, 2, 3, 4});
    assert(fast.range_query(1, 4) == 10.0);
    fast.point_update(2, 10.0);
    assert(fast.get(2) == 10.0);
    fast.flush();
    auto frozen = fast.freeze(certigap::Backend::Fenwick);
    assert(frozen.unchecked_range_query(1, 4) == 18.0);
    auto compiled = fast.freeze_static<
        certigap::Backend::Fenwick, certigap::Aggregate::Sum>();
    assert(compiled.unchecked_range_query(1, 4) == 18.0);
    return index.migration_is_metric() && fast.explain().operations == 3 ? 0 : 1;
}
""",
                encoding="utf-8",
            )
            self.compile_and_run(source, root, sanitize=False)

    def test_native_service_model_matches_verified_python_model(self) -> None:
        output = self.compile_and_run(
            ROOT / "cpp" / "tracking_autoindex_differential.cpp",
            ROOT / "cpp",
            sanitize=False,
        )
        operations = WorkloadTrace(32)
        operations.add_get(7)
        operations.add_range(1, 32)
        operations.add_range(3, 27)
        operations.add_update(5, 9.0)
        operations.add_range(8, 8)
        operations.add_update(32, -4.0)
        training = WorkloadTrace(32)
        for key in range(1, 33):
            training.add_get(key)
        artifact = compile_from_spec(
            range(32), training, AdaptiveSpec()
        ).export_selection_artifact()
        expected = _PreparedAnalyticalPortfolio(artifact).costs(operations)
        names = (
            "sorted_array",
            "prefix_sum",
            "fenwick",
            "sqrt_decomposition",
            "segment_tree",
        )
        rows = [[float(value) for value in line.split(",")]
                for line in output.strip().splitlines()]
        self.assertEqual(len(rows), len(operations.operations))
        for time, row in enumerate(rows):
            self.assertEqual(int(row[0]), time)
            self.assertEqual(
                row[1:6],
                [expected[name][time] for name in names],
            )


if __name__ == "__main__":
    unittest.main()
