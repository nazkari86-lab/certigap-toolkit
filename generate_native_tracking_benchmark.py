from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
from pathlib import Path
import shutil
import statistics
import subprocess
import tempfile
import time

from certigap import AdaptiveSpec, TrackingPolicy, WorkloadTrace
from certigap.spec import compile_from_spec
from certigap.tracking_autoindex import TrackingAutoIndex


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def operations(n: int, count: int, name: str) -> list[tuple[str, int, int, float]]:
    rows = []
    for index in range(count):
        if name == "range_to_update":
            is_range = index < count // 2
        elif name == "update_to_range":
            is_range = index >= count // 2
        elif name == "alternating":
            is_range = index % 2 == 0
        else:
            is_range = index % 10 < 7
        key = 1 + (index * 17) % n
        if is_range:
            left = 1 + (index * 7) % max(1, n // 4)
            rows.append(("range", left, n, 0.0))
        elif name == "read_mostly" and index % 10 >= 7 and index % 2:
            rows.append(("get", key, key, 0.0))
        else:
            rows.append(("update", key, key, float(index % 101 - 50)))
    return rows


def python_rows(count: int) -> list[dict[str, str]]:
    output = []
    for n in (64, 256, 4096):
        training = WorkloadTrace(n)
        for key in range(1, n + 1):
            training.add_get(key)
        # Budget zero keeps benchmark setup linear; construction is excluded.
        spec = AdaptiveSpec(budget=0)
        artifact = compile_from_spec(
            range(1, n + 1), training, spec
        ).export_selection_artifact()
        for name in (
            "range_to_update", "update_to_range", "alternating", "read_mostly"
        ):
            stream = operations(n, count, name)
            samples = []
            checksum = 0.0
            switches = 0
            for _ in range(3):
                tracker = TrackingAutoIndex(
                    [float(value) for value in range(1, n + 1)],
                    artifact,
                    spec,
                    TrackingPolicy(migration_cost_units=8.0),
                )
                current_checksum = 0.0
                start = time.perf_counter_ns()
                for kind, left, right, value in stream:
                    if kind == "range":
                        current_checksum += tracker.range_query(left, right)
                    elif kind == "get":
                        current_checksum += tracker.get(left)
                    else:
                        tracker.point_update(left, value)
                elapsed = time.perf_counter_ns() - start
                samples.append(elapsed / count)
                checksum = current_checksum
                switches = tracker.switch_count
            output.append({
                "n": str(n),
                "workload": name,
                "implementation": "tracking_python_reference",
                "operations": str(count),
                "ns_per_operation": f"{statistics.median(samples):.12g}",
                "switches": str(switches),
                "checksum": f"{checksum:.12g}",
            })
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operations", type=int, default=5000)
    args = parser.parse_args()
    if args.operations <= 0:
        raise ValueError("operations must be positive")
    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("C++ compiler is unavailable")
    source = ROOT / "cpp" / "tracking_autoindex_benchmark.cpp"
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / "tracking_benchmark"
        command = [
            compiler, "-std=c++17", "-O3", "-DNDEBUG", "-march=native",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror",
            f"-I{ROOT / 'cpp'}", str(source), "-o", str(executable),
        ]
        subprocess.run(command, check=True, cwd=ROOT)
        completed = subprocess.run(
            [str(executable), str(args.operations)],
            check=True,
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
    legacy_sizes = {"64", "256", "4096"}
    legacy_workloads = {
        "range_to_update", "update_to_range", "alternating", "read_mostly",
    }
    native = [
        row for row in csv.DictReader(completed.stdout.splitlines())
        if row["n"] in legacy_sizes
        and row["workload"] in legacy_workloads
        and row["implementation"] != "tracking_native_fast_sampled"
    ]
    rows = native + python_rows(args.operations)
    csv_path = RESULTS / "tracking_autoindex_native_runtime.csv"
    fields = [
        "n", "workload", "implementation", "operations",
        "ns_per_operation", "switches", "checksum",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    keyed = {(r["n"], r["workload"], r["implementation"]): r for r in rows}
    production = [r for r in native
                  if r["implementation"] == "tracking_native_rebuild_metric_production"]
    fixed_names = {
        "sorted_array", "prefix_sum", "fenwick",
        "sqrt_decomposition", "segment_tree",
    }
    fixed_ratios = []
    python_speedups = []
    audit_ratios = []
    for row in production:
        group = [r for r in native if r["n"] == row["n"]
                 and r["workload"] == row["workload"]
                 and r["implementation"] in fixed_names]
        fastest = min(float(r["ns_per_operation"]) for r in group)
        fixed_ratios.append(float(row["ns_per_operation"]) / fastest)
        python = keyed[(row["n"], row["workload"], "tracking_python_reference")]
        uniform = keyed[(row["n"], row["workload"],
                         "tracking_native_uniform_production")]
        python_speedups.append(
            float(python["ns_per_operation"]) / float(uniform["ns_per_operation"])
        )
        audit_row = keyed[(row["n"], row["workload"],
                           "tracking_native_rebuild_metric_audit")]
        audit_ratios.append(
            float(audit_row["ns_per_operation"]) / float(row["ns_per_operation"])
        )
    read_switch_reductions = []
    read_speedups = []
    for n in (256, 4096):
        uniform = keyed[(str(n), "read_mostly", "tracking_native_uniform_production")]
        rebuild = keyed[(str(n), "read_mostly",
                         "tracking_native_rebuild_metric_production")]
        read_switch_reductions.append(
            int(uniform["switches"]) / max(1, int(rebuild["switches"]))
        )
        read_speedups.append(
            float(uniform["ns_per_operation"]) / float(rebuild["ns_per_operation"])
        )
    checksums_match = True
    for n in (64, 256, 4096):
        for name in ("range_to_update", "update_to_range", "alternating", "read_mostly"):
            values = [float(r["checksum"]) for r in rows
                      if r["n"] == str(n) and r["workload"] == name]
            checksums_match &= all(math.isclose(values[0], value) for value in values[1:])

    markdown = f"""# Native TrackingAutoIndex Runtime Benchmark

This benchmark executes the same deterministic phased streams at `n=64,256,4096`.
Native rows use five median C++ repetitions; the Python reference uses three.
Construction is excluded, while in-stream migrations and WFA accounting are included.

## Results

- Correctness checksum agreement across every implementation/configuration: `{checksums_match}`.
- Native rebuild-aware production latency: `{min(float(r['ns_per_operation']) for r in production):.2f}` to `{max(float(r['ns_per_operation']) for r in production):.2f}` ns/op.
- Native uniform-metric production is `{min(python_speedups):.1f}x` to `{max(python_speedups):.1f}x` faster than the full Python uniform-metric research reference on the matching streams.
- Against the fastest fixed C++ backend, online tracking costs `{statistics.median(fixed_ratios):.1f}x` median and `{max(fixed_ratios):.1f}x` worst-case. Tracking is therefore not a drop-in latency winner when the best backend is known in advance.
- Recording the full audit trajectory costs `{statistics.median(audit_ratios):.2f}x` median over production mode.
- On `read_mostly` at `n=256,4096`, rebuild-aware migration reduces switching by `{min(read_switch_reductions):.0f}x` to `{max(read_switch_reductions):.0f}x` and improves runtime by `{min(read_speedups):.1f}x` to `{max(read_speedups):.1f}x` versus the naive uniform migration model.

## Interpretation

The native core removes Python from the hot path and makes causal representation
tracking practical when workload adaptation matters more than minimum single-backend
latency. The rebuild-aware matrix is a positive symmetric metric, so it preserves the
classical metric precondition checked by the API. Arbitrary directed matrices remain
available for empirical deployment, but the API returns no competitive factor for them.

Raw data: `tracking_autoindex_native_runtime.csv`.
"""
    report_path = RESULTS / "tracking_autoindex_native_runtime.md"
    report_path.write_text(markdown, encoding="utf-8")
    metadata = {
        "schema": "certigap-native-tracking-benchmark-v1",
        "operations_per_configuration": args.operations,
        "native_repetitions": 5,
        "python_repetitions": 3,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "compiler": subprocess.run(
            [compiler, "--version"], text=True, capture_output=True, check=True
        ).stdout.splitlines()[0],
        "compile_command": command,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    (RESULTS / "tracking_autoindex_native_runtime.metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(markdown)


if __name__ == "__main__":
    main()
