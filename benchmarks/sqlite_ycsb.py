from __future__ import annotations

import argparse
import csv
import json
import math
import random
import sqlite3
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from certigap import (
    HybridConstraints,
    PrefixBlockIndex,
    WorkloadTrace,
    compile_hybrid_index,
)


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


@dataclass(frozen=True)
class Operation:
    kind: str
    left: int
    right: int
    value: float


class Fenwick:
    def __init__(self, values: list[float]) -> None:
        self.values = list(values)
        self.tree = [0.0] * (len(values) + 1)
        for key, value in enumerate(values, 1):
            self._add(key, value)

    def _add(self, key: int, delta: float) -> None:
        while key < len(self.tree):
            self.tree[key] += delta
            key += key & -key

    def _prefix(self, key: int) -> float:
        result = 0.0
        while key:
            result += self.tree[key]
            key -= key & -key
        return result

    def get(self, key: int) -> float:
        return self.values[key - 1]

    def update(self, key: int, value: float) -> None:
        delta = value - self.values[key - 1]
        self.values[key - 1] = value
        self._add(key, delta)

    def range_sum(self, left: int, right: int) -> float:
        return self._prefix(right) - self._prefix(left - 1)


class SQLiteIndex:
    def __init__(self, values: list[float]) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA journal_mode=OFF")
        self.connection.execute("PRAGMA synchronous=OFF")
        self.connection.execute("PRAGMA temp_store=MEMORY")
        self.connection.execute(
            "CREATE TABLE kv (key INTEGER PRIMARY KEY, value REAL NOT NULL)"
        )
        self.connection.executemany(
            "INSERT INTO kv(key, value) VALUES (?, ?)",
            enumerate(values, 1),
        )
        self.connection.commit()
        self.connection.execute("BEGIN")

    def get(self, key: int) -> float:
        row = self.connection.execute(
            "SELECT value FROM kv WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            raise RuntimeError("SQLite key disappeared")
        return float(row[0])

    def update(self, key: int, value: float) -> None:
        self.connection.execute(
            "UPDATE kv SET value = ? WHERE key = ?", (value, key)
        )

    def range_sum(self, left: int, right: int) -> float:
        row = self.connection.execute(
            "SELECT SUM(value) FROM kv WHERE key BETWEEN ? AND ?",
            (left, right),
        ).fetchone()
        return float(row[0])

    def close(self) -> None:
        self.connection.rollback()
        self.connection.close()


class HybridAdapter:
    def __init__(self, values: list[float], boundaries: list[int]) -> None:
        self.index = PrefixBlockIndex(values, boundaries)

    def get(self, key: int) -> float:
        return self.index.get(key)

    def update(self, key: int, value: float) -> None:
        self.index.point_update(key, value)

    def range_sum(self, left: int, right: int) -> float:
        return self.index.range_query(left, right)


def _hot_key(generator: random.Random, n: int) -> int:
    width = max(1, n // 5)
    if generator.random() < 0.8:
        return generator.randint(1, width)
    return generator.randint(width + 1, n)


def make_operations(
    workload: str,
    n: int,
    count: int,
    seed: int,
) -> list[Operation]:
    generator = random.Random(seed)
    result = []
    for index in range(count):
        roll = generator.random()
        key = _hot_key(generator, n)
        value = float((index * 17 + key * 13) % 10_007)
        if workload == "A":
            kind = "get" if roll < 0.5 else "update"
        elif workload == "B":
            kind = "get" if roll < 0.95 else "update"
        elif workload == "C":
            kind = "get"
        elif workload == "F":
            kind = "get" if roll < 0.5 else "rmw"
        elif workload == "R":
            if roll < 0.70:
                kind = "range"
            elif roll < 0.95:
                kind = "get"
            else:
                kind = "update"
        else:
            raise ValueError(f"unknown workload {workload}")
        if kind == "range":
            width = generator.randint(1, max(2, n // 16))
            right = min(n, key + width - 1)
        else:
            right = key
        result.append(Operation(kind, key, right, value))
    return result


def training_trace(n: int, operations: list[Operation]) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for operation in operations:
        if operation.kind == "get":
            trace.add_get(operation.left)
        elif operation.kind == "range":
            trace.add_range(operation.left, operation.right)
        elif operation.kind == "update":
            trace.add_update(operation.left, operation.value)
        else:
            trace.add_get(operation.left)
            trace.add_update(operation.left, operation.value)
    return trace


def execute(
    backend: object,
    operations: list[Operation],
) -> float:
    checksum = 0.0
    for operation in operations:
        if operation.kind == "get":
            checksum += backend.get(operation.left)
        elif operation.kind == "range":
            checksum += backend.range_sum(operation.left, operation.right)
        elif operation.kind == "update":
            backend.update(operation.left, operation.value)
        else:
            current = backend.get(operation.left)
            checksum += current
            backend.update(operation.left, current + 1.0)
    return checksum


def bootstrap_median_interval(
    samples: list[float],
    seed: int,
    resamples: int = 2_000,
) -> tuple[float, float]:
    generator = random.Random(seed)
    medians = []
    for _ in range(resamples):
        draw = [generator.choice(samples) for _ in samples]
        medians.append(statistics.median(draw))
    medians.sort()
    return (
        medians[int(0.025 * (resamples - 1))],
        medians[int(0.975 * (resamples - 1))],
    )


def run(mode: str) -> tuple[list[dict], list[dict]]:
    n, operation_count, repeats = (
        (128, 1_000, 15) if mode == "quick" else (512, 5_000, 25)
    )
    values = [float((index * 7) % 101) for index in range(1, n + 1)]
    raw_rows: list[dict] = []
    summary_rows: list[dict] = []
    for workload_index, workload in enumerate(("A", "B", "C", "F", "R")):
        operations = make_operations(
            workload,
            n,
            operation_count,
            seed=20260730 + workload_index,
        )
        train = training_trace(n, operations[: min(800, len(operations))])
        hybrid = compile_hybrid_index(
            values,
            train,
            constraints=HybridConstraints(
                max_blocks=4 if n == 128 else 8,
                max_block_width=64 if n == 128 else 128,
            ),
        )
        boundaries = list(hybrid.selected_boundaries)
        factories: dict[str, Callable[[], object]] = {
            "sqlite_btree": lambda: SQLiteIndex(values),
            "fenwick": lambda: Fenwick(values),
            "certigap_h": lambda: HybridAdapter(values, boundaries),
        }
        expected_checksum: float | None = None
        for backend_index, (name, factory) in enumerate(factories.items()):
            samples = []
            build_samples = []
            for repeat in range(repeats):
                build_start = time.perf_counter_ns()
                backend = factory()
                build_ns = time.perf_counter_ns() - build_start
                start = time.perf_counter_ns()
                checksum = execute(backend, operations)
                elapsed = time.perf_counter_ns() - start
                if isinstance(backend, SQLiteIndex):
                    backend.close()
                if expected_checksum is None:
                    expected_checksum = checksum
                if not math.isclose(
                    checksum,
                    expected_checksum,
                    rel_tol=1e-12,
                    abs_tol=1e-7,
                ):
                    raise RuntimeError(
                        f"checksum mismatch for {workload}/{name}"
                    )
                ns_per_operation = elapsed / len(operations)
                samples.append(ns_per_operation)
                build_samples.append(float(build_ns))
                raw_rows.append(
                    {
                        "mode": mode,
                        "workload": workload,
                        "backend": name,
                        "n": n,
                        "operations": operation_count,
                        "repeat": repeat,
                        "ns_per_operation": f"{ns_per_operation:.6f}",
                        "build_ns": build_ns,
                        "checksum": f"{checksum:.6f}",
                        "blocks": (
                            len(boundaries) if name == "certigap_h" else 0
                        ),
                    }
                )
            lower, upper = bootstrap_median_interval(
                samples,
                seed=20260800 + workload_index * 10 + backend_index,
            )
            summary_rows.append(
                {
                    "mode": mode,
                    "workload": workload,
                    "backend": name,
                    "n": n,
                    "operations": operation_count,
                    "repeats": repeats,
                    "median_ns_per_operation": f"{statistics.median(samples):.6f}",
                    "p95_ns_per_operation": f"{sorted(samples)[math.ceil(0.95 * repeats) - 1]:.6f}",
                    "bootstrap_median_ci95_low": f"{lower:.6f}",
                    "bootstrap_median_ci95_high": f"{upper:.6f}",
                    "median_build_ns": f"{statistics.median(build_samples):.0f}",
                    "blocks": (
                        len(boundaries) if name == "certigap_h" else 0
                    ),
                }
            )
    return raw_rows, summary_rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("quick", "full"), default="quick")
    args = parser.parse_args()
    raw_rows, summary_rows = run(args.mode)
    RESULTS.mkdir(exist_ok=True)
    write_csv(RESULTS / "sqlite_ycsb_raw.csv", raw_rows)
    write_csv(RESULTS / "sqlite_ycsb_summary.csv", summary_rows)
    metadata = {
        "schema": "certigap-sqlite-ycsb-pilot-v1",
        "mode": args.mode,
        "sqlite_version": sqlite3.sqlite_version,
        "workloads": {
            "A": "50% get, 50% update",
            "B": "95% get, 5% update",
            "C": "100% get",
            "F": "50% get, 50% read-modify-write",
            "R": "70% range sum, 25% get, 5% update",
        },
        "limitations": [
            "YCSB-compatible operation mixes, not the official Java harness",
            "application-level Python integration, not a SQLite extension",
            "SQLite uses an in-memory primary-key table and one transaction",
            "single-machine timings are not portable",
            "CertiGap-H grammar is fixed before timed holdout execution",
        ],
    }
    (RESULTS / "sqlite_ycsb_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# SQLite and YCSB-Compatible Pilot",
        "",
        "This is a real SQLite execution pilot with YCSB-compatible A/B/C/F "
        "operation mixes plus a CertiGap-specific range workload. It is not "
        "the official Java YCSB harness and not a SQLite extension.",
        "",
        "| Workload | Backend | Median ns/op | 95% bootstrap CI | p95 |",
        "|---|---|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            f"| {row['workload']} | {row['backend']} | "
            f"{float(row['median_ns_per_operation']):.1f} | "
            f"[{float(row['bootstrap_median_ci95_low']):.1f}, "
            f"{float(row['bootstrap_median_ci95_high']):.1f}] | "
            f"{float(row['p95_ns_per_operation']):.1f} |"
        )
    (RESULTS / "sqlite_ycsb_pilot.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {len(raw_rows)} raw rows and {len(summary_rows)} summaries"
    )


if __name__ == "__main__":
    main()
