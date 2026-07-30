from __future__ import annotations

import unittest

from benchmarks.sqlite_ycsb import (
    Fenwick,
    SQLiteIndex,
    execute,
    make_operations,
)


class SQLiteYcsbTests(unittest.TestCase):
    def test_declared_operation_mixes_are_deterministic(self) -> None:
        expected = {
            "A": {"get", "update"},
            "B": {"get", "update"},
            "C": {"get"},
            "F": {"get", "rmw"},
            "R": {"get", "update", "range"},
        }
        for workload, kinds in expected.items():
            left = make_operations(workload, 128, 1_000, 42)
            right = make_operations(workload, 128, 1_000, 42)
            self.assertEqual(left, right)
            self.assertEqual({operation.kind for operation in left}, kinds)

    def test_sqlite_and_fenwick_match_on_identical_trace(self) -> None:
        values = [float(index % 17) for index in range(1, 129)]
        operations = make_operations("R", 128, 500, 20260730)
        sqlite = SQLiteIndex(values)
        try:
            sqlite_checksum = execute(sqlite, operations)
        finally:
            sqlite.close()
        fenwick_checksum = execute(Fenwick(values), operations)
        self.assertAlmostEqual(sqlite_checksum, fenwick_checksum, places=7)


if __name__ == "__main__":
    unittest.main()
