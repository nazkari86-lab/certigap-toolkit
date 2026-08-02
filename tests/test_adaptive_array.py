from __future__ import annotations

import random
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from certigap import AdaptiveArray, AdaptiveArrayPolicy, AutoIndexConstraints


def policy(**overrides: object) -> AdaptiveArrayPolicy:
    values: dict[str, object] = {
        "warmup_operations": 16,
        "check_interval": 16,
        "minimum_relative_improvement": 0.01,
        "max_profile_operations": 64,
    }
    values.update(overrides)
    return AdaptiveArrayPolicy(**values)  # type: ignore[arg-type]


class AdaptiveArrayTests(unittest.TestCase):
    def test_range_workload_selects_prefix_sum_automatically(self) -> None:
        data = AdaptiveArray(range(32), policy=policy())
        for _ in range(16):
            self.assertEqual(data.range_sum(2, 30), sum(range(2, 30)))

        explanation = data.explain()
        self.assertEqual(data.selected_name, "prefix_sum")
        self.assertTrue(data.optimized)
        self.assertTrue(explanation["switched"])
        self.assertGreater(explanation["relative_improvement"], 0.9)
        self.assertIn("wall-clock", explanation["claim_boundary"])

    def test_mixed_workload_selects_fenwick_and_preserves_semantics(self) -> None:
        oracle = [float(value) for value in range(64)]
        data = AdaptiveArray(oracle, policy=policy(warmup_operations=32))
        for operation in range(32):
            if operation % 3 == 0:
                position = operation % len(oracle)
                oracle[position] = float(operation * 2)
                data.update(position, oracle[position])
            else:
                self.assertEqual(data.range_sum(2, 60), sum(oracle[2:60]))

        self.assertEqual(data.selected_name, "fenwick")
        rng = random.Random(20260802)
        for _ in range(100):
            position = rng.randrange(len(oracle))
            if rng.random() < 0.35:
                value = rng.uniform(-100.0, 100.0)
                oracle[position] = value
                data.update(position, value)
            elif rng.random() < 0.5:
                self.assertEqual(data.get(position), oracle[position])
            else:
                last = rng.randrange(position + 1, len(oracle) + 1)
                self.assertAlmostEqual(
                    data.range_sum(position, last),
                    sum(oracle[position:last]),
                )

    def test_deployment_threshold_fails_closed(self) -> None:
        data = AdaptiveArray(
            range(16),
            policy=policy(
                warmup_operations=8,
                check_interval=8,
                minimum_relative_improvement=2.0,
                max_profile_operations=32,
            ),
        )
        for _ in range(8):
            data.range_sum(0, 16)

        self.assertEqual(data.selected_name, "sorted_array")
        self.assertFalse(data.optimized)
        self.assertEqual(
            data.explain()["reason"],
            "candidate improvement below deployment threshold",
        )

    def test_explicit_maintenance_and_min_aggregate(self) -> None:
        data = AdaptiveArray(
            range(16),
            constraints=AutoIndexConstraints(aggregate="min"),
            policy=policy(
                warmup_operations=8,
                check_interval=8,
                max_profile_operations=32,
                automatic_maintenance=False,
            ),
        )
        for _ in range(8):
            self.assertEqual(data.range_query(1, 14), 1.0)
        self.assertFalse(data.optimized)
        self.assertTrue(data.maintenance())
        self.assertIn(data.selected_name, {"segment_tree", "sparse_table"})
        self.assertTrue(data.optimized)
        self.assertEqual(data.range_query(2, 7), 2.0)
        with self.assertRaisesRegex(RuntimeError, "aggregate='sum'"):
            data.range_sum(2, 7)

    def test_profile_round_trip_triggers_warm_start(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile_path = Path(directory) / "adaptive.profile"
            configured = policy(
                warmup_operations=8,
                check_interval=8,
                max_profile_operations=32,
                profile_path=profile_path,
            )
            with AdaptiveArray(range(16), policy=configured) as data:
                for _ in range(8):
                    data.range_sum(1, 15)

            restored = AdaptiveArray(range(16), policy=configured)
            self.assertTrue(
                profile_path.read_text(encoding="utf-8").startswith(
                    "CERTIGAP_PROFILE_V1\n"
                )
            )
            self.assertEqual(restored.profile_operations, 8)
            self.assertEqual(restored.lifetime_operations, 8)
            self.assertEqual(restored.selected_name, "prefix_sum")
            self.assertEqual(restored.range_sum(1, 15), sum(range(1, 15)))

    def test_duplicate_profile_records_are_accumulated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            profile_path = Path(directory) / "duplicate.profile"
            profile_path.write_text(
                "CERTIGAP_PROFILE_V1\n"
                "size 8\n"
                "aggregate sum\n"
                "range 1 8 3\n"
                "range 1 8 5\n"
                "end\n",
                encoding="utf-8",
            )
            restored = AdaptiveArray(
                range(8),
                policy=policy(
                    warmup_operations=8,
                    check_interval=8,
                    max_profile_operations=32,
                    profile_path=profile_path,
                ),
            )
            self.assertEqual(restored.profile_operations, 8)
            self.assertTrue(restored.optimized)
            self.assertNotEqual(restored.selected_name, "sorted_array")
            self.assertEqual(restored.range_sum(0, 8), sum(range(8)))

    def test_incompatible_profiles_fail_closed(self) -> None:
        profiles = (
            "CERTIGAP_PROFILE_V1\nsize 7\naggregate sum\nget 1 8\nend\n",
            "CERTIGAP_PROFILE_V1\nsize 8\naggregate sum\nget 1 1.5\nend\n",
        )
        with tempfile.TemporaryDirectory() as directory:
            profile_path = Path(directory) / "invalid.profile"
            for text in profiles:
                with self.subTest(profile=text):
                    profile_path.write_text(text, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        AdaptiveArray(
                            range(8),
                            policy=policy(
                                warmup_operations=8,
                                check_interval=8,
                                max_profile_operations=32,
                                profile_path=profile_path,
                            ),
                        )

    def test_profile_capacity_decays_without_losing_lifetime_count(self) -> None:
        data = AdaptiveArray(
            range(16),
            policy=policy(
                warmup_operations=8,
                check_interval=8,
                max_profile_operations=16,
                automatic_maintenance=False,
            ),
        )
        for operation in range(100):
            self.assertEqual(data.get(operation % 16), float(operation % 16))
        self.assertLessEqual(data.profile_operations, 16)
        self.assertEqual(data.lifetime_operations, 100)

    def test_concurrent_read_profile_is_consistent(self) -> None:
        data = AdaptiveArray(
            range(32),
            policy=policy(
                warmup_operations=10_000,
                check_interval=10_000,
                max_profile_operations=20_000,
            ),
        )

        def read(_: int) -> None:
            for _ in range(100):
                self.assertEqual(data.get(7), 7.0)
                self.assertEqual(data.range_sum(3, 11), sum(range(3, 11)))

        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(read, range(4)))
        self.assertEqual(data.lifetime_operations, 800)
        self.assertEqual(data.profile_operations, 800)

    def test_input_validation(self) -> None:
        for values in ([], [1.0, float("nan")]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                AdaptiveArray(values)

    def test_index_and_range_validation(self) -> None:
        data = AdaptiveArray(range(4))
        with self.assertRaises(IndexError):
            data.get(-1)
        with self.assertRaises(IndexError):
            data.update(4, 0.0)
        with self.assertRaises(IndexError):
            data.range_query(2, 2)
        with self.assertRaises(ValueError):
            data.update(0, float("inf"))


if __name__ == "__main__":
    unittest.main()
