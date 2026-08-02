from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from certigap.martingale_safe_compiler import (
    compile_martingale_safe_spec,
    generate_martingale_safe_cpp_header,
)


ROOT = Path(__file__).resolve().parents[1]


def trace(count: int, kind: str = "range") -> dict:
    operations = []
    for index in range(count):
        if kind == "range":
            operations.append({"kind": "range", "left": 2, "right": 7})
        else:
            operations.append(
                {
                    "kind": "update",
                    "left": 1 + index % 8,
                    "right": 1 + index % 8,
                    "value": float(index),
                }
            )
    return {"n": 8, "operations": operations}


def spec() -> dict:
    monitoring = trace(1_000)["operations"] + trace(
        3_000, "update"
    )["operations"]
    return {
        "schema": "certigap-martingale-safe-compile-input-v1",
        "values": list(range(8)),
        "train_trace": trace(100),
        "monitoring_trace": {"n": 8, "operations": monitoring},
        "test_trace": trace(50),
        "policy": {"minimum_observations": 50},
    }


class MartingaleSafeCompilerTests(unittest.TestCase):
    def test_revoked_header_materializes_baseline(self) -> None:
        certificate = compile_martingale_safe_spec(spec())
        self.assertTrue(certificate["decision"]["candidate_revoked"])
        header = generate_martingale_safe_cpp_header(
            certificate, namespace="martingale_generated"
        )
        self.assertIn(certificate["sha256"], header)
        self.assertIn(
            f'kSelectedName = "{certificate["decision"]["deployed"]}"',
            header,
        )

    def test_cli_writes_replayable_artifact(self) -> None:
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
                    "martingale-safe-compile",
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
            self.assertTrue(payload["candidate_revoked"])
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
            compile_martingale_safe_spec(raw)


if __name__ == "__main__":
    unittest.main()
