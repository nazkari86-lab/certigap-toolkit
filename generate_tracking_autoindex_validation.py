from __future__ import annotations

import csv
import json
from pathlib import Path

from certigap import (
    AdaptiveSpec,
    TrackingPolicy,
    WorkloadTrace,
    start_tracking_autoindex,
    verify_tracking_autoindex_certificate,
)


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "results" / "tracking_autoindex_validation.csv"
MD_PATH = ROOT / "results" / "tracking_autoindex_validation.md"
EXAMPLE_PATH = ROOT / "results" / "tracking_autoindex_example.json"


def training_trace(n: int) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for _ in range(3):
        for key in range(1, n + 1):
            trace.add_get(key)
    return trace


def run_scenario(scenario: str, migration: float) -> dict:
    n = 32
    tracker = start_tracking_autoindex(
        range(n),
        training_trace(n),
        AdaptiveSpec(),
        policy=TrackingPolicy(
            migration_cost_units=migration,
            max_comparator_switches=3,
        ),
    )
    if scenario == "stable_points":
        for _ in range(12):
            tracker.get(3)
    elif scenario == "stable_ranges":
        for _ in range(12):
            tracker.range_query(1, n)
    elif scenario == "point_to_range_shift":
        for _ in range(6):
            tracker.get(3)
        for _ in range(12):
            tracker.range_query(1, n)
    elif scenario == "range_to_updates_shift":
        for _ in range(12):
            tracker.range_query(1, n)
        for key in range(1, 7):
            tracker.point_update(key, float(-key))
    elif scenario == "alternating":
        for key in range(1, 9):
            tracker.range_query(1, n)
            tracker.point_update(key, float(-key))
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    artifact = tracker.export_certificate()
    verified = verify_tracking_autoindex_certificate(artifact)
    oracle = artifact["constrained_oracle"]
    return {
        "scenario": scenario,
        "migration_cost_units": migration,
        "operations": len(artifact["steps"]),
        "feasible_candidates": len(artifact["candidates"]),
        "initial_candidate": artifact["policy"]["initial_candidate"],
        "final_candidate": artifact["steps"][-1]["selected"],
        "wfa_switches": sum(step["switched"] for step in artifact["steps"]),
        "oracle_switches": oracle["switches"],
        "actual_cost": f"{artifact['actual_cost']:.12f}",
        "constrained_oracle_cost": f"{oracle['cost']:.12f}",
        "dynamic_regret": f"{artifact['dynamic_regret']:.12f}",
        "competitive_ratio_observed": (
            f"{artifact['actual_cost'] / artifact['unrestricted_oracle']['cost']:.12f}"
        ),
        "observed_factor_bound_holds": artifact[
            "observed_factor_bound_holds"
        ],
        "certificate_verified": verified["verified"],
        "scope": artifact["scope"],
        "artifact": artifact,
    }


def main() -> None:
    records = [
        run_scenario(scenario, migration)
        for migration in (2.0, 8.0, 32.0)
        for scenario in (
            "stable_points",
            "stable_ranges",
            "point_to_range_shift",
            "range_to_updates_shift",
            "alternating",
        )
    ]
    rows = [{key: value for key, value in row.items() if key != "artifact"} for row in records]
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    example = next(
        row["artifact"]
        for row in records
        if row["scenario"] == "point_to_range_shift"
        and row["migration_cost_units"] == 8.0
    )
    EXAMPLE_PATH.write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    regrets = [float(row["dynamic_regret"]) for row in rows]
    ratios = [float(row["competitive_ratio_observed"]) for row in rows]
    MD_PATH.write_text(
        "\n".join(
            [
                "# TrackingAutoIndex validation",
                "",
                f"- Scenarios: `{len(rows)}`.",
                "- Independently replay-verified certificates: "
                f"`{sum(row['certificate_verified'] for row in rows)}/{len(rows)}`.",
                f"- Maximum exact K-switch dynamic regret: `{max(regrets):.6f}` structural units.",
                f"- Maximum observed unrestricted-oracle ratio: `{max(ratios):.6f}`.",
                "- Migration costs tested: `2`, `8`, and `32` structural units.",
                "",
                "Every row executes the selected backend and independently replays "
                "the causal Work Function Algorithm. The comparator is an exact "
                "dynamic-programming oracle with at most three switches. Costs are "
                "analytical structural work, not portable wall-clock latency.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} verified tracking scenarios")


if __name__ == "__main__":
    main()
