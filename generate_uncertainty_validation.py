from __future__ import annotations

import csv
import random
from pathlib import Path

from certigap import make_distribution, multinomial_uncertainty


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def draw_counts(probabilities: list[float], sample_size: int, rng: random.Random) -> list[int]:
    counts = [0] * len(probabilities)
    for index in rng.choices(range(len(probabilities)), weights=probabilities, k=sample_size):
        counts[index] += 1
    return counts


def main() -> None:
    repetitions = 250
    rows = []
    for distribution in ("uniform", "zipf"):
        for n in (8, 32):
            truth = make_distribution(distribution, n)
            for sample_size in (100, 1_000, 10_000):
                covered = 0
                radii = []
                distances = []
                for repetition in range(repetitions):
                    rng = random.Random(
                        f"{distribution}:{n}:{sample_size}:{repetition}"
                    )
                    counts = draw_counts(truth, sample_size, rng)
                    uncertainty = multinomial_uncertainty(
                        counts,
                        confidence=0.95,
                        pseudocount=0.5,
                    )
                    distance = 0.5 * sum(
                        abs(left - right)
                        for left, right in zip(truth, uncertainty.nominal)
                    )
                    covered += distance <= uncertainty.tv_radius + 1e-12
                    radii.append(uncertainty.tv_radius)
                    distances.append(distance)
                rows.append(
                    {
                        "distribution": distribution,
                        "n": n,
                        "sample_size": sample_size,
                        "repetitions": repetitions,
                        "target_confidence": 0.95,
                        "empirical_coverage": covered / repetitions,
                        "mean_tv_radius": sum(radii) / repetitions,
                        "max_tv_radius": max(radii),
                        "mean_true_distance": sum(distances) / repetitions,
                    }
                )

    RESULTS.mkdir(exist_ok=True)
    csv_path = RESULTS / "uncertainty_validation.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Finite-Sample TV Radius Validation",
        "",
        "Each row uses 250 deterministic i.i.d. multinomial repetitions. Coverage "
        "checks whether the known generating distribution lies inside the reported "
        "smoothed TV ball. This validates implementation and conservatism under "
        "the i.i.d. model only; it is not evidence for dependent production traces.",
        "",
        "| Distribution | n | N | Coverage | Mean radius | Mean true TV |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {row['distribution']} | {row['n']} | {row['sample_size']} | "
        f"{row['empirical_coverage']:.3f} | {row['mean_tv_radius']:.5f} | "
        f"{row['mean_true_distance']:.5f} |"
        for row in rows
    ]
    (RESULTS / "uncertainty_validation.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} uncertainty-validation rows")


if __name__ == "__main__":
    main()
