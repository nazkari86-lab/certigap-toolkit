from __future__ import annotations

import copy
import hashlib
import json
import random
import unittest

from certigap import (
    AutoIndexConstraints,
    AutoIndexVerificationError,
    WorkloadTrace,
    compile_autoindex,
    verify_autoindex_artifact,
)


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


class AutoIndexTests(unittest.TestCase):
    def test_chronological_split_preserves_order(self) -> None:
        trace = WorkloadTrace(8)
        for key in range(1, 9):
            trace.add_get(key)
        train, holdout = trace.chronological_split(0.75)
        self.assertEqual([op.left for op in train.operations], list(range(1, 7)))
        self.assertEqual([op.left for op in holdout.operations], [7, 8])

    def test_static_sum_range_workload_selects_prefix_sum(self) -> None:
        trace = WorkloadTrace(32)
        for _ in range(100):
            trace.add_range(3, 30)
        model = compile_autoindex(
            range(32),
            trace,
            constraints=AutoIndexConstraints(aggregate="sum", budget=4),
        )
        self.assertEqual(model.selected_name, "prefix_sum")
        self.assertEqual(model.range_query(3, 30), sum(range(2, 30)))

    def test_calibration_can_select_fenwick(self) -> None:
        trace = WorkloadTrace(32)
        for _ in range(100):
            trace.add_range(3, 30)
        model = compile_autoindex(
            range(32),
            trace,
            constraints=AutoIndexConstraints(
                aggregate="sum",
                budget=4,
                prefix_unit_cost=10.0,
            ),
        )
        self.assertEqual(model.selected_name, "fenwick")

    def test_non_power_of_two_mixed_trace_selects_fenwick(self) -> None:
        trace = WorkloadTrace(24)
        for _ in range(10):
            trace.add_range(2, 23)
        for index in range(5):
            trace.add_update(1 + (index * 7) % 24, float(index))
        model = compile_autoindex(range(24), trace)
        self.assertEqual(model.selected_name, "fenwick")

    def test_backend_calibration_can_change_selection(self) -> None:
        trace = WorkloadTrace(32)
        for _ in range(100):
            trace.add_range(3, 30)
        model = compile_autoindex(
            range(32),
            trace,
            constraints=AutoIndexConstraints(
                aggregate="sum",
                budget=4,
                segment_tree_unit_cost=0.1,
            ),
        )
        self.assertEqual(model.selected_name, "segment_tree")

    def test_sqrt_decomposition_is_executable(self) -> None:
        trace = WorkloadTrace(36)
        for _ in range(80):
            trace.add_range(4, 31)
        model = compile_autoindex(
            range(36, 0, -1),
            trace,
            constraints=AutoIndexConstraints(
                aggregate="min",
                sqrt_unit_cost=0.1,
                sparse_unit_cost=10.0,
            ),
        )
        self.assertEqual(model.selected_name, "sqrt_decomposition")
        self.assertEqual(model.range_query(4, 31), 6)
        model.point_update(31, 100)
        self.assertEqual(model.range_query(4, 31), 7)

    def test_memory_budget_can_select_sqrt_decomposition(self) -> None:
        trace = WorkloadTrace(36)
        for _ in range(80):
            trace.add_range(4, 31)
        model = compile_autoindex(
            range(36),
            trace,
            constraints=AutoIndexConstraints(memory_limit_slots=42),
        )
        self.assertEqual(model.selected_name, "sqrt_decomposition")

    def test_sparse_table_wins_static_idempotent_ranges(self) -> None:
        trace = WorkloadTrace(32)
        for _ in range(100):
            trace.add_range(3, 30)
        model = compile_autoindex(
            range(32, 0, -1),
            trace,
            constraints=AutoIndexConstraints(aggregate="min"),
        )
        self.assertEqual(model.selected_name, "sparse_table")
        self.assertEqual(model.range_query(3, 30), 3)
        model.point_update(30, 100)
        self.assertEqual(model.range_query(3, 30), 4)

    def test_min_workload_rejects_fenwick_and_executes(self) -> None:
        trace = WorkloadTrace(16)
        for _ in range(20):
            trace.add_range(2, 15)
        model = compile_autoindex(
            list(range(16, 0, -1)),
            trace,
            constraints=AutoIndexConstraints(aggregate="min", budget=3),
        )
        artifact = model.export_selection_artifact()
        fenwick = next(
            row for row in artifact["candidates"] if row["name"] == "fenwick"
        )
        self.assertFalse(fenwick["feasible"])
        self.assertIn("sum only", fenwick["reason"])
        self.assertEqual(model.range_query(2, 15), 2)

    def test_snapshot_requirement_selects_certirange(self) -> None:
        trace = WorkloadTrace(16)
        for _ in range(40):
            trace.add_range(1, 6)
        model = compile_autoindex(
            range(1, 17),
            trace,
            constraints=AutoIndexConstraints(
                aggregate="sum",
                budget=4,
                require_persistent_snapshots=True,
            ),
        )
        self.assertTrue(model.selected_name.startswith("certirange"))
        before = model.snapshot()
        model.point_update(2, 200)
        self.assertEqual(before.get(2), 2)
        self.assertEqual(model.get(2), 200)

    def test_holdout_never_changes_training_selection(self) -> None:
        train = WorkloadTrace(16)
        holdout_a = WorkloadTrace(16)
        holdout_b = WorkloadTrace(16)
        for _ in range(100):
            train.add_range(1, 16)
            holdout_a.add_get(1)
            holdout_b.add_range(2, 15)
        constraints = AutoIndexConstraints(aggregate="sum", budget=3)
        selected_a = compile_autoindex(
            range(16), train, constraints=constraints, holdout_trace=holdout_a
        )
        selected_b = compile_autoindex(
            range(16), train, constraints=constraints, holdout_trace=holdout_b
        )
        self.assertEqual(selected_a.selected_name, selected_b.selected_name)
        self.assertNotEqual(
            selected_a.summary()["holdout_score"],
            selected_b.summary()["holdout_score"],
        )

    def test_runtime_matches_array_oracle_under_random_operations(self) -> None:
        rng = random.Random(130)
        trace = WorkloadTrace(31)
        for _ in range(120):
            left = rng.randint(1, 31)
            trace.add_range(left, rng.randint(left, 31))
        model = compile_autoindex(
            [float(index) for index in range(31)],
            trace,
            constraints=AutoIndexConstraints(aggregate="sum", budget=5),
        )
        oracle = [float(index) for index in range(31)]
        for _ in range(300):
            if rng.random() < 0.35:
                key = rng.randint(1, 31)
                value = float(rng.randint(-100, 100))
                oracle[key - 1] = value
                model.point_update(key, value)
            else:
                left = rng.randint(1, 31)
                right = rng.randint(left, 31)
                self.assertAlmostEqual(
                    model.range_query(left, right),
                    sum(oracle[left - 1 : right]),
                )

    def test_verifier_detects_omitted_candidate_even_after_redigest(self) -> None:
        trace = WorkloadTrace(12)
        for _ in range(20):
            trace.add_range(1, 8)
        artifact = compile_autoindex(
            range(12), trace
        ).export_selection_artifact()
        artifact["candidates"] = artifact["candidates"][:-1]
        redigest(artifact)
        with self.assertRaises(AutoIndexVerificationError):
            verify_autoindex_artifact(artifact)

    def test_verifier_detects_rewritten_winner_and_holdout(self) -> None:
        train = WorkloadTrace(10)
        holdout = WorkloadTrace(10)
        for _ in range(20):
            train.add_range(1, 10)
            holdout.add_get(10)
        artifact = compile_autoindex(
            range(10), train, holdout_trace=holdout
        ).export_selection_artifact()
        artifact["selected"] = "sorted_array"
        artifact["candidates"][0]["holdout"]["score"] += 1
        redigest(artifact)
        with self.assertRaises(AutoIndexVerificationError):
            verify_autoindex_artifact(artifact)

    def test_impossible_constraints_fail(self) -> None:
        trace = WorkloadTrace(8).add_get(1)
        with self.assertRaisesRegex(ValueError, "no portfolio candidate"):
            compile_autoindex(
                range(8),
                trace,
                constraints=AutoIndexConstraints(
                    require_persistent_snapshots=True,
                    memory_limit_slots=8,
                ),
            )

    def test_public_input_validation(self) -> None:
        trace = WorkloadTrace(4).add_get(1)
        with self.assertRaises(TypeError):
            compile_autoindex(range(4), object())  # type: ignore[arg-type]
        model = compile_autoindex(range(4), trace)
        with self.assertRaises(ValueError):
            model.get(0)
        with self.assertRaises(ValueError):
            model.range_query(3, 2)
        with self.assertRaises(ValueError):
            model.point_update(1, float("nan"))


if __name__ == "__main__":
    unittest.main()
