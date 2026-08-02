from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import platform
import random
import statistics
import sys
import time
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import cast

from certigap import (
    AdaptiveSpec,
    TrackingAutoIndex,
    TrackingPolicy,
    WorkloadTrace,
    compile_from_spec,
    verify_tracking_autoindex_certificate,
)
from certigap.autoindex import (
    CandidateName,
    TraceOperation,
    _runtime_for_candidate,
)
from certigap.dynamic_range import DynamicCertiRange


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
STRUCTURAL_PATH = RESULTS / "tracking_autoindex_comparison.csv"
CANDIDATE_PATH = RESULTS / "tracking_autoindex_candidates.csv"
RUNTIME_PATH = RESULTS / "tracking_autoindex_runtime.csv"
SUMMARY_PATH = RESULTS / "tracking_autoindex_comparison.md"
METADATA_PATH = RESULTS / "tracking_autoindex_comparison_metadata.json"

SIZES = (16, 64, 128)
MIGRATION_COSTS = (2.0, 8.0, 32.0)
HORIZON = 96
SCENARIOS = (
    "stable_points",
    "stable_ranges",
    "stable_updates",
    "mixed_read_heavy",
    "mixed_write_heavy",
    "point_to_range",
    "range_to_update",
    "update_to_range",
    "three_phase",
    "alternating_range_update",
    "short_bursts",
    "random_iid",
    "markov_bursty",
    "varying_ranges",
)


def training_trace(n: int) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for key in range(1, n + 1):
        trace.add_get(key)
    return trace


def _operation(kind: str, index: int, n: int) -> TraceOperation:
    key = 1 + (index * 17 + 3) % n
    if kind == "get":
        return TraceOperation("get", key, key)
    if kind == "update":
        return TraceOperation("update", key, key, float(-(index + 1)))
    left = 1 + (index * 11) % max(1, n // 3)
    right = max(left, n - (index * 7) % max(1, n // 4))
    return TraceOperation("range", left, right)


def workload(
    n: int, scenario: str, horizon: int = HORIZON
) -> tuple[TraceOperation, ...]:
    kinds: list[str] = []
    if scenario == "stable_points":
        kinds = ["get"] * horizon
    elif scenario == "stable_ranges":
        kinds = ["range"] * horizon
    elif scenario == "stable_updates":
        kinds = ["update"] * horizon
    elif scenario == "mixed_read_heavy":
        pattern = ("get",) * 6 + ("range",) * 3 + ("update",)
        kinds = [pattern[index % len(pattern)] for index in range(horizon)]
    elif scenario == "mixed_write_heavy":
        pattern = ("get", "range", "range") + ("update",) * 6
        kinds = [pattern[index % len(pattern)] for index in range(horizon)]
    elif scenario in {"point_to_range", "range_to_update", "update_to_range"}:
        first, second = {
            "point_to_range": ("get", "range"),
            "range_to_update": ("range", "update"),
            "update_to_range": ("update", "range"),
        }[scenario]
        kinds = [first] * (horizon // 2) + [second] * (horizon - horizon // 2)
    elif scenario == "three_phase":
        third = horizon // 3
        kinds = ["get"] * third + ["range"] * third
        kinds += ["update"] * (horizon - len(kinds))
    elif scenario == "alternating_range_update":
        kinds = ["range" if index % 2 == 0 else "update" for index in range(horizon)]
    elif scenario == "short_bursts":
        phases = ("get", "range", "update", "range")
        kinds = [phases[(index // 8) % len(phases)] for index in range(horizon)]
    elif scenario == "random_iid":
        rng = random.Random(17_003 + n)
        kinds = rng.choices(
            ("get", "range", "update"), weights=(0.35, 0.40, 0.25), k=horizon
        )
    elif scenario == "markov_bursty":
        rng = random.Random(31_337 + n)
        state = "get"
        for _ in range(horizon):
            if rng.random() < 0.16:
                state = rng.choice(
                    [kind for kind in ("get", "range", "update") if kind != state]
                )
            kinds.append(state)
    elif scenario == "varying_ranges":
        kinds = ["range"] * horizon
    else:
        raise ValueError(f"unknown scenario: {scenario}")
    operations = []
    for index, kind in enumerate(kinds):
        if scenario == "varying_ranges":
            left = 1 + index % max(1, n // 2)
            right = left + (index * 13) % (n - left + 1)
            operations.append(TraceOperation("range", left, right))
        else:
            operations.append(_operation(kind, index, n))
    return tuple(operations)


def execute(target: object, operations: Iterable[TraceOperation]) -> float:
    checksum = 0.0
    for operation in operations:
        if operation.kind == "get":
            if isinstance(target, list):
                value = target[operation.left - 1]
            elif isinstance(target, DynamicCertiRange):
                value = target.get(operation.left, track=False)
            else:
                value = target.get(operation.left)
            checksum += float(value)
        elif operation.kind == "range":
            if isinstance(target, list):
                value = sum(target[operation.left - 1 : operation.right])
            elif isinstance(target, DynamicCertiRange):
                value = target.range_query(operation.left, operation.right, track=False)
            else:
                value = target.range_query(operation.left, operation.right)
            checksum += float(value)
        else:
            if isinstance(target, list):
                target[operation.left - 1] = operation.value
            else:
                target.point_update(operation.left, operation.value)
            checksum += operation.value
    return checksum


def _distance(left: str, right: str, migration: float) -> float:
    return 0.0 if left == right else migration


def policy_costs(artifact: dict) -> dict[str, tuple[float, int]]:
    rows = [step["service_costs"] for step in artifact["steps"]]
    candidates = tuple(artifact["candidates"])
    initial = artifact["policy"]["initial_candidate"]
    migration = float(artifact["policy"]["migration_cost_units"])
    fixed = {
        candidate: _distance(initial, candidate, migration)
        + sum(row[candidate] for row in rows)
        for candidate in candidates
    }
    best_fixed = min(
        candidates,
        key=lambda candidate: (fixed[candidate], candidates.index(candidate)),
    )

    def online(
        selector: Callable[[dict[str, float], str, dict[str, float]], str],
    ) -> tuple[float, int]:
        current = initial
        cumulative_service = {candidate: 0.0 for candidate in candidates}
        cost = 0.0
        switches = 0
        for row in rows:
            for candidate in candidates:
                cumulative_service[candidate] += row[candidate]
            selected = selector(row, current, cumulative_service)
            if selected != current:
                cost += migration
                switches += 1
            cost += row[selected]
            current = selected
        return cost, switches

    myopic = online(
        lambda row, current, _: min(
            candidates,
            key=lambda candidate: (
                row[candidate] + _distance(current, candidate, migration),
                candidates.index(candidate),
            ),
        )
    )
    cumulative_leader = online(
        lambda _row, current, cumulative: min(
            candidates,
            key=lambda candidate: (
                cumulative[candidate] + _distance(current, candidate, migration),
                candidates.index(candidate),
            ),
        )
    )
    return {
        "tracking_wfa": (
            float(artifact["actual_cost"]),
            sum(step["switched"] for step in artifact["steps"]),
        ),
        "initial_static": (fixed[initial], 0),
        "best_fixed_hindsight": (fixed[best_fixed], int(best_fixed != initial)),
        "myopic_current_operation": myopic,
        "cumulative_leader": cumulative_leader,
        "exact_k_switch_oracle": (
            float(artifact["constrained_oracle"]["cost"]),
            int(artifact["constrained_oracle"]["switches"]),
        ),
        "exact_unrestricted_oracle": (
            float(artifact["unrestricted_oracle"]["cost"]),
            int(artifact["unrestricted_oracle"]["switches"]),
        ),
    }


def structural_matrix(
    sizes: tuple[int, ...],
    scenarios: tuple[str, ...],
    migration_costs: tuple[float, ...],
) -> tuple[list[dict], list[dict]]:
    structural: list[dict] = []
    candidate_rows: list[dict] = []
    spec = AdaptiveSpec()
    for n in sizes:
        values = [float(index + 1) for index in range(n)]
        compiled = compile_from_spec(values, training_trace(n), spec)
        autoindex = compiled.export_selection_artifact()
        candidates = tuple(
            row["name"] for row in autoindex["candidates"] if row["feasible"]
        )
        for scenario in scenarios:
            operations = workload(n, scenario)
            expected = execute(list(values), operations)
            for migration in migration_costs:
                tracker = TrackingAutoIndex(
                    values,
                    autoindex,
                    spec,
                    TrackingPolicy(
                        migration_cost_units=migration,
                        max_comparator_switches=4,
                    ),
                )
                observed = execute(tracker, operations)
                if not math.isclose(observed, expected, rel_tol=1e-12, abs_tol=1e-9):
                    raise RuntimeError("TrackingAutoIndex checksum mismatch")
                artifact = tracker.export_certificate()
                verification = verify_tracking_autoindex_certificate(artifact)
                policies = policy_costs(artifact)
                oracle_cost = policies["exact_unrestricted_oracle"][0]
                for policy, (cost, switches) in policies.items():
                    structural.append(
                        {
                            "n": n,
                            "scenario": scenario,
                            "migration_cost_units": migration,
                            "policy": policy,
                            "cost": f"{cost:.12f}",
                            "switches": switches,
                            "ratio_to_unrestricted_oracle": f"{cost / oracle_cost:.12f}",
                            "certificate_verified": verification["verified"],
                        }
                    )
                service_rows = [step["service_costs"] for step in artifact["steps"]]
                for candidate in candidates:
                    cost = _distance(
                        artifact["policy"]["initial_candidate"], candidate, migration
                    ) + sum(row[candidate] for row in service_rows)
                    manifest_row = next(
                        row
                        for row in autoindex["candidates"]
                        if row["name"] == candidate
                    )
                    candidate_rows.append(
                        {
                            "n": n,
                            "scenario": scenario,
                            "migration_cost_units": migration,
                            "candidate": candidate,
                            "fixed_total_cost": f"{cost:.12f}",
                            "ratio_to_tracking_wfa": f"{cost / artifact['actual_cost']:.12f}",
                            "memory_slots": manifest_row["resources"]["memory_slots"],
                            "height": manifest_row["resources"]["height"],
                        }
                    )
    return structural, candidate_rows


def _runtime_factory(
    method: str,
    values: list[float],
    autoindex: dict,
    spec: AdaptiveSpec,
) -> object:
    if method == "tracking_wfa":
        return TrackingAutoIndex(
            values,
            autoindex,
            spec,
            TrackingPolicy(migration_cost_units=8.0),
        )
    if method == "python_list":
        return list(values)
    return _runtime_for_candidate(values, cast(CandidateName, method), autoindex)


def runtime_matrix(
    sizes: tuple[int, ...], *, repetitions: int, horizon: int
) -> list[dict]:
    rows: list[dict] = []
    spec = AdaptiveSpec()
    runtime_scenarios = (
        "stable_points",
        "stable_ranges",
        "mixed_read_heavy",
        "point_to_range",
        "alternating_range_update",
    )
    for n in sizes:
        values = [float(index + 1) for index in range(n)]
        compiled = compile_from_spec(values, training_trace(n), spec)
        artifact = compiled.export_selection_artifact()
        methods = ["python_list", "tracking_wfa"] + [
            row["name"] for row in artifact["candidates"] if row["feasible"]
        ]
        for scenario in runtime_scenarios:
            operations = workload(n, scenario, horizon=horizon)
            expected = execute(list(values), operations)
            for method in methods:
                samples = []
                checksums = []
                for _ in range(repetitions):
                    target = _runtime_factory(method, values, artifact, spec)
                    gc.disable()
                    started = time.perf_counter_ns()
                    checksum = execute(target, operations)
                    elapsed = time.perf_counter_ns() - started
                    gc.enable()
                    samples.append(elapsed / len(operations))
                    checksums.append(checksum)
                if any(
                    not math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-9)
                    for value in checksums
                ):
                    raise RuntimeError(f"runtime checksum mismatch for {method}")
                ordered = sorted(samples)
                rows.append(
                    {
                        "n": n,
                        "scenario": scenario,
                        "method": method,
                        "operations": len(operations),
                        "repetitions": len(samples),
                        "median_ns_per_operation": f"{statistics.median(samples):.3f}",
                        "p95_ns_per_operation": f"{ordered[-1]:.3f}",
                        "checksum": f"{expected:.12f}",
                        "includes_online_accounting": method == "tracking_wfa",
                        "includes_in_trace_rebuilds": method == "tracking_wfa",
                        "initial_build_excluded": True,
                    }
                )
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare TrackingAutoIndex against structural and runtime baselines."
    )
    parser.add_argument("--mode", choices=("quick", "full", "max"), default="max")
    args = parser.parse_args()
    if args.mode == "quick":
        sizes = (16,)
        scenarios = SCENARIOS[:5]
        migration_costs = (2.0, 8.0)
        runtime_sizes = (64,)
        runtime_repetitions = 3
        runtime_horizon = 128
    elif args.mode == "full":
        sizes = (16, 64)
        scenarios = SCENARIOS
        migration_costs = MIGRATION_COSTS
        runtime_sizes = (64, 256)
        runtime_repetitions = 3
        runtime_horizon = 192
    else:
        sizes = SIZES
        scenarios = SCENARIOS
        migration_costs = MIGRATION_COSTS
        runtime_sizes = (64, 256)
        runtime_repetitions = 5
        runtime_horizon = 256
    RESULTS.mkdir(exist_ok=True)
    structural, candidates = structural_matrix(sizes, scenarios, migration_costs)
    runtime = runtime_matrix(
        runtime_sizes,
        repetitions=runtime_repetitions,
        horizon=runtime_horizon,
    )
    write_csv(STRUCTURAL_PATH, structural)
    write_csv(CANDIDATE_PATH, candidates)
    write_csv(RUNTIME_PATH, runtime)

    grouped: dict[tuple[int, str, float], dict[str, float]] = {}
    for row in structural:
        key = (int(row["n"]), str(row["scenario"]), float(row["migration_cost_units"]))
        grouped.setdefault(key, {})[str(row["policy"])] = float(row["cost"])
    comparisons = {
        baseline: sum(
            costs["tracking_wfa"] < costs[baseline] - 1e-9 for costs in grouped.values()
        )
        for baseline in (
            "initial_static",
            "best_fixed_hindsight",
            "myopic_current_operation",
            "cumulative_leader",
        )
    }
    ties = {
        baseline: sum(
            math.isclose(
                costs["tracking_wfa"], costs[baseline], rel_tol=1e-12, abs_tol=1e-9
            )
            for costs in grouped.values()
        )
        for baseline in comparisons
    }
    wfa_ratios = [
        costs["tracking_wfa"] / costs["exact_unrestricted_oracle"]
        for costs in grouped.values()
    ]
    runtime_groups: dict[tuple[int, str], dict[str, float]] = {}
    for row in runtime:
        runtime_groups.setdefault((int(row["n"]), str(row["scenario"])), {})[
            str(row["method"])
        ] = float(row["median_ns_per_operation"])
    tracking_slowdowns = [
        values["tracking_wfa"]
        / min(latency for method, latency in values.items() if method != "tracking_wfa")
        for values in runtime_groups.values()
    ]
    portfolio_slowdowns = [
        values["tracking_wfa"]
        / min(
            latency
            for method, latency in values.items()
            if method not in {"tracking_wfa", "python_list"}
        )
        for values in runtime_groups.values()
    ]
    migration_rows = []
    for migration in migration_costs:
        selected = [
            costs for key, costs in grouped.items() if math.isclose(key[2], migration)
        ]
        ratios = [
            costs["tracking_wfa"] / costs["exact_unrestricted_oracle"]
            for costs in selected
        ]
        migration_rows.append(
            (
                migration,
                statistics.mean(ratios),
                max(ratios),
                statistics.mean(
                    next(
                        float(row["switches"])
                        for row in structural
                        if int(row["n"]) == key[0]
                        and row["scenario"] == key[1]
                        and math.isclose(float(row["migration_cost_units"]), key[2])
                        and row["policy"] == "tracking_wfa"
                    )
                    for key, costs in grouped.items()
                    if math.isclose(key[2], migration)
                ),
            )
        )
    scenario_rows = []
    for scenario in scenarios:
        selected = [costs for key, costs in grouped.items() if key[1] == scenario]
        wins = sum(
            costs["tracking_wfa"] < costs["best_fixed_hindsight"] - 1e-9
            for costs in selected
        )
        ties_count = sum(
            math.isclose(
                costs["tracking_wfa"],
                costs["best_fixed_hindsight"],
                rel_tol=1e-12,
                abs_tol=1e-9,
            )
            for costs in selected
        )
        scenario_rows.append(
            (scenario, wins, ties_count, len(selected) - wins - ties_count)
        )
    candidate_groups: dict[tuple[int, str, float], list[dict]] = {}
    for row in candidates:
        candidate_groups.setdefault(
            (
                int(row["n"]),
                str(row["scenario"]),
                float(row["migration_cost_units"]),
            ),
            [],
        ).append(row)
    fixed_winner_counts: dict[str, int] = {}
    for rows in candidate_groups.values():
        winner = min(
            rows,
            key=lambda row: (
                float(row["fixed_total_cost"]),
                str(row["candidate"]),
            ),
        )["candidate"]
        fixed_winner_counts[str(winner)] = fixed_winner_counts.get(str(winner), 0) + 1
    runtime_table = []
    for (n, scenario), values in sorted(runtime_groups.items()):
        fixed = {
            method: latency
            for method, latency in values.items()
            if method not in {"tracking_wfa", "python_list"}
        }
        fastest = min(fixed, key=fixed.get)
        runtime_table.append(
            (
                n,
                scenario,
                values["tracking_wfa"],
                fastest,
                fixed[fastest],
                values["tracking_wfa"] / fixed[fastest],
            )
        )
    SUMMARY_PATH.write_text(
        "\n".join(
            [
                "# TrackingAutoIndex comprehensive comparison",
                "",
                f"- Certified workload configurations: `{len(grouped)}`.",
                f"- Structural policy rows: `{len(structural)}`.",
                f"- Fixed-candidate rows: `{len(candidates)}`.",
                f"- Wall-clock method rows: `{len(runtime)}`.",
                "- All runtime methods passed identical checksum validation.",
                "",
                "## Structural outcomes",
                "",
                *[
                    f"- Versus `{baseline}`: WFA wins `{comparisons[baseline]}`, "
                    f"ties `{ties[baseline]}`, loses "
                    f"`{len(grouped) - comparisons[baseline] - ties[baseline]}`."
                    for baseline in comparisons
                ],
                f"- Mean ratio to exact unrestricted oracle: `{statistics.mean(wfa_ratios):.6f}`.",
                f"- Median ratio to exact unrestricted oracle: `{statistics.median(wfa_ratios):.6f}`.",
                f"- Maximum ratio to exact unrestricted oracle: `{max(wfa_ratios):.6f}`.",
                f"- Best fixed candidate frequency: `{dict(sorted(fixed_winner_counts.items()))}`.",
                "",
                "### Versus best fixed hindsight by workload",
                "",
                "| Workload | Wins | Ties | Losses |",
                "|---|---:|---:|---:|",
                *[
                    f"| `{scenario}` | {wins} | {ties_count} | {losses} |"
                    for scenario, wins, ties_count, losses in scenario_rows
                ],
                "",
                "### Migration sensitivity",
                "",
                "| Migration units | Mean oracle ratio | Max oracle ratio | Mean switches |",
                "|---:|---:|---:|---:|",
                *[
                    f"| {migration:g} | {mean_ratio:.6f} | {max_ratio:.6f} | {mean_switches:.3f} |"
                    for migration, mean_ratio, max_ratio, mean_switches in migration_rows
                ],
                "",
                "## Runtime boundary",
                "",
                f"- Median TrackingAutoIndex slowdown versus fastest tested runtime: `{statistics.median(tracking_slowdowns):.2f}x`.",
                f"- Maximum TrackingAutoIndex slowdown versus fastest tested runtime: `{max(tracking_slowdowns):.2f}x`.",
                f"- Median slowdown versus fastest fixed portfolio backend: `{statistics.median(portfolio_slowdowns):.2f}x`.",
                f"- Maximum slowdown versus fastest fixed portfolio backend: `{max(portfolio_slowdowns):.2f}x`.",
                "- These Python timings include online WFA accounting and in-trace rebuilds, "
                "but exclude initial construction and certificate export.",
                "- Structural scores and wall-clock nanoseconds are reported separately; "
                "neither is substituted for the other.",
                "",
                "| n | Workload | Tracking ns/op | Fastest fixed | Fixed ns/op | Slowdown |",
                "|---:|---|---:|---|---:|---:|",
                *[
                    f"| {n} | `{scenario}` | {tracking:.1f} | `{fastest}` | {fixed:.1f} | {slowdown:.2f}x |"
                    for n, scenario, tracking, fastest, fixed, slowdown in runtime_table
                ],
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    METADATA_PATH.write_text(
        json.dumps(
            {
                "schema": "certigap-tracking-comparison-metadata-v1",
                "python": sys.version,
                "platform": platform.platform(),
                "processor": platform.processor(),
                "mode": args.mode,
                "sizes": list(sizes),
                "migration_cost_units": list(migration_costs),
                "horizon": HORIZON,
                "scenarios": list(scenarios),
                "runtime_sizes": list(runtime_sizes),
                "runtime_horizon": runtime_horizon,
                "runtime_repetitions": runtime_repetitions,
                "runtime_scope": (
                    "Python end-to-end operations after initial construction; "
                    "TrackingAutoIndex includes online accounting and rebuilds"
                ),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(structural)} policy, {len(candidates)} candidate, "
        f"and {len(runtime)} runtime rows"
    )


if __name__ == "__main__":
    main()
