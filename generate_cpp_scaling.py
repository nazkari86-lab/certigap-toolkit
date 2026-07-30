from __future__ import annotations

import csv
import statistics
import time
from pathlib import Path

from certigap import (
    CppCertiGap,
    make_distribution,
    verify_pruned_beam_certificate,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def main() -> None:
    core = CppCertiGap()
    rows: list[dict] = []
    for n in (1_000, 10_000, 100_000):
        for distribution in ("zipf", "hot_middle", "uniform"):
            weights = make_distribution(distribution, n)
            timings = []
            result = None
            for _ in range(3):
                start = time.perf_counter()
                result = core.pruned_beam(weights, budget=6, eta=0.15, beam_width=16, candidate_limit=32)
                timings.append((time.perf_counter() - start) * 1000)
            verification = verify_pruned_beam_certificate(weights, result)
            rows.append(
                {
                    "distribution": distribution,
                    "n": n,
                    "budget": 6,
                    "eta": 0.15,
                    "beam_width": 16,
                    "candidate_limit": 32,
                    "repeats": 3,
                    "median_ms": statistics.median(timings),
                    "objective": result["objective"],
                    "lower_bound": result["lower_bound"],
                    "absolute_gap": result["absolute_gap"],
                    "relative_gap_to_upper": result[
                        "relative_gap_to_upper"
                    ],
                    "certificate_verified": verification["verified"],
                }
            )
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "cpp_pruned_scaling.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    lines = [
        "# C++ Pruned-Beam Scaling",
        "",
        "This measures the candidate-pruned C++ heuristic, not an exact solver. "
        "It exports a feasible tree and an independently replayed "
        "information-theoretic lower bound. The gap is instance-specific and "
        "is not an approximation ratio.",
        "",
        "| Distribution | n | Median ms | Upper | Lower | Gap / upper |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    lines += [
        f"| {row['distribution']} | {row['n']} | "
        f"{row['median_ms']:.3f} | {row['objective']:.6f} | "
        f"{row['lower_bound']:.6f} | "
        f"{row['relative_gap_to_upper']:.2%} |"
        for row in rows
    ]
    (RESULTS / "cpp_pruned_scaling.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("Wrote C++ pruned-beam scaling artifacts")


if __name__ == "__main__":
    main()
