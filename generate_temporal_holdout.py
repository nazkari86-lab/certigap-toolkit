from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

from certigap import beam_search_best, evaluate_tree, normalize_weights
from certigap.benchmark_datasets import CACHE_DIR, SOURCES, load_real_workload


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def aggregate(counts: Counter[int], n: int) -> list[float]:
    values = [counts[key] for key in range(1, max(counts) + 1)]
    bins = [0.0] * n
    for index, value in enumerate(values):
        bins[(index * n) // len(values)] += value
    return normalize_weights(bins)


def main() -> None:
    load_real_workload("movielens_100k")
    events = []
    for line in (CACHE_DIR / SOURCES["movielens_100k"]["filename"]).read_text(encoding="latin-1").splitlines():
        _, movie, _, timestamp = line.split("\t")
        events.append((int(timestamp), int(movie)))
    events.sort()
    pivot = int(len(events) * 0.8)
    train, test = Counter(movie for _, movie in events[:pivot]), Counter(movie for _, movie in events[pivot:])
    rows = []
    for n in (32, 64, 128):
        train_weights, test_weights = aggregate(train, n), aggregate(test, n)
        for eta in (0.0, 0.15, 0.30):
            model = beam_search_best(train_weights, budget=6, eta=eta, beam_width=16)
            test_evaluation = evaluate_tree(model["tree"], test_weights, eta=0.0)
            rows.append({"dataset": "movielens_100k", "n": n, "train_events": pivot, "test_events": len(events) - pivot, "eta": eta, "train_objective": model["objective"], "future_average_cost": test_evaluation["average_cost"], "future_max_cost": test_evaluation["max_cost"]})
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "temporal_holdout.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)
    lines = ["# Temporal Holdout: MovieLens 100K", "", "Trees are fitted on the earliest 80% of timestamped ratings and evaluated on the final 20%. Movie identifier order is preserved; this is a distribution-shift experiment, not a causal production study.", "", "| n | eta | Train objective | Future average cost | Future max cost |", "|---:|---:|---:|---:|---:|"]
    lines += [f"| {r['n']} | {r['eta']:.2f} | {r['train_objective']:.6f} | {r['future_average_cost']:.6f} | {r['future_max_cost']} |" for r in rows]
    (RESULTS / "temporal_holdout.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} temporal-holdout rows")


if __name__ == "__main__":
    main()
