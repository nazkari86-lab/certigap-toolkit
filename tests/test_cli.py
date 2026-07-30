from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from certigap.compiler import compile_spec
from certigap.hybrid import HybridConstraints, compile_hybrid_index
from certigap.autoindex import WorkloadTrace


ROOT = Path(__file__).resolve().parents[1]


def autoindex_spec() -> dict:
    return {
        "schema": "certigap-compile-input-v1",
        "values": list(range(8)),
        "train_trace": {
            "n": 8,
            "operations": [
                {"kind": "range", "left": 1, "right": 8, "value": 0.0}
            ]
            * 20,
        },
        "constraints": {"aggregate": "sum", "budget": 3},
    }


class UnifiedCliTests(unittest.TestCase):
    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "-m", "certigap.cli", *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_verify_and_explain_autoindex(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "autoindex.json"
            artifact_path.write_text(
                json.dumps(compile_spec(autoindex_spec())),
                encoding="utf-8",
            )
            verified = self.run_cli("verify", str(artifact_path))
            self.assertEqual(verified.returncode, 0, verified.stderr)
            payload = json.loads(verified.stdout)
            self.assertEqual(
                payload["artifact_type"], "certigap-autoindex-v1"
            )
            explained = self.run_cli("explain", str(artifact_path))
            self.assertEqual(explained.returncode, 0, explained.stderr)
            explanation = json.loads(explained.stdout)
            self.assertTrue(explanation["verified"])
            self.assertIn("declared", explanation["claim_boundary"])
            self.assertGreaterEqual(explanation["candidate_count"], 1)
            self.assertEqual(
                len(explanation["leaderboard"]),
                explanation["candidate_count"],
            )

    def test_verify_auto_detects_hybrid_artifact(self) -> None:
        trace = WorkloadTrace(8)
        for _ in range(10):
            trace.add_range(1, 6)
        artifact = compile_hybrid_index(
            range(8),
            trace,
            constraints=HybridConstraints(
                max_blocks=4,
                max_block_width=4,
            ),
        ).export_certificate()
        with tempfile.TemporaryDirectory() as directory:
            artifact_path = Path(directory) / "hybrid.json"
            artifact_path.write_text(json.dumps(artifact), encoding="utf-8")
            result = self.run_cli("verify", str(artifact_path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                json.loads(result.stdout)["artifact_type"],
                "certigap-hybrid-v1",
            )
            explained = self.run_cli("explain", str(artifact_path))
            explanation = json.loads(explained.stdout)
            self.assertEqual(sum(explanation["block_widths"]), 8)
            self.assertEqual(explanation["operation_counts"]["range"], 10)

    def test_unknown_or_tampered_artifacts_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "unknown.json"
            path.write_text('{"schema":"unknown-v1"}', encoding="utf-8")
            unknown = self.run_cli("verify", str(path))
            self.assertEqual(unknown.returncode, 2)
            self.assertIn("unsupported artifact", unknown.stderr)

            artifact = compile_spec(autoindex_spec())
            artifact["selected"] = "sorted_array"
            path.write_text(json.dumps(artifact), encoding="utf-8")
            tampered = self.run_cli("verify", str(path))
            self.assertEqual(tampered.returncode, 2)
            self.assertIn("digest mismatch", tampered.stderr)

    def test_reproduce_tests_command_can_locate_checkout(self) -> None:
        from certigap.cli import _checkout_root

        self.assertEqual(_checkout_root(), ROOT)

    def test_installed_cli_finds_checkout_from_working_directory(self) -> None:
        from certigap.cli import _checkout_root

        with patch(
            "certigap.cli.__file__",
            "/tmp/site-packages/certigap/cli.py",
        ):
            self.assertEqual(_checkout_root(), ROOT)


if __name__ == "__main__":
    unittest.main()
