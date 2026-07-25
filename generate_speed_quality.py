from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from certigap import (
    baseline_balanced,
    baseline_weighted_median,
    beam_search_best,
    frontier_dp_best,
    greedy_best,
    make_distribution,
)


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "speed_quality.csv"
SUMMARY_MD_PATH = RESULTS_DIR / "speed_quality_summary.md"


FAST_PRESET = {
    "small_sizes": [8, 12, 16, 20],
    "large_sizes": [32, 48, 64],
    "budgets_small": [2, 3, 4],
    "budgets_large": [3, 4, 6],
    "etas": [0.0, 0.15, 0.30],
}

DEEP_PRESET = {
    "small_sizes": [8, 12, 16, 20, 24],
    "large_sizes": [32, 48, 64, 96, 128],
    "budgets_small": [2, 3, 4],
    "budgets_large": [3, 4, 6, 8],
    "etas": [0.0, 0.15, 0.30],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate CertiGap speed/quality benchmark artifacts.")
    parser.add_argument(
        "--mode",
        choices=("fast", "deep"),
        default="fast",
        help="fast is the default report-friendly benchmark; deep covers larger task families.",
    )
    return parser.parse_args()


def timed_call(fn, *args, repeats: int = 3, **kwargs):
    best_result = None
    best_seconds = None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = time.perf_counter() - start
        if best_seconds is None or elapsed < best_seconds:
            best_seconds = elapsed
            best_result = result
    assert best_result is not None
    return best_result, best_seconds


def write_csv(mode: str) -> list[dict]:
    distributions = ["uniform", "zipf", "hot_middle", "hot_tail"]
    cases = []

    preset = FAST_PRESET if mode == "fast" else DEEP_PRESET
    small_sizes = preset["small_sizes"]
    large_sizes = preset["large_sizes"]
    budgets_small = preset["budgets_small"]
    budgets_large = preset["budgets_large"]
    etas = preset["etas"]

    fieldnames = [
        "distribution",
        "n",
        "budget",
        "eta",
        "solver",
        "objective",
        "average_cost",
        "max_cost",
        "time_ms",
        "absolute_objective_gap_vs_exact",
        "relative_objective_gap_vs_exact",
    ]

    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()

        for distribution in distributions:
            for n in small_sizes:
                for budget in budgets_small:
                    if budget >= n:
                        continue
                    for eta in etas:
                        weights = make_distribution(distribution, n)
                        exact, exact_seconds = timed_call(frontier_dp_best, weights, budget, eta, repeats=3)
                        exact_row = {
                            "distribution": distribution,
                            "n": n,
                            "budget": budget,
                            "eta": eta,
                            "solver": "exact",
                            "objective": exact["objective"],
                            "average_cost": exact["average_cost"],
                            "max_cost": exact["max_cost"],
                            "time_ms": exact_seconds * 1000.0,
                            "absolute_objective_gap_vs_exact": 0.0,
                            "relative_objective_gap_vs_exact": 0.0,
                        }
                        cases.append(exact_row)
                        writer.writerow(_format_row(exact_row))

                        for name, fn in [
                            ("beam", beam_search_best),
                            ("greedy", greedy_best),
                            ("balanced", baseline_balanced),
                            ("weighted", baseline_weighted_median),
                        ]:
                            result, seconds = timed_call(fn, weights, budget, eta, repeats=5)
                            row = {
                                "distribution": distribution,
                                "n": n,
                                "budget": budget,
                                "eta": eta,
                                "solver": name,
                                "objective": result["objective"],
                                "average_cost": result["average_cost"],
                                "max_cost": result["max_cost"],
                                "time_ms": seconds * 1000.0,
                                "absolute_objective_gap_vs_exact": result["objective"] - exact["objective"],
                                "relative_objective_gap_vs_exact": 0.0 if exact["objective"] == 0.0 else (result["objective"] - exact["objective"]) / exact["objective"],
                            }
                            cases.append(row)
                            writer.writerow(_format_row(row))

        for distribution in distributions:
            for n in large_sizes:
                for budget in budgets_large:
                    if budget >= n:
                        continue
                    for eta in etas:
                        weights = make_distribution(distribution, n)
                        beam, beam_seconds = timed_call(beam_search_best, weights, budget, eta, repeats=3)
                        greedy, greedy_seconds = timed_call(greedy_best, weights, budget, eta, repeats=5)
                        balanced, balanced_seconds = timed_call(baseline_balanced, weights, budget, eta, repeats=5)
                        weighted, weighted_seconds = timed_call(baseline_weighted_median, weights, budget, eta, repeats=5)
                        for name, result, seconds in [
                            ("beam", beam, beam_seconds),
                            ("greedy", greedy, greedy_seconds),
                            ("balanced", balanced, balanced_seconds),
                            ("weighted", weighted, weighted_seconds),
                        ]:
                            row = {
                                "distribution": distribution,
                                "n": n,
                                "budget": budget,
                                "eta": eta,
                                "solver": name,
                                "objective": result["objective"],
                                "average_cost": result["average_cost"],
                                "max_cost": result["max_cost"],
                                "time_ms": seconds * 1000.0,
                                "absolute_objective_gap_vs_exact": None,
                                "relative_objective_gap_vs_exact": None,
                            }
                            cases.append(row)
                            writer.writerow(_format_row(row))

    return cases


def _format_row(row: dict) -> dict[str, str]:
    return {
        "distribution": str(row["distribution"]),
        "n": str(row["n"]),
        "budget": str(row["budget"]),
        "eta": f"{float(row['eta']):.2f}",
        "solver": str(row["solver"]),
        "objective": f"{float(row['objective']):.6f}",
        "average_cost": f"{float(row['average_cost']):.6f}",
        "max_cost": f"{float(row['max_cost']):.6f}",
        "time_ms": f"{float(row['time_ms']):.6f}",
        "absolute_objective_gap_vs_exact": "" if row["absolute_objective_gap_vs_exact"] is None else f"{float(row['absolute_objective_gap_vs_exact']):.6f}",
        "relative_objective_gap_vs_exact": "" if row["relative_objective_gap_vs_exact"] is None else f"{float(row['relative_objective_gap_vs_exact']):.6f}",
    }


def build_summary(rows: list[dict]) -> str:
    small_rows = [row for row in rows if row["absolute_objective_gap_vs_exact"] is not None]
    large_rows = [row for row in rows if row["absolute_objective_gap_vs_exact"] is None]

    def avg(values):
        return sum(values) / len(values) if values else 0.0

    beam_small = [row for row in small_rows if row["solver"] == "beam"]
    greedy_small = [row for row in small_rows if row["solver"] == "greedy"]
    balanced_small = [row for row in small_rows if row["solver"] == "balanced"]
    weighted_small = [row for row in small_rows if row["solver"] == "weighted"]
    exact_small = [row for row in small_rows if row["solver"] == "exact"]

    beam_large = [row for row in large_rows if row["solver"] == "beam"]
    greedy_large = [row for row in large_rows if row["solver"] == "greedy"]
    balanced_large = [row for row in large_rows if row["solver"] == "balanced"]
    weighted_large = [row for row in large_rows if row["solver"] == "weighted"]

    lines = [
        "# CertiGap Speed and Quality Summary",
        "",
        "## Small Cases With Exact Reference",
        "",
        f"- Exact mean time: `{avg([row['time_ms'] for row in exact_small]):.3f} ms`",
        f"- Beam mean time: `{avg([row['time_ms'] for row in beam_small]):.3f} ms`",
        f"- Greedy mean time: `{avg([row['time_ms'] for row in greedy_small]):.3f} ms`",
        f"- Balanced mean time: `{avg([row['time_ms'] for row in balanced_small]):.3f} ms`",
        f"- Weighted mean time: `{avg([row['time_ms'] for row in weighted_small]):.3f} ms`",
        f"- Beam mean absolute objective gap vs exact: `{avg([row['absolute_objective_gap_vs_exact'] for row in beam_small]):.6f}`",
        f"- Greedy mean absolute objective gap vs exact: `{avg([row['absolute_objective_gap_vs_exact'] for row in greedy_small]):.6f}`",
        f"- Balanced mean absolute objective gap vs exact: `{avg([row['absolute_objective_gap_vs_exact'] for row in balanced_small]):.6f}`",
        f"- Weighted mean absolute objective gap vs exact: `{avg([row['absolute_objective_gap_vs_exact'] for row in weighted_small]):.6f}`",
        f"- Beam mean relative objective gap vs exact: `{avg([row['relative_objective_gap_vs_exact'] for row in beam_small]):.2%}`",
        f"- Greedy mean relative objective gap vs exact: `{avg([row['relative_objective_gap_vs_exact'] for row in greedy_small]):.2%}`",
        "",
        "## Large Cases Without Exact Reference",
        "",
        f"- Beam mean time: `{avg([row['time_ms'] for row in beam_large]):.3f} ms`",
        f"- Greedy mean time: `{avg([row['time_ms'] for row in greedy_large]):.3f} ms`",
        f"- Balanced mean time: `{avg([row['time_ms'] for row in balanced_large]):.3f} ms`",
        f"- Weighted mean time: `{avg([row['time_ms'] for row in weighted_large]):.3f} ms`",
        "",
        "## Solver Tradeoff",
        "",
        "- `exact` is the reference solver for the measured small instances.",
        "- `beam` is near-exact on the measured small cases, but is not faster than exact there; this benchmark does not establish a crossover point.",
        "- `greedy` is usually faster but can be substantially worse on structured skewed tasks.",
        "- `balanced` and `weighted` are cheap baselines, but quality is systematically weaker on skewed workloads.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    args = parse_args()
    rows = write_csv(args.mode)
    SUMMARY_MD_PATH.write_text(build_summary(rows), encoding="utf-8")
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {SUMMARY_MD_PATH}")
    print(f"Mode: {args.mode}, rows written: {len(rows)}")


if __name__ == "__main__":
    main()
