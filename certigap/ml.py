from __future__ import annotations

from dataclasses import asdict, dataclass
from math import exp, isfinite, log, sqrt
from typing import Sequence


EPS = 1e-12


class CertiGapMLError(ValueError):
    pass


@dataclass(frozen=True)
class LogisticConfig:
    name: str
    learning_rate: float
    l2: float = 0.0

    def validate(self) -> None:
        if not self.name or not isfinite(self.learning_rate) or self.learning_rate <= 0.0:
            raise CertiGapMLError("learning_rate must be finite and positive")
        if not isfinite(self.l2) or self.l2 < 0.0:
            raise CertiGapMLError("l2 must be finite and non-negative")


def _validate_dataset(
    features: Sequence[Sequence[float]], labels: Sequence[int]
) -> tuple[list[list[float]], list[int]]:
    if not features or len(features) != len(labels):
        raise CertiGapMLError("features and labels must be non-empty and aligned")
    width = len(features[0])
    if width == 0:
        raise CertiGapMLError("features must have at least one column")
    matrix = [[float(value) for value in row] for row in features]
    if any(len(row) != width for row in matrix) or any(
        not isfinite(value) for row in matrix for value in row
    ):
        raise CertiGapMLError("features must be a finite rectangular matrix")
    targets = [int(label) for label in labels]
    if any(label not in (0, 1) for label in targets):
        raise CertiGapMLError("only binary labels 0 and 1 are supported")
    return matrix, targets


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        return 1.0 / (1.0 + exp(-value))
    ratio = exp(value)
    return ratio / (1.0 + ratio)


@dataclass
class _OnlineLogistic:
    config: LogisticConfig
    weights: list[float]
    bias: float = 0.0

    @classmethod
    def create(cls, config: LogisticConfig, width: int) -> "_OnlineLogistic":
        return cls(config=config, weights=[0.0] * width)

    def train_epoch(self, features: list[list[float]], labels: list[int]) -> None:
        for row, label in zip(features, labels, strict=True):
            probability = _sigmoid(
                self.bias + sum(weight * value for weight, value in zip(self.weights, row, strict=True))
            )
            error = probability - label
            for index, value in enumerate(row):
                gradient = error * value + self.config.l2 * self.weights[index]
                self.weights[index] -= self.config.learning_rate * gradient
            self.bias -= self.config.learning_rate * error

    def predict(self, features: list[list[float]]) -> list[int]:
        return [
            int(
                _sigmoid(
                    self.bias
                    + sum(
                        weight * value
                        for weight, value in zip(self.weights, row, strict=True)
                    )
                )
                >= 0.5
            )
            for row in features
        ]


def _accuracy(predictions: list[int], labels: list[int]) -> float:
    if len(predictions) != len(labels):
        raise CertiGapMLError("prediction length mismatch")
    return sum(prediction == label for prediction, label in zip(predictions, labels, strict=True)) / len(labels)


def _confidence_radius(
    validation_size: int,
    candidate_count: int,
    checkpoint_count: int,
    alpha: float,
) -> float:
    # Union bound across the predeclared candidate/checkpoint programs.
    return sqrt(log(2.0 * candidate_count * checkpoint_count / alpha) / (2.0 * validation_size))


class CertiGapML:
    """Certified finite-portfolio elimination for binary online logistic models.

    The certificate controls validation accuracy for every *evaluated* fixed
    checkpoint program. It does not assert that a pruned candidate would not
    improve after unseen future training epochs.
    """

    def __init__(
        self,
        configs: Sequence[LogisticConfig],
        checkpoints: Sequence[int],
        *,
        alpha: float = 0.05,
        pruning_margin: float = 0.0,
    ) -> None:
        self.configs = tuple(configs)
        self.checkpoints = tuple(int(value) for value in checkpoints)
        self.alpha = float(alpha)
        self.pruning_margin = float(pruning_margin)
        if len(self.configs) < 2:
            raise CertiGapMLError("at least two predeclared candidates are required")
        if len({config.name for config in self.configs}) != len(self.configs):
            raise CertiGapMLError("candidate names must be unique")
        for config in self.configs:
            config.validate()
        if (
            not self.checkpoints
            or self.checkpoints[0] <= 0
            or any(right <= left for left, right in zip(self.checkpoints, self.checkpoints[1:]))
        ):
            raise CertiGapMLError("checkpoints must be strictly increasing positive epochs")
        if not isfinite(self.alpha) or not 0.0 < self.alpha < 1.0:
            raise CertiGapMLError("alpha must lie in (0, 1)")
        if not isfinite(self.pruning_margin) or self.pruning_margin < 0.0:
            raise CertiGapMLError("pruning_margin must be finite and non-negative")

    def fit(
        self,
        train_features: Sequence[Sequence[float]],
        train_labels: Sequence[int],
        validation_features: Sequence[Sequence[float]],
        validation_labels: Sequence[int],
        test_features: Sequence[Sequence[float]],
        test_labels: Sequence[int],
    ) -> dict:
        train_x, train_y = _validate_dataset(train_features, train_labels)
        validation_x, validation_y = _validate_dataset(validation_features, validation_labels)
        test_x, test_y = _validate_dataset(test_features, test_labels)
        width = len(train_x[0])
        if len(validation_x[0]) != width or len(test_x[0]) != width:
            raise CertiGapMLError("all splits must have the same feature width")

        radius = _confidence_radius(
            len(validation_y), len(self.configs), len(self.checkpoints), self.alpha
        )
        models = {
            config.name: _OnlineLogistic.create(config, width) for config in self.configs
        }
        active = {config.name for config in self.configs}
        epochs = {config.name: 0 for config in self.configs}
        records: list[dict] = []
        final_records: dict[str, dict] = {}

        for round_index, checkpoint in enumerate(self.checkpoints):
            current: list[dict] = []
            for config in self.configs:
                if config.name not in active:
                    continue
                model = models[config.name]
                while epochs[config.name] < checkpoint:
                    model.train_epoch(train_x, train_y)
                    epochs[config.name] += 1
                predictions = model.predict(validation_x)
                accuracy = _accuracy(predictions, validation_y)
                row = {
                    "round": round_index,
                    "checkpoint": checkpoint,
                    "candidate": config.name,
                    "validation_predictions": predictions,
                    "validation_accuracy": accuracy,
                    "confidence_radius": radius,
                    "lower_accuracy": max(0.0, accuracy - radius),
                    "upper_accuracy": min(1.0, accuracy + radius),
                    "pruned": False,
                }
                current.append(row)
                final_records[config.name] = row
            if not current:
                raise RuntimeError("elimination removed every candidate")
            leader = min(current, key=lambda row: (-row["validation_accuracy"], row["candidate"]))
            leader_lower = leader["lower_accuracy"]
            for row in current:
                row["pruned"] = (
                    row["candidate"] != leader["candidate"]
                    and row["upper_accuracy"] < leader_lower - self.pruning_margin
                )
                if row["pruned"]:
                    active.remove(row["candidate"])
            records.extend(current)

        selected = min(
            (final_records[name] for name in active),
            key=lambda row: (-row["validation_accuracy"], row["candidate"]),
        )
        selected_model = models[selected["candidate"]]
        test_predictions = selected_model.predict(test_x)
        test_accuracy = _accuracy(test_predictions, test_y)
        maximum_upper = max(row["upper_accuracy"] for row in records)
        selection_regret_upper_bound = max(
            0.0, maximum_upper - selected["lower_accuracy"]
        )
        certificate = {
            "schema": "certigap-ml-v1",
            "model": "online-logistic-v1",
            "configs": [asdict(config) for config in self.configs],
            "checkpoints": list(self.checkpoints),
            "alpha": self.alpha,
            "pruning_margin": self.pruning_margin,
            "validation_labels": validation_y,
            "records": records,
            "selected": selected["candidate"],
            "selection_regret_upper_bound": selection_regret_upper_bound,
            "test_evaluation": {
                "labels": test_y,
                "predictions": test_predictions,
                "accuracy": test_accuracy,
                "evaluated_after_selection": True,
            },
            "scope": (
                "simultaneous Hoeffding coverage for predeclared candidate/checkpoint "
                "programs under IID validation examples; pruning does not certify "
                "unobserved future-training quality"
            ),
        }
        from .ml_verifier import verify_certigap_ml_certificate

        verification = verify_certigap_ml_certificate(certificate)
        return {
            "selected": selected["candidate"],
            "validation_accuracy": selected["validation_accuracy"],
            "test_accuracy": test_accuracy,
            "selection_regret_upper_bound": selection_regret_upper_bound,
            "fully_trained_candidates": len(active),
            "pruned_candidates": len(self.configs) - len(active),
            "certificate": certificate,
            "verification": verification,
        }
