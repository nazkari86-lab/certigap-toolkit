from __future__ import annotations

import copy
import unittest

from certigap import (
    CertiGapML,
    CertiGapMLVerificationError,
    LogisticConfig,
    verify_certigap_ml_certificate,
)


def split_data(repeats: int) -> tuple[list[list[float]], list[int]]:
    rows = [[-2.0], [-1.0], [-0.5], [0.5], [1.0], [2.0]] * repeats
    labels = [0, 0, 0, 1, 1, 1] * repeats
    return rows, labels


class CertiGapMLTests(unittest.TestCase):
    def build_result(self) -> dict:
        train_x, train_y = split_data(20)
        validation_x, validation_y = split_data(40)
        test_x, test_y = split_data(15)
        return CertiGapML(
            [
                LogisticConfig("over_regularized", 0.2, 1_000.0),
                LogisticConfig("fast", 0.2),
                LogisticConfig("regularized", 0.05, 0.1),
            ],
            [1, 2, 4],
            alpha=0.05,
        ).fit(train_x, train_y, validation_x, validation_y, test_x, test_y)

    def test_certificate_replays_and_keeps_test_after_selection(self) -> None:
        result = self.build_result()
        verified = verify_certigap_ml_certificate(result["certificate"])
        self.assertTrue(verified["verified"])
        self.assertTrue(
            result["certificate"]["test_evaluation"]["evaluated_after_selection"]
        )
        self.assertGreaterEqual(result["test_accuracy"], 0.9)

    def test_weak_candidate_is_pruned_with_declared_confidence_rule(self) -> None:
        result = self.build_result()
        records = result["certificate"]["records"]
        self.assertTrue(
            any(
                row["candidate"] == "over_regularized" and row["pruned"]
                for row in records
            )
        )
        self.assertGreater(result["pruned_candidates"], 0)

    def test_verifier_rejects_tampered_pruning_decision(self) -> None:
        result = self.build_result()
        artifact = copy.deepcopy(result["certificate"])
        artifact["records"][0]["pruned"] = not artifact["records"][0]["pruned"]
        with self.assertRaises(CertiGapMLVerificationError):
            verify_certigap_ml_certificate(artifact)


if __name__ == "__main__":
    unittest.main()
