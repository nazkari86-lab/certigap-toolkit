from __future__ import annotations

import csv
from pathlib import Path

from certigap import CertiGapAutoDRO, fit_autodro, make_distribution, normalize_weights


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def counts(probabilities: list[float], total: int = 10_000) -> list[int]:
    result = [int(round(value * total)) for value in probabilities]
    result[max(range(len(result)), key=result.__getitem__)] += total - sum(result)
    return result


def mix(left: list[float], right: list[float], fraction: float) -> list[float]:
    return normalize_weights(
        [
            (1.0 - fraction) * left_value + fraction * right_value
            for left_value, right_value in zip(left, right)
        ]
    )


def expected_cost(model: CertiGapAutoDRO, probabilities: list[float]) -> float:
    return sum(
        probability * model.estimated_query_cost(index + 1)
        for index, probability in enumerate(probabilities)
    )


def main() -> None:
    n = 32
    head = normalize_weights([25.0 if index < 4 else 1.0 for index in range(n)])
    tail = make_distribution("hot_tail", n)
    windows = (
        [head] * 3
        + [mix(head, tail, fraction) for fraction in (0.2, 0.4, 0.6, 0.8)]
        + [tail] * 3
        + [make_distribution("zipf", n)] * 2
    )
    oracle_costs = []
    for probabilities in windows:
        oracle = fit_autodro(
            counts(probabilities),
            4,
            tv_radius=0.1,
            direct_tv_limit=0,
        )
        oracle_costs.append(
            sum(
                probability * cost
                for probability, cost in zip(
                    probabilities,
                    oracle.selected["per_key_execution_costs"],
                )
            )
        )

    rows = []
    for threshold in (0.0, 0.03, 0.08, 0.15):
        model = CertiGapAutoDRO().fit(
            counts(windows[0]),
            4,
            tv_radius=0.1,
            direct_tv_limit=0,
        )
        rebuilds = 1
        total_cost = 0.0
        max_regret = 0.0
        for probabilities, oracle_cost in zip(windows, oracle_costs):
            model.update_window(
                counts(probabilities),
                min_tv_drift=threshold,
            )
            rebuilds += int(model.summary()["last_adaptation"]["refit"])
            cost = expected_cost(model, probabilities)
            total_cost += cost
            max_regret = max(max_regret, cost - oracle_cost)
        rows.append(
            {
                "n": n,
                "windows": len(windows),
                "drift_threshold": threshold,
                "rebuilds_including_initial": rebuilds,
                "mean_window_cost": total_cost / len(windows),
                "mean_oracle_cost": sum(oracle_costs) / len(oracle_costs),
                "mean_regret": (
                    total_cost - sum(oracle_costs)
                ) / len(windows),
                "max_window_regret": max_regret,
            }
        )

    RESULTS.mkdir(exist_ok=True)
    csv_path = RESULTS / "online_adaptation.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# Online Rebuild Threshold Simulation",
        "",
        "A deterministic 12-window stream moves from a hot head to a hot tail and "
        "then to Zipf access. The always-refit tuned portfolio is the per-window "
        "oracle. This measures rebuild/regret trade-offs, not in-place mutation.",
        "",
        "| TV threshold | Rebuilds | Mean cost | Mean oracle | Mean regret | Max regret |",
        "|---:|---:|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {row['drift_threshold']:.2f} | {row['rebuilds_including_initial']} | "
        f"{row['mean_window_cost']:.6f} | {row['mean_oracle_cost']:.6f} | "
        f"{row['mean_regret']:.6f} | {row['max_window_regret']:.6f} |"
        for row in rows
    ]
    (RESULTS / "online_adaptation.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} online-adaptation rows")


if __name__ == "__main__":
    main()
