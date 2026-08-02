from __future__ import annotations

import copy
import hashlib
import json
import unittest

from certigap.autoindex import WorkloadTrace
from certigap.martingale_safe_autoindex import (
    MartingaleSafeSelectionPolicy,
    compile_martingale_safe_autoindex,
)
from certigap.martingale_safe_autoindex_verifier import (
    MartingaleSafeAutoIndexVerificationError,
    verify_martingale_safe_autoindex_certificate,
)


def ranges(count: int) -> WorkloadTrace:
    trace = WorkloadTrace(8)
    for _ in range(count):
        trace.add_range(2, 7)
    return trace


def deploy_then_harm() -> WorkloadTrace:
    trace = ranges(1_000)
    for index in range(3_000):
        trace.add_update(1 + index % 8, float(index))
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


class MartingaleSafeAutoIndexTests(unittest.TestCase):
    def test_stable_adapted_stream_deploys(self) -> None:
        model = compile_martingale_safe_autoindex(
            range(8),
            ranges(100),
            ranges(1_000),
            test_trace=ranges(50),
            policy=MartingaleSafeSelectionPolicy(
                minimum_observations=50
            ),
        )
        summary = model.summary()
        self.assertTrue(summary["candidate_approved"])
        self.assertFalse(summary["candidate_revoked"])
        self.assertEqual(summary["selected"], "prefix_sum")
        self.assertEqual(summary["deployment_operation"], 371)
        verified = verify_martingale_safe_autoindex_certificate(
            model.export_certificate()
        )
        self.assertTrue(verified["verified"])

    def test_post_deployment_harm_revokes_to_baseline(self) -> None:
        model = compile_martingale_safe_autoindex(
            range(8),
            ranges(100),
            deploy_then_harm(),
            policy=MartingaleSafeSelectionPolicy(
                minimum_observations=50
            ),
        )
        summary = model.summary()
        self.assertTrue(summary["candidate_approved"])
        self.assertTrue(summary["candidate_revoked"])
        self.assertEqual(summary["selected"], summary["safe_baseline"])
        self.assertGreater(
            summary["revocation_operation"],
            summary["deployment_operation"],
        )

    def test_short_stream_fails_closed(self) -> None:
        model = compile_martingale_safe_autoindex(
            range(8),
            ranges(100),
            ranges(20),
            policy=MartingaleSafeSelectionPolicy(
                minimum_observations=10
            ),
        )
        self.assertFalse(model.summary()["candidate_approved"])
        self.assertEqual(
            model.summary()["selected"], model.summary()["safe_baseline"]
        )

    def test_verifier_rejects_fabricated_revocation(self) -> None:
        certificate = compile_martingale_safe_autoindex(
            range(8),
            ranges(100),
            ranges(1_000),
        ).export_certificate()
        certificate["decision"]["candidate_revoked"] = True
        redigest(certificate)
        with self.assertRaisesRegex(
            MartingaleSafeAutoIndexVerificationError, "decision"
        ):
            verify_martingale_safe_autoindex_certificate(certificate)

    def test_policy_validation(self) -> None:
        with self.assertRaisesRegex(ValueError, "betting_fractions"):
            compile_martingale_safe_autoindex(
                range(8),
                ranges(100),
                ranges(20),
                policy=MartingaleSafeSelectionPolicy(
                    betting_fractions=()
                ),
            )


if __name__ == "__main__":
    unittest.main()
