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
FIXED = {
    "sorted_array", "prefix_sum", "fenwick",
    "sqrt_decomposition", "segment_tree",
}
FAST = "tracking_native_fast_sampled"
HORIZONS = (5000, 50000)


def percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[round((len(ordered) - 1) * probability)]


def main() -> None:
    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("C++ compiler is unavailable")
    source = ROOT / "cpp" / "tracking_autoindex_benchmark.cpp"
    command: list[str]
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / "tracking_benchmark"
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
                if row["implementation"] in FIXED | {FAST}:
                    row["horizon"] = str(horizon)
                    rows.append(row)

    fields = [
        "horizon", "n", "workload", "implementation", "operations",
        "ns_per_operation", "switches", "checksum",
    ]
    csv_path = RESULTS / "tracking_autoindex_fast_runtime.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["horizon"], row["n"], row["workload"]), []).append(row)
    best_ratios: list[float] = []
    fenwick_ratios: list[float] = []
    checksums_match = True
    for group in groups.values():
        fast = next(row for row in group if row["implementation"] == FAST)
        fixed = [row for row in group if row["implementation"] in FIXED]
        fast_time = float(fast["ns_per_operation"])
        best_ratios.append(
            fast_time / min(float(row["ns_per_operation"]) for row in fixed)
        )
        fenwick = next(row for row in fixed if row["implementation"] == "fenwick")
        fenwick_ratios.append(fast_time / float(fenwick["ns_per_operation"]))
        expected = float(group[0]["checksum"])
        checksums_match &= all(
            math.isclose(expected, float(row["checksum"]), rel_tol=1e-12, abs_tol=1e-9)
            for row in group[1:]
        )

    markdown = f"""# Fast TrackingAutoIndex Runtime Benchmark

This benchmark covers 4 sizes, 8 stationary/adversarial workloads, and 2 stream
horizons. Every row is the median of five native C++ repetitions. Construction is
excluded; controller sampling, fallback, leases, and in-stream migrations are included.

## Results

- Correctness checksum agreement: `{checksums_match}` across all `{len(groups)}` configurations.
- Versus robust Fenwick: `{statistics.median(fenwick_ratios):.2f}x` median, `{percentile(fenwick_ratios, 0.95):.2f}x` p95, `{max(fenwick_ratios):.2f}x` maximum.
- Versus fastest fixed backend chosen with hindsight: `{statistics.median(best_ratios):.2f}x` median, `{percentile(best_ratios, 0.95):.2f}x` p95, `{max(best_ratios):.2f}x` maximum.

## Interpretation

The robust comparison answers the deployment question: overhead relative to a backend
that safely supports arbitrary future point updates and range sums. The hindsight
comparison is deliberately stricter and includes structures such as an O(1)-update
array on update-only streams, even though it may need O(n) for an unexpected range.
No causal online selector can know that the future will remain update-only. Fast mode
therefore keeps a current Fenwick shadow and immediately abandons a static specialized
view when an unsafe update arrives. It guarantees runtime semantics, not a universal
competitive latency factor.

Raw data: `tracking_autoindex_fast_runtime.csv`.
"""
    report_path = RESULTS / "tracking_autoindex_fast_runtime.md"
    report_path.write_text(markdown, encoding="utf-8")
    metadata = {
        "schema": "certigap-fast-tracking-benchmark-v1",
        "horizons": list(HORIZONS),
        "native_repetitions": 5,
        "configurations": len(groups),
        "platform": platform.platform(),
        "compiler": subprocess.run(
            [compiler, "--version"], check=True, text=True, capture_output=True
        ).stdout.splitlines()[0],
        "compile_command": command,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    (RESULTS / "tracking_autoindex_fast_runtime.metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(markdown)


if __name__ == "__main__":
    main()
