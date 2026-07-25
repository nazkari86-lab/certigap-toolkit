import unittest

from generate_scaling_benchmark import resize


class ScalingBenchmarkTests(unittest.TestCase):
    def test_resize_preserves_probability_mass_and_order(self) -> None:
        resized = resize([0.1, 0.2, 0.3, 0.4], 2)
        self.assertAlmostEqual(sum(resized), 1.0)
        self.assertAlmostEqual(resized[0], 0.3)
        self.assertAlmostEqual(resized[1], 0.7)

    def test_resize_does_not_invent_observed_keys(self) -> None:
        with self.assertRaises(ValueError):
            resize([0.5, 0.5], 3)


if __name__ == "__main__":
    unittest.main()
