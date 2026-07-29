from __future__ import annotations

import csv
import random
from pathlib import Path
from time import perf_counter

from certigap import fit_autodro


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "direct_tv_validation.csv"
REPORT_PATH = RESULTS / "direct_tv_validation.md"


def main() -> None:
    rows: list[dict] = []
    for n in range(4, 9):
        for budget in range(1, min(3, n - 1) + 1):
            for radius in (0.05, 0.2, 0.4):
                for seed in range(4):
                    rng = random.Random((n, budget, radius, seed).__repr__())
                    counts = [1 + int(10_000 * rng.expovariate(1.0)) for _ in range(n)]
                    started = perf_counter()
                    exact = fit_autodro(
                        counts,
                        budget,
                        tv_radius=radius,
                        exact_limit=8,
                        direct_tv_limit=n,
                    )
                    exact_seconds = perf_counter() - started
                    started = perf_counter()
                    heuristic = fit_autodro(
                        counts,
                        budget,
                        tv_radius=radius,
                        exact_limit=8,
                        direct_tv_limit=0,
                    )
                    heuristic_seconds = perf_counter() - started
                    exact_score = float(exact.selected["robust_score"])
                    heuristic_score = float(heuristic.selected["robust_score"])
                    if exact_score > heuristic_score + 1e-9:
                        raise AssertionError("complete direct-TV search lost to its heuristic subset")
                    direct_space = exact.portfolio_manifest["direct_tree_space"]
                    rows.append(
                        {
                            "case_family": "random_exponential",
                            "n": n,
                            "budget": budget,
                            "tv_radius": radius,
                            "seed": seed,
                            "tree_count": direct_space["tree_count"],
                            "tree_space_sha256": direct_space["tree_space_sha256"],
                            "direct_score": exact_score,
                            "heuristic_score": heuristic_score,
                            "heuristic_gap": heuristic_score - exact_score,
                            "direct_seconds": exact_seconds,
                            "heuristic_seconds": heuristic_seconds,
                            "selected_solver": exact.selected["solver"],
                            "selected_fallback": exact.selected["fallback"],
                            "scope": exact.portfolio_manifest["selection_scope"],
                        }
                    )

    witness_counts = [1134, 165, 7077, 2112, 1313, 1368, 8649]
    started = perf_counter()
    witness_exact = fit_autodro(
        witness_counts,
        2,
        tv_radius=0.1,
        exact_limit=8,
        direct_tv_limit=7,
    )
    witness_exact_seconds = perf_counter() - started
    started = perf_counter()
    witness_heuristic = fit_autodro(
        witness_counts,
        2,
        tv_radius=0.1,
        exact_limit=8,
        direct_tv_limit=0,
    )
    witness_heuristic_seconds = perf_counter() - started
    witness_space = witness_exact.portfolio_manifest["direct_tree_space"]
    rows.append(
        {
            "case_family": "fixed_tv_separation_witness",
            "n": 7,
            "budget": 2,
            "tv_radius": 0.1,
            "seed": "witness-001",
            "tree_count": witness_space["tree_count"],
            "tree_space_sha256": witness_space["tree_space_sha256"],
            "direct_score": witness_exact.selected["robust_score"],
            "heuristic_score": witness_heuristic.selected["robust_score"],
            "heuristic_gap": (
                witness_heuristic.selected["robust_score"]
                - witness_exact.selected["robust_score"]
            ),
            "direct_seconds": witness_exact_seconds,
            "heuristic_seconds": witness_heuristic_seconds,
            "selected_solver": witness_exact.selected["solver"],
            "selected_fallback": witness_exact.selected["fallback"],
            "scope": witness_exact.portfolio_manifest["selection_scope"],
        }
    )

    RESULTS.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    positive = [row for row in rows if row["heuristic_gap"] > 1e-9]
    lines = [
        "# Direct TV-DRO Exact-Space Validation",
        "",
        "Every row exhaustively enumerates all ordered partial trees up to the split "
        "budget and both built-in fallbacks. The heuristic portfolio is a subset, "
        "so a negative gap is a test failure.",
        "",
        f"- Cases: `{len(rows)}`",
        f"- Exact improvements over the heuristic portfolio: `{len(positive)}`",
        f"- Maximum heuristic minus exact robust score: "
        f"`{max(row['heuristic_gap'] for row in rows):.9f}`",
        f"- Largest enumerated tree space: `{max(row['tree_count'] for row in rows)}`",
        "- The fixed separation witness is retained as a regression case showing "
        "that direct TV optimization can beat every candidate generated from the "
        "Huber frontier and heuristic portfolio.",
        "",
        "| n | B | rho | Cases | Exact improvements | Mean gap | Max gap |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    groups = sorted({(row["n"], row["budget"], row["tv_radius"]) for row in rows})
    for n, budget, radius in groups:
        group = [
            row
            for row in rows
            if (row["n"], row["budget"], row["tv_radius"]) == (n, budget, radius)
        ]
        lines.append(
            f"| {n} | {budget} | {radius:.2f} | {len(group)} | "
            f"{sum(row['heuristic_gap'] > 1e-9 for row in group)} | "
            f"{sum(row['heuristic_gap'] for row in group) / len(group):.9f} | "
            f"{max(row['heuristic_gap'] for row in group):.9f} |"
        )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {CSV_PATH} ({len(rows)} rows)")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
