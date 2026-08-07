from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from certigap import (
    CppCertiGap,
    baseline_balanced,
    baseline_weighted_median,
    evaluate_tree,
    verify_pruned_beam_certificate,
)
from certigap.benchmark_datasets import load_movielens_100k_temporal_trace


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def percentile(values: list[int], fraction: float) -> int:
    ordered = sorted(values)
    return ordered[max(0, (len(ordered) * fraction + 0.9999999999999999).__ceil__() - 1)]


def event_metrics(per_key_costs: list[int], events: list[tuple[int, int]]) -> dict:
    costs = [per_key_costs[movie - 1] for _, movie in events]
    return {
        "mean_event_cost": sum(costs) / len(costs),
        "p95_event_cost": percentile(costs, 0.95),
        "max_event_cost": max(costs),
    }


def serialized_split_count(tree: dict) -> int:
    if tree.get("type") == "leaf":
        return 0
    if tree.get("type") != "split":
        raise ValueError("C++ certificate returned an invalid tree")
    return 1 + serialized_split_count(tree["left"]) + serialized_split_count(
        tree["right"]
    )


def main() -> None:
    events, provenance = load_movielens_100k_temporal_trace()
    split = int(len(events) * 0.8)
    train_events = events[:split]
    test_events = events[split:]
    n = max(movie for _, movie in events)
    train_counts = Counter(movie for _, movie in train_events)
    train_weights = [float(train_counts[key]) for key in range(1, n + 1)]
    budget = 6
    eta = 0.15

    cpp = CppCertiGap()
    pruned = cpp.pruned_beam(
        train_weights,
        budget=budget,
        eta=eta,
        beam_width=32,
        candidate_limit=16,
    )
    pruned_verification = verify_pruned_beam_certificate(train_weights, pruned)
    candidates = [
        (
            "certigap_pruned",
            pruned["tree"],
            pruned["per_key_costs"],
            serialized_split_count(pruned["tree"]),
        )
    ]
    for name, result in (
        ("balanced_budgeted", baseline_balanced(train_weights, budget, eta)),
        ("weighted_budgeted", baseline_weighted_median(train_weights, budget, eta)),
    ):
        evaluation = evaluate_tree(result["tree"], train_weights, eta)
        candidates.append(
            (name, evaluation["serialized_tree"], evaluation["per_key_costs"], evaluation["split_count"])
        )

    rows: list[dict] = []
    for name, tree, per_key_costs, splits in candidates:
        rows.append(
            {
                "dataset": "movielens_100k",
                "trace_source": "timestamped_rating_events",
                "n": n,
                "train_events": len(train_events),
                "test_events": len(test_events),
                "budget": budget,
                "eta": eta,
                "solver": name,
                "split_count": splits,
                **event_metrics(per_key_costs, test_events),
            }
        )

    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "real_temporal_access.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    artifact = {
        "dataset_provenance": provenance,
        "protocol": {
            "train_prefix_fraction": 0.8,
            "selection": "train timestamp prefix only",
            "evaluation": "untouched later timestamp suffix",
            "operation_model": "static ordered movie-id lookup per observed rating event",
            "not_claimed": "database latency, range/update trace, or production storage-engine workload",
        },
        "certigap_pruned": {
            "weights": train_weights,
            **pruned,
            "verification": pruned_verification,
        },
        "rows": rows,
    }
    (RESULTS / "real_temporal_access.json").write_text(
        json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# Real Temporal Access Trace: MovieLens 100K",
        "",
        "The first 80% of the original timestamped rating events forms the training profile. The final 20% is an untouched chronological test trace. Each event is treated only as a static lookup of its numeric movie identifier; no synthetic query sequence is generated.",
        "",
        "| Solver | Splits | Later-trace mean comparisons | Later-trace p95 | Later-trace max |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['solver']} | {row['split_count']} | {row['mean_event_cost']:.6f} | "
            f"{row['p95_event_cost']} | {row['max_event_cost']} |"
        )
    lines.extend(
        [
            "",
            "The comparison is modeled comparison count, not nanoseconds. Movie ID order is not semantic similarity, and this trace does not establish dynamic-range or database-engine performance.",
        ]
    )
    (RESULTS / "real_temporal_access.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(rows)} real temporal-access rows")


if __name__ == "__main__":
    main()
