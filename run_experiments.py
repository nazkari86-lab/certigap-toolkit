from certigap import benchmark_case


def main() -> None:
    distributions = ["uniform", "zipf", "hot_middle", "hot_tail"]
    sizes = [8, 12, 16, 20, 24]
    budgets = [1, 2, 3, 4]
    etas = [0.0, 0.15, 0.30]

    print(
        "distribution,n,budget,eta,exact,greedy,beam,balanced,weighted,greedy_gap,beam_gap"
    )
    for distribution in distributions:
        for n in sizes:
            for budget in budgets:
                if budget >= n:
                    continue
                for eta in etas:
                    result = benchmark_case(distribution, n, budget, eta, include_certificate=False)
                    print(
                        f"{distribution},{n},{budget},{eta:.2f},"
                        f"{result['exact_objective']:.6f},{result['greedy_objective']:.6f},"
                        f"{result['beam_objective']:.6f},{result['balanced_objective']:.6f},"
                        f"{result['weighted_objective']:.6f},{result['greedy_gap_vs_exact']:.6f},"
                        f"{result['beam_gap_vs_exact']:.6f}"
                    )


if __name__ == "__main__":
    main()
