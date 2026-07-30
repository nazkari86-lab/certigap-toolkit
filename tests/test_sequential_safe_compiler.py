from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from certigap.sequential_safe_compiler import (
    compile_sequential_safe_spec,
    generate_sequential_safe_cpp_header,
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
        "schema": "certigap-sequential-safe-compile-input-v1",
        "values": list(range(8)),
        "train_trace": trace(8, 100),
        "validation_trace": trace(8, 12_000),
        "test_trace": trace(8, 50),
        "policy": {
            "minimum_observations": 100,
            "horizon_operations": 1_000_000
        },
    }


class SequentialSafeCompilerTests(unittest.TestCase):
    def test_header_embeds_outer_certificate(self) -> None:
        certificate = compile_sequential_safe_spec(spec())
        header = generate_sequential_safe_cpp_header(
            certificate, namespace="sequential_generated"
        )
        self.assertIn(certificate["sha256"], header)
        self.assertIn(
            f'kSelectedName = "{certificate["decision"]["deployed"]}"',
            header,
        )

    def test_cli_compiles_and_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            artifact = root / "selection.json"
            header = root / "selection.hpp"
            source.write_text(json.dumps(spec()), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "certigap.cli",
                    "sequential-safe-compile",
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
                payload["artifact_type"],
                "certigap-sequential-safe-autoindex-v1",
            )
            verified = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "certigap.cli",
                    "verify",
                    str(artifact),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)

    def test_unknown_policy_field_fails_closed(self) -> None:
        raw = spec()
        raw["policy"]["unknown"] = 1
        with self.assertRaisesRegex(ValueError, "do not validate"):
            compile_sequential_safe_spec(raw)


if __name__ == "__main__":
    unittest.main()
