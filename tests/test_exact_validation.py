import random
import unittest

from certigap import brute_force_best, frontier_dp_best, normalize_weights


class ExactValidationTests(unittest.TestCase):
    def test_frontier_matches_bruteforce_across_small_random_family(self) -> None:
        rng = random.Random(20260725)
        for n in range(2, 8):
            for budget in range(min(3, n - 1) + 1):
                for eta in (0.0, 0.1, 0.5, 1.0):
                    for _ in range(4):
                        weights = normalize_weights([rng.randint(0, 9) for _ in range(n - 1)] + [1])
                        exact = frontier_dp_best(weights, budget, eta)
                        brute = brute_force_best(weights, budget, eta)
                        self.assertAlmostEqual(exact["objective"], brute["objective"], places=9)
                        self.assertEqual(exact["max_cost"], brute["max_cost"])

    def test_mirror_symmetry_preserves_exact_objective(self) -> None:
        weights = normalize_weights([1, 3, 0, 8, 2, 5, 1])
        for budget in range(4):
            for eta in (0.0, 0.3, 1.0):
                forward = frontier_dp_best(weights, budget, eta)
                mirrored = frontier_dp_best(list(reversed(weights)), budget, eta)
                self.assertAlmostEqual(forward["objective"], mirrored["objective"], places=9)
