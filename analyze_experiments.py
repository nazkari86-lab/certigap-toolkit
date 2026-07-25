from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "experiment_sweep.csv"
SUMMARY_MD_PATH = RESULTS_DIR / "summary.md"
COUNTEREXAMPLE_MD_PATH = RESULTS_DIR / "counterexamples.md"


def read_rows() -> list[dict[str, str]]:
    with CSV_PATH.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def summarize(rows: list[dict[str, str]]) -> str:
    beam_gaps = [float(row["beam_absolute_objective_gap"]) for row in rows]
    greedy_gaps = [float(row["greedy_absolute_objective_gap"]) for row in rows]
    beam_relative_gaps = [float(row["beam_relative_objective_gap"]) for row in rows]
    greedy_relative_gaps = [float(row["greedy_relative_objective_gap"]) for row in rows]

    by_distribution: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_distribution[row["distribution"]].append(row)

    lines = [
        "# CertiGap Experiment Summary",
        "",
        "## Global Summary",
        "",
        f"- Rows analyzed: `{len(rows)}`",
        f"- Mean greedy absolute objective gap vs exact: `{mean(greedy_gaps):.4f}`",
        f"- Mean beam absolute objective gap vs exact: `{mean(beam_gaps):.4f}`",
        f"- Mean greedy relative objective gap vs exact: `{mean(greedy_relative_gaps):.2%}`",
        f"- Mean beam relative objective gap vs exact: `{mean(beam_relative_gaps):.2%}`",
        f"- Beam strictly improves on greedy in `{sum(1 for g, b in zip(greedy_gaps, beam_gaps) if b < g - 1e-9)}` rows",
        f"- Beam matches exact in `{sum(1 for gap in beam_gaps if abs(gap) <= 1e-9)}` rows",
        "",
        "## By Distribution",
        "",
        "| Distribution | Mean Greedy Absolute Gap | Mean Beam Absolute Gap | Mean Greedy Relative Gap | Mean Beam Relative Gap | Beam Better Rows |",
        "|---|---:|---:|---:|---:|",
    ]

    for distribution in sorted(by_distribution):
        rows_here = by_distribution[distribution]
        greedy_here = [float(row["greedy_absolute_objective_gap"]) for row in rows_here]
        beam_here = [float(row["beam_absolute_objective_gap"]) for row in rows_here]
        greedy_relative_here = [float(row["greedy_relative_objective_gap"]) for row in rows_here]
        beam_relative_here = [float(row["beam_relative_objective_gap"]) for row in rows_here]
        beam_better = sum(1 for g, b in zip(greedy_here, beam_here) if b < g - 1e-9)
        lines.append(
            f"| {distribution} | {mean(greedy_here):.4f} | {mean(beam_here):.4f} | {mean(greedy_relative_here):.2%} | {mean(beam_relative_here):.2%} | {beam_better} |"
        )

    best_rows = sorted(
        rows,
        key=lambda row: float(row["greedy_absolute_objective_gap"]) - float(row["beam_absolute_objective_gap"]),
        reverse=True,
    )[:10]

    lines.extend(
        [
            "",
            "## Top Beam Improvements",
            "",
            "| Distribution | n | B | eta | Greedy Absolute Gap | Beam Absolute Gap |",
            "|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in best_rows:
        lines.append(
            f"| {row['distribution']} | {row['n']} | {row['budget']} | {row['eta']} | "
            f"{float(row['greedy_absolute_objective_gap']):.4f} | {float(row['beam_absolute_objective_gap']):.4f} |"
        )

    if COUNTEREXAMPLE_MD_PATH.exists():
        lines.extend(
            [
                "",
                "## Counterexample Note",
                "",
                "See `counterexamples.md` for automatically discovered hot-block families where one-step greedy is much worse than exact while beam recovers the optimum.",
            ]
        )

    return "\n".join(lines) + "\n"


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    rows = read_rows()
    SUMMARY_MD_PATH.write_text(summarize(rows), encoding="utf-8")
    print(f"Wrote {SUMMARY_MD_PATH}")


if __name__ == "__main__":
    main()
