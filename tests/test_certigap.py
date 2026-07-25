import unittest

from certigap import (
    CertificateError,
    IntervalLeaf,
    SplitNode,
    baseline_balanced,
    beam_search_best,
    brute_force_best,
    combined_lower_bound,
    counterexample_search,
    certify_tree,
    frontier_dp_best,
    greedy_best,
    hot_block_distribution,
    make_distribution,
    normalize_weights,
    verify_certificate_artifact,
    verify_tree,
)


class CertiGapTests(unittest.TestCase):
    def test_frontier_matches_bruteforce_on_small_instance(self) -> None:
        weights = [0.05, 0.45, 0.30, 0.10, 0.10]
        exact = frontier_dp_best(weights, budget=2, eta=0.2)
        brute = brute_force_best(weights, budget=2, eta=0.2)
        self.assertAlmostEqual(exact["objective"], brute["objective"], places=9)
        self.assertAlmostEqual(exact["average_cost"], brute["average_cost"], places=9)
        self.assertEqual(exact["max_cost"], brute["max_cost"])

    def test_hot_distribution_beats_balanced_baseline(self) -> None:
        weights = make_distribution("hot_middle", 16)
        exact = frontier_dp_best(weights, budget=3, eta=0.15)
        baseline = baseline_balanced(weights, budget=3, eta=0.15)
        self.assertLess(exact["objective"], baseline["objective"])

    def test_certificate_accepts_valid_tree(self) -> None:
        weights = [0.1, 0.1, 0.35, 0.35, 0.05, 0.05]
        exact = frontier_dp_best(weights, budget=2, eta=0.1)
        certificate = certify_tree(exact["tree"], weights, budget=2, eta=0.1)
        self.assertEqual(certificate["budget"], 2)
        self.assertTrue(certificate["splits"])
        self.assertAlmostEqual(certificate["exact_gap"], 0.0, places=9)

    def test_certificate_rejects_invalid_partition(self) -> None:
        weights = [0.25, 0.25, 0.25, 0.25]
        bad_tree = SplitNode(
            left=1,
            right=4,
            threshold=2,
            left_child=IntervalLeaf(1, 2),
            right_child=IntervalLeaf(4, 4),
        )
        with self.assertRaises(CertificateError):
            certify_tree(bad_tree, weights, budget=1, eta=0.0)

    def test_combined_lower_bound_is_valid(self) -> None:
        weights = [0.05, 0.45, 0.30, 0.10, 0.10]
        exact = frontier_dp_best(weights, budget=2, eta=0.2)
        lower = combined_lower_bound(weights, budget=2, eta=0.2)
        self.assertLessEqual(lower["lower_bound"], exact["objective"] + 1e-9)

    def test_greedy_respects_budget_and_improves_leaf_only_tree(self) -> None:
        weights = make_distribution("hot_tail", 20)
        greedy = greedy_best(weights, budget=4, eta=0.25)
        leaf_only = frontier_dp_best(weights, budget=0, eta=0.25)
        self.assertLessEqual(greedy["split_count"], 4)
        self.assertLess(greedy["objective"], leaf_only["objective"])

    def test_beam_matches_exact_on_small_case(self) -> None:
        weights = [0.05, 0.45, 0.30, 0.10, 0.10]
        exact = frontier_dp_best(weights, budget=2, eta=0.2)
        beam = beam_search_best(weights, budget=2, eta=0.2, beam_width=8)
        self.assertAlmostEqual(beam["objective"], exact["objective"], places=9)

    def test_beam_dominates_greedy_on_multistep_case(self) -> None:
        weights = make_distribution("hot_middle", 16)
        greedy = greedy_best(weights, budget=3, eta=0.15)
        beam = beam_search_best(weights, budget=3, eta=0.15, beam_width=12)
        self.assertLessEqual(beam["objective"], greedy["objective"] + 1e-9)

    def test_normalize_weights(self) -> None:
        weights = normalize_weights([2, 3, 5])
        self.assertAlmostEqual(sum(weights), 1.0, places=9)

    def test_problem_validation_rejects_invalid_parameters(self) -> None:
        with self.assertRaises(ValueError):
            frontier_dp_best([0.5, -0.5], budget=1, eta=0.2)
        with self.assertRaises(ValueError):
            frontier_dp_best([0.5, 0.5], budget=-1, eta=0.2)
        with self.assertRaises(ValueError):
            frontier_dp_best([0.5, 0.5], budget=1, eta=1.1)

    def test_verifier_rejects_inconsistent_certificate_arithmetic(self) -> None:
        weights = [0.5, 0.5]
        tree = SplitNode(1, 2, 1, IntervalLeaf(1, 1), IntervalLeaf(2, 2))
        evaluation = verify_tree(tree, weights, budget=1, eta=0.0)
        with self.assertRaises(ValueError):
            verify_certificate_artifact(
                tree,
                weights,
                budget=1,
                eta=0.0,
                artifact={"upper_bound": evaluation["objective"], "lower_bound": evaluation["objective"] + 1.0, "certified_gap": 0.0},
            )

    def test_hot_block_distribution(self) -> None:
        weights = hot_block_distribution(8, start=3, width=2, hot_weight=10.0)
        self.assertAlmostEqual(sum(weights), 1.0, places=9)
        self.assertGreater(weights[2], weights[0])
        self.assertGreater(weights[3], weights[0])

    def test_counterexample_search_finds_positive_gap(self) -> None:
        findings = counterexample_search(
            n_values=(8,),
            budgets=(2, 3),
            etas=(0.0, 0.15),
            widths=(2, 3, 4),
            hot_weights=(8.0, 16.0),
        )
        self.assertTrue(findings)
        self.assertGreaterEqual(findings[0]["greedy_gap"], findings[0]["beam_gap"] - 1e-9)


if __name__ == "__main__":
    unittest.main()
