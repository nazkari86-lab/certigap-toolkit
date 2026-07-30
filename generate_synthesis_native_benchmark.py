from __future__ import annotations

import bisect
import csv
import hashlib
import json
import platform
import random
import subprocess
from pathlib import Path
from typing import Sequence

from certigap import (
    HardwareProfile,
    HybridConstraints,
    SynthesisConstraints,
    WorkloadTrace,
    compile_hybrid_index,
    compile_synthesized_index,
)
from certigap.benchmark_datasets import SOURCES, load_real_workload
from certigap.synthesis import _interval_score


ROOT = Path(__file__).resolve().parent
CPP_DIR = ROOT / "cpp"
BUILD_DIR = ROOT / "build"
RESULTS_DIR = ROOT / "results"
HEADER_PATH = CPP_DIR / "synthesis_native_cases.hpp"
BINARY_PATH = BUILD_DIR / "synthesis_native_benchmark"
CSV_PATH = RESULTS_DIR / "synthesis_native_latency.csv"
METADATA_PATH = RESULTS_DIR / "synthesis_native_latency_metadata.json"
SUMMARY_PATH = RESULTS_DIR / "synthesis_native_latency.md"

N = 256
TRAIN_OPERATIONS = 800
HOLDOUT_OPERATIONS = 6000
REPEATS = 9
SEED = 20260730
METHODS = (
    "array",
    "global_prefix",
    "fenwick",
    "segment_tree",
    "uniform_block",
    "certigap_x",
    "uniform_prefix",
    "certigap_x_prefix",
    "certigap_hybrid",
    "certigap_auto",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resize(weights: Sequence[float], n: int) -> list[float]:
    """Aggregate an observed ordered key universe into contiguous bins."""
    if len(weights) < n:
        raise ValueError(f"cannot aggregate {len(weights)} keys into {n} bins")
    bins = [0.0] * n
    for index, weight in enumerate(weights):
        bins[(index * n) // len(weights)] += float(weight)
    total = sum(bins)
    if total <= 0.0:
        raise ValueError("workload has no positive probability mass")
    return [weight / total for weight in bins]


def synthetic_weights(name: str, n: int) -> list[float]:
    if name == "left_hot":
        raw = [30.0 if index < n // 5 else 1.0 for index in range(n)]
    elif name == "two_hot":
        raw = [
            24.0
            if n // 8 <= index < n // 4
            or 5 * n // 8 <= index < 3 * n // 4
            else 1.0
            for index in range(n)
        ]
    elif name == "uniform":
        raw = [1.0] * n
    elif name == "temporal_shift_train":
        raw = [36.0 if index < n // 4 else 1.0 for index in range(n)]
    elif name == "temporal_shift_holdout":
        raw = [36.0 if index >= 3 * n // 4 else 1.0 for index in range(n)]
    elif name == "adversarial_edges":
        raw = [30.0 if index % 32 in {0, 31} else 1.0 for index in range(n)]
    else:
        raise ValueError(f"unknown synthetic workload: {name}")
    total = sum(raw)
    return [value / total for value in raw]


def sample_key(rng: random.Random, cumulative: Sequence[float]) -> int:
    return min(len(cumulative), bisect.bisect_left(cumulative, rng.random()) + 1)


def make_trace(
    weights: Sequence[float],
    operation_count: int,
    *,
    seed: int,
    profile: str,
    update_fraction: float = 0.10,
) -> WorkloadTrace:
    rng = random.Random(seed)
    cumulative: list[float] = []
    running = 0.0
    for weight in weights:
        running += weight
        cumulative.append(running)
    cumulative[-1] = 1.0
    trace = WorkloadTrace(len(weights))
    anchors = (1, 17, 33, 65, 97, 129, 161, 193, 225, len(weights))
    for position in range(operation_count):
        center = sample_key(rng, cumulative)
        selector = rng.random()
        if selector < 0.12:
            trace.add_get(center)
        elif selector < 0.12 + update_fraction:
            trace.add_update(center, float((position * 17 + center * 5) % 997))
        else:
            if profile == "uniform":
                radius = rng.randint(0, max(1, len(weights) // 3))
                left = max(1, center - radius)
                right = min(len(weights), center + rng.randint(0, radius + 1))
            elif profile == "adversarial_edges":
                width = rng.choice((15, 17, 31, 33, 47))
                left = max(1, center - width // 2)
                right = min(len(weights), left + width - 1)
            else:
                nearest = min(anchors, key=lambda value: abs(value - center))
                if rng.random() < 0.60:
                    other = min(
                        anchors,
                        key=lambda value: abs(value - (center + rng.randint(-40, 40))),
                    )
                    left, right = sorted((nearest, other))
                else:
                    radius = rng.choice((3, 7, 15, 31))
                    left = max(1, center - rng.randint(0, radius))
                    right = min(len(weights), center + rng.randint(0, radius))
            trace.add_range(left, right)
    return trace


def uniform_boundaries(n: int, width: int) -> tuple[int, ...]:
    return tuple([*range(width, n, width), n])


def partition_score(
    trace: WorkloadTrace,
    boundaries: Sequence[int],
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> float:
    starts = (1, *(boundary + 1 for boundary in boundaries[:-1]))
    return sum(
        _interval_score(trace, left, right, constraints, profile)[0]
        for left, right in zip(starts, boundaries)
    )


def best_uniform(
    trace: WorkloadTrace,
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> tuple[int, ...]:
    candidates = []
    for width in range(1, constraints.max_block_width + 1):
        boundaries = uniform_boundaries(trace.n, width)
        if len(boundaries) <= constraints.max_blocks:
            candidates.append(
                (
                    partition_score(trace, boundaries, constraints, profile),
                    len(boundaries),
                    boundaries,
                )
            )
    if not candidates:
        raise RuntimeError("uniform baseline grammar has no feasible candidate")
    return min(candidates)[2]


def cpp_operation(operation: object) -> str:
    kinds = {"get": 0, "range": 1, "update": 2}
    return (
        f"    {{{kinds[operation.kind]}, {operation.left}, "
        f"{operation.right}, {operation.value:.17g}}},"
    )


def write_header(cases: Sequence[dict]) -> None:
    lines = [
        "#pragma once",
        "",
        "#include <cstddef>",
        "",
        "namespace synthesis_cases {",
        "",
        "struct Operation { int kind; int left; int right; double value; };",
        "struct Case {",
        "    const char* name;",
        "    int n;",
        "    const Operation* operations;",
        "    std::size_t operation_count;",
        "    const Operation* train_operations;",
        "    std::size_t train_operation_count;",
        "    const int* uniform_boundaries;",
        "    std::size_t uniform_count;",
        "    const int* synthesized_boundaries;",
        "    std::size_t synthesized_count;",
        "    const int* hybrid_boundaries;",
        "    std::size_t hybrid_count;",
        "};",
        "",
    ]
    for index, case in enumerate(cases):
        lines.append(f"inline constexpr Operation operations_{index}[] = {{")
        lines.extend(cpp_operation(operation) for operation in case["holdout"].operations)
        lines.extend(
            [
                "};",
                f"inline constexpr Operation train_operations_{index}[] = {{",
            ]
        )
        lines.extend(
            cpp_operation(operation) for operation in case["train"].operations
        )
        lines.extend(
            [
                "};",
                f"inline constexpr int uniform_{index}[] = {{"
                + ", ".join(map(str, case["uniform"]))
                + "};",
                f"inline constexpr int synthesized_{index}[] = {{"
                + ", ".join(map(str, case["synthesized"]))
                + "};",
                f"inline constexpr int hybrid_{index}[] = {{"
                + ", ".join(map(str, case["hybrid"]))
                + "};",
                "",
            ]
        )
    lines.append("inline constexpr Case cases[] = {")
    for index, case in enumerate(cases):
        lines.append(
            f'    {{"{case["name"]}", {N}, operations_{index}, '
            f"sizeof(operations_{index}) / sizeof(operations_{index}[0]), "
            f"train_operations_{index}, "
            f"sizeof(train_operations_{index}) / "
            f"sizeof(train_operations_{index}[0]), "
            f"uniform_{index}, sizeof(uniform_{index}) / sizeof(uniform_{index}[0]), "
            f"synthesized_{index}, "
            f"sizeof(synthesized_{index}) / sizeof(synthesized_{index}[0]), "
            f"hybrid_{index}, "
            f"sizeof(hybrid_{index}) / sizeof(hybrid_{index}[0])}},"
        )
    lines.extend(
        [
            "};",
            "inline constexpr std::size_t case_count = sizeof(cases) / sizeof(cases[0]);",
            "",
            "}  // namespace synthesis_cases",
            "",
        ]
    )
    HEADER_PATH.write_text("\n".join(lines), encoding="utf-8")


def compiler_identity() -> str:
    return subprocess.run(
        ["c++", "--version"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()[0]


def build_cases() -> tuple[list[dict], dict]:
    workload_specs: list[
        tuple[str, list[float], list[float], str, float]
    ] = []
    for name in ("left_hot", "two_hot", "uniform", "adversarial_edges"):
        weights = synthetic_weights(name, N)
        workload_specs.append((name, weights, weights, name, 0.10))
    workload_specs.append(
        (
            "temporal_shift",
            synthetic_weights("temporal_shift_train", N),
            synthetic_weights("temporal_shift_holdout", N),
            "default",
            0.10,
        )
    )
    workload_specs.extend(
        [
            (
                "read_only_skew",
                synthetic_weights("left_hot", N),
                synthetic_weights("left_hot", N),
                "default",
                0.0,
            ),
            (
                "update_30_uniform",
                synthetic_weights("uniform", N),
                synthetic_weights("uniform", N),
                "uniform",
                0.30,
            ),
            (
                "update_50_uniform",
                synthetic_weights("uniform", N),
                synthetic_weights("uniform", N),
                "uniform",
                0.50,
            ),
        ]
    )
    provenance: dict = {}
    for name in SOURCES:
        observed, info = load_real_workload(name)
        weights = resize(observed, N)
        scenario = f"{name}_frequency_derived"
        workload_specs.append((scenario, weights, weights, "default", 0.10))
        provenance[scenario] = {
            **info,
            "derivation": (
                "ordered observed frequency vector aggregated into 256 contiguous "
                "bins; range/get/update operations are deterministic synthetic draws"
            ),
        }

    constraints = SynthesisConstraints(
        aggregate="sum",
        max_blocks=16,
        max_block_width=64,
        tail_weight=0.15,
    )
    hybrid_constraints = HybridConstraints(
        max_blocks=16,
        max_block_width=64,
        tail_weight=0.15,
    )
    hardware = HardwareProfile()
    values = [float((key * 13 + 7) % 101) for key in range(N)]
    cases = []
    for index, (
        name,
        train_weights,
        holdout_weights,
        trace_profile,
        update_fraction,
    ) in enumerate(workload_specs):
        train = make_trace(
            train_weights,
            TRAIN_OPERATIONS,
            seed=SEED + index * 2,
            profile=trace_profile,
            update_fraction=update_fraction,
        )
        holdout = make_trace(
            holdout_weights,
            HOLDOUT_OPERATIONS,
            seed=SEED + index * 2 + 1,
            profile=trace_profile,
            update_fraction=update_fraction,
        )
        model = compile_synthesized_index(
            values,
            train,
            constraints=constraints,
            hardware=hardware,
        )
        hybrid_model = compile_hybrid_index(
            values,
            train,
            constraints=hybrid_constraints,
            hardware=hardware,
        )
        cases.append(
            {
                "name": name,
                "train": train,
                "holdout": holdout,
                "uniform": best_uniform(train, constraints, hardware),
                "synthesized": tuple(model.selected_boundaries),
                "hybrid": tuple(hybrid_model.selected_boundaries),
                "certificate_sha256": model.export_certificate()["sha256"],
                "hybrid_certificate_sha256": (
                    hybrid_model.export_certificate()["sha256"]
                ),
                "update_fraction": update_fraction,
            }
        )
    return cases, {
        "constraints": {
            "aggregate": constraints.aggregate,
            "max_blocks": constraints.max_blocks,
            "max_block_width": constraints.max_block_width,
            "tail_weight": constraints.tail_weight,
        },
        "hardware_profile": hardware.manifest(),
        "hybrid_constraints": {
            "max_blocks": hybrid_constraints.max_blocks,
            "max_block_width": hybrid_constraints.max_block_width,
            "tail_weight": hybrid_constraints.tail_weight,
        },
        "public_workloads": provenance,
    }


def write_summary(rows: Sequence[dict[str, str]]) -> None:
    by_scenario: dict[str, dict[str, dict[str, str]]] = {}
    for row in rows:
        by_scenario.setdefault(row["scenario"], {})[row["method"]] = row
    hybrid_fenwick_wins = 0
    hybrid_uniform_wins = 0
    hybrid_overall_wins = 0
    auto_matches = 0
    auto_regrets: list[float] = []
    table = [
        "# CertiGap-H native holdout benchmark",
        "",
        "| Scenario | Auto selected | Auto ns/op | Holdout oracle | Auto regret | Hybrid vs Fenwick |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for scenario, methods in by_scenario.items():
        timings = {
            method: float(row["median_ns_per_operation"])
            for method, row in methods.items()
        }
        fastest = min(
            (
                method
                for method in timings
                if method != "certigap_auto"
            ),
            key=timings.get,
        )
        hybrid_time = timings["certigap_hybrid"]
        uniform_time = timings["uniform_prefix"]
        fenwick_time = timings["fenwick"]
        hybrid_fenwick_wins += int(hybrid_time < fenwick_time)
        hybrid_uniform_wins += int(hybrid_time < uniform_time)
        hybrid_overall_wins += int(fastest == "certigap_hybrid")
        auto_row = methods["certigap_auto"]
        selected_backend = auto_row["selected_backend"]
        selectable = {
            method: timings[method]
            for method in (
                "global_prefix",
                "fenwick",
                "certigap_hybrid",
            )
        }
        holdout_oracle = min(selectable, key=selectable.get)
        auto_matches += int(selected_backend == holdout_oracle)
        auto_regret = (
            timings["certigap_auto"] / selectable[holdout_oracle] - 1.0
        )
        auto_regrets.append(auto_regret)
        table.append(
            f"| {scenario} | {selected_backend} | "
            f"{timings['certigap_auto']:.3f} | {holdout_oracle} | "
            f"{auto_regret:+.1%} | "
            f"{(fenwick_time / hybrid_time - 1.0):+.1%} |"
        )
    table.extend(
        [
            "",
            f"- CertiGap-H beats Fenwick in "
            f"`{hybrid_fenwick_wins}/{len(by_scenario)}` holdout scenarios.",
            f"- CertiGap-H beats uniform-prefix in "
            f"`{hybrid_uniform_wins}/{len(by_scenario)}` holdout scenarios.",
            f"- CertiGap-H is the fastest tested implementation in "
            f"`{hybrid_overall_wins}/{len(by_scenario)}` scenarios.",
            f"- Train-only AutoIndex matches the three-candidate holdout oracle in "
            f"`{auto_matches}/{len(by_scenario)}` scenarios.",
            f"- Mean AutoIndex holdout regret is "
            f"`{sum(auto_regrets) / len(auto_regrets):.2%}`; maximum is "
            f"`{max(auto_regrets):.2%}`.",
            f"- Excluding the declared `temporal_shift` stress case, mean "
            f"AutoIndex regret is "
            f"`{sum(regret for scenario, regret in zip(by_scenario, auto_regrets) if scenario != 'temporal_shift') / (len(auto_regrets) - 1):.2%}` "
            f"and maximum is "
            f"`{max(regret for scenario, regret in zip(by_scenario, auto_regrets) if scenario != 'temporal_shift'):.2%}`.",
            "- Timings are post-build medians of nine complete trace executions; "
            "p95 is the nearest-rank batch statistic and MAD reports robust spread. "
            "Each method receives a separate untimed warm-up trace.",
            "- Public datasets provide observed key-frequency distributions, not "
            "native range-query traces. Their range/get/update operations are "
            "deterministically generated and labelled `frequency_derived`.",
            "- These measurements describe this machine and compiler only. They "
            "are not a portable speed guarantee.",
        ]
    )
    SUMMARY_PATH.write_text("\n".join(table) + "\n", encoding="utf-8")


def main() -> None:
    BUILD_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)
    cases, design_metadata = build_cases()
    write_header(cases)
    command = [
        "c++",
        "-std=c++17",
        "-O3",
        "-DNDEBUG",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-pedantic",
        "-Icpp",
        "cpp/synthesis_native_benchmark.cpp",
        "-o",
        str(BINARY_PATH),
    ]
    subprocess.run(command, cwd=ROOT, check=True)
    completed = subprocess.run(
        [str(BINARY_PATH)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    CSV_PATH.write_text(completed.stdout, encoding="utf-8")
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != len(cases) * len(METHODS):
        raise RuntimeError("native benchmark emitted an incomplete result matrix")
    if any(row["correct"] != "true" for row in rows):
        raise RuntimeError("native benchmark failed an oracle check")
    write_summary(rows)
    base_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    worktree_dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    )
    metadata = {
        "schema": "certigap-native-benchmark-v1",
        "selection_protocol": (
            "partitions selected from train trace only; holdout operations are "
            "generated from an independent seed and used only after index build"
        ),
        "n": N,
        "train_operations_per_scenario": TRAIN_OPERATIONS,
        "holdout_operations_per_scenario": HOLDOUT_OPERATIONS,
        "repeats": REPEATS,
        "seed": SEED,
        "methods": list(METHODS),
        "timing": {
            "clock": "std::chrono::steady_clock",
            "unit": "nanoseconds per operation",
            "construction_timed": False,
            "summary": "median and nearest-rank p95 of complete trace batches",
            "warmup_batches_per_method": 1,
        },
        "compiler": compiler_identity(),
        "compile_command": command,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "base_git_commit": base_commit,
        "worktree_dirty_at_measurement": worktree_dirty,
        "benchmark_source_sha256": sha256(
            CPP_DIR / "synthesis_native_benchmark.cpp"
        ),
        "generated_cases_sha256": sha256(HEADER_PATH),
        "results_sha256": sha256(CSV_PATH),
        "design": design_metadata,
        "cases": [
            {
                "name": case["name"],
                "uniform_boundaries": list(case["uniform"]),
                "synthesized_boundaries": list(case["synthesized"]),
                "hybrid_boundaries": list(case["hybrid"]),
                "certificate_sha256": case["certificate_sha256"],
                "hybrid_certificate_sha256": case[
                    "hybrid_certificate_sha256"
                ],
                "update_fraction": case["update_fraction"],
            }
            for case in cases
        ],
        "limitations": [
            "single-machine microbenchmark",
            "public datasets are frequency-derived synthetic range traces",
            "unit synthesis profiles are not fitted to measured latency",
            "no concurrency, persistence, allocation, or cache-cold isolation",
        ],
    }
    METADATA_PATH.write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} native measurements across {len(cases)} scenarios")


if __name__ == "__main__":
    main()
