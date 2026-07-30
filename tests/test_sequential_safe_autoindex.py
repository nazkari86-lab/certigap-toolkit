from __future__ import annotations

import copy
import hashlib
import json
import unittest

from certigap import (
    SequentialSafeAutoIndexVerificationError,
    SequentialSafeSelectionPolicy,
    WorkloadTrace,
    compile_sequential_safe_autoindex,
    verify_sequential_safe_autoindex_certificate,
)


def ranges(n: int, count: int) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for _ in range(count):
        trace.add_range(2, n - 1)
    return trace


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


class SequentialSafeAutoIndexTests(unittest.TestCase):
    def test_first_safe_prefix_is_recorded_and_verified(self) -> None:
        validation = ranges(8, 12_000)
        model = compile_sequential_safe_autoindex(
            range(8),
            ranges(8, 100),
            validation,
            test_trace=ranges(8, 50),
            policy=SequentialSafeSelectionPolicy(
                minimum_observations=100,
                horizon_operations=1_000_000,
            ),
        )
        summary = model.summary()
        self.assertTrue(summary["candidate_approved"])
        self.assertEqual(summary["selected"], "prefix_sum")
        self.assertGreaterEqual(summary["stopping_operation"], 100)
        self.assertLess(summary["stopping_operation"], 12_000)
        decision = model.artifact["decision"]
        self.assertEqual(
            decision["monitoring"]["post_stop_operations"],
            12_000 - summary["stopping_operation"],
        )
        verified = verify_sequential_safe_autoindex_certificate(
            model.export_certificate()
        )
        self.assertTrue(verified["verified"])
        self.assertEqual(
            verified["stopping_operation"], summary["stopping_operation"]
        )

    def test_small_stream_fails_closed(self) -> None:
        model = compile_sequential_safe_autoindex(
            range(8),
            ranges(8, 100),
            ranges(8, 10),
            policy=SequentialSafeSelectionPolicy(minimum_observations=5),
        )
        self.assertFalse(model.summary()["candidate_approved"])
        self.assertIsNone(model.summary()["stopping_operation"])

    def test_alpha_spending_never_exceeds_budget(self) -> None:
        certificate = compile_sequential_safe_autoindex(
            range(8),
            ranges(8, 100),
            ranges(8, 12_000),
        ).export_certificate()
        checkpoint = certificate["decision"]["selection_checkpoint"]
        self.assertIsNotNone(checkpoint)
        self.assertLess(
            checkpoint["spent_alpha_through_operation"],
            certificate["policy"]["confidence_alpha"],
        )

    def test_verifier_rejects_later_fabricated_stop(self) -> None:
        certificate = compile_sequential_safe_autoindex(
            range(8),
            ranges(8, 100),
            ranges(8, 12_000),
        ).export_certificate()
        certificate["decision"]["stopping_operation"] += 1
        redigest(certificate)
        with self.assertRaisesRegex(
            SequentialSafeAutoIndexVerificationError,
            "decision",
        ):
            verify_sequential_safe_autoindex_certificate(certificate)

    def test_minimum_observations_must_fit_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "exceeds"):
            compile_sequential_safe_autoindex(
                range(8),
                ranges(8, 100),
                ranges(8, 10),
                policy=SequentialSafeSelectionPolicy(
                    minimum_observations=11
                ),
            )


if __name__ == "__main__":
    unittest.main()
