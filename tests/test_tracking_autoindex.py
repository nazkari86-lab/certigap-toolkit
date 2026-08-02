from __future__ import annotations

import copy
import hashlib
import itertools
import json
import random
import unittest
from unittest import mock

from certigap import (
    AdaptiveSpec,
    TrackingAutoIndexVerificationError,
    TrackingPolicy,
    WorkloadTrace,
    start_tracking_autoindex,
    verify_tracking_autoindex_certificate,
)
from certigap.autoindex_verifier import verify_autoindex_artifact
from certigap.spec import compile_from_spec
from certigap.tracking_autoindex import TrackingAutoIndex


def redigest(artifact: dict) -> None:
    unsigned = copy.deepcopy(artifact)
    unsigned.pop("sha256", None)
    artifact["sha256"] = hashlib.sha256(
        json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def train_trace(n: int) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for key in range(1, n + 1):
        trace.add_get(key)
    return trace


class TrackingAutoIndexTests(unittest.TestCase):
    def test_runtime_switches_and_matches_array_oracle(self) -> None:
        n = 32
        values = [float(index) for index in range(n)]
        tracker = start_tracking_autoindex(
            values,
            train_trace(n),
            AdaptiveSpec(),
            policy=TrackingPolicy(migration_cost_units=2.0),
        )
        oracle = list(values)
        for _ in range(12):
            self.assertEqual(tracker.range_query(1, n), sum(oracle))
        for key in range(1, 9):
            value = float(-key)
            tracker.point_update(key, value)
            oracle[key - 1] = value
            self.assertEqual(tracker.get(key), value)
        certificate = tracker.export_certificate()
        verified = verify_tracking_autoindex_certificate(certificate)
        self.assertTrue(verified["verified"])
        self.assertGreater(tracker.switch_count, 0)
        self.assertEqual(certificate["steps"][-1]["selected"], tracker.selected_name)

    def test_exact_switch_limited_oracle_matches_brute_force(self) -> None:
        n = 8
        policy = TrackingPolicy(
            migration_cost_units=3.0,
            max_comparator_switches=1,
        )
        tracker = start_tracking_autoindex(
            range(n), train_trace(n), AdaptiveSpec(), policy=policy
        )
        tracker.range_query(1, n)
        tracker.point_update(2, 20.0)
        tracker.get(2)
        artifact = tracker.export_certificate()
        candidates = artifact["candidates"]
        rows = [step["service_costs"] for step in artifact["steps"]]
        best: tuple[float, list[str]] | None = None
        for path_tuple in itertools.product(candidates, repeat=len(rows)):
            previous = policy.initial_candidate
            switches = 0
            cost = 0.0
            for candidate, row in zip(path_tuple, rows, strict=True):
                if candidate != previous:
                    switches += 1
                    cost += policy.migration_cost_units
                cost += row[candidate]
                previous = candidate
            if switches <= policy.max_comparator_switches and (
                best is None or cost < best[0] - 1e-12
            ):
                best = (cost, list(path_tuple))
        assert best is not None
        self.assertAlmostEqual(artifact["constrained_oracle"]["cost"], best[0])
        self.assertEqual(artifact["constrained_oracle"]["path"], best[1])

    def test_decisions_are_prefix_causal(self) -> None:
        kwargs = {
            "values": range(16),
            "train_trace": train_trace(16),
            "spec": AdaptiveSpec(),
            "policy": TrackingPolicy(migration_cost_units=2.0),
        }
        first = start_tracking_autoindex(**kwargs)
        second = start_tracking_autoindex(**kwargs)
        for tracker in (first, second):
            tracker.range_query(1, 16)
            tracker.get(3)
        first_prefix = first.export_certificate()["steps"]
        second.point_update(3, 99.0)
        second.range_query(2, 14)
        self.assertEqual(first_prefix, second.export_certificate()["steps"][:2])

    def test_verifier_rejects_redigested_trajectory_tampering(self) -> None:
        tracker = start_tracking_autoindex(range(8), train_trace(8), AdaptiveSpec())
        tracker.range_query(1, 8)
        artifact = tracker.export_certificate()
        artifact["steps"][0]["service_cost"] += 1.0
        redigest(artifact)
        with self.assertRaisesRegex(
            TrackingAutoIndexVerificationError,
            "work-function replay mismatch",
        ):
            verify_tracking_autoindex_certificate(artifact)

    def test_verifier_rejects_unknown_fields_even_after_redigest(self) -> None:
        tracker = start_tracking_autoindex(range(8), train_trace(8), AdaptiveSpec())
        tracker.get(1)
        artifact = tracker.export_certificate()
        artifact["policy"]["future_hint"] = "range"
        redigest(artifact)
        with self.assertRaisesRegex(
            TrackingAutoIndexVerificationError,
            "policy fields mismatch",
        ):
            verify_tracking_autoindex_certificate(artifact)

    def test_policy_and_empty_history_fail_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "finite and positive"):
            start_tracking_autoindex(
                range(8),
                train_trace(8),
                AdaptiveSpec(),
                policy=TrackingPolicy(migration_cost_units=0.0),
            )
        tracker = start_tracking_autoindex(range(8), train_trace(8), AdaptiveSpec())
        with self.assertRaisesRegex(RuntimeError, "at least one operation"):
            tracker.export_certificate()

    def test_randomized_streams_match_all_aggregate_oracles(self) -> None:
        for aggregate in ("sum", "min", "max"):
            for seed in range(3):
                with self.subTest(aggregate=aggregate, seed=seed):
                    rng = random.Random(10_000 + seed)
                    n = 9 + seed
                    values = [float(rng.randint(-20, 20)) for _ in range(n)]
                    tracker = start_tracking_autoindex(
                        values,
                        train_trace(n),
                        AdaptiveSpec(aggregate=aggregate),
                        policy=TrackingPolicy(
                            migration_cost_units=1.0 + seed,
                            max_comparator_switches=seed,
                        ),
                    )
                    oracle = list(values)
                    for operation_index in range(48):
                        kind = rng.choice(("get", "range", "update"))
                        key = rng.randint(1, n)
                        if kind == "get":
                            self.assertEqual(tracker.get(key), oracle[key - 1])
                        elif kind == "update":
                            value = float(rng.randint(-50, 50))
                            tracker.point_update(key, value)
                            oracle[key - 1] = value
                        else:
                            right = rng.randint(key, n)
                            expected = {
                                "sum": sum,
                                "min": min,
                                "max": max,
                            }[aggregate](oracle[key - 1 : right])
                            self.assertEqual(tracker.range_query(key, right), expected)
                    artifact = tracker.export_certificate()
                    self.assertTrue(
                        verify_tracking_autoindex_certificate(artifact)["verified"]
                    )
                    self.assertAlmostEqual(
                        sum(step["migration_cost"] for step in artifact["steps"]),
                        tracker.switch_count
                        * artifact["policy"]["migration_cost_units"],
                    )

    def test_zero_switch_comparator_stays_on_initial_candidate(self) -> None:
        tracker = start_tracking_autoindex(
            range(16),
            train_trace(16),
            AdaptiveSpec(),
            policy=TrackingPolicy(
                migration_cost_units=0.5,
                max_comparator_switches=0,
            ),
        )
        for _ in range(20):
            tracker.range_query(1, 16)
        artifact = tracker.export_certificate()
        oracle = artifact["constrained_oracle"]
        self.assertEqual(oracle["switches"], 0)
        self.assertEqual(set(oracle["path"]), {"sorted_array"})

    def test_verifier_rejects_multiple_redigested_mutations(self) -> None:
        tracker = start_tracking_autoindex(range(8), train_trace(8), AdaptiveSpec())
        tracker.range_query(1, 8)
        tracker.point_update(3, 30.0)
        original = tracker.export_certificate()

        def mutate_candidate(artifact: dict) -> None:
            artifact["candidates"].reverse()

        def mutate_work(artifact: dict) -> None:
            artifact["steps"][0]["work_function"]["sorted_array"] += 1.0

        def mutate_oracle(artifact: dict) -> None:
            artifact["unrestricted_oracle"]["path"][0] = "segment_tree"

        def mutate_regret(artifact: dict) -> None:
            artifact["dynamic_regret"] += 1.0

        for mutation in (
            mutate_candidate,
            mutate_work,
            mutate_oracle,
            mutate_regret,
        ):
            with self.subTest(mutation=mutation.__name__):
                artifact = copy.deepcopy(original)
                mutation(artifact)
                redigest(artifact)
                with self.assertRaises(TrackingAutoIndexVerificationError):
                    verify_tracking_autoindex_certificate(artifact)

    def test_runtime_migrations_do_not_repeat_manifest_verification(self) -> None:
        n = 16
        spec = AdaptiveSpec()
        artifact = compile_from_spec(
            range(n), train_trace(n), spec
        ).export_selection_artifact()
        with mock.patch(
            "certigap.autoindex_verifier.verify_autoindex_artifact",
            wraps=verify_autoindex_artifact,
        ) as verifier:
            tracker = TrackingAutoIndex(
                [float(value) for value in range(n)],
                artifact,
                spec,
                TrackingPolicy(migration_cost_units=0.1),
            )
            for _ in range(12):
                tracker.range_query(1, n)
            for key in range(1, 9):
                tracker.point_update(key, float(-key))
        self.assertGreater(tracker.switch_count, 0)
        self.assertEqual(verifier.call_count, 1)


if __name__ == "__main__":
    unittest.main()
