from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from certigap import (
    SafeAutoIndexVerificationError,
    SafeSelectionPolicy,
    WorkloadTrace,
    compile_safe_autoindex,
    verify_safe_autoindex_certificate,
)


def redigest(certificate: dict) -> None:
    unsigned = copy.deepcopy(certificate)
    unsigned.pop("sha256", None)
    certificate["sha256"] = hashlib.sha256(
        json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def ranges(n: int, count: int, left: int, right: int) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for _ in range(count):
        trace.add_range(left, right)
    return trace


class SafeAutoIndexTests(unittest.TestCase):
    def test_large_validation_approves_prefix_sum(self) -> None:
        train = ranges(32, 200, 3, 30)
        validation = ranges(32, 20_000, 3, 30)
        test = ranges(32, 100, 4, 29)
        model = compile_safe_autoindex(
            range(32),
            train,
            validation,
            test_trace=test,
            policy=SafeSelectionPolicy(horizon_operations=1_000_000),
        )
        self.assertEqual(model.summary()["train_candidate"], "prefix_sum")
        self.assertTrue(model.summary()["candidate_approved"])
        self.assertEqual(model.selected_name, "prefix_sum")
        self.assertEqual(model.range_query(3, 30), sum(range(2, 30)))
        verified = verify_safe_autoindex_certificate(
            model.export_certificate()
        )
        self.assertTrue(verified["verified"])
        self.assertIsNotNone(verified["test_score"])

    def test_small_validation_falls_back(self) -> None:
        model = compile_safe_autoindex(
            range(32),
            ranges(32, 200, 3, 30),
            ranges(32, 4, 3, 30),
        )
        summary = model.summary()
        self.assertEqual(summary["train_candidate"], "prefix_sum")
        self.assertFalse(summary["candidate_approved"])
        self.assertEqual(model.selected_name, summary["safe_baseline"])
        self.assertIn("insufficient", summary["reason"])

    def test_transition_cost_can_block_migration(self) -> None:
        model = compile_safe_autoindex(
            range(32),
            ranges(32, 200, 3, 30),
            ranges(32, 20_000, 3, 30),
            policy=SafeSelectionPolicy(
                horizon_operations=100,
                migration_cost_units=10_000.0,
            ),
        )
        self.assertFalse(model.summary()["candidate_approved"])

    def test_test_trace_never_changes_deployment(self) -> None:
        train = ranges(32, 200, 3, 30)
        validation = ranges(32, 20_000, 3, 30)
        left = compile_safe_autoindex(
            range(32),
            train,
            validation,
            test_trace=ranges(32, 100, 3, 30),
        )
        right_test = WorkloadTrace(32)
        for index in range(100):
            right_test.add_update(1 + index % 32, float(index))
        right = compile_safe_autoindex(
            range(32),
            train,
            validation,
            test_trace=right_test,
        )
        self.assertEqual(left.selected_name, right.selected_name)
        self.assertNotEqual(
            left.artifact["test_evaluation"]["deployed_score"],
            right.artifact["test_evaluation"]["deployed_score"],
        )

    def test_verifier_rejects_rewritten_decision(self) -> None:
        certificate = compile_safe_autoindex(
            range(16),
            ranges(16, 100, 2, 15),
            ranges(16, 2_000, 2, 15),
        ).export_certificate()
        certificate["decision"]["candidate_approved"] = not certificate[
            "decision"
        ]["candidate_approved"]
        redigest(certificate)
        with self.assertRaisesRegex(
            SafeAutoIndexVerificationError, "decision"
        ):
            verify_safe_autoindex_certificate(certificate)

    def test_unified_cli_verifies_and_explains(self) -> None:
        certificate = compile_safe_autoindex(
            range(16),
            ranges(16, 100, 2, 15),
            ranges(16, 2_000, 2, 15),
        ).export_certificate()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "safe.json"
            path.write_text(json.dumps(certificate), encoding="utf-8")
            for command in ("verify", "explain"):
                completed = subprocess.run(
                    [sys.executable, "-m", "certigap.cli", command, str(path)],
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertEqual(
                    payload["artifact_type"],
                    "certigap-safe-autoindex-v1",
                )

    def test_public_input_validation(self) -> None:
        trace = ranges(8, 10, 1, 8)
        with self.assertRaisesRegex(ValueError, "validation"):
            compile_safe_autoindex(range(8), trace, WorkloadTrace(8))
        with self.assertRaisesRegex(ValueError, "confidence_alpha"):
            compile_safe_autoindex(
                range(8),
                trace,
                trace,
                policy=SafeSelectionPolicy(confidence_alpha=1.0),
            )


if __name__ == "__main__":
    unittest.main()
