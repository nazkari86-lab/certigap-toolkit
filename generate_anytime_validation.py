from __future__ import annotations

import csv
import json
import time
from pathlib import Path

from certigap import (
    anytime_tv_branch_and_bound,
    fit_autodro,
    make_distribution,
    verify_anytime_tv_certificate,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def run_anytime(
    weights: list[float],
    budget: int,
    radius: float,
    expansions: int,
) -> tuple[dict, float]:
    started = time.perf_counter()
    result = anytime_tv_branch_and_bound(
        weights,
        budget,
        radius,
        max_expansions=expansions,
    )
    elapsed = time.perf_counter() - started
    verification = verify_anytime_tv_certificate(result["certificate"])
    if not verification["verified"]:
        raise RuntimeError("anytime certificate did not verify")
    return result, elapsed


def main() -> None:
    rows: list[dict] = []
    exact_cases = 0
    for n in (4, 5, 6, 7):
        for distribution in ("uniform", "zipf", "hot_tail"):
            weights = make_distribution(distribution, n)
            budget = min(3, n - 1)
            radius = 0.15
            result, elapsed = run_anytime(
                weights,
                budget,
                radius,
                200_000,
            )
            oracle = fit_autodro(
                weights,
                budget,
                tv_radius=radius,
                pseudocount=0.0,
                solvers=["balanced"],
                fallbacks=["fixed_rounds"],
                direct_tv_limit=n,
            )
            oracle_score = oracle.selected["robust_score"]
            oracle_gap = result["score"] - oracle_score
            if abs(oracle_gap) > 1e-9 or not result["exact"]:
                raise RuntimeError("anytime solver disagrees with direct tree-space oracle")
            exact_cases += 1
            rows.append(
                {
                    "phase": "exact_oracle",
                    "distribution": distribution,
                    "n": n,
                    "budget": budget,
                    "tv_radius": radius,
                    "max_expansions": 200_000,
                    "processed_states": result["search_stats"]["processed_states"],
                    "frontier_states": result["search_stats"]["frontier_states"],
                    "score": result["score"],
                    "global_lower_bound": result["global_lower_bound"],
                    "absolute_gap": result["absolute_gap"],
                    "relative_gap": result["relative_gap"],
                    "exact": result["exact"],
                    "oracle_score": oracle_score,
                    "oracle_gap": oracle_gap,
                    "verified": True,
                    "seconds": elapsed,
                }
            )

    limits = (0, 25, 100, 400)
    trajectories = 0
    example_certificate: dict | None = None
    for n in (16, 32, 64):
        for distribution in ("uniform", "zipf", "hot_tail"):
            weights = make_distribution(distribution, n)
            previous_upper = float("inf")
            previous_lower = float("-inf")
            previous_gap = float("inf")
            for expansions in limits:
                result, elapsed = run_anytime(
                    weights,
                    budget=6,
                    radius=0.1,
                    expansions=expansions,
                )
                if (
                    result["score"] > previous_upper + 1e-9
                    or result["global_lower_bound"] < previous_lower - 1e-9
                    or result["relative_gap"] > previous_gap + 1e-9
                ):
                    raise RuntimeError("anytime certified interval is not monotone")
                previous_upper = result["score"]
                previous_lower = result["global_lower_bound"]
                previous_gap = result["relative_gap"]
                trajectories += 1
                rows.append(
                    {
                        "phase": "scaling_trajectory",
                        "distribution": distribution,
                        "n": n,
                        "budget": 6,
                        "tv_radius": 0.1,
                        "max_expansions": expansions,
                        "processed_states": result["search_stats"]["processed_states"],
                        "frontier_states": result["search_stats"]["frontier_states"],
                        "score": result["score"],
                        "global_lower_bound": result["global_lower_bound"],
                        "absolute_gap": result["absolute_gap"],
                        "relative_gap": result["relative_gap"],
                        "exact": result["exact"],
                        "oracle_score": "",
                        "oracle_gap": "",
                        "verified": True,
                        "seconds": elapsed,
                    }
                )
                if n == 16 and distribution == "zipf" and expansions == 100:
                    example_certificate = result["certificate"]

    RESULTS.mkdir(exist_ok=True)
    fields = list(rows[0])
    with (RESULTS / "anytime_validation.csv").open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    if example_certificate is None:
        raise RuntimeError("example certificate was not generated")
    (RESULTS / "anytime_certificate_example.json").write_text(
        json.dumps(example_certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    scaling = [row for row in rows if row["phase"] == "scaling_trajectory"]
    final_rows = [row for row in scaling if row["max_expansions"] == max(limits)]
    exact_final = sum(bool(row["exact"]) for row in final_rows)
    lines = [
        "# Anytime TV-DRO Validation",
        "",
        "The exact phase compares against independent complete-tree-space enumeration. "
        "The scaling phase reports certified intervals, not unverified solution quality.",
        "",
        f"- Exact oracle matches: `{exact_cases}/{exact_cases}`.",
        f"- Verified scaling trajectory rows: `{trajectories}`.",
        f"- Exact after {max(limits)} expansions: `{exact_final}/{len(final_rows)}`.",
        "",
        "| n | Workload | Expansions | Upper | Lower | Relative gap | Exact | Seconds |",
        "|---:|---|---:|---:|---:|---:|:---:|---:|",
    ]
    for row in scaling:
        lines.append(
            f"| {row['n']} | {row['distribution']} | {row['max_expansions']} | "
            f"{row['score']:.6f} | {row['global_lower_bound']:.6f} | "
            f"{row['relative_gap']:.6f} | {'yes' if row['exact'] else 'no'} | "
            f"{row['seconds']:.6f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "A zero reported gap is a proof for the configured TV radius, fallback, "
            "memory/build/tail cost model, and split budget. A nonzero gap is an "
            "honest unresolved interval, not an optimality claim.",
        ]
    )
    (RESULTS / "anytime_validation.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} anytime validation rows")


if __name__ == "__main__":
    main()

