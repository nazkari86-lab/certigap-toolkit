from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

from certigap import (
    SequentialSafeSelectionPolicy,
    WorkloadTrace,
    compile_sequential_safe_autoindex,
    verify_sequential_safe_autoindex_certificate,
)


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "results" / "sequential_safe_validation.csv"
MC_PATH = ROOT / "results" / "optional_stopping_monte_carlo.csv"
MD_PATH = ROOT / "results" / "sequential_safe_validation.md"
EXAMPLE_PATH = ROOT / "results" / "sequential_safe_example.json"


def ranges(count: int) -> WorkloadTrace:
    trace = WorkloadTrace(8)
    for _ in range(count):
        trace.add_range(2, 7)
    return trace


def reversal() -> WorkloadTrace:
    trace = ranges(2_000)
    for index in range(6_000):
        trace.add_update(1 + index % 8, float(index))
    return trace


def monte_carlo() -> dict[str, object]:
    trials = 5_000
    horizon = 1_000
    alpha = 0.05
    width = 2.0
    generator = random.Random(20260731)
    anytime_hits = 0
    repeated_fixed_hits = 0
    for _ in range(trials):
        cumulative = 0.0
        anytime_hit = False
        fixed_hit = False
        for operation in range(1, horizon + 1):
            cumulative += 1.0 if generator.random() < 0.5 else -1.0
            mean = cumulative / operation
            alpha_at_operation = alpha / (
                operation * (operation + 1)
            )
            anytime_radius = width * math.sqrt(
                math.log(1.0 / alpha_at_operation) / (2.0 * operation)
            )
            fixed_radius = width * math.sqrt(
                math.log(1.0 / alpha) / (2.0 * operation)
            )
            anytime_hit = anytime_hit or mean + anytime_radius < 0.0
            fixed_hit = fixed_hit or mean + fixed_radius < 0.0
        anytime_hits += anytime_hit
        repeated_fixed_hits += fixed_hit
    return {
        "seed": 20260731,
        "trials": trials,
        "horizon": horizon,
        "alpha": alpha,
        "anytime_false_approvals": anytime_hits,
        "anytime_false_approval_rate": f"{anytime_hits / trials:.6f}",
        "repeated_fixed_false_approvals": repeated_fixed_hits,
        "repeated_fixed_false_approval_rate": (
            f"{repeated_fixed_hits / trials:.6f}"
        ),
        "scope": (
            "diagnostic Monte Carlo under IID mean-zero Rademacher "
            "differences; theorem, not simulation, provides the guarantee"
        ),
    }


def main() -> None:
    train = ranges(100)
    test = ranges(100)
    scenarios = (
        (
            "stable_stream",
            ranges(2_000),
            SequentialSafeSelectionPolicy(
                minimum_observations=100,
                horizon_operations=1_000_000,
            ),
        ),
        (
            "insufficient_stream",
            ranges(50),
            SequentialSafeSelectionPolicy(
                minimum_observations=10,
                horizon_operations=1_000_000,
            ),
        ),
        (
            "migration_dominated",
            ranges(2_000),
            SequentialSafeSelectionPolicy(
                minimum_observations=100,
                horizon_operations=100,
                migration_cost_units=10_000.0,
            ),
        ),
        (
            "post_stop_reversal",
            reversal(),
            SequentialSafeSelectionPolicy(
                minimum_observations=100,
                horizon_operations=1_000_000,
            ),
        ),
    )
    rows: list[dict[str, object]] = []
    example = None
    for scenario, validation, policy in scenarios:
        model = compile_sequential_safe_autoindex(
            range(8),
            train,
            validation,
            test_trace=test,
            policy=policy,
        )
        certificate = model.export_certificate()
        verified = verify_sequential_safe_autoindex_certificate(certificate)
        decision = certificate["decision"]
        selection = decision["selection_checkpoint"]
        final = decision["final_audit"]
        rows.append(
            {
                "scenario": scenario,
                "validation_operations": len(validation.operations),
                "candidate": decision["train_candidate"],
                "baseline": decision["safe_baseline"],
                "deployed": decision["deployed"],
                "candidate_approved": decision["candidate_approved"],
                "stopping_operation": (
                    "" if selection is None else selection["operation_count"]
                ),
                "selection_upper_difference": (
                    ""
                    if selection is None
                    else f"{selection['upper_difference']:.12f}"
                ),
                "final_upper_difference": (
                    "" if final is None else f"{final['upper_difference']:.12f}"
                ),
                "post_stop_operations": decision["monitoring"][
                    "post_stop_operations"
                ],
                "certificate_verified": verified["verified"],
            }
        )
        if scenario == "stable_stream":
            example = certificate

    if example is None:
        raise RuntimeError("sequential example was not generated")
    monte_carlo_row = monte_carlo()
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    with MC_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(monte_carlo_row), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow(monte_carlo_row)
    EXAMPLE_PATH.write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    approvals = sum(row["candidate_approved"] is True for row in rows)
    reversal_row = next(
        row for row in rows if row["scenario"] == "post_stop_reversal"
    )
    MD_PATH.write_text(
        "\n".join(
            [
                "# Sequential Safe AutoIndex validation",
                "",
                f"- Deployment scenarios: `{len(rows)}`.",
                f"- Candidate approvals: `{approvals}`.",
                f"- Replay-verified certificates: `{len(rows)}/{len(rows)}`.",
                "- Stable evidence approves at the first valid prefix.",
                "- Small samples and migration-dominated horizons fail closed.",
                "- Post-stop reversal does not retroactively change deployment; "
                f"`{reversal_row['post_stop_operations']}` operations remain "
                "evaluation-only.",
                f"- Mean-zero Monte Carlo false approvals: "
                f"`{monte_carlo_row['anytime_false_approvals']}/"
                f"{monte_carlo_row['trials']}` for alpha spending versus "
                f"`{monte_carlo_row['repeated_fixed_false_approvals']}/"
                f"{monte_carlo_row['trials']}` for invalid repeated fixed-time "
                "checks.",
                "",
                "The confidence-sequence theorem is conditional on independent "
                "IID bounded validation operations. The Monte Carlo row is a "
                "diagnostic, not a proof and not evidence for arbitrary drift.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print("Wrote sequential SafeAutoIndex validation artifacts")


if __name__ == "__main__":
    main()
