from __future__ import annotations

import csv
import json
import platform
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "cpp" / "dynamic_range_benchmark.cpp"
BINARY = ROOT / "build" / (
    "certigap_dynamic_range_benchmark.exe"
    if platform.system().lower() == "windows"
    else "certigap_dynamic_range_benchmark"
)
CSV_PATH = ROOT / "results" / "cpp_dynamic_range.csv"
MD_PATH = ROOT / "results" / "cpp_dynamic_range.md"
METADATA_PATH = ROOT / "results" / "cpp_dynamic_range_metadata.json"


def compile_benchmark() -> None:
    BINARY.parent.mkdir(exist_ok=True)
    subprocess.run(
        ["c++", "-std=c++17", "-O3", str(SOURCE), "-o", str(BINARY)],
        cwd=ROOT,
        check=True,
    )


def build_markdown(rows: list[dict[str, str]]) -> str:
    lines = [
        "# C++ Dynamic CertiRange benchmark",
        "",
        f"- Rows: `{len(rows)}`",
        "- Same deterministic mixed get/range-sum/update trace for every method.",
        "- Latency is post-build median and p95 across whole-batch per-operation means.",
        "- CertiRange uses contiguous nodes and a workload-shaped routing prefix.",
        "- This local microbenchmark is not independent-hardware evidence.",
        "",
        "| n | workload | fastest | CertiRange rank | CertiRange ns/op | fastest ns/op | hot depth vs balanced |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault((row["n"], row["workload"]), []).append(row)
    for (n, workload), group in sorted(
        grouped.items(), key=lambda item: (int(item[0][0]), item[0][1])
    ):
        ordered = sorted(group, key=lambda row: float(row["median_ns_per_operation"]))
        certirange = next(row for row in group if row["method"] == "certirange")
        rank = next(
            index
            for index, row in enumerate(ordered, start=1)
            if row["method"] == "certirange"
        )
        balanced_depth = next(
            int(row["height"]) for row in group if row["method"] == "segment_tree"
        )
        lines.append(
            f"| {n} | {workload} | {ordered[0]['method']} | {rank}/4 | "
            f"{float(certirange['median_ns_per_operation']):.1f} | "
            f"{float(ordered[0]['median_ns_per_operation']):.1f} | "
            f"{certirange['hot_key_depth']} vs {balanced_depth} |"
        )
    lines.extend(
        [
            "",
            "## Honest result",
            "",
            "Fenwick or an iterative segment tree wins raw range-sum throughput in this matrix. "
            "CertiRange reduces hot-key depth on skewed traces, but irregular routing and recursive "
            "range traversal currently outweigh that comparison saving. The result rejects a blanket "
            "speed claim and motivates portfolio selection rather than replacing classical structures.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    compile_benchmark()
    completed = subprocess.run(
        [str(BINARY), "200000", "7"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    CSV_PATH.write_text(completed.stdout, encoding="utf-8")
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 36 or any(row["correct"] != "true" for row in rows):
        raise RuntimeError("C++ dynamic range benchmark matrix is incomplete")
    MD_PATH.write_text(build_markdown(rows), encoding="utf-8")
    METADATA_PATH.write_text(
        json.dumps(
            {
                "schema": "certigap-cpp-dynamic-range-v1",
                "compiler": subprocess.check_output(
                    ["c++", "--version"], text=True
                ).splitlines()[0],
                "platform": platform.platform(),
                "operations_per_case": 200000,
                "repeats": 7,
                "measurement_scope": (
                    "post-build mixed operations; p95 across batch means"
                ),
                "workloads": [
                    "uniform_mixed",
                    "hotspot_point",
                    "clustered_range",
                ],
                "methods": [
                    "array",
                    "fenwick",
                    "segment_tree",
                    "certirange",
                ],
                "limitations": [
                    "single local machine",
                    "synthetic deterministic traces",
                    "sum aggregate only",
                    "no concurrent writers",
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} rows to {CSV_PATH}")


if __name__ == "__main__":
    main()
