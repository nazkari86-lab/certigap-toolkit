import csv
import subprocess
import unittest
from fractions import Fraction
from functools import lru_cache
from itertools import product
from pathlib import Path

from certigap import (
    IntervalLeaf,
    SplitNode,
    evaluate_tree_with_fallback,
    frontier_dp_best,
    generalized_frontier_dp_best,
    midpoint_binary_profile,
    normalize_weights,
    verify_serialized_tree_exact,
)


ROOT = Path(__file__).resolve().parents[1]


class GeneralizedModelTests(unittest.TestCase):
    def test_fixed_rounds_generalization_matches_original_dp(self) -> None:
        cases = [
            ([1, 2, 3], 1, 0.0),
            ([1, 7, 2, 4, 9], 2, 0.15),
            ([0, 1, 0, 8, 2, 1], 3, 0.5),
        ]
        for weights, budget, eta in cases:
            original = frontier_dp_best(weights, budget, eta)
            generalized = generalized_frontier_dp_best(weights, budget, eta, fallback="fixed_rounds")
            self.assertAlmostEqual(original["objective"], generalized["objective"], places=9)
            self.assertEqual(original["max_cost"], generalized["max_cost"])

    def test_midpoint_binary_profile_is_exact_per_key(self) -> None:
        self.assertEqual(midpoint_binary_profile(1, 3), (2, 2, 1))
        result = generalized_frontier_dp_best([1, 1, 8], budget=0, eta=0.0)
        self.assertEqual(result["per_key_costs"], [2, 2, 1])
        self.assertAlmostEqual(result["average_cost"], 1.2)

    def test_midpoint_generalized_dp_matches_independent_enumeration(self) -> None:
        weights = normalize_weights([1, 5, 2, 8])

        @lru_cache(maxsize=None)
        def trees(left: int, right: int, budget: int):
            candidates = [IntervalLeaf(left, right)]
            if budget > 0 and left < right:
                for threshold in range(left, right):
                    for left_budget in range(budget):
                        right_budget = budget - 1 - left_budget
                        for left_tree, right_tree in product(
                            trees(left, threshold, left_budget),
                            trees(threshold + 1, right, right_budget),
                        ):
                            candidates.append(
                                SplitNode(left, right, threshold, left_tree, right_tree)
                            )
            return tuple(candidates)

        exact = generalized_frontier_dp_best(
            weights, budget=2, eta=0.2, fallback="midpoint_binary"
        )
        brute = min((
            evaluate_tree_with_fallback(tree, weights, 0.2, "midpoint_binary")
            for tree in trees(1, len(weights), 2)
        ), key=lambda result: result["objective"])
        self.assertAlmostEqual(exact["objective"], brute["objective"], places=9)

    def test_exact_verifier_matches_float_evaluation(self) -> None:
        result = frontier_dp_best([1, 4, 2, 7], budget=2, eta=0.25)
        exact = verify_serialized_tree_exact(
            result["serialized_tree"],
            [1, 4, 2, 7],
            budget=2,
            eta=Fraction(1, 4),
        )
        self.assertEqual(float(exact["objective"]), result["objective"])
        self.assertEqual(exact["per_key_costs"], tuple(result["per_key_costs"]))

    def test_exact_verifier_rejects_wrong_parent_interval(self) -> None:
        with self.assertRaises(ValueError):
            verify_serialized_tree_exact(
                {"type": "leaf", "interval": [1, 2]},
                [1, 1, 1],
                budget=0,
            )

    def test_generalized_evaluator_rejects_malformed_child_interval(self) -> None:
        malformed = SplitNode(
            1,
            3,
            1,
            IntervalLeaf(1, 2),
            IntervalLeaf(2, 3),
        )
        with self.assertRaisesRegex(ValueError, "interval disagrees"):
            evaluate_tree_with_fallback(malformed, [2, 3, 5], eta=0.25)

    def test_generalized_solver_rejects_fractional_fallback_cost(self) -> None:
        def fractional(left: int, right: int) -> tuple[float, ...]:
            return (0.5,) * (right - left + 1)

        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            generalized_frontier_dp_best([1, 2, 3], 1, 0.25, fractional)

    def test_cpp_lookup_benchmark_reports_matched_budget_schema(self) -> None:
        binary = ROOT / "build" / "certigap_lookup_benchmark_test"
        binary.parent.mkdir(exist_ok=True)
        subprocess.run(
            ["c++", "-std=c++17", "-O2", "cpp/lookup_benchmark.cpp", "-o", str(binary)],
            cwd=ROOT,
            check=True,
        )
        output = subprocess.check_output([str(binary), "64", "1000", "3"], cwd=ROOT, text=True)
        rows = list(csv.DictReader(output.splitlines()))
        self.assertEqual(len(rows), 15)
        for row in rows:
            self.assertIn("total_index_bytes", row)
            if row["solver"] in {"certigap_pruned", "balanced_budgeted", "weighted_budgeted"}:
                self.assertEqual(row["budget"], "6")
                self.assertLessEqual(int(row["routing_nodes"]), 13)
