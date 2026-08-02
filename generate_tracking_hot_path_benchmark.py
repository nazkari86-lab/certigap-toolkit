from __future__ import annotations

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


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
HORIZONS = (5000, 50000)
IMPLEMENTATIONS = {
    "frozen_fenwick_checked", "frozen_fenwick_unchecked",
    "static_fenwick_checked", "static_fenwick_unchecked",
    "fast_checked", "fast_unchecked", "fast_detached_data_plane",
}


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * probability)]


def main() -> None:
    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("C++ compiler is unavailable")
    source = ROOT / "cpp" / "tracking_hot_path_benchmark.cpp"
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / "tracking_hot_path"
        command = [
            compiler, "-std=c++17", "-O3", "-DNDEBUG", "-march=native",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror",
            f"-I{ROOT / 'cpp'}", str(source), "-o", str(executable),
        ]
        subprocess.run(command, check=True, cwd=ROOT)
        for horizon in HORIZONS:
            completed = subprocess.run(
                [str(executable), str(horizon)], check=True, cwd=ROOT,
                text=True, capture_output=True,
            )
            for row in csv.DictReader(completed.stdout.splitlines()):
                row["horizon"] = str(horizon)
                rows.append(row)

    fields = [
        "horizon", "n", "workload", "implementation", "operations",
        "ns_per_operation", "baseline_ns_per_operation", "ratio_to_direct",
        "checksum", "baseline_checksum",
    ]
    csv_path = RESULTS / "tracking_hot_path_runtime.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["horizon"], row["n"], row["workload"]), []).append(row)
    ratios: dict[str, list[float]] = {
        implementation: [] for implementation in IMPLEMENTATIONS
    }
    long_ratios: dict[str, list[float]] = {
        implementation: [] for implementation in IMPLEMENTATIONS
    }
    checksums_match = True
    for group in groups.values():
        for row in group:
            checksums_match &= math.isclose(
                float(row["baseline_checksum"]), float(row["checksum"]),
                rel_tol=1e-12, abs_tol=1e-9,
            )
            ratios[row["implementation"]].append(float(row["ratio_to_direct"]))
            if row["horizon"] == "50000":
                long_ratios[row["implementation"]].append(
                    float(row["ratio_to_direct"])
                )

    lines = []
    for implementation in sorted(ratios):
        values = ratios[implementation]
        lines.append(
            f"- `{implementation}`: `{statistics.median(values):.2f}x` median, "
            f"`{percentile(values, 0.95):.2f}x` p95, `{max(values):.2f}x` maximum."
        )
    long_lines = []
    for implementation in sorted(long_ratios):
        values = long_ratios[implementation]
        long_lines.append(
            f"- `{implementation}`: `{statistics.median(values):.2f}x` median, "
            f"`{percentile(values, 0.95):.2f}x` p95, `{max(values):.2f}x` maximum."
        )
    markdown = f"""# Tracking Hot-Path Benchmark

This benchmark isolates controller and API overhead from algorithm selection. It
compares the direct Fenwick runtime with checked/unchecked frozen and adaptive
paths over 64 configurations. Construction is excluded; each row is the median
of seven native repetitions.

## Results

- Correctness checksum agreement: `{checksums_match}`.
{chr(10).join(lines)}

### 50,000-operation horizon

{chr(10).join(long_lines)}

## Boundary

Frozen mode removes sampling, switching, leases, and the robust shadow. It still
uses one indirect function dispatch because the backend is selected at runtime.
Unchecked methods require one-based keys, valid inclusive ranges, and finite update
values; violating those preconditions is outside the API contract. Measurements are
machine-specific and are not a universal latency theorem.

Raw data: `tracking_hot_path_runtime.csv`.
"""
    (RESULTS / "tracking_hot_path_runtime.md").write_text(markdown, encoding="utf-8")
    metadata = {
        "schema": "certigap-tracking-hot-path-v1",
        "horizons": list(HORIZONS),
        "native_repetitions": 7,
        "configurations": len(groups),
        "platform": platform.platform(),
        "compiler": subprocess.run(
            [compiler, "--version"], check=True, text=True, capture_output=True
        ).stdout.splitlines()[0],
        "compile_command": command,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "header_sha256": hashlib.sha256(
            (ROOT / "cpp" / "certigap_tracking.hpp").read_bytes()
        ).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    (RESULTS / "tracking_hot_path_runtime.metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(markdown)


if __name__ == "__main__":
    main()
