from __future__ import annotations

import unittest

from certigap import AdaptiveSpec, WorkloadTrace, compile_from_spec


class AdaptiveSpecTests(unittest.TestCase):
    def test_contract_compiles_declared_workload(self) -> None:
        trace = WorkloadTrace(32)
        for _ in range(32):
            trace.add_range(2, 30)
        spec = AdaptiveSpec(
            operations=("range",),
            memory_limit_slots=100,
        )

        compiled = compile_from_spec(range(32), trace, spec)

        self.assertEqual(compiled.selected_name, "prefix_sum")
        self.assertEqual(compiled.range_query(2, 30), sum(range(1, 30)))
        self.assertEqual(spec.to_dict()["fixed_size"], True)

    def test_undeclared_operation_fails_before_compilation(self) -> None:
        trace = WorkloadTrace(8).add_range(1, 8).add_update(2, 10.0)
        with self.assertRaisesRegex(ValueError, "undeclared operations: update"):
            compile_from_spec(
                range(8),
                trace,
                AdaptiveSpec(operations=("range",)),
            )

    def test_snapshot_contract_filters_portfolio(self) -> None:
        trace = WorkloadTrace(16)
        for _ in range(16):
            trace.add_get(1)
        compiled = compile_from_spec(
            range(16),
            trace,
            AdaptiveSpec(
                operations=("get",),
                require_persistent_snapshots=True,
            ),
        )
        self.assertTrue(compiled.selected_name.startswith("certirange"))

    def test_invalid_contract_fails_closed(self) -> None:
        trace = WorkloadTrace(4).add_get(1)
        for operations in ((), ("get", "get"), ("insert",)):
            with self.subTest(operations=operations), self.assertRaises(
                ValueError
            ):
                compile_from_spec(
                    range(4),
                    trace,
                    AdaptiveSpec(operations=operations),  # type: ignore[arg-type]
                )


if __name__ == "__main__":
    unittest.main()
