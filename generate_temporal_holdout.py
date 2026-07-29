from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from certigap import evaluate_tree_with_fallback, fit_autodro, normalize_weights
from certigap.benchmark_datasets import CACHE_DIR, SOURCES, load_real_workload


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def aggregate_counts(counts: Counter[int], n: int) -> list[int]:
    values = [counts[key] for key in range(1, max(counts) + 1)]
    bins = [0] * n
    for index, value in enumerate(values):
        bins[(index * n) // len(values)] += value
    return bins


def main() -> None:
    load_real_workload("movielens_100k")
    events = []
    source = CACHE_DIR / SOURCES["movielens_100k"]["filename"]
    for line in source.read_text(encoding="latin-1").splitlines():
        _, movie, _, timestamp = line.split("\t")
        events.append((int(timestamp), int(movie)))
    events.sort()
    pivot = int(len(events) * 0.8)
    train = Counter(movie for _, movie in events[:pivot])
    test = Counter(movie for _, movie in events[pivot:])
    rows = []
    for n in (32, 64, 128):
        train_counts = aggregate_counts(train, n)
        test_weights = normalize_weights(aggregate_counts(test, n))
        for method, radius in (
            ("tuned_nominal", 0.0),
            ("tuned_tv_010", 0.1),
            ("tuned_tv_020", 0.2),
        ):
            model = fit_autodro(
                train_counts,
                max_budget=6,
                tv_radius=radius,
                training_etas=(0.0, 0.1, 0.2),
                exact_limit=8,
                direct_tv_limit=0,
            )
            selected = model.selected
            future = evaluate_tree_with_fallback(
                selected["tree"],
                test_weights,
                0.0,
                selected["fallback"],
            )
            rows.append(
                {
                    "dataset": "movielens_100k",
                    "n": n,
                    "train_events": pivot,
                    "test_events": len(events) - pivot,
                    "method": method,
                    "tv_radius": radius,
                    "solver": selected["solver"],
                    "fallback": selected["fallback"],
                    "split_count": selected["split_count"],
                    "selection_robust_score": selected["robust_score"],
                    "future_average_cost": future["average_cost"],
                    "future_max_cost": future["max_cost"],
                }
            )

    RESULTS.mkdir(exist_ok=True)
    csv_path = RESULTS / "temporal_holdout.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# Temporal Holdout: MovieLens 100K",
        "",
        "Identical tuned portfolios are fitted on the earliest 80% of timestamped "
        "ratings and evaluated on the final 20%. Only the TV selection radius "
        "changes. Movie identifier order is preserved; this is a public temporal "
        "shift test, not a production latency study.",
        "",
        "| n | Method | rho | Solver | Fallback | Splits | Future average | Future max |",
        "|---:|---|---:|---|---|---:|---:|---:|",
    ]
    lines += [
        f"| {row['n']} | {row['method']} | {row['tv_radius']:.2f} | "
        f"{row['solver']} | {row['fallback']} | {row['split_count']} | "
        f"{row['future_average_cost']:.6f} | {row['future_max_cost']} |"
        for row in rows
    ]
    (RESULTS / "temporal_holdout.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} temporal-holdout rows")


if __name__ == "__main__":
    main()
