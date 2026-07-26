from __future__ import annotations

import csv
import json
from pathlib import Path

from certigap import (
    ExecutionCostModel,
    baseline_balanced,
    beam_search_best,
    fit_autodro,
    make_distribution,
    normalize_weights,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "autodro_shift.csv"
REPORT_PATH = RESULTS / "autodro_shift.md"
ARTIFACT_PATH = RESULTS / "autodro_selection_example.json"


def hot_head(n: int) -> list[float]:
    return normalize_weights([30.0 if index < max(1, n // 10) else 1.0 for index in range(n)])


def mixture(left: list[float], right: list[float], fraction: float) -> list[float]:
    return normalize_weights([
        (1.0 - fraction) * left_value + fraction * right_value
        for left_value, right_value in zip(left, right)
    ])


def integer_counts(probabilities: list[float], total: int = 20_000) -> list[int]:
    counts = [int(round(value * total)) for value in probabilities]
    counts[max(range(len(counts)), key=counts.__getitem__)] += total - sum(counts)
    return counts


def summarize_candidate(
    scenario: str,
    n: int,
    method: str,
    solver: str,
    fallback: str,
    budget: int,
    split_count: int,
    memory_bytes: int,
    robust_score: float | None,
    per_key_costs: list[float],
    test_distribution: list[float],
) -> dict:
    return {
        "scenario": scenario,
        "n": n,
        "method": method,
        "solver": solver,
        "fallback": fallback,
        "budget": budget,
        "split_count": split_count,
        "memory_bytes": memory_bytes,
        "selection_robust_score": "" if robust_score is None else robust_score,
        "test_mean_cost": sum(
            probability * cost
            for probability, cost in zip(test_distribution, per_key_costs)
        ),
        "test_max_cost": max(per_key_costs),
    }


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    cost_model = ExecutionCostModel()
    rows: list[dict] = []
    example_artifact: dict | None = None
    for n in (32, 64):
        uniform = make_distribution("uniform", n)
        zipf = make_distribution("zipf", n)
        head = hot_head(n)
        tail = make_distribution("hot_tail", n)
        scenarios = {
            "stationary_zipf": (zipf, zipf),
            "hot_reversal": (head, tail),
            "partial_hot_drift": (head, mixture(head, tail, 0.35)),
            "uniform_to_zipf": (uniform, zipf),
        }
        for scenario, (train, test) in scenarios.items():
            budget = 4
            auto = fit_autodro(
                integer_counts(train),
                max_budget=budget,
                tv_radius=0.2,
                training_etas=(0.0, 0.15, 0.2),
                exact_limit=8,
                cost_model=cost_model,
            )
            selected = auto.selected
            if scenario == "stationary_zipf" and n == 32:
                example_artifact = auto.export_selection_artifact()
            rows.append(
                summarize_candidate(
                    scenario,
                    n,
                    "autodro",
                    selected["solver"],
                    selected["fallback"],
                    selected["budget"],
                    selected["split_count"],
                    selected["memory_bytes"],
                    selected["robust_score"],
                    selected["per_key_execution_costs"],
                    test,
                )
            )
            for method, result in (
                ("fixed_beam", beam_search_best(train, budget, 0.15)),
                ("fixed_balanced", baseline_balanced(train, budget, 0.15)),
            ):
                splits = result["split_count"]
                rows.append(
                    summarize_candidate(
                        scenario,
                        n,
                        method,
                        method.removeprefix("fixed_"),
                        "fixed_rounds",
                        budget,
                        splits,
                        cost_model.key_bytes * n + cost_model.node_bytes * (2 * splits + 1),
                        None,
                        result["per_key_costs"],
                        test,
                    )
                )

    fieldnames = list(rows[0])
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    groups = {(row["scenario"], row["n"]) for row in rows}
    beam_wins = balanced_wins = 0
    lines = [
        "# CertiGap-AutoDRO Distribution-Shift Benchmark",
        "",
        "Selection uses only the training counts and a fixed TV radius of `0.2`. "
        "The test distribution is used only after selection.",
        "",
        "| Scenario | n | Method | Selected solver | Fallback | Splits | Bytes | Test mean | Test max |",
        "|---|---:|---|---|---|---:|---:|---:|---:|",
    ]
    for scenario, n in sorted(groups):
        group = [row for row in rows if row["scenario"] == scenario and row["n"] == n]
        by_method = {row["method"]: row for row in group}
        if by_method["autodro"]["test_mean_cost"] < by_method["fixed_beam"]["test_mean_cost"]:
            beam_wins += 1
        if by_method["autodro"]["test_mean_cost"] < by_method["fixed_balanced"]["test_mean_cost"]:
            balanced_wins += 1
        for row in group:
            lines.append(
                f"| {scenario} | {n} | {row['method']} | {row['solver']} | "
                f"{row['fallback']} | {row['split_count']} | {row['memory_bytes']} | "
                f"{row['test_mean_cost']:.5f} | {row['test_max_cost']:.5f} |"
            )
    lines.extend(
        [
            "",
            "## Aggregate",
            "",
            f"- AutoDRO beats fixed beam on shifted/stationary test mean in `{beam_wins}/{len(groups)}` cases.",
            f"- AutoDRO beats fixed balanced on shifted/stationary test mean in `{balanced_wins}/{len(groups)}` cases.",
            "",
            "## Scope",
            "",
            "This is a deterministic comparison-cost experiment, not a hardware-latency claim. "
            "It tests selection under distribution shift; an external trace replay remains required.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if example_artifact is None:
        raise RuntimeError("selection artifact example was not generated")
    ARTIFACT_PATH.write_text(
        json.dumps(example_artifact, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {CSV_PATH} ({len(rows)} rows)")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {ARTIFACT_PATH}")


if __name__ == "__main__":
    main()
