from __future__ import annotations

import csv
from pathlib import Path

from certigap import MeasuredDeploymentPolicy, paired_latency_decision


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def main() -> None:
    policy = MeasuredDeploymentPolicy(
        repetitions=64,
        minimum_normalized_improvement=0.05,
    )
    scenarios = (
        ("strong_win", 1000, 100, True),
        ("weak_win", 1000, 900, False),
        ("parity", 1000, 1000, False),
        ("regression", 1000, 1200, False),
    )
    rows = []
    for name, baseline_ns, candidate_ns, expected in scenarios:
        decision = paired_latency_decision(
            [(baseline_ns, candidate_ns)] * policy.repetitions,
            policy,
        )
        rows.append(
            {
                "scenario": name,
                "baseline_ns": baseline_ns,
                "candidate_ns": candidate_ns,
                "sample_count": decision["sample_count"],
                "mean_normalized_harm": decision["mean_normalized_harm"],
                "upper_normalized_harm": decision["upper_normalized_harm"],
                "candidate_deployed": decision["candidate_deployed"],
                "expected_deployed": expected,
                "passed": decision["candidate_deployed"] is expected,
            }
        )
    RESULTS.mkdir(parents=True, exist_ok=True)
    csv_path = RESULTS / "measured_deployment_validation.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    markdown = [
        "# Measured Deployment Gate Validation",
        "",
        "Deterministic boundary cases for the paired bounded-harm decision.",
        "These are synthetic latency pairs, not hardware benchmark results.",
        "",
        "| Scenario | Mean harm | Upper bound | Deploy | Passed |",
        "|---|---:|---:|---:|---:|",
    ]
    markdown.extend(
        f"| {row['scenario']} | {row['mean_normalized_harm']:.6f} | "
        f"{row['upper_normalized_harm']:.6f} | "
        f"{row['candidate_deployed']} | {row['passed']} |"
        for row in rows
    )
    (RESULTS / "measured_deployment_validation.md").write_text(
        "\n".join(markdown) + "\n",
        encoding="utf-8",
    )
    if not all(row["passed"] for row in rows):
        raise RuntimeError("measured deployment validation failed")
    print(f"Wrote {len(rows)} rows to {csv_path}")


if __name__ == "__main__":
    main()
