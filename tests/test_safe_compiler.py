from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from certigap.safe_compiler import (
    compile_safe_spec,
    generate_safe_cpp_header,
)


ROOT = Path(__file__).resolve().parents[1]


def trace(n: int, count: int) -> dict:
    return {
        "n": n,
        "operations": [
            {"kind": "range", "left": 2, "right": n - 1}
            for _ in range(count)
        ],
    }


def spec() -> dict:
    return {
        "schema": "certigap-safe-compile-input-v1",
        "values": list(range(8)),
        "train_trace": trace(8, 100),
        "validation_trace": trace(8, 5_000),
        "test_trace": trace(8, 50),
        "policy": {"horizon_operations": 1_000_000},
    }


class SafeCompilerTests(unittest.TestCase):
    def test_header_embeds_safe_decision_and_executes(self) -> None:
        certificate = compile_safe_spec(spec())
        header = generate_safe_cpp_header(
            certificate, namespace="safe_generated"
        )
        self.assertIn(certificate["sha256"], header)
        self.assertIn(
            f'kSelectedName = "{certificate["decision"]["deployed"]}"',
            header,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "safe.hpp").write_text(header, encoding="utf-8")
            source = root / "main.cpp"
            source.write_text(
                """
#include <cmath>
#include "safe.hpp"

int main() {
    safe_generated::Index index({0, 1, 2, 3, 4, 5, 6, 7});
    if (std::abs(index.range_query(2, 7) - 21.0) > 1e-12) return 2;
    index.point_update(4, 100.0);
    return std::abs(index.range_query(2, 7) - 118.0) > 1e-12;
}
""",
                encoding="utf-8",
            )
            executable = root / "safe"
            compiled = subprocess.run(
                [
                    "c++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-pedantic",
                    "-I",
                    str(root),
                    "-I",
                    str(ROOT / "cpp"),
                    str(source),
                    "-o",
                    str(executable),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertEqual(subprocess.run([executable], check=False).returncode, 0)

    def test_cli_writes_verified_artifact_and_header(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            artifact = root / "safe.json"
            header = root / "safe.hpp"
            source.write_text(json.dumps(spec()), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "certigap.cli",
                    "safe-compile",
                    str(source),
                    "--artifact",
                    str(artifact),
                    "--header",
                    str(header),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(
                payload["artifact_type"], "certigap-safe-autoindex-v1"
            )
            self.assertTrue(artifact.is_file())
            self.assertTrue(header.is_file())

    def test_unknown_policy_field_fails_closed(self) -> None:
        raw = spec()
        raw["policy"]["unknown"] = 1
        with self.assertRaisesRegex(ValueError, "do not validate"):
            compile_safe_spec(raw)


if __name__ == "__main__":
    unittest.main()
