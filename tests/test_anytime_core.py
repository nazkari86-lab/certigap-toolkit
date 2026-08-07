from __future__ import annotations

import copy
import unittest

from certigap import (
    AnytimeCoreVerificationError,
    anytime_branch_and_bound,
    frontier_dp_best,
    verify_anytime_core_certificate,
)


class AnytimeCoreTests(unittest.TestCase):
    def test_early_certificate_contains_the_exact_oracle(self) -> None:
        weights = [1, 7, 2, 11, 3, 5]
        result = anytime_branch_and_bound(
            weights, budget=3, eta=0.15, max_expansions=4
        )
        exact = frontier_dp_best(weights, budget=3, eta=0.15)
        verified = verify_anytime_core_certificate(result["certificate"])
        self.assertTrue(verified["verified"])
        self.assertLessEqual(result["lower_bound"], exact["objective"] + 1e-9)
        self.assertLessEqual(exact["objective"], result["upper_bound"] + 1e-9)
        self.assertAlmostEqual(
            result["upper_bound"] - result["lower_bound"],
            result["absolute_gap"],
            places=9,
        )

    def test_sufficient_search_limit_certifies_exactness(self) -> None:
        weights = [1, 7, 2, 11, 3, 5]
        result = anytime_branch_and_bound(
            weights, budget=3, eta=0.15, max_expansions=100_000
        )
        exact = frontier_dp_best(weights, budget=3, eta=0.15)
        self.assertTrue(result["exact"])
        self.assertAlmostEqual(result["objective"], exact["objective"], places=9)
        self.assertAlmostEqual(result["absolute_gap"], 0.0, places=8)

    def test_more_search_cannot_widen_the_certified_interval(self) -> None:
        weights = [1, 7, 2, 11, 3, 5]
        early = anytime_branch_and_bound(
            weights, budget=3, eta=0.15, max_expansions=2
        )
        later = anytime_branch_and_bound(
            weights, budget=3, eta=0.15, max_expansions=12
        )
        self.assertLessEqual(later["absolute_gap"], early["absolute_gap"] + 1e-9)

    def test_verifier_rejects_tampered_interval(self) -> None:
        result = anytime_branch_and_bound(
            [1, 7, 2, 11, 3, 5], budget=3, eta=0.15, max_expansions=4
        )
        artifact = copy.deepcopy(result["certificate"])
        artifact["lower_bound"] += 0.25
        with self.assertRaises(AnytimeCoreVerificationError):
            verify_anytime_core_certificate(artifact)


if __name__ == "__main__":
    unittest.main()
