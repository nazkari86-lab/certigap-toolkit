"""Build and run the C++ post-build lookup microbenchmark."""
from __future__ import annotations

import argparse
import csv
import json
import platform
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
    parser.add_argument("--repeats", type=int, default=31)
    args = parser.parse_args()
    if any(size < 2 for size in args.sizes) or args.queries < 1 or args.repeats < 1:
        raise SystemExit("sizes must be >= 2; queries and repeats must be positive")

    BINARY.parent.mkdir(exist_ok=True)
    run_command(["c++", "-std=c++17", "-O3", "-DNDEBUG", str(SOURCE), "-o", str(BINARY)])
    rows: list[dict[str, str]] = []
    for size in args.sizes:
        rows.extend(csv.DictReader(run_command([str(BINARY), str(size), str(args.queries), str(args.repeats)]).splitlines()))

    RESULTS.mkdir(exist_ok=True)
    fields = [
        "workload", "solver", "n", "budget", "queries", "repeats", "fallback",
        "median_batch_ns_per_query", "p95_batch_ns_per_query", "routing_nodes",
        "auxiliary_bytes", "total_index_bytes",
    ]
    with (RESULTS / "cpp_lookup_latency.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    lines = [
        "# C++ Post-Build Lookup Microbenchmark", "",
        "This measures only rank lookup after each structure is built. Times are local-machine measurements, not cross-machine or production claims.", "",
        "- Queries are sampled from each workload distribution with a deterministic PRNG.",
        "- CertiGap uses the candidate-pruned C++ beam (`B=min(6,n-1)`, `eta=0.15`, width 32, candidate limit 16).",
        "- CertiGap and budgeted trees use at most `B=min(6,n-1)` materialized splits and fixed-round interval fallback.",
        "- `balanced_full_reference` and `std_lower_bound` are explicitly unconstrained references, not equal-budget competitors.",
        "- Reported p95 is across repeated batch means; it is not single-query tail latency.",
        "- Total index bytes include the shared integer key array; auxiliary bytes exclude allocator overhead.", "",
        "| Workload | Solver | n | B | Median batch ns/query | p95 batch ns/query | Nodes | Auxiliary bytes | Total bytes |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['workload']} | {row['solver']} | {row['n']} | {row['budget']} | "
            f"{row['median_batch_ns_per_query']} | {row['p95_batch_ns_per_query']} | "
            f"{row['routing_nodes']} | {row['auxiliary_bytes']} | {row['total_index_bytes']} |"
        )
    matched_cases = {(row["workload"], row["n"]) for row in rows}
    certigap_by_case = {
        (row["workload"], row["n"]): float(row["median_batch_ns_per_query"])
        for row in rows if row["solver"] == "certigap_pruned"
    }
    lines.extend(["", "## Matched-Budget Interpretation", ""])
    for baseline in ("balanced_budgeted", "weighted_budgeted"):
        baseline_by_case = {
            (row["workload"], row["n"]): float(row["median_batch_ns_per_query"])
            for row in rows if row["solver"] == baseline
        }
        wins = sum(
            certigap_by_case[case] < baseline_by_case[case]
            for case in matched_cases
        )
        lines.append(
            f"- CertiGap has lower median batch lookup time than `{baseline}` "
            f"in `{wins}/{len(matched_cases)}` measured workload-size cases."
        )
    lines.extend(["", "## Limits", "", "This is not a hardware-routing, cache-miss, or external-library benchmark. It is reproducible CPU-level evidence that the exported CertiGap decision tree executes real lookups with an explicit storage footprint. Production claims require a target key encoding, allocator, CPU, and independent external baselines."])
    (RESULTS / "cpp_lookup_latency.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    metadata = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "compiler": run_command(["c++", "--version"]).splitlines()[0],
        "command": {
            "sizes": args.sizes,
            "queries_per_batch": args.queries,
            "batch_repeats": args.repeats,
        },
        "measurement_scope": "post-build lookup; p95 across batch means",
    }
    (RESULTS / "cpp_lookup_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Wrote results/cpp_lookup_latency.csv and results/cpp_lookup_latency.md")


if __name__ == "__main__":
    main()
