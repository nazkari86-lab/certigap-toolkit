from __future__ import annotations

import csv
from pathlib import Path

from certigap import CppCertiGap, frontier_dp_best, make_distribution


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def main() -> None:
    core = CppCertiGap()
    rows: list[dict] = []
    for distribution in ("uniform", "zipf", "hot_middle", "hot_tail"):
        for n in (12, 16, 20):
            weights = make_distribution(distribution, n)
            for budget in (2, 3, 4):
                for eta in (0.0, 0.15, 0.30):
                    exact = frontier_dp_best(weights, budget, eta)
                    for limit in (4, 8, 16, 32):
                        pruned = core.pruned_beam(weights, budget, eta, beam_width=16, candidate_limit=limit)
                        rows.append({"distribution": distribution, "n": n, "budget": budget, "eta": eta, "candidate_limit": limit, "exact_objective": exact["objective"], "pruned_objective": pruned["objective"], "absolute_gap": pruned["objective"] - exact["objective"], "relative_gap": 0.0 if exact["objective"] == 0 else (pruned["objective"] - exact["objective"]) / exact["objective"]})
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "pruning_validation.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    lines = ["# C++ Pruning Quality Validation", "", "Exact frontier DP is the oracle. This validates empirical quality only; it is not an approximation proof.", "", "| Candidate limit | Mean absolute gap | Max absolute gap | Mean relative gap |", "|---:|---:|---:|---:|"]
    for limit in (4, 8, 16, 32):
        subset = [row for row in rows if row["candidate_limit"] == limit]
        lines.append(f"| {limit} | {sum(r['absolute_gap'] for r in subset) / len(subset):.6f} | {max(r['absolute_gap'] for r in subset):.6f} | {sum(r['relative_gap'] for r in subset) / len(subset):.2%} |")
    (RESULTS / "pruning_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} pruning-validation rows")


if __name__ == "__main__":
    main()
