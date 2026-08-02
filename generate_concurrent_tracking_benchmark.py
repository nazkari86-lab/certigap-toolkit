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
IMPLEMENTATIONS = {
    "direct_fenwick", "direct_prefix",
    "concurrent_fallback", "concurrent_snapshot",
    "concurrent_snapshot_session",
    "concurrent_snapshot_session_unchecked",
}
OPERATIONS = 500_000


def main() -> None:
    compiler = shutil.which("c++")
    if compiler is None:
        raise RuntimeError("C++ compiler is unavailable")
    source = ROOT / "cpp" / "concurrent_tracking_benchmark.cpp"
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / "concurrent_tracking_benchmark"
        command = [
            compiler, "-std=c++17", "-O3", "-DNDEBUG", "-march=native",
            "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-pthread",
            f"-I{ROOT / 'cpp'}", str(source), "-o", str(executable),
        ]
        subprocess.run(command, check=True, cwd=ROOT)
        completed = subprocess.run(
            [str(executable), str(OPERATIONS)], check=True, cwd=ROOT,
            text=True, capture_output=True,
        )
    rows = list(csv.DictReader(completed.stdout.splitlines()))
    fields = [
        "n", "scenario", "implementation", "threads", "operations",
        "ns_per_operation", "checksum", "atomics_lock_free",
    ]
    csv_path = RESULTS / "concurrent_tracking_runtime.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["n"], row["scenario"], row["threads"]), []).append(row)
    checksums_match = all(
        all(
            math.isclose(
                float(group[0]["checksum"]), float(row["checksum"]),
                rel_tol=1e-12, abs_tol=1e-9,
            )
            for row in group[1:]
        )
        for group in groups.values()
    )
    atomics_lock_free = {row["atomics_lock_free"] for row in rows} == {"true"}
    snapshot_vs_fallback = []
    snapshot_vs_prefix = []
    session_vs_prefix = []
    unchecked_session_vs_prefix = []
    for group in groups.values():
        keyed = {row["implementation"]: row for row in group}
        snapshot = float(keyed["concurrent_snapshot"]["ns_per_operation"])
        snapshot_vs_fallback.append(
            float(keyed["concurrent_fallback"]["ns_per_operation"]) / snapshot
        )
        snapshot_vs_prefix.append(
            snapshot / float(keyed["direct_prefix"]["ns_per_operation"])
        )
        session_vs_prefix.append(
            float(keyed["concurrent_snapshot_session"]["ns_per_operation"])
            / float(keyed["direct_prefix"]["ns_per_operation"])
        )
        unchecked_session_vs_prefix.append(
            float(keyed["concurrent_snapshot_session_unchecked"]["ns_per_operation"])
            / float(keyed["direct_prefix"]["ns_per_operation"])
        )
    markdown = f"""# Concurrent Tracking Runtime Benchmark

This benchmark compares the immutable Prefix snapshot, locked Fenwick fallback,
direct Fenwick, and direct Prefix paths for one and four reader threads. Every row
is the median of five repetitions over {OPERATIONS:,} deterministic operations; structure
construction and snapshot publication are excluded.

## Results

- Correctness checksum agreement: `{checksums_match}` across all `{len(groups)}` configurations.
- Pointer/reader-count atomics report lock-free on this platform: `{atomics_lock_free}`.
- Epoch snapshot speedup over locked fallback: `{min(snapshot_vs_fallback):.2f}x` to `{max(snapshot_vs_fallback):.2f}x`, `{statistics.median(snapshot_vs_fallback):.2f}x` median.
- Snapshot overhead versus direct Prefix: `{min(snapshot_vs_prefix):.2f}x` to `{max(snapshot_vs_prefix):.2f}x`, `{statistics.median(snapshot_vs_prefix):.2f}x` median.
- Batched snapshot-view overhead versus direct Prefix: `{min(session_vs_prefix):.2f}x` to `{max(session_vs_prefix):.2f}x`, `{statistics.median(session_vs_prefix):.2f}x` median.
- Unchecked batched-view overhead versus direct Prefix: `{min(unchecked_session_vs_prefix):.2f}x` to `{max(unchecked_session_vs_prefix):.2f}x`, `{statistics.median(unchecked_session_vs_prefix):.2f}x` median.

## Boundary

Individual snapshot reads use an atomic epoch entry/exit. A snapshot view amortizes
that pair across a caller-defined read batch. Fallback reads use a shared mutex and
point updates use its exclusive side. Results are machine-specific;
the benchmark does not establish wait-free progress, multi-writer scalability, or a
portable latency theorem.

Raw data: `concurrent_tracking_runtime.csv`.
"""
    (RESULTS / "concurrent_tracking_runtime.md").write_text(
        markdown, encoding="utf-8")
    metadata = {
        "schema": "certigap-concurrent-tracking-v1",
        "operations_per_configuration": OPERATIONS,
        "native_repetitions": 5,
        "configurations": len(groups),
        "atomics_lock_free": atomics_lock_free,
        "platform": platform.platform(),
        "compiler": subprocess.run(
            [compiler, "--version"], check=True, text=True, capture_output=True
        ).stdout.splitlines()[0],
        "compile_command": command,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "header_sha256": hashlib.sha256(
            (ROOT / "cpp" / "certigap_concurrent.hpp").read_bytes()
        ).hexdigest(),
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    }
    (RESULTS / "concurrent_tracking_runtime.metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(markdown)


if __name__ == "__main__":
    main()
