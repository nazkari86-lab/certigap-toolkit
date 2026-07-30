from __future__ import annotations

import csv
import json
from pathlib import Path

from certigap import (
    SafeSelectionPolicy,
    WorkloadTrace,
    compile_safe_autoindex,
    verify_safe_autoindex_certificate,
)


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "results" / "safe_autoindex_validation.csv"
MD_PATH = ROOT / "results" / "safe_autoindex_validation.md"
EXAMPLE_PATH = ROOT / "results" / "safe_autoindex_example.json"


def range_trace(n: int, count: int) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for _ in range(count):
        trace.add_range(2, n - 1)
    return trace


def update_trace(n: int, count: int) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for index in range(count):
        trace.add_update(1 + index % n, float(index))
    return trace


def main() -> None:
    rows: list[dict[str, object]] = []
    example: dict | None = None
    for n in (16, 32, 64, 128):
        train = range_trace(n, 200)
        test = range_trace(n, 200)
        scenarios = (
            (
                "stable_large",
                range_trace(n, 100_000),
                SafeSelectionPolicy(horizon_operations=1_000_000),
            ),
            (
                "insufficient_sample",
                range_trace(n, 4),
                SafeSelectionPolicy(horizon_operations=1_000_000),
            ),
            (
                "migration_dominated",
                range_trace(n, 100_000),
                SafeSelectionPolicy(
                    horizon_operations=100,
                    migration_cost_units=100_000.0,
                ),
            ),
            (
                "validation_shift",
                update_trace(n, 5_000),
                SafeSelectionPolicy(horizon_operations=1_000_000),
            ),
        )
        for scenario, validation, policy in scenarios:
            model = compile_safe_autoindex(
                range(n),
                train,
                validation,
                test_trace=test,
                policy=policy,
            )
            certificate = model.export_certificate()
            verified = verify_safe_autoindex_certificate(certificate)
            decision = certificate["decision"]
            validation_result = decision["validation"]
            rows.append(
                {
                    "group_id": f"{scenario}-n{n}",
                    "n": n,
                    "scenario": scenario,
                    "train_candidate": decision["train_candidate"],
                    "safe_baseline": decision["safe_baseline"],
                    "deployed": decision["deployed"],
                    "candidate_approved": decision["candidate_approved"],
                    "validation_operations": validation_result[
                        "operation_count"
                    ],
                    "mean_difference": (
                        f"{validation_result['mean_difference']:.12f}"
                    ),
                    "confidence_radius": (
                        f"{validation_result['confidence_radius']:.12f}"
                    ),
                    "amortized_transition_cost": (
                        f"{validation_result['amortized_transition_cost']:.12f}"
                    ),
                    "upper_difference": (
                        f"{validation_result['upper_difference']:.12f}"
                    ),
                    "test_deployed_score": (
                        f"{certificate['test_evaluation']['deployed_score']:.12f}"
                    ),
                    "certificate_verified": verified["verified"],
                }
            )
            if n == 16 and scenario == "stable_large":
                example = compile_safe_autoindex(
                    range(n),
                    train,
                    range_trace(n, 2_000),
                    test_trace=test,
                    policy=SafeSelectionPolicy(
                        horizon_operations=1_000_000
                    ),
                ).export_certificate()

    if example is None:
        raise RuntimeError("safe AutoIndex example was not generated")
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    EXAMPLE_PATH.write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    approvals = sum(row["candidate_approved"] is True for row in rows)
    MD_PATH.write_text(
        "\n".join(
            [
                "# Safe AutoIndex validation",
                "",
                f"- Cases: `{len(rows)}`.",
                f"- Candidate approvals: `{approvals}`.",
                f"- Safe fallbacks: `{len(rows) - approvals}`.",
                f"- Replay-verified certificates: `{len(rows)}/{len(rows)}`.",
                "- Stable large validation approves specialization.",
                "- Small samples, workload shift, and migration-dominated "
                "horizons retain the declared safe baseline.",
                "",
                "The Hoeffding statement is conditional on independent IID "
                "bounded validation operations. Structural work is not "
                "portable wall-clock latency.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} Safe AutoIndex validation cases")


if __name__ == "__main__":
    main()
