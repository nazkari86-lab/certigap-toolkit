import random
import unittest

from certigap import branch_and_bound_exact, brute_force_best, cost_cap_dp_best, frontier_dp_best, normalize_weights, verify_branch_and_bound_certificate


class ExactValidationTests(unittest.TestCase):
    def test_frontier_matches_bruteforce_across_small_random_family(self) -> None:
        rng = random.Random(20260725)
        for n in range(2, 8):
            for budget in range(min(3, n - 1) + 1):
                for eta in (0.0, 0.1, 0.5, 1.0):
                    for _ in range(4):
                        weights = normalize_weights([rng.randint(0, 9) for _ in range(n - 1)] + [1])
                        exact = frontier_dp_best(weights, budget, eta)
                        cost_cap = cost_cap_dp_best(weights, budget, eta)
                        brute = brute_force_best(weights, budget, eta)
                        self.assertAlmostEqual(exact["objective"], brute["objective"], places=9)
                        self.assertAlmostEqual(cost_cap["objective"], brute["objective"], places=9)
                        self.assertEqual(exact["max_cost"], brute["max_cost"])

    def test_mirror_symmetry_preserves_exact_objective(self) -> None:
        weights = normalize_weights([1, 3, 0, 8, 2, 5, 1])
        for budget in range(4):
            for eta in (0.0, 0.3, 1.0):
                forward = frontier_dp_best(weights, budget, eta)
                mirrored = frontier_dp_best(list(reversed(weights)), budget, eta)
                self.assertAlmostEqual(forward["objective"], mirrored["objective"], places=9)

    def test_branch_and_bound_produces_verifiable_exact_trace(self) -> None:
        weights = normalize_weights([1, 4, 2, 7, 3, 1])
        frontier = frontier_dp_best(weights, budget=2, eta=0.15)
        branch_and_bound = branch_and_bound_exact(weights, budget=2, eta=0.15)
        self.assertAlmostEqual(branch_and_bound["objective"], frontier["objective"], places=9)
        proof = verify_branch_and_bound_certificate(weights, 2, 0.15, branch_and_bound["certificate"])
        self.assertGreater(proof["visited_nodes"], 0)

    def test_branch_and_bound_matches_frontier_on_multiple_shapes(self) -> None:
        cases = [
            ([1, 1, 1, 1], 2, 0.0),
            ([2, 1, 5, 1, 2], 2, 0.0),
            ([1, 4, 2, 7, 3, 1], 3, 0.3),
        ]
        for raw_weights, budget, eta in cases:
            weights = normalize_weights(raw_weights)
            branch_and_bound = branch_and_bound_exact(weights, budget, eta)
            frontier = frontier_dp_best(weights, budget, eta)
            self.assertAlmostEqual(branch_and_bound["objective"], frontier["objective"], places=9)
