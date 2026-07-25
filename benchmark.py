from certigap import (
    beam_search_best,
    benchmark_case,
    certify_tree,
    frontier_dp_best,
    greedy_best,
    make_distribution,
)


def main() -> None:
    cases = [
        ("uniform", 16, 3, 0.15),
        ("zipf", 16, 3, 0.15),
        ("hot_middle", 16, 3, 0.15),
        ("hot_tail", 16, 4, 0.30),
        ("zipf", 24, 5, 0.20),
    ]
    for kind, n, budget, eta in cases:
        summary = benchmark_case(kind, n, budget, eta)
        print(
            f"{kind:>10} n={n:2d} B={budget} eta={eta:.2f} "
            f"exact={summary['exact_objective']:.4f} "
            f"greedy={summary['greedy_objective']:.4f} "
            f"beam={summary['beam_objective']:.4f} "
            f"balanced={summary['balanced_objective']:.4f} "
            f"weighted={summary['weighted_objective']:.4f} "
            f"greedy_gap={summary['greedy_gap_vs_exact']:.4f} "
            f"beam_gap={summary['beam_gap_vs_exact']:.4f}"
        )

    weights = make_distribution("hot_middle", 8)
    exact = frontier_dp_best(weights, budget=2, eta=0.15)
    certificate = certify_tree(exact["tree"], weights, budget=2, eta=0.15)
    greedy = greedy_best(weights, budget=2, eta=0.15)
    beam = beam_search_best(weights, budget=2, eta=0.15)
    print("\nCertificate sample:")
    print(certificate)
    print("\nGreedy sample:")
    print(greedy["serialized_tree"])
    print("\nBeam sample:")
    print(beam["serialized_tree"])


if __name__ == "__main__":
    main()
