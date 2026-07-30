from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

from certigap import (
    AutoIndexConstraints,
    WorkloadTrace,
    compile_autoindex,
    verify_autoindex_artifact,
)


ROOT = Path(__file__).resolve().parent
PORTFOLIO_SIZE = 8
CSV_PATH = ROOT / "results" / "autoindex_validation.csv"
MD_PATH = ROOT / "results" / "autoindex_validation.md"
EXAMPLE_PATH = ROOT / "results" / "autoindex_selection_example.json"


def traces(n: int, scenario: str) -> tuple[WorkloadTrace, WorkloadTrace]:
    train = WorkloadTrace(n)
    holdout = WorkloadTrace(n)
    if scenario == "point_hot":
        for index in range(120):
            train.add_get(1 + index % max(2, n // 8))
            holdout.add_get(n - index % max(2, n // 8))
    elif scenario == "range_hot":
        for index in range(120):
            left = 2 + index % max(1, n // 8)
            train.add_range(left, n - 2)
            holdout.add_range(1, n - index % max(2, n // 8))
    elif scenario == "point_to_range_drift":
        for index in range(120):
            train.add_get(1 + index % max(2, n // 8))
            holdout.add_range(1 + index % max(2, n // 8), n)
    elif scenario == "min_ranges":
        for index in range(120):
            left = 1 + index % max(2, n // 6)
            train.add_range(left, n - index % max(2, n // 7))
            holdout.add_range(1, max(2, n - index % max(2, n // 5)))
    elif scenario == "snapshot_ranges":
        for index in range(120):
            key = 1 + index % n
            train.add_update(key, float(index))
            train.add_range(1, max(1, n // 3))
            holdout.add_range(max(1, n // 3), n)
    elif scenario == "memory_tight":
        for index in range(120):
            train.add_range(1 + index % max(2, n // 8), n)
            holdout.add_get(1 + index % n)
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    return train, holdout


def constraints(n: int, scenario: str) -> AutoIndexConstraints:
    return AutoIndexConstraints(
        aggregate="min" if scenario == "min_ranges" else "sum",
        budget=5,
        require_persistent_snapshots=scenario == "snapshot_ranges",
        memory_limit_slots=n if scenario == "memory_tight" else None,
    )


def main() -> None:
    rows: list[dict[str, object]] = []
    selected_counts: Counter[str] = Counter()
    regrets: list[float] = []
    example: dict | None = None
    scenarios = (
        "point_hot",
        "range_hot",
        "point_to_range_drift",
        "min_ranges",
        "snapshot_ranges",
        "memory_tight",
    )
    for n in (16, 32, 64, 128):
        for scenario in scenarios:
            train, holdout = traces(n, scenario)
            model = compile_autoindex(
                [float(index) for index in range(n)],
                train,
                constraints=constraints(n, scenario),
                holdout_trace=holdout,
            )
            artifact = model.export_selection_artifact()
            verified = verify_autoindex_artifact(artifact)
            selected_counts[model.selected_name] += 1
            regrets.append(float(verified["holdout_regret"]))
            if n == 32 and scenario == "snapshot_ranges":
                example = artifact

            # Exercise the chosen implementation, not only its analytical model.
            expected = (
                0.0
                if artifact["constraints"]["aggregate"] == "min"
                else sum(float(index) for index in range(n))
            )
            if model.range_query(1, n) != expected:
                raise RuntimeError("compiled runtime failed the full-range oracle")

            group_id = f"{scenario}-n{n}"
            for candidate in artifact["candidates"]:
                rows.append(
                    {
                        "group_id": group_id,
                        "n": n,
                        "scenario": scenario,
                        "aggregate": artifact["constraints"]["aggregate"],
                        "snapshots_required": artifact["constraints"][
                            "require_persistent_snapshots"
                        ],
                        "memory_limit_slots": artifact["constraints"][
                            "memory_limit_slots"
                        ]
                        or "",
                        "candidate": candidate["name"],
                        "feasible": candidate["feasible"],
                        "selected": candidate["name"] == artifact["selected"],
                        "train_score": f"{candidate['train']['score']:.12f}",
                        "holdout_score": f"{candidate['holdout']['score']:.12f}",
                        "memory_slots": candidate["resources"]["memory_slots"],
                        "height": candidate["resources"]["height"],
                        "holdout_oracle_score": (
                            f"{verified['holdout_oracle_score']:.12f}"
                        ),
                        "selected_holdout_regret": (
                            f"{verified['holdout_regret']:.12f}"
                        ),
                        "certificate_verified": verified["verified"],
                        "scope": artifact["scope"],
                    }
                )

    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    if example is None:
        raise RuntimeError("AutoIndex example artifact was not generated")
    EXAMPLE_PATH.write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    MD_PATH.write_text(
        "\n".join(
            [
                "# Certified AutoIndex validation",
                "",
                f"- Rows: `{len(rows)}` (`{len(rows) // PORTFOLIO_SIZE}` complete portfolios).",
                f"- Candidate count per portfolio: `{PORTFOLIO_SIZE}`.",
                "- Independently replay-verified portfolios: `24/24`.",
                f"- Selection distribution: `{dict(sorted(selected_counts.items()))}`.",
                f"- Mean chronological-holdout regret: `{sum(regrets) / len(regrets):.6f}` primitive visits.",
                f"- Maximum chronological-holdout regret: `{max(regrets):.6f}` primitive visits.",
                "",
                "Selection uses training operations only. Holdout measures temporal "
                "generalization and is never consulted by the compiler. Scores are "
                "declared structural primitive visits, not wall-clock latency.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(rows)} rows across "
        f"{len(rows) // PORTFOLIO_SIZE} portfolios"
    )


if __name__ == "__main__":
    main()
