from __future__ import annotations

import csv
import json
from pathlib import Path

from certigap import (
    anytime_branch_and_bound,
    frontier_dp_best,
    make_distribution,
    verify_anytime_core_certificate,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def mean(rows: list[dict], field: str) -> float:
    return sum(float(row[field]) for row in rows) / len(rows)


def main() -> None:
    rows: list[dict] = []
    example: dict | None = None
    for distribution in ("uniform", "zipf", "hot_middle", "hot_tail"):
        for n in (6, 8):
            weights = make_distribution(distribution, n)
            for budget in (2, 3):
                for eta in (0.0, 0.25):
                    exact = frontier_dp_best(weights, budget, eta)
                    for max_expansions in (0, 4, 128):
                        anytime = anytime_branch_and_bound(
                            weights,
                            budget,
                            eta,
                            max_expansions=max_expansions,
                        )
                        verified = verify_anytime_core_certificate(
                            anytime["certificate"])
                        rows.append(
                            {
                                "distribution": distribution,
                                "n": n,
                                "budget": budget,
                                "eta": eta,
                                "max_expansions": max_expansions,
                                "exact_objective": exact["objective"],
                                "lower_bound": anytime["lower_bound"],
                                "upper_bound": anytime["upper_bound"],
                                "absolute_gap": anytime["absolute_gap"],
                                "exact": anytime["exact"],
                                "certificate_verified": verified["verified"],
                                "processed_states": anytime["search_stats"]["processed_states"],
                                "stop_reason": anytime["stop_reason"],
                            }
                        )
                        if example is None and max_expansions == 4:
                            example = anytime["certificate"]
    assert example is not None
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "anytime_core_validation.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (RESULTS / "anytime_core_example.json").write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "# Ordinary CertiGap Anytime Certificate Validation",
        "",
        "Each row compares the replay-verified interval against the unrestricted exact frontier-DP oracle. The theorem guarantees the interval for every accepted certificate; exact-oracle comparison is a diagnostic validation on proof-sized inputs.",
        "",
        "| Expansion limit | Mean certified absolute gap | Exact certificates | Max processed states |",
        "|---:|---:|---:|---:|",
    ]
    for max_expansions in (0, 4, 128):
        subset = [row for row in rows if row["max_expansions"] == max_expansions]
        lines.append(
            "| {limit} | {gap:.6f} | {exact}/{count} | {processed} |".format(
                limit=max_expansions,
                gap=mean(subset, "absolute_gap"),
                exact=sum(row["exact"] is True for row in subset),
                count=len(subset),
                processed=max(int(row["processed_states"]) for row in subset),
            )
        )
    (RESULTS / "anytime_core_validation.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(rows)} ordinary-anytime validation rows")


if __name__ == "__main__":
    main()
