from __future__ import annotations

import csv
import json
import random
from pathlib import Path

from certigap import (
    CertiGapML,
    LogisticConfig,
    verify_certigap_ml_certificate,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"

CONFIGS = [
    LogisticConfig("fast", 0.15),
    LogisticConfig("regularized", 0.05, 0.03),
    LogisticConfig("conservative", 0.02, 0.005),
    LogisticConfig("over_regularized", 0.15, 50.0),
]


def make_dataset(kind: str, seed: int, size: int = 720) -> tuple[list[list[float]], list[int]]:
    generator = random.Random(seed)
    features: list[list[float]] = []
    labels: list[int] = []
    for _ in range(size):
        first = generator.gauss(0.0, 1.0)
        second = generator.gauss(0.0, 1.0)
        noise = generator.gauss(0.0, 0.45 if kind != "noisy" else 1.2)
        if kind == "linear":
            score = first - 0.7 * second + noise
        elif kind == "imbalanced":
            score = first - 0.5 * second + noise - 1.0
        elif kind == "sparse":
            score = 1.6 * first + noise
        elif kind == "noisy":
            score = 0.8 * first - 0.3 * second + noise
        else:
            raise ValueError(f"unknown synthetic scenario {kind}")
        features.append([first, second])
        labels.append(int(score >= 0.0))
    return features, labels


def split(features: list[list[float]], labels: list[int]) -> tuple[list[list[float]], ...]:
    return (
        features[:360],
        labels[:360],
        features[360:540],
        labels[360:540],
        features[540:],
        labels[540:],
    )


def mean(rows: list[dict], field: str) -> float:
    return sum(float(row[field]) for row in rows) / len(rows)


def main() -> None:
    rows: list[dict] = []
    example: dict | None = None
    for scenario in ("linear", "sparse", "imbalanced", "noisy"):
        for seed in range(4):
            data = split(*make_dataset(scenario, 20260807 + seed))
            certigap = CertiGapML(CONFIGS, [1, 2, 4, 8], alpha=0.05).fit(*data)
            full = CertiGapML(
                CONFIGS, [1, 2, 4, 8], alpha=0.05, pruning_margin=2.0
            ).fit(*data)
            verified = verify_certigap_ml_certificate(certigap["certificate"])
            rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "selected": certigap["selected"],
                    "test_accuracy": certigap["test_accuracy"],
                    "full_portfolio_test_accuracy": full["test_accuracy"],
                    "test_accuracy_difference": certigap["test_accuracy"] - full["test_accuracy"],
                    "fully_trained_candidates": certigap["fully_trained_candidates"],
                    "pruned_candidates": certigap["pruned_candidates"],
                    "selection_regret_upper_bound": certigap["selection_regret_upper_bound"],
                    "certificate_verified": verified["verified"],
                }
            )
            if example is None:
                example = certigap["certificate"]
    assert example is not None
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "certigap_ml_validation.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (RESULTS / "certigap_ml_example.json").write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# CertiGap-ML Synthetic Diagnostic Validation",
        "",
        "This small deterministic suite validates implementation and certificate replay only. It is not evidence of broad AutoML superiority; public tabular datasets and external baselines remain required research work.",
        "",
        f"- Rows: `{len(rows)}`",
        f"- Replayed certificates: `{sum(row['certificate_verified'] is True for row in rows)}/{len(rows)}`",
        f"- Mean candidates fully trained: `{mean(rows, 'fully_trained_candidates'):.2f}` of `{len(CONFIGS)}`",
        f"- Mean test-accuracy difference against full portfolio: `{mean(rows, 'test_accuracy_difference'):.4f}`",
        f"- Mean certified regret upper bound over evaluated checkpoints: `{mean(rows, 'selection_regret_upper_bound'):.4f}`",
    ]
    (RESULTS / "certigap_ml_validation.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(rows)} CertiGap-ML validation rows")


if __name__ == "__main__":
    main()
