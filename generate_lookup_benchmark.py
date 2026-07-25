"""Build and run the C++ post-build lookup microbenchmark."""
from __future__ import annotations

import argparse
import csv
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
SOURCE = ROOT / "cpp" / "lookup_benchmark.cpp"
BINARY = ROOT / "build" / "certigap_lookup_benchmark"


def run_command(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproduce CertiGap C++ lookup latency microbenchmarks.")
    parser.add_argument("--sizes", type=int, nargs="+", default=[1_000, 10_000])
    parser.add_argument("--queries", type=int, default=200_000)
    parser.add_argument("--repeats", type=int, default=7)
    args = parser.parse_args()
    if any(size < 2 for size in args.sizes) or args.queries < 1 or args.repeats < 1:
        raise SystemExit("sizes must be >= 2; queries and repeats must be positive")

    BINARY.parent.mkdir(exist_ok=True)
    run_command(["c++", "-std=c++17", "-O3", "-DNDEBUG", str(SOURCE), "-o", str(BINARY)])
    rows: list[dict[str, str]] = []
    for size in args.sizes:
        rows.extend(csv.DictReader(run_command([str(BINARY), str(size), str(args.queries), str(args.repeats)]).splitlines()))

    RESULTS.mkdir(exist_ok=True)
    fields = ["workload", "solver", "n", "queries", "repeats", "median_ns", "p95_ns", "routing_nodes", "routing_bytes"]
    with (RESULTS / "cpp_lookup_latency.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)

    lines = [
        "# C++ Post-Build Lookup Microbenchmark", "",
        "This measures only rank lookup after each structure is built. Times are local-machine measurements, not cross-machine or production claims.", "",
        "- Queries are sampled from each workload distribution with a deterministic PRNG.",
        "- CertiGap uses the candidate-pruned C++ beam (`B=min(6,n-1)`, `eta=0.15`, width 32, candidate limit 16).",
        "- A CertiGap leaf completes its contiguous interval with binary search; balanced and weighted-median trees have singleton leaves.",
        "- `routing_bytes` is reachable-node count times `sizeof(Node)`, excluding allocator and key-array overhead.", "",
        "| Workload | Solver | n | Median ns/query | p95 ns/query | Routing nodes | Routing bytes |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(f"| {row['workload']} | {row['solver']} | {row['n']} | {row['median_ns']} | {row['p95_ns']} | {row['routing_nodes']} | {row['routing_bytes']} |")
    lines.extend(["", "## Limits", "", "This is not a hardware-routing, cache-miss, or external-library benchmark. It is reproducible CPU-level evidence that the exported CertiGap decision tree executes real lookups with an explicit storage footprint. Production claims require a target key encoding, allocator, CPU, and independent external baselines."])
    (RESULTS / "cpp_lookup_latency.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote results/cpp_lookup_latency.csv and results/cpp_lookup_latency.md")


if __name__ == "__main__":
    main()
