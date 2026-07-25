from __future__ import annotations

import argparse
import csv
from pathlib import Path

from certigap import counterexample_search


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "counterexamples.csv"
MD_PATH = RESULTS_DIR / "counterexamples.md"


FAST_PRESET = {
    "n_values": (8, 10, 12, 16),
    "budgets": (2, 3, 4),
    "etas": (0.0, 0.15, 0.30),
    "widths": (2, 3, 4),
    "hot_weights": (8.0, 16.0, 24.0),
}

DEEP_PRESET = {
    "n_values": (8, 10, 12, 16, 20, 24),
    "budgets": (2, 3, 4),
    "etas": (0.0, 0.15, 0.30),
    "widths": (2, 3, 4, 5, 6),
    "hot_weights": (4.0, 8.0, 12.0, 16.0, 24.0),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate greedy counterexamples for CertiGap.")
    parser.add_argument(
        "--mode",
        choices=("fast", "deep"),
        default="fast",
        help="fast is the default reproducible sweep; deep explores a larger family.",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=20,
        help="number of top findings to save",
    )
    return parser.parse_args()


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    args = parse_args()
    preset = FAST_PRESET if args.mode == "fast" else DEEP_PRESET
    findings = counterexample_search(**preset)
    top = findings[: args.top]

    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "n",
                "budget",
                "eta",
                "start",
                "width",
                "hot_weight",
                "greedy_gap",
                "beam_gap",
                "exact_objective",
                "greedy_objective",
                "beam_objective",
            ],
        )
        writer.writeheader()
        for row in top:
            writer.writerow({key: row[key] for key in writer.fieldnames})

    lines = [
        "# Greedy Counterexamples",
        "",
        "Top automatically discovered hot-block instances where one-step greedy is much worse than exact.",
        "",
        "| n | B | eta | hot start | hot width | hot weight | greedy gap | beam gap |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in top:
        lines.append(
            f"| {row['n']} | {row['budget']} | {row['eta']:.2f} | {row['start']} | {row['width']} | "
            f"{row['hot_weight']:.1f} | {row['greedy_gap']:.4f} | {row['beam_gap']:.4f} |"
        )

    if top:
        best = top[0]
        lines.extend(
            [
                "",
                "## Best Found Instance",
                "",
                f"- `n = {best['n']}`, `B = {best['budget']}`, `eta = {best['eta']:.2f}`",
                f"- hot block: start `{best['start']}`, width `{best['width']}`, hot weight `{best['hot_weight']:.1f}`",
                f"- greedy gap: `{best['greedy_gap']:.6f}`",
                f"- beam gap: `{best['beam_gap']:.6f}`",
                f"- exact tree: `{best['exact_tree']}`",
                f"- greedy tree: `{best['greedy_tree']}`",
                f"- beam tree: `{best['beam_tree']}`",
            ]
        )

    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {MD_PATH}")
    print(f"Mode: {args.mode}, findings scanned: {len(findings)}, saved: {len(top)}")


if __name__ == "__main__":
    main()
