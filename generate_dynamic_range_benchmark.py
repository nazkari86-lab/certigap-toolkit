from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from certigap import CertiRangeWorkload, DynamicCertiRange


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
CSV_PATH = RESULTS / "dynamic_range_benchmark.csv"
MD_PATH = RESULTS / "dynamic_range_benchmark.md"
CERTIFICATE_PATH = RESULTS / "dynamic_range_certificate_example.json"


Operation = tuple[str, int, int | float]


class RangeIndex(Protocol):
    def get(self, key: int) -> float: ...

    def range_query(self, left: int, right: int) -> float: ...

    def point_update(self, key: int, value: float) -> None: ...


class ArrayIndex:
    def __init__(self, values: list[float]) -> None:
        self.values = list(values)

    def get(self, key: int) -> float:
        return self.values[key - 1]

    def range_query(self, left: int, right: int) -> float:
        return sum(self.values[left - 1 : right])

    def point_update(self, key: int, value: float) -> None:
        self.values[key - 1] = value


class FenwickIndex:
    def __init__(self, values: list[float]) -> None:
        self.values = list(values)
        self.tree = [0.0] * (len(values) + 1)
        for key, value in enumerate(values, start=1):
            self._add(key, value)

    def _add(self, key: int, delta: float) -> None:
        while key < len(self.tree):
            self.tree[key] += delta
            key += key & -key

    def _prefix(self, key: int) -> float:
        result = 0.0
        while key > 0:
            result += self.tree[key]
            key -= key & -key
        return result

    def get(self, key: int) -> float:
        return self._prefix(key) - self._prefix(key - 1)

    def range_query(self, left: int, right: int) -> float:
        return self._prefix(right) - self._prefix(left - 1)

    def point_update(self, key: int, value: float) -> None:
        delta = value - self.values[key - 1]
        self.values[key - 1] = value
        self._add(key, delta)


class SegmentTreeIndex:
    def __init__(self, values: list[float]) -> None:
        size = 1
        while size < len(values):
            size *= 2
        self.n = len(values)
        self.size = size
        self.tree = [0.0] * (2 * size)
        self.tree[size : size + len(values)] = values
        for index in range(size - 1, 0, -1):
            self.tree[index] = self.tree[2 * index] + self.tree[2 * index + 1]

    def get(self, key: int) -> float:
        return self.tree[self.size + key - 1]

    def range_query(self, left: int, right: int) -> float:
        left = self.size + left - 1
        right = self.size + right
        result = 0.0
        while left < right:
            if left & 1:
                result += self.tree[left]
                left += 1
            if right & 1:
                right -= 1
                result += self.tree[right]
            left //= 2
            right //= 2
        return result

    def point_update(self, key: int, value: float) -> None:
        index = self.size + key - 1
        self.tree[index] = value
        index //= 2
        while index:
            self.tree[index] = self.tree[2 * index] + self.tree[2 * index + 1]
            index //= 2


@dataclass
class BuiltIndex:
    index: RangeIndex
    build_ms: float
    metadata: dict[str, float | int | str]


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, math.ceil(probability * len(ordered)) - 1)]


def _trace(
    n: int, workload: str, operation_count: int, seed: int
) -> list[Operation]:
    rng = random.Random(seed)
    operations: list[Operation] = []
    hot_width = max(2, n // 10)
    for step in range(operation_count):
        draw = rng.random()
        if workload == "uniform_mixed":
            if draw < 0.20:
                key = rng.randint(1, n)
                operations.append(("update", key, float((step * 17) % 101)))
            elif draw < 0.45:
                operations.append(("get", rng.randint(1, n), 0))
            else:
                left = rng.randint(1, n)
                right = rng.randint(left, min(n, left + rng.randint(0, max(1, n // 4))))
                operations.append(("range", left, right))
        elif workload == "hotspot_point":
            if draw < 0.10:
                key = rng.randint(1, n)
                operations.append(("update", key, float((step * 19) % 97)))
            elif draw < 0.85:
                key = (
                    rng.randint(1, hot_width)
                    if rng.random() < 0.90
                    else rng.randint(1, n)
                )
                operations.append(("get", key, 0))
            else:
                left = rng.randint(1, hot_width)
                right = rng.randint(left, min(n, left + hot_width))
                operations.append(("range", left, right))
        elif workload == "clustered_range":
            center = n // 2
            if draw < 0.15:
                key = rng.randint(max(1, center - hot_width), min(n, center + hot_width))
                operations.append(("update", key, float((step * 23) % 89)))
            elif draw < 0.25:
                operations.append(("get", rng.randint(1, n), 0))
            else:
                left = rng.randint(
                    max(1, center - 2 * hot_width), min(n, center + hot_width)
                )
                right = rng.randint(left, min(n, left + 2 * hot_width))
                operations.append(("range", left, right))
        else:
            raise ValueError(f"unknown workload: {workload}")
    return operations


def _workload_profile(n: int, operations: list[Operation]) -> CertiRangeWorkload:
    workload = CertiRangeWorkload(n)
    for operation, first, second in operations:
        if operation == "get":
            workload.add_point(first)
        elif operation == "range":
            workload.add_range(first, int(second))
        else:
            workload.add_update(first)
    return workload


def _build(
    method: str,
    values: list[float],
    operations: list[Operation],
    budget: int,
) -> BuiltIndex:
    started = time.perf_counter_ns()
    metadata: dict[str, float | int | str] = {}
    if method == "array":
        index: RangeIndex = ArrayIndex(values)
        metadata["estimated_numeric_slots"] = len(values)
    elif method == "fenwick":
        index = FenwickIndex(values)
        metadata["estimated_numeric_slots"] = 2 * len(values) + 1
    elif method == "segment_tree":
        index = SegmentTreeIndex(values)
        metadata["estimated_numeric_slots"] = len(index.tree)
    elif method == "certirange":
        profile = _workload_profile(len(values), operations)
        model = profile.compile(
            values,
            budget=budget,
            eta=0.10,
            solver="beam",
            aggregate="sum",
            max_depth=2 * math.ceil(math.log2(len(values))) + 1,
            min_rebuild_observations=64,
        )
        index = model
        summary = model.summary()
        metadata.update(
            {
                "height": summary["height"],
                "mean_point_depth": summary["mean_point_depth"],
                "hot_key_depth": model.query_cost(1),
                "estimated_numeric_slots": summary["node_count"] + len(values),
            }
        )
    else:
        raise ValueError(f"unknown method: {method}")
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return BuiltIndex(index=index, build_ms=elapsed_ms, metadata=metadata)


def _execute(index: RangeIndex, operations: list[Operation]) -> float:
    checksum = 0.0
    for operation, first, second in operations:
        if operation == "get":
            if isinstance(index, DynamicCertiRange):
                checksum += index.get(first, track=False)
            else:
                checksum += index.get(first)
        elif operation == "range":
            if isinstance(index, DynamicCertiRange):
                checksum += index.range_query(first, int(second), track=False)
            else:
                checksum += index.range_query(first, int(second))
        else:
            index.point_update(first, float(second))
    return checksum


def _reset_updates(
    index: RangeIndex, values: list[float], operations: list[Operation]
) -> None:
    for key in {
        first
        for operation, first, _ in operations
        if operation == "update"
    }:
        index.point_update(key, values[key - 1])


def _benchmark_case(
    n: int,
    workload: str,
    operation_count: int,
    repeats: int,
    budget: int,
) -> list[dict[str, object]]:
    values = [float((index * 13 + 7) % 101) for index in range(n)]
    operations = _trace(
        n, workload, operation_count, seed=20260730 + n * 17 + len(workload)
    )
    expected = _execute(ArrayIndex(values), operations)
    rows: list[dict[str, object]] = []
    for method in ("array", "fenwick", "segment_tree", "certirange"):
        built = _build(method, values, operations, budget)
        batch_times: list[float] = []
        metadata = built.metadata
        checksum = 0.0
        for _ in range(repeats):
            _reset_updates(built.index, values, operations)
            started = time.perf_counter_ns()
            checksum = _execute(built.index, operations)
            elapsed = time.perf_counter_ns() - started
            if abs(checksum - expected) > 1e-8:
                raise RuntimeError(
                    f"{method} failed checksum for {workload}, n={n}"
                )
            batch_times.append(elapsed / operation_count)
        rows.append(
            {
                "n": n,
                "workload": workload,
                "method": method,
                "operations": operation_count,
                "repeats": repeats,
                "budget": budget if method == "certirange" else "",
                "build_ms": f"{built.build_ms:.6f}",
                "median_ns_per_operation": f"{statistics.median(batch_times):.3f}",
                "p95_batch_ns_per_operation": f"{_percentile(batch_times, 0.95):.3f}",
                "checksum": f"{checksum:.6f}",
                "correct": True,
                "height": metadata.get("height", ""),
                "mean_point_depth": (
                    f"{float(metadata['mean_point_depth']):.6f}"
                    if "mean_point_depth" in metadata
                    else ""
                ),
                "hot_key_depth": metadata.get("hot_key_depth", ""),
                "estimated_numeric_slots": metadata["estimated_numeric_slots"],
            }
        )
    return rows


def _write_markdown(rows: list[dict[str, object]]) -> None:
    lines = [
        "# Dynamic CertiRange mixed-workload benchmark",
        "",
        f"- Rows: `{len(rows)}`",
        "- Operations: point get, range sum, and point update on identical deterministic traces.",
        "- Latency: median and p95 across whole-batch per-operation means; Python microbenchmark, not production C++ latency.",
        "- Build time: one untimed-for-operations construction; values are reset outside every measured repeat.",
        "- Memory: `estimated_numeric_slots` is an analytical storage proxy, not measured RSS.",
        "- Range endpoint frequencies are a routing heuristic and do not imply globally optimal range-query shape.",
        "",
        "| n | workload | fastest method | CertiRange rank | CertiRange ns/op | fastest ns/op |",
        "|---:|---|---|---:|---:|---:|",
    ]
    grouped: dict[tuple[int, str], list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault((int(row["n"]), str(row["workload"])), []).append(row)
    for (n, workload), group in sorted(grouped.items()):
        ordered = sorted(
            group, key=lambda row: float(row["median_ns_per_operation"])
        )
        certirange = next(row for row in group if row["method"] == "certirange")
        rank = next(
            index
            for index, row in enumerate(ordered, start=1)
            if row["method"] == "certirange"
        )
        lines.append(
            f"| {n} | {workload} | {ordered[0]['method']} | {rank}/4 | "
            f"{float(certirange['median_ns_per_operation']):.1f} | "
            f"{float(ordered[0]['median_ns_per_operation']):.1f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Fenwick and iterative segment trees are expected to win raw Python range-sum throughput. "
            "CertiRange's measured claim is different: it combines workload-shaped point paths, "
            "generic range aggregates, persistent snapshots, drift-aware rebuilding, and a replayable certificate.",
            "",
            "A production speed claim requires the same benchmark in the C++ core on independent hardware.",
        ]
    )
    MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("quick", "full"), default="full")
    args = parser.parse_args()
    if args.mode == "quick":
        sizes, operations, repeats = (128, 512), 800, 3
    else:
        sizes, operations, repeats = (128, 512, 2048), 2_500, 7
    rows: list[dict[str, object]] = []
    for n in sizes:
        budget = min(8, n - 1)
        for workload in (
            "uniform_mixed",
            "hotspot_point",
            "clustered_range",
        ):
            rows.extend(
                _benchmark_case(
                    n, workload, operations, repeats, budget
                )
            )
            print(f"dynamic range: n={n} workload={workload}")
    RESULTS.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    _write_markdown(rows)

    example_workload = CertiRangeWorkload(16)
    example_workload.add_point(1, 500).add_point(2, 200)
    example_workload.add_range(1, 4, 100).add_update(2, 20)
    example = example_workload.compile(
        list(range(1, 17)), budget=5, eta=0.10, max_depth=8
    )
    example.point_update(4, 100)
    CERTIFICATE_PATH.write_text(
        json.dumps(example.export_certificate(), indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} rows to {CSV_PATH}")


if __name__ == "__main__":
    main()
