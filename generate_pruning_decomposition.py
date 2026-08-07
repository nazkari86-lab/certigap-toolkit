from __future__ import annotations

import csv
from pathlib import Path

from certigap import (
    CppCertiGap,
    candidate_restricted_frontier_dp_best,
    frontier_dp_best,
    make_distribution,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def mean(rows: list[dict], field: str) -> float:
    return sum(float(row[field]) for row in rows) / len(rows)


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
                        restricted = candidate_restricted_frontier_dp_best(
                            weights, budget, eta, candidate_limit=limit
                        )
                        beam = core.pruned_beam(
                            weights, budget, eta, beam_width=16,
                            candidate_limit=limit,
                        )
                        pruning_gap = restricted["objective"] - exact["objective"]
                        truncation_gap = beam["objective"] - restricted["objective"]
                        total_gap = beam["objective"] - exact["objective"]
                        rows.append(
                            {
                                "distribution": distribution,
                                "n": n,
                                "budget": budget,
                                "eta": eta,
                                "candidate_limit": limit,
                                "exact_objective": exact["objective"],
                                "restricted_objective": restricted["objective"],
                                "beam_objective": beam["objective"],
                                "candidate_pruning_gap": pruning_gap,
                                "beam_truncation_gap": truncation_gap,
                                "total_gap": total_gap,
                                "decomposition_residual": total_gap - pruning_gap - truncation_gap,
                            }
                        )
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "pruning_decomposition.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# C++ Pruning Gap Decomposition",
        "",
        "The unrestricted frontier DP is the exact oracle. The candidate-restricted frontier DP is exact only over the deterministic C++ mass-quantile threshold grammar. Therefore `total gap = candidate-pruning gap + beam-truncation gap` on every row. This is an empirical decomposition, not an approximation guarantee for the C++ beam.",
        "",
        "| Candidate limit | Mean candidate-pruning gap | Mean beam-truncation gap | Mean total gap | Max absolute residual |",
        "|---:|---:|---:|---:|---:|",
    ]
    for limit in (4, 8, 16, 32):
        subset = [row for row in rows if row["candidate_limit"] == limit]
        lines.append(
            "| {limit} | {pruning:.6f} | {truncation:.6f} | {total:.6f} | {residual:.2e} |".format(
                limit=limit,
                pruning=mean(subset, "candidate_pruning_gap"),
                truncation=mean(subset, "beam_truncation_gap"),
                total=mean(subset, "total_gap"),
                residual=max(abs(float(row["decomposition_residual"])) for row in subset),
            )
        )
    (RESULTS / "pruning_decomposition.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(rows)} pruning-decomposition rows")


if __name__ == "__main__":
    main()
