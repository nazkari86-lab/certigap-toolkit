import unittest

from certigap import (
    expectation_shift_bound,
    online_regret_certificate,
    total_variation_distance,
)


class OnlineCertificateTests(unittest.TestCase):
    def test_expectation_shift_bound_contains_observed_shift(self) -> None:
        reference = [0.7, 0.2, 0.1]
        current = [0.1, 0.2, 0.7]
        costs = [1.0, 3.0, 5.0]
        certificate = expectation_shift_bound(reference, current, costs)
        observed = abs(
            sum(p * c for p, c in zip(reference, costs))
            - sum(p * c for p, c in zip(current, costs))
        )
        self.assertLessEqual(
            observed,
            certificate["expectation_shift_upper_bound"] + 1e-9,
        )
        self.assertAlmostEqual(certificate["tv_drift"], 0.6)

    def test_online_regret_bound_increases_with_drift_and_horizon(self) -> None:
        reference = [0.8, 0.1, 0.1]
        near = [0.7, 0.2, 0.1]
        far = [0.1, 0.1, 0.8]
        near_certificate = online_regret_certificate(
            reference,
            near,
            budget=2,
            optimization_gap=0.05,
            horizon_queries=10,
            rebuild_cost=100.0,
        )
        far_certificate = online_regret_certificate(
            reference,
            far,
            budget=2,
            optimization_gap=0.05,
            horizon_queries=1_000,
            rebuild_cost=100.0,
        )
        self.assertLess(
            near_certificate.per_query_regret_upper_bound,
            far_certificate.per_query_regret_upper_bound,
        )
        self.assertFalse(near_certificate.rebuild_recommended)
        self.assertTrue(far_certificate.rebuild_recommended)

    def test_tv_distance_normalizes_counts(self) -> None:
        self.assertAlmostEqual(
            total_variation_distance([8, 2], [4, 6]),
            0.4,
        )


if __name__ == "__main__":
    unittest.main()
