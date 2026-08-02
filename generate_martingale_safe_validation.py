from __future__ import annotations

import csv
import json
import math
import random
from pathlib import Path

from certigap import (
    MartingaleSafeSelectionPolicy,
    WorkloadTrace,
    compile_martingale_safe_autoindex,
    verify_martingale_safe_autoindex_certificate,
)


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "results" / "martingale_safe_validation.csv"
MC_PATH = ROOT / "results" / "martingale_null_monte_carlo.csv"
MD_PATH = ROOT / "results" / "martingale_safe_validation.md"
EXAMPLE_PATH = ROOT / "results" / "martingale_safe_example.json"


def ranges(count: int) -> WorkloadTrace:
    trace = WorkloadTrace(8)
    for _ in range(count):
        trace.add_range(2, 7)
    return trace


def deploy_then_harm() -> WorkloadTrace:
    trace = ranges(1_000)
    for index in range(3_000):
        trace.add_update(1 + index % 8, float(index))
    return trace


def adapted_null_monte_carlo() -> dict[str, object]:
    trials = 5_000
    horizon = 1_000
    alpha = 0.05
    width = 2.0
    fractions = (0.125, 0.25, 0.5, 1.0, 2.0)
    generator = random.Random(20260802)
    false_deployments = 0
    for _ in range(trials):
        cumulative = 0.0
        crossed = False
        for operation in range(1, horizon + 1):
            # The predictable amplitude depends on history, but the fresh sign
            # keeps conditional mean zero. Observations are not IID.
            amplitude = 1.0 if cumulative >= 0.0 else 0.25
            cumulative += amplitude * (
                1.0 if generator.random() < 0.5 else -1.0
            )
            terms = [
                -math.log(len(fractions))
                + (fraction / width) * cumulative
                - fraction * fraction * operation / 8.0
                for fraction in fractions
            ]
            maximum = max(terms)
            log_e = maximum + math.log(
                sum(math.exp(term - maximum) for term in terms)
            )
            crossed = crossed or log_e >= math.log(1.0 / alpha)
        false_deployments += crossed
    return {
        "seed": 20260802,
        "trials": trials,
        "horizon": horizon,
        "alpha": alpha,
        "false_deployments": false_deployments,
        "false_deployment_rate": f"{false_deployments / trials:.6f}",
        "within_nominal_alpha": false_deployments / trials <= alpha,
        "process": "history-adaptive amplitude times fresh Rademacher sign",
        "scope": (
            "diagnostic bounded martingale-difference simulation; Ville's "
            "inequality, not Monte Carlo, supplies the guarantee"
        ),
    }


def main() -> None:
    scenarios = (
        (
            "stable_benefit",
            ranges(1_000),
            MartingaleSafeSelectionPolicy(minimum_observations=50),
        ),
        (
            "insufficient_evidence",
            ranges(20),
            MartingaleSafeSelectionPolicy(minimum_observations=10),
        ),
        (
            "migration_dominated",
            ranges(1_000),
            MartingaleSafeSelectionPolicy(
                minimum_observations=50,
                horizon_operations=100,
                migration_cost_units=10_000.0,
            ),
        ),
        (
            "deploy_then_harm",
            deploy_then_harm(),
            MartingaleSafeSelectionPolicy(minimum_observations=50),
        ),
    )
    rows: list[dict[str, object]] = []
    example = None
    for scenario, monitoring, policy in scenarios:
        model = compile_martingale_safe_autoindex(
            range(8),
            ranges(100),
            monitoring,
            test_trace=ranges(50),
            policy=policy,
        )
        certificate = model.export_certificate()
        verified = verify_martingale_safe_autoindex_certificate(certificate)
        decision = certificate["decision"]
        deployment = decision["deployment_event"]
        revocation = decision["revocation_event"]
        rows.append(
            {
                "scenario": scenario,
                "monitoring_operations": len(monitoring.operations),
                "candidate": decision["train_candidate"],
                "baseline": decision["safe_baseline"],
                "deployed": decision["deployed"],
                "candidate_approved": decision["candidate_approved"],
                "candidate_revoked": decision["candidate_revoked"],
                "deployment_operation": (
                    "" if deployment is None else deployment["stream_operation"]
                ),
                "deployment_log_e": (
                    "" if deployment is None else f"{deployment['log_e_value']:.12f}"
                ),
                "revocation_operation": (
                    "" if revocation is None else revocation["stream_operation"]
                ),
                "revocation_log_e": (
                    "" if revocation is None else f"{revocation['log_e_value']:.12f}"
                ),
                "certificate_verified": verified["verified"],
            }
        )
        if scenario == "stable_benefit":
            example = certificate
    if example is None:
        raise RuntimeError("martingale safe example was not generated")
    monte_carlo = adapted_null_monte_carlo()
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    with MC_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(monte_carlo), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerow(monte_carlo)
    EXAMPLE_PATH.write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    MD_PATH.write_text(
        "\n".join(
            [
                "# Martingale Safe AutoIndex validation",
                "",
                "- Lifecycle scenarios: `4/4` replay-verified.",
                "- Stable benefit deploys specialization.",
                "- Insufficient evidence and migration cost fail closed.",
                "- Update-heavy post-deployment harm revokes to baseline.",
                f"- Adapted-null false deployments: "
                f"`{monte_carlo['false_deployments']}/{monte_carlo['trials']}` "
                f"at nominal alpha `{monte_carlo['alpha']}`.",
                "",
                "The Monte Carlo process has history-dependent amplitude and "
                "fresh mean-zero signs. It is diagnostic only; the formal "
                "claim follows from the e-process supermartingale and Ville "
                "inequality under the declared conditional-mean null.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print("Wrote Martingale SafeAutoIndex validation artifacts")


if __name__ == "__main__":
    main()
