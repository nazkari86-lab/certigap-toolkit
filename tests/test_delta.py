from __future__ import annotations

import copy
import hashlib
import json
import unittest
import subprocess
import sys
import tempfile
from pathlib import Path

from certigap import (
    DeltaSpec,
    DeltaVerificationError,
    compile_proof_carrying_delta_index,
    verify_delta_certificate,
)


def rehash(artifact: dict) -> None:
    unsigned = dict(artifact)
    unsigned.pop("sha256", None)
    artifact["sha256"] = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


class DeltaIndexTests(unittest.TestCase):
    def test_mixed_operations_and_deterministic_rebuild(self) -> None:
        index = compile_proof_carrying_delta_index(
            [(10, 1), (20, 2), (40, 4)], DeltaSpec(rebuild_threshold=2)
        )
        index.insert(30, 3)
        self.assertEqual(index.range_query(15, 35), 5)
        index.erase(20)
        index.update(40, 8)
        self.assertEqual(index.get(40), 8)
        certificate = index.export_certificate()
        summary = verify_delta_certificate(certificate)
        self.assertEqual(summary["rebuild_count"], 1)
        self.assertEqual(
            certificate["final_entries"], [[10, 1.0], [30, 3.0], [40, 8.0]]
        )

    def test_min_and_empty_range_identity(self) -> None:
        index = compile_proof_carrying_delta_index(
            [(1, 4), (3, -2)], DeltaSpec(algebra="min")
        )
        self.assertEqual(index.range_query(1, 3), -2)
        self.assertEqual(index.range_query(10, 20), float("inf"))
        verify_delta_certificate(index.export_certificate())

    def test_rehashed_event_tampering_is_rejected(self) -> None:
        index = compile_proof_carrying_delta_index([(1, 1)], DeltaSpec())
        index.insert(2, 2)
        forged = copy.deepcopy(index.export_certificate())
        forged["events"][0]["value"] = 9.0
        rehash(forged)
        with self.assertRaises(DeltaVerificationError):
            verify_delta_certificate(forged)

    def test_invalid_mutations_fail_closed(self) -> None:
        index = compile_proof_carrying_delta_index([(1, 1)])
        with self.assertRaises(KeyError):
            index.insert(1, 2)
        with self.assertRaises(KeyError):
            index.erase(2)
        with self.assertRaises(ValueError):
            index.update(1, float("nan"))

    def test_unified_cli_verifies_and_explains_delta(self) -> None:
        index = compile_proof_carrying_delta_index([(1, 1), (2, 2)])
        index.insert(3, 3)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "delta.json"
            path.write_text(json.dumps(index.export_certificate()), encoding="utf-8")
            root = Path(__file__).resolve().parents[1]
            for command in ("verify", "explain"):
                output = subprocess.check_output(
                    [sys.executable, "-m", "certigap.cli", command, str(path)],
                    cwd=root,
                    text=True,
                )
                payload = json.loads(output)
                self.assertEqual(
                    payload["artifact_type"], "certigap-proof-carrying-delta-v1"
                )
                verified = (
                    payload["verification"]["verified"]
                    if command == "verify"
                    else payload["verified"]
                )
                self.assertTrue(verified)


if __name__ == "__main__":
    unittest.main()
