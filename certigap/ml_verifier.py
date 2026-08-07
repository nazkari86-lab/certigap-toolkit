from __future__ import annotations

from math import isfinite, log, sqrt


EPS = 1e-9


class CertiGapMLVerificationError(ValueError):
    pass


def _accuracy(predictions: list[int], labels: list[int]) -> float:
    if len(predictions) != len(labels) or not labels:
        raise CertiGapMLVerificationError("invalid prediction vector")
    if any(value not in (0, 1) for value in predictions + labels):
        raise CertiGapMLVerificationError("predictions and labels must be binary")
    return sum(prediction == label for prediction, label in zip(predictions, labels, strict=True)) / len(labels)


def verify_certigap_ml_certificate(certificate: dict) -> dict:
    """Verify finite-portfolio confidence and pruning arithmetic.

    This verifier checks the submitted prediction-level statistical certificate.
    It intentionally does not claim independent replay of numerical training.
    """
    if not isinstance(certificate, dict) or certificate.get("schema") != "certigap-ml-v1":
        raise CertiGapMLVerificationError("unsupported CertiGap-ML certificate")
    configs = certificate.get("configs")
    checkpoints = certificate.get("checkpoints")
    validation_labels = certificate.get("validation_labels")
    alpha = certificate.get("alpha")
    margin = certificate.get("pruning_margin")
    records = certificate.get("records")
    if (
        not isinstance(configs, list)
        or len(configs) < 2
        or not isinstance(checkpoints, list)
        or not checkpoints
        or not isinstance(validation_labels, list)
        or not validation_labels
        or any(label not in (0, 1) for label in validation_labels)
        or isinstance(alpha, bool)
        or not isinstance(alpha, (int, float))
        or not isfinite(float(alpha))
        or not 0.0 < float(alpha) < 1.0
        or isinstance(margin, bool)
        or not isinstance(margin, (int, float))
        or not isfinite(float(margin))
        or float(margin) < 0.0
        or not isinstance(records, list)
    ):
        raise CertiGapMLVerificationError("certificate inputs are invalid")
    names = [config.get("name") if isinstance(config, dict) else None for config in configs]
    if len(set(names)) != len(names) or any(not isinstance(name, str) or not name for name in names):
        raise CertiGapMLVerificationError("candidate names are invalid")
    if any(
        not isinstance(value, int)
        or isinstance(value, bool)
        or value <= 0
        for value in checkpoints
    ) or any(right <= left for left, right in zip(checkpoints, checkpoints[1:])):
        raise CertiGapMLVerificationError("checkpoints are invalid")
    radius = sqrt(log(2.0 * len(names) * len(checkpoints) / float(alpha)) / (2.0 * len(validation_labels)))
    active = set(names)
    offset = 0
    last_rows: dict[str, dict] = {}
    for round_index, checkpoint in enumerate(checkpoints):
        expected_names = [name for name in names if name in active]
        rows = records[offset : offset + len(expected_names)]
        if len(rows) != len(expected_names):
            raise CertiGapMLVerificationError("candidate records are incomplete")
        if [row.get("candidate") for row in rows] != expected_names:
            raise CertiGapMLVerificationError("candidate record order is invalid")
        for row in rows:
            predictions = row.get("validation_predictions")
            if (
                row.get("round") != round_index
                or row.get("checkpoint") != checkpoint
                or not isinstance(predictions, list)
            ):
                raise CertiGapMLVerificationError("checkpoint record is invalid")
            accuracy = _accuracy(predictions, validation_labels)
            expected = {
                "validation_accuracy": accuracy,
                "confidence_radius": radius,
                "lower_accuracy": max(0.0, accuracy - radius),
                "upper_accuracy": min(1.0, accuracy + radius),
            }
            for field, value in expected.items():
                supplied = row.get(field)
                if (
                    isinstance(supplied, bool)
                    or not isinstance(supplied, (int, float))
                    or not isfinite(float(supplied))
                    or abs(float(supplied) - value) > EPS
                ):
                    raise CertiGapMLVerificationError(f"{field} does not replay")
            last_rows[row["candidate"]] = row
        leader = min(rows, key=lambda row: (-row["validation_accuracy"], row["candidate"]))
        for row in rows:
            expected_pruned = (
                row["candidate"] != leader["candidate"]
                and row["upper_accuracy"] < leader["lower_accuracy"] - float(margin)
            )
            if row.get("pruned") is not expected_pruned:
                raise CertiGapMLVerificationError("pruning decision does not replay")
            if expected_pruned:
                active.remove(row["candidate"])
        offset += len(rows)
    if offset != len(records) or not active:
        raise CertiGapMLVerificationError("certificate has extra records or no survivor")
    selected = certificate.get("selected")
    expected_selected = min(
        (last_rows[name] for name in active),
        key=lambda row: (-row["validation_accuracy"], row["candidate"]),
    )["candidate"]
    if selected != expected_selected:
        raise CertiGapMLVerificationError("selected candidate does not replay")
    regret = max(
        0.0,
        max(row["upper_accuracy"] for row in records)
        - last_rows[selected]["lower_accuracy"],
    )
    supplied_regret = certificate.get("selection_regret_upper_bound")
    if (
        isinstance(supplied_regret, bool)
        or not isinstance(supplied_regret, (int, float))
        or not isfinite(float(supplied_regret))
        or abs(float(supplied_regret) - regret) > EPS
    ):
        raise CertiGapMLVerificationError("selection regret bound does not replay")
    test = certificate.get("test_evaluation")
    if (
        not isinstance(test, dict)
        or test.get("evaluated_after_selection") is not True
        or not isinstance(test.get("labels"), list)
        or not isinstance(test.get("predictions"), list)
    ):
        raise CertiGapMLVerificationError("test evaluation is invalid")
    test_accuracy = _accuracy(test["predictions"], test["labels"])
    if abs(float(test.get("accuracy")) - test_accuracy) > EPS:
        raise CertiGapMLVerificationError("test accuracy does not replay")
    return {
        "verified": True,
        "selected": selected,
        "active_candidates": sorted(active),
        "evaluated_checkpoint_models": len(records),
        "confidence_radius": radius,
        "selection_regret_upper_bound": regret,
        "test_accuracy": test_accuracy,
        "scope": certificate.get("scope"),
    }
