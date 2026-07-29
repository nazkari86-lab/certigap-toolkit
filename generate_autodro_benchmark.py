from __future__ import annotations

import csv
import json
from pathlib import Path
from time import perf_counter

from certigap import (
    ExecutionCostModel,
    baseline_balanced,
    baseline_weighted_median,
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
    selection_score: float | None,
    selection_seconds: float,
    candidate_count: int,
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
        "selection_score": "" if selection_score is None else selection_score,
        "selection_seconds": selection_seconds,
        "candidate_count": candidate_count,
        "test_mean_cost": sum(
            probability * cost
            for probability, cost in zip(test_distribution, per_key_costs)
        ),
        "test_max_cost": max(per_key_costs),
    }


def fit_portfolio(
    counts: list[int],
    budget: int,
    radius: float,
    cost_model: ExecutionCostModel,
):
    started = perf_counter()
    result = fit_autodro(
        counts,
        max_budget=budget,
        tv_radius=radius,
        training_etas=(0.0, 0.15, 0.2),
        exact_limit=8,
        direct_tv_limit=8,
        cost_model=cost_model,
    )
    return result, perf_counter() - started


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    cost_model = ExecutionCostModel()
    rows: list[dict] = []
    example_artifact: dict | None = None
    for n in (32, 64, 128):
        uniform = make_distribution("uniform", n)
        zipf = make_distribution("zipf", n)
        head = hot_head(n)
        tail = make_distribution("hot_tail", n)
        scenarios = {
            "stationary_zipf": (zipf, zipf),
            "stationary_hot_head": (head, head),
            "hot_reversal": (head, tail),
            "partial_hot_drift_15": (head, mixture(head, tail, 0.15)),
            "partial_hot_drift_35": (head, mixture(head, tail, 0.35)),
            "partial_hot_drift_65": (head, mixture(head, tail, 0.65)),
            "uniform_to_zipf": (uniform, zipf),
            "zipf_to_uniform": (zipf, uniform),
        }
        for scenario, (train, test) in scenarios.items():
            budget = 4
            counts = integer_counts(train)
            robust, robust_seconds = fit_portfolio(counts, budget, 0.2, cost_model)
            nominal, nominal_seconds = fit_portfolio(counts, budget, 0.0, cost_model)
            if scenario == "stationary_zipf" and n == 32:
                example_artifact = robust.export_selection_artifact()

            for method, fit, seconds in (
                ("tuned_tv_dro", robust, robust_seconds),
                ("tuned_nominal", nominal, nominal_seconds),
            ):
                selected = fit.selected
                rows.append(
                    summarize_candidate(
                        scenario,
                        n,
                        method,
                        selected["solver"],
                        selected["fallback"],
                        selected["budget"],
                        selected["split_count"],
                        selected["memory_bytes"],
                        selected["robust_score"],
                        seconds,
                        len(fit.leaderboard),
                        selected["per_key_execution_costs"],
                        test,
                    )
                )

            for method, result in (
                ("fixed_beam", beam_search_best(train, budget, 0.15)),
                ("fixed_balanced", baseline_balanced(train, budget, 0.15)),
                ("fixed_weighted", baseline_weighted_median(train, budget, 0.15)),
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
                        0.0,
                        1,
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
    opponents = ("tuned_nominal", "fixed_beam", "fixed_balanced", "fixed_weighted")
    wins = {name: 0 for name in opponents}
    losses = {name: 0 for name in opponents}
    lines = [
        "# CertiGap-AutoDRO Fair Distribution-Shift Benchmark",
        "",
        "`tuned_tv_dro` and `tuned_nominal` search the identical budgets, eta grid, "
        "solver set, and fallback set. Their only selection difference is TV radius "
        "`0.2` versus `0.0`; this is the primary DRO ablation.",
        "",
        "| Scenario | n | Method | Solver | Fallback | Splits | Bytes | Candidates | Select s | Test mean | Test max |",
        "|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for scenario, n in sorted(groups):
        group = [row for row in rows if row["scenario"] == scenario and row["n"] == n]
        by_method = {row["method"]: row for row in group}
        dro_cost = float(by_method["tuned_tv_dro"]["test_mean_cost"])
        for opponent in opponents:
            other = float(by_method[opponent]["test_mean_cost"])
            wins[opponent] += dro_cost < other - 1e-12
            losses[opponent] += dro_cost > other + 1e-12
        for row in group:
            lines.append(
                f"| {scenario} | {n} | {row['method']} | {row['solver']} | "
                f"{row['fallback']} | {row['split_count']} | {row['memory_bytes']} | "
                f"{row['candidate_count']} | {float(row['selection_seconds']):.4f} | "
                f"{float(row['test_mean_cost']):.5f} | {float(row['test_max_cost']):.5f} |"
            )
    lines.extend(["", "## Paired Outcomes", ""])
    for opponent in opponents:
        ties = len(groups) - wins[opponent] - losses[opponent]
        lines.append(
            f"- tuned TV-DRO vs `{opponent}`: `{wins[opponent]}` wins, "
            f"`{losses[opponent]}` losses, `{ties}` ties across `{len(groups)}` pairs."
        )
    lines.extend(
        [
            "",
            "## Scope",
            "",
            "Expected comparison cost is deterministic for each supplied test distribution, "
            "so sampling confidence intervals are not applicable to this table. Construction "
            "timings are local-machine measurements. External implementations, real request "
            "latency, and prospective traces remain separate experiments.",
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
