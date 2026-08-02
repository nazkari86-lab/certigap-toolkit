from __future__ import annotations

import hashlib
import json
import unittest

from certigap import (
    AdaptiveSpec,
    MeasuredDeploymentPolicy,
    MeasuredDeploymentVerificationError,
    WorkloadTrace,
    compile_measured_autoindex,
    paired_latency_decision,
    verify_measured_deployment_artifact,
)


def redigest(artifact: dict) -> None:
    artifact.pop("sha256", None)
    payload = json.dumps(
        artifact,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    artifact["sha256"] = hashlib.sha256(payload).hexdigest()


class MeasuredDeploymentTests(unittest.TestCase):
    def test_paired_gate_approves_only_with_bounded_evidence(self) -> None:
        policy = MeasuredDeploymentPolicy(
            repetitions=64,
            minimum_normalized_improvement=0.05,
        )
        approved = paired_latency_decision([(1000, 100)] * 64, policy)
        rejected = paired_latency_decision([(1000, 900)] * 64, policy)

        self.assertTrue(approved["candidate_deployed"])
        self.assertFalse(rejected["candidate_deployed"])
        self.assertLess(approved["upper_normalized_harm"], -0.05)
        self.assertGreater(rejected["upper_normalized_harm"], -0.05)

    def test_real_shadow_replay_preserves_runtime_semantics(self) -> None:
        train = WorkloadTrace(128)
        validation = WorkloadTrace(128)
        for _ in range(32):
            train.add_range(2, 120)
            validation.add_range(3, 110)
        validation.add_update(5, 1000.0).add_range(2, 10)
        compiled = compile_measured_autoindex(
            range(128),
            train,
            validation,
            AdaptiveSpec(operations=("range", "update")),
            policy=MeasuredDeploymentPolicy(
                repetitions=8,
                warmup_repetitions=1,
            ),
        )

        verified = verify_measured_deployment_artifact(
            compiled.export_certificate()
        )
        self.assertTrue(verified["verified"])
        self.assertIn(compiled.selected_name, {"sorted_array", "prefix_sum"})
        self.assertEqual(compiled.range_query(2, 10), sum(range(1, 10)))
        compiled.point_update(2, 100.0)
        self.assertEqual(compiled.get(2), 100.0)

    def test_verifier_rejects_rewritten_measurement(self) -> None:
        train = WorkloadTrace(32)
        validation = WorkloadTrace(32)
        for _ in range(8):
            train.add_range(1, 32)
            validation.add_range(1, 32)
        compiled = compile_measured_autoindex(
            range(32),
            train,
            validation,
            AdaptiveSpec(operations=("range",)),
            policy=MeasuredDeploymentPolicy(
                repetitions=4,
                warmup_repetitions=0,
            ),
        )
        tampered = compiled.export_certificate()
        tampered["paired_batch_latency_ns"][0]["candidate"] *= 100
        redigest(tampered)

        with self.assertRaisesRegex(
            MeasuredDeploymentVerificationError,
            "decision field mismatch",
        ):
            verify_measured_deployment_artifact(tampered)

    def test_verifier_rejects_rewritten_spec_and_sample_count(self) -> None:
        trace = WorkloadTrace(16)
        for _ in range(4):
            trace.add_range(1, 16)
        compiled = compile_measured_autoindex(
            range(16),
            trace,
            trace,
            AdaptiveSpec(operations=("range",)),
            policy=MeasuredDeploymentPolicy(
                repetitions=4,
                warmup_repetitions=0,
            ),
        )

        altered_spec = compiled.export_certificate()
        altered_spec["spec"]["operations"] = ["get"]
        redigest(altered_spec)
        with self.assertRaisesRegex(
            MeasuredDeploymentVerificationError,
            "invalid validation operation",
        ):
            verify_measured_deployment_artifact(altered_spec)

        altered_count = compiled.export_certificate()
        altered_count["decision"]["sample_count"] += 1
        redigest(altered_count)
        with self.assertRaisesRegex(
            MeasuredDeploymentVerificationError,
            "sample count mismatch",
        ):
            verify_measured_deployment_artifact(altered_count)

        altered_build = compiled.export_certificate()
        altered_build["build_latency_ns"]["migration_penalty"] += 1
        redigest(altered_build)
        with self.assertRaisesRegex(
            MeasuredDeploymentVerificationError,
            "migration penalty mismatch",
        ):
            verify_measured_deployment_artifact(altered_build)

    def test_invalid_policy_and_pairs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            paired_latency_decision(
                [(1, 1)],
                MeasuredDeploymentPolicy(alpha=0.0, repetitions=1),
            )
        with self.assertRaises(ValueError):
            paired_latency_decision(
                [(0, 1)],
                MeasuredDeploymentPolicy(repetitions=1),
            )


if __name__ == "__main__":
    unittest.main()
