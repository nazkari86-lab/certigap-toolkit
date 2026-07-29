from __future__ import annotations

import copy
import csv
import random
import subprocess
import unittest
from pathlib import Path

from certigap import (
    CertiRangeWorkload,
    DynamicCertiRange,
    DynamicRangeVerificationError,
    RangeOptimizerVerificationError,
    make_range_optimizer_artifact,
    range_aware_beam_search,
    verify_dynamic_range_certificate,
    score_range_workload,
    verify_range_optimizer_artifact,
)


class DynamicCertiRangeTests(unittest.TestCase):
    def test_cpp_contiguous_range_core_matches_all_checksums(self) -> None:
        root = Path(__file__).resolve().parents[1]
        binary = root / "build" / "certigap_dynamic_range_benchmark_test"
        subprocess.run(
            [
                "c++",
                "-std=c++17",
                "-O2",
                "cpp/dynamic_range_benchmark.cpp",
                "-o",
                str(binary),
            ],
            cwd=root,
            check=True,
        )
        output = subprocess.check_output(
            [str(binary), "200", "1"], cwd=root, text=True
        )
        rows = list(csv.DictReader(output.splitlines()))
        self.assertEqual(len(rows), 36)
        self.assertTrue(all(row["correct"] == "true" for row in rows))
        self.assertEqual(
            {row["method"] for row in rows},
            {"array", "fenwick", "segment_tree", "certirange"},
        )

    def test_range_optimizer_artifact_replays_and_rejects_tampering(self) -> None:
        workload = CertiRangeWorkload(16)
        workload.add_point(1, 200).add_range(1, 6, 500)
        ranges = [
            (left, right, count)
            for (left, right), count in workload.range_counts.items()
        ]
        result = range_aware_beam_search(
            point_counts=workload.point_counts,
            update_counts=workload.update_counts,
            range_counts=ranges,
            budget=3,
            max_depth=7,
        )
        artifact = make_range_optimizer_artifact(
            point_counts=workload.point_counts,
            update_counts=workload.update_counts,
            range_counts=ranges,
            max_depth=7,
            tail_weight=0.10,
            budget=3,
            result=result,
        )
        self.assertTrue(verify_range_optimizer_artifact(artifact)["verified"])
        tampered = copy.deepcopy(artifact)
        tampered["reported"]["objective"] += 1
        with self.assertRaises(RangeOptimizerVerificationError):
            verify_range_optimizer_artifact(tampered)
        malformed = copy.deepcopy(artifact)
        malformed["routing_tree"] = {
            "type": "split",
            "interval": [1, 16],
            "threshold": 1,
            "left": {
                "type": "split",
                "interval": [1, 1],
                "threshold": 1,
            },
            "right": {"type": "leaf", "interval": [2, 16]},
        }
        with self.assertRaises(RangeOptimizerVerificationError):
            verify_range_optimizer_artifact(malformed)

    def test_range_aware_search_improves_exact_training_trace_score(self) -> None:
        workload = CertiRangeWorkload(32)
        workload.add_range(1, 10, 1000).add_range(20, 27, 500)
        proxy = workload.compile(
            [0.0] * 32,
            budget=4,
            max_depth=8,
            routing="point_proxy",
        )
        aware = workload.compile(
            [0.0] * 32,
            budget=4,
            max_depth=8,
            routing="range_aware",
        )

        def training_score(model: DynamicCertiRange) -> float:
            tree = model.export_certificate()["routing_tree"]
            return score_range_workload(
                tree,
                point_counts=workload.point_counts,
                update_counts=workload.update_counts,
                range_counts=[
                    (left, right, count)
                    for (left, right), count in workload.range_counts.items()
                ],
                max_depth=8,
                tail_weight=0.15,
            ).objective

        self.assertLess(training_score(aware), training_score(proxy))
        self.assertEqual(
            aware.summary()["routing_label"], "range_aware_beam"
        )

    def test_workload_compiler_uses_points_ranges_and_updates(self) -> None:
        workload = CertiRangeWorkload(16)
        workload.add_point(1, 1000).add_range(1, 3, 200).add_update(2, 100)
        model = workload.compile(
            [0.0] * 16,
            budget=5,
            eta=0.05,
            max_depth=8,
        )
        self.assertLess(model.query_cost(1), model.query_cost(16))
        manifest = workload.manifest()
        self.assertEqual(len(manifest["sha256"]), 64)
        self.assertIn("routing-cost proxy", manifest["range_model"])

    def test_random_operations_match_array_oracle(self) -> None:
        rng = random.Random(20260730)
        for aggregate in ("sum", "min", "max"):
            values = [float(rng.randint(-50, 50)) for _ in range(31)]
            model = DynamicCertiRange().fit(
                values,
                weights=[40.0 if index < 4 else 1.0 for index in range(31)],
                budget=8,
                eta=0.2,
                aggregate=aggregate,
                max_depth=9,
            )
            for _ in range(250):
                if rng.random() < 0.35:
                    key = rng.randint(1, len(values))
                    value = float(rng.randint(-100, 100))
                    values[key - 1] = value
                    model.point_update(key, value)
                else:
                    left = rng.randint(1, len(values))
                    right = rng.randint(left, len(values))
                    observed = model.range_query(left, right, track=False)
                    selected = values[left - 1 : right]
                    expected = {
                        "sum": sum,
                        "min": min,
                        "max": max,
                    }[aggregate](selected)
                    self.assertAlmostEqual(observed, expected)
            for key, expected in enumerate(values, start=1):
                self.assertEqual(model.get(key, track=False), expected)

    def test_snapshot_isolation_after_persistent_update(self) -> None:
        model = DynamicCertiRange().fit(
            [1, 2, 3, 4], weights=[10, 1, 1, 1], budget=2
        )
        before = model.snapshot()
        model.point_update(2, 200)
        after = model.snapshot()
        self.assertEqual(before.range_query(1, 4), 10)
        self.assertEqual(before.get(2), 2)
        self.assertEqual(after.range_query(1, 4), 208)
        self.assertEqual(after.get(2), 200)
        self.assertEqual(before.data_version, 0)
        self.assertEqual(after.data_version, 1)

    def test_max_depth_cap_and_range_visit_bound_hold_exhaustively(self) -> None:
        n = 29
        model = DynamicCertiRange().fit(
            list(range(1, n + 1)),
            weights=[1000.0] + [1.0] * (n - 1),
            budget=20,
            eta=0.0,
            max_depth=6,
        )
        summary = model.summary()
        self.assertLessEqual(summary["height"], 6)
        for left in range(1, n + 1):
            for right in range(left, n + 1):
                expected = sum(range(left, right + 1))
                self.assertEqual(
                    model.range_query(left, right, track=False), expected
                )
                self.assertLessEqual(
                    model.summary()["last_range_node_visits"],
                    summary["range_node_visit_bound"],
                )

    def test_hot_keys_can_be_shallower_than_balanced_depth(self) -> None:
        n = 32
        model = DynamicCertiRange().fit(
            [0.0] * n,
            weights=[10_000.0] + [1.0] * (n - 1),
            budget=8,
            eta=0.05,
            max_depth=10,
        )
        self.assertLess(model.query_cost(1), 5)
        self.assertLess(
            model.summary()["mean_point_depth"],
            5.0,
        )

    def test_drift_controlled_rebuild_changes_structure_version(self) -> None:
        model = DynamicCertiRange().fit(
            [0.0] * 16,
            weights=[100.0] + [1.0] * 15,
            budget=5,
            drift_threshold=0.20,
            min_rebuild_observations=20,
        )
        before_cost = model.query_cost(16)
        for _ in range(19):
            model.observe(16)
        self.assertFalse(model.maybe_rebuild())
        model.observe(16)
        self.assertTrue(model.maybe_rebuild())
        self.assertEqual(model.summary()["structure_version"], 1)
        self.assertEqual(model.summary()["rebuild_count"], 1)
        self.assertLess(model.query_cost(16), before_cost)
        self.assertEqual(model.summary()["observed_drift"], 0.0)

    def test_range_queries_feed_endpoint_workload(self) -> None:
        model = DynamicCertiRange().fit(
            [1.0] * 8,
            weights=[1.0] * 8,
            budget=3,
            range_endpoint_weight=2.0,
        )
        model.range_query(2, 7)
        self.assertEqual(model.summary()["range_queries"], 1)
        self.assertGreater(model.summary()["observed_drift"], 0)

    def test_certificate_replays_and_rejects_tampering(self) -> None:
        model = DynamicCertiRange().fit(
            [5, -2, 7, 3, 9],
            weights=[1, 8, 2, 1, 1],
            budget=3,
            aggregate="max",
            max_depth=4,
        )
        model.point_update(2, 20)
        artifact = model.export_certificate()
        verified = verify_dynamic_range_certificate(artifact)
        self.assertTrue(verified["verified"])
        self.assertEqual(verified["root_aggregate"], 20)

        for mutate in (
            lambda item: item["values"].__setitem__(0, 999),
            lambda item: item["state"].__setitem__("height", 0),
            lambda item: item["complete_topology"].__setitem__("threshold", 1),
            lambda item: item["digests"].__setitem__(
                "topology_sha256", "0" * 64
            ),
        ):
            tampered = copy.deepcopy(artifact)
            mutate(tampered)
            with self.assertRaises(DynamicRangeVerificationError):
                verify_dynamic_range_certificate(tampered)

    def test_invalid_inputs_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            DynamicCertiRange().fit([], budget=0)
        with self.assertRaises(ValueError):
            DynamicCertiRange().fit([1, float("nan")], budget=0)
        with self.assertRaises(ValueError):
            DynamicCertiRange().fit([1, 2, 3], budget=1, max_depth=1)
        model = DynamicCertiRange().fit([1, 2, 3], budget=1)
        with self.assertRaises(ValueError):
            model.range_query(0, 2)
        with self.assertRaises(ValueError):
            model.point_update(4, 0)
        with self.assertRaises(ValueError):
            model.observe(1, 0)


if __name__ == "__main__":
    unittest.main()
