from __future__ import annotations

import csv
from pathlib import Path

from certigap import benchmark_case, certify_tree, frontier_dp_best, make_distribution


ROOT = Path(__file__).resolve().parent
RESULTS_DIR = ROOT / "results"
CSV_PATH = RESULTS_DIR / "experiment_sweep.csv"
CERTIFICATE_MD_PATH = RESULTS_DIR / "certificate_examples.md"


def write_sweep() -> None:
    distributions = ["uniform", "zipf", "hot_middle", "hot_tail"]
    sizes = [8, 12, 16, 20, 24]
    budgets = [1, 2, 3, 4]
    etas = [0.0, 0.15, 0.30]

    fieldnames = [
        "distribution",
        "n",
        "budget",
        "eta",
        "exact",
        "greedy",
        "beam",
        "balanced",
        "weighted",
        "greedy_gap",
        "beam_gap",
    ]

    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for distribution in distributions:
            for n in sizes:
                for budget in budgets:
                    if budget >= n:
                        continue
                    for eta in etas:
                        result = benchmark_case(distribution, n, budget, eta, include_certificate=False)
                        writer.writerow(
                            {
                                "distribution": distribution,
                                "n": n,
                                "budget": budget,
                                "eta": f"{eta:.2f}",
                                "exact": f"{result['exact_objective']:.6f}",
                                "greedy": f"{result['greedy_objective']:.6f}",
                                "beam": f"{result['beam_objective']:.6f}",
                                "balanced": f"{result['balanced_objective']:.6f}",
                                "weighted": f"{result['weighted_objective']:.6f}",
                                "greedy_gap": f"{result['greedy_gap_vs_exact']:.6f}",
                                "beam_gap": f"{result['beam_gap_vs_exact']:.6f}",
                            }
                        )


def write_certificates() -> None:
    cases = [
        ("zipf", 8, 2, 0.15),
        ("hot_middle", 12, 3, 0.15),
        ("hot_tail", 16, 4, 0.30),
    ]
    lines = [
        "# CertiGap Certificate Examples",
        "",
    ]
    for distribution, n, budget, eta in cases:
        weights = make_distribution(distribution, n)
        exact = frontier_dp_best(weights, budget, eta)
        certificate = certify_tree(exact["tree"], weights, budget, eta)
        lines.extend(
            [
                f"## {distribution}, n={n}, B={budget}, eta={eta:.2f}",
                "",
                f"- Upper bound: `{certificate['upper_bound']:.6f}`",
                f"- Lower bound: `{certificate['lower_bound']:.6f}`",
                f"- Certified gap: `{certificate['certified_gap']:.6f}`",
                f"- Exact gap: `{certificate['exact_gap']:.6f}`",
                f"- Bound source: `{certificate['bound_source']}`",
                f"- Splits: `{certificate['splits']}`",
                "",
            ]
        )
    CERTIFICATE_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    write_sweep()
    write_certificates()
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {CERTIFICATE_MD_PATH}")


if __name__ == "__main__":
    main()
