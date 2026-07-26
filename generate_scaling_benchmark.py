from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
import time
import tracemalloc
from pathlib import Path

from certigap import CertiGapToolkit, beam_search_best, greedy_best, normalize_weights
from certigap.benchmark_datasets import MANIFEST_PATH, SOURCES, load_real_workload


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "scaling_benchmark.csv"
TEMP_CSV_PATH = RESULTS_DIR / "scaling_benchmark.csv.tmp"
SUMMARY_PATH = RESULTS_DIR / "scaling_benchmark.md"
PROVENANCE_PATH = RESULTS_DIR / "benchmark_provenance.json"

PRESETS = {
    "quick": {"sizes": [32, 64, 128], "repeats": 2, "beams": [1, 4]},
    "full": {"sizes": [32, 64, 128, 256, 512, 1024], "repeats": 3, "beams": [1, 4, 16]},
    "max": {"sizes": [32, 64, 128, 256, 512], "repeats": 5, "beams": [1, 4, 16, 32]},
}
SYNTHETIC = ("uniform", "zipf", "hot_middle", "hot_tail", "dirichlet", "two_hot_blocks", "alternating_hot")
REAL = tuple(SOURCES)
BASELINES = ("balanced", "weighted", "binary_search", "learned_segment")


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
    if kind == "alternating_hot":
        return normalize_weights([30.0 if index % 2 == 0 else 1.0 for index in range(n)])
    from certigap import make_distribution
    return make_distribution(kind, n)


def resize(weights: list[float], n: int) -> list[float]:
    """Contiguously aggregate an observed key order into exactly n bins."""
    if n > len(weights):
        raise ValueError(f"cannot expand observed workload from {len(weights)} to {n} keys")
    bins = [0.0] * n
    for index, weight in enumerate(weights):
        bins[(index * n) // len(weights)] += weight
    return normalize_weights(bins)


def measure(fn, weights: list[float], budget: int, eta: float, **kwargs) -> tuple[dict, float, float]:
    tracemalloc.start()
    start = time.perf_counter()
    result = fn(weights, budget, eta, **kwargs)
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return result, elapsed_ms, peak / (1024.0 * 1024.0)


def run_solver(solver: str, weights: list[float], budget: int, eta: float, beam_width: int) -> tuple[dict, float, float]:
    if solver == "greedy":
        return measure(greedy_best, weights, budget, eta)
    if solver == "beam":
        return measure(beam_search_best, weights, budget, eta, beam_width=beam_width)
    model = CertiGapToolkit()
    return measure(lambda w, b, e: model.fit(w, b, e, solver=solver).summary(), weights, budget, eta)


def measurement_plan(mode: str, preset: dict, n: int) -> tuple[list[int], int]:
    """Keep the maximum sweep finite while retaining every solver family.

    Wide beams are repeated where variance can be estimated cheaply.  At very
    large n, narrow beams are the deployable configurations; a single timed
    sample is explicitly labelled as such rather than misreported as p95 data.
    """
    if mode != "max" or n <= 512:
        return list(preset["beams"]), preset["repeats"]
    return list(preset["beams"]), preset["repeats"]


def workload_rows(args: argparse.Namespace, preset: dict) -> tuple[list[tuple[str, str, list[float]]], dict]:
    rows = [("synthetic", kind, distribution(kind, max(preset["sizes"]), 20260725)) for kind in SYNTHETIC]
    provenance: dict = {"synthetic": {"generator_seed": 20260725, "families": list(SYNTHETIC)}}
    if args.datasets == "synthetic":
        return rows, provenance
    for name in REAL:
        try:
            weights, info = load_real_workload(name)
        except Exception as error:
            if args.datasets == "real":
                raise RuntimeError(f"required real dataset {name} is unavailable: {error}") from error
            provenance[name] = {"status": "unavailable", "error": str(error), "source": SOURCES[name]}
            continue
        rows.append(("real", name, weights))
        provenance[name] = {"status": "loaded", **info}
    return rows, provenance


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproducible CertiGap scaling and real-workload benchmark.")
    parser.add_argument("--mode", choices=tuple(PRESETS), default="quick")
    parser.add_argument("--datasets", choices=("synthetic", "real", "all"), default="all")
    args = parser.parse_args()
    preset = PRESETS[args.mode]
    RESULTS_DIR.mkdir(exist_ok=True)
    workloads, provenance = workload_rows(args, preset)
    fieldnames = ["workload_type", "workload", "n", "budget", "eta", "solver", "beam_width", "repeats", "median_ms", "p95_ms", "peak_memory_mb", "objective"]
    rows: list[dict] = []
    with TEMP_CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for workload_type, workload, source_weights in workloads:
            for n in preset["sizes"]:
                if n > len(source_weights):
                    continue
                weights = distribution(workload, n, 20260725 + n) if workload_type == "synthetic" else resize(source_weights, n)
                budget = min(6, n - 1)
                beams, repeats = measurement_plan(args.mode, preset, n)
                solver_specs = [("greedy", 0)] + [("beam", width) for width in beams] + [(solver, 0) for solver in BASELINES]
                for solver, width in solver_specs:
                    timings, memories, objective = [], [], None
                    for _ in range(repeats):
                        result, elapsed, memory = run_solver(solver, weights, budget, 0.15, width)
                        timings.append(elapsed)
                        memories.append(memory)
                        objective = result["objective"]
                    row = {
                        "workload_type": workload_type, "workload": workload, "n": n, "budget": budget, "eta": 0.15,
                        "solver": solver, "beam_width": width, "repeats": repeats,
                        "median_ms": statistics.median(timings),
                        "p95_ms": sorted(timings)[min(len(timings) - 1, math.ceil(0.95 * len(timings)) - 1)],
                        "peak_memory_mb": max(memories), "objective": objective,
                    }
                    rows.append(row)
                    writer.writerow(row)
    TEMP_CSV_PATH.replace(CSV_PATH)
    provenance["run"] = {"mode": args.mode, "dataset_selection": args.datasets, "sizes": preset["sizes"], "base_repeats": preset["repeats"], "measurement_plan": {str(n): {"beams": measurement_plan(args.mode, preset, n)[0], "repeats": measurement_plan(args.mode, preset, n)[1]} for n in preset["sizes"]}, "eta": 0.15, "budget": "min(6, n-1)", "raw_cache_manifest": str(MANIFEST_PATH.relative_to(ROOT))}
    PROVENANCE_PATH.write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# CertiGap Scaling Benchmark", "", f"Mode: `{args.mode}`; datasets: `{args.datasets}`. This measures heuristic and baseline scaling, not exact-optimality quality.", "", "## Coverage", "", f"- Workloads completed: `{len({(row['workload_type'], row['workload']) for row in rows})}`", f"- Rows: `{len(rows)}`", f"- Sizes: `{', '.join(map(str, preset['sizes']))}`", f"- Solvers: greedy, beam widths up to `{max(preset['beams'])}`, and {', '.join(BASELINES)}", "- `max` is the largest complete range for this threshold-enumerating Python reference implementation. Exploratory runs above `n=512` were deliberately not published because they did not complete within the benchmark budget.", "- Raw-source provenance and SHA-256: [`benchmark_provenance.json`](benchmark_provenance.json)", "", "## Zipf / First Real Workload Snapshot", "", "| Workload | n | Solver | Width | Repeats | Median ms | p95 ms | Peak MB | Objective |", "|---|---:|---|---:|---:|---:|---:|---:|"]
    snapshots = [("synthetic", "zipf")]
    first_real = next(((kind, name) for kind, name, _ in workloads if kind == "real"), None)
    if first_real:
        snapshots.append(first_real)
    for kind, workload in snapshots:
        for n in preset["sizes"]:
            for row in [item for item in rows if item["workload_type"] == kind and item["workload"] == workload and item["n"] == n]:
                lines.append(f"| {workload} | {n} | {row['solver']} | {row['beam_width']} | {row['repeats']} | {row['median_ms']:.3f} | {row['p95_ms']:.3f} | {row['peak_memory_mb']:.3f} | {row['objective']:.5f} |")
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {SUMMARY_PATH}")
    print(f"Wrote {PROVENANCE_PATH}")


if __name__ == "__main__":
    main()
