from __future__ import annotations

import argparse
import csv
import random
import math
import statistics
import time
import tracemalloc
from pathlib import Path

from certigap import beam_search_best, greedy_best, normalize_weights


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "scaling_benchmark.csv"
SUMMARY_PATH = RESULTS_DIR / "scaling_benchmark.md"


PRESETS = {
    "quick": {"sizes": [32, 64, 128], "widths": [1, 4], "repeats": 2},
    "full": {"sizes": [32, 64, 128, 256, 512, 1024], "widths": [1, 2, 4, 8, 16, 32], "repeats": 5},
}


def distribution(kind: str, n: int, seed: int) -> list[float]:
    if kind == "dirichlet":
        rng = random.Random(seed)
        return normalize_weights([rng.expovariate(1.0) for _ in range(n)])
    if kind == "two_hot_blocks":
        weights = [1.0] * n
        width = max(2, n // 16)
        for start in (n // 4, 3 * n // 4):
            for index in range(start, min(n, start + width)):
                weights[index] = 20.0
        return normalize_weights(weights)
    from certigap import make_distribution
    return make_distribution(kind, n)


def measure(fn, weights: list[float], budget: int, eta: float, **kwargs) -> tuple[dict, float, float]:
    tracemalloc.start()
    start = time.perf_counter()
    result = fn(weights, budget, eta, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, elapsed_ms, peak / (1024.0 * 1024.0)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproducible CertiGap large-n scaling benchmark.")
    parser.add_argument("--mode", choices=tuple(PRESETS), default="quick")
    args = parser.parse_args()
    preset = PRESETS[args.mode]
    RESULTS_DIR.mkdir(exist_ok=True)
    fieldnames = ["distribution", "n", "budget", "eta", "solver", "beam_width", "median_ms", "p95_ms", "peak_memory_mb", "objective"]
    rows: list[dict] = []
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for n in preset["sizes"]:
            budget = min(6, n - 1)
            for kind in ("zipf", "hot_middle", "dirichlet", "two_hot_blocks"):
                weights = distribution(kind, n, seed=20260725 + n)
                for solver, fn, width in [("greedy", greedy_best, 0)] + [("beam", beam_search_best, w) for w in preset["widths"]]:
                    timings, memories, objective = [], [], None
                    for _ in range(preset["repeats"]):
                        kwargs = {} if solver == "greedy" else {"beam_width": width}
                        result, elapsed, memory = measure(fn, weights, budget, 0.15, **kwargs)
                        timings.append(elapsed)
                        memories.append(memory)
                        objective = result["objective"]
                    row = {
                        "distribution": kind,
                        "n": n,
                        "budget": budget,
                        "eta": 0.15,
                        "solver": solver,
                        "beam_width": width,
                        "median_ms": statistics.median(timings),
                        "p95_ms": sorted(timings)[min(len(timings) - 1, math.ceil(0.95 * len(timings)) - 1)],
                        "peak_memory_mb": max(memories),
                        "objective": objective,
                    }
                    rows.append(row)
                    writer.writerow(row)
    lines = ["# CertiGap Scaling Benchmark", "", f"Mode: `{args.mode}`. Exact solvers are intentionally excluded: this benchmark measures heuristic scaling, not exact quality.", ""]
    lines.extend(["| n | Solver | Width | Median ms | p95 ms | Peak MB |", "|---:|---|---:|---:|---:|---:|"])
    for n in preset["sizes"]:
        subset = [row for row in rows if row["n"] == n and row["distribution"] == "zipf"]
        for row in subset:
            lines.append(f"| {n} | {row['solver']} | {row['beam_width']} | {row['median_ms']:.3f} | {row['p95_ms']:.3f} | {row['peak_memory_mb']:.3f} |")
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
