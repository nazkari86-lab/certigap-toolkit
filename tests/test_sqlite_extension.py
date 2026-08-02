from __future__ import annotations

import random
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from certigap.sqlite_extension import (
    build_sqlite_extension,
    extension_source_path,
    sqlite_include_dir,
    virtual_table_source_path,
)


class SQLiteExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        candidates = [
            shutil.which("sqlite3"),
            "/opt/homebrew/opt/sqlite/bin/sqlite3",
            "/usr/local/opt/sqlite/bin/sqlite3",
        ]
        cls.sqlite = None
        for candidate in candidates:
            if candidate is None or not Path(candidate).is_file():
                continue
            help_result = subprocess.run(
                [candidate, ":memory:", ".help load"],
                text=True,
                capture_output=True,
                check=False,
            )
            if ".load FILE" in help_result.stdout:
                cls.sqlite = candidate
                break
        if cls.sqlite is None:
            raise unittest.SkipTest("loadable-extension SQLite CLI is unavailable")
        try:
            sqlite_include_dir()
        except FileNotFoundError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def run_sql(
        self,
        extension: Path,
        sql: str,
        database: str = ":memory:",
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.sqlite, database],
            input=f".load {extension}\n{sql}\n",
            text=True,
            capture_output=True,
            check=False,
        )

    def test_real_loadable_extension_lifecycle(self) -> None:
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        with tempfile.TemporaryDirectory() as directory:
            extension = build_sqlite_extension(
                Path(directory) / f"certigap{suffix}"
            )
            completed = self.run_sql(
                extension,
                "\n".join(
                    [
                        "SELECT certigap_build('demo','[0,1,2,3,4,5,6,7]');",
                        "WITH RECURSIVE c(x) AS (VALUES(1) UNION ALL "
                        "SELECT x+1 FROM c WHERE x<500) "
                        "SELECT sum(certigap_range_sum('demo',2,7)) FROM c;",
                        "SELECT certigap_optimize('demo');",
                        "SELECT certigap_update('demo',4,100);",
                        "SELECT certigap_range_sum('demo',2,7);",
                        "SELECT certigap_drop('demo');",
                    ]
                ),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            lines = completed.stdout.strip().splitlines()
            self.assertEqual(lines[0], "8")
            self.assertAlmostEqual(float(lines[1]), 10_500.0)
            self.assertIn(
                lines[2],
                {
                    "sorted_array",
                    "prefix_sum",
                    "fenwick",
                    "sqrt_decomposition",
                    "segment_tree",
                    "sparse_table",
                    "certirange_point",
                    "certirange_range",
                },
            )
            self.assertEqual(lines[3], "100.0")
            self.assertEqual(lines[4], "118.0")
            self.assertEqual(lines[5], "1")

    def test_extension_rejects_invalid_input(self) -> None:
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        with tempfile.TemporaryDirectory() as directory:
            extension = build_sqlite_extension(
                Path(directory) / f"certigap{suffix}"
            )
            completed = self.run_sql(
                extension,
                "SELECT certigap_build('demo','[1,not-a-number]');",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("invalid number", completed.stderr)

    def test_extension_enforces_json_number_grammar(self) -> None:
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        with tempfile.TemporaryDirectory() as directory:
            extension = build_sqlite_extension(
                Path(directory) / f"certigap{suffix}"
            )
            leading_zero = self.run_sql(
                extension,
                "SELECT certigap_build('leading-zero','[01]');",
            )
            incomplete_exponent = self.run_sql(
                extension,
                "SELECT certigap_build('bad-exponent','[1e+]');",
            )
            valid_exponent = self.run_sql(
                extension,
                "SELECT certigap_build('valid-exponent','[-1.5e+2,2E-1]');",
            )

            self.assertNotEqual(leading_zero.returncode, 0)
            self.assertIn("leading zero", leading_zero.stderr)
            self.assertNotEqual(incomplete_exponent.returncode, 0)
            self.assertIn("invalid exponent", incomplete_exponent.stderr)
            self.assertEqual(valid_exponent.returncode, 0, valid_exponent.stderr)
            self.assertEqual(valid_exponent.stdout.strip(), "2")

    def test_packaged_source_is_discoverable(self) -> None:
        self.assertTrue(extension_source_path().is_file())
        self.assertTrue(virtual_table_source_path().is_file())

    def test_virtual_table_planner_and_range_pushdown(self) -> None:
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        with tempfile.TemporaryDirectory() as directory:
            extension = build_sqlite_extension(
                Path(directory) / f"certigap{suffix}"
            )
            completed = self.run_sql(
                extension,
                "\n".join(
                    [
                        "CREATE VIRTUAL TABLE items USING certigap_vtab;",
                        "INSERT INTO items(key,value) "
                        "VALUES(1,10),(2,20),(3,30),(5,50);",
                        "SELECT group_concat(key||':'||value,',') FROM "
                        "(SELECT key,value FROM items WHERE key>=2 AND key<5 "
                        "ORDER BY key);",
                        "SELECT range_sum FROM items "
                        "WHERE key=2 AND right_key=5;",
                        "EXPLAIN QUERY PLAN SELECT value FROM items WHERE key=3;",
                    ]
                ),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("2:20.0,3:30.0", completed.stdout)
            self.assertIn("100.0", completed.stdout)
            self.assertIn("VIRTUAL TABLE INDEX 1:key_eq", completed.stdout)

    def test_virtual_table_is_durable_and_transactional(self) -> None:
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extension = build_sqlite_extension(root / f"certigap{suffix}")
            database = str(root / "persistent.db")
            first = self.run_sql(
                extension,
                "\n".join(
                    [
                        "CREATE VIRTUAL TABLE items USING certigap_vtab;",
                        "INSERT INTO items VALUES(1,10),(3,30),(5,50);",
                        "BEGIN;",
                        "UPDATE items SET value=300 WHERE key=3;",
                        "INSERT INTO items VALUES(4,40);",
                        "ROLLBACK;",
                        "SELECT range_sum FROM items "
                        "WHERE key=1 AND right_key=5;",
                    ]
                ),
                database,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(first.stdout.strip(), "90.0")

            second = self.run_sql(
                extension,
                "\n".join(
                    [
                        "SELECT group_concat(key||':'||value,',') FROM items;",
                        "DELETE FROM items WHERE key=3;",
                        "UPDATE items SET key=2,value=22 WHERE key=1;",
                        "SELECT group_concat(key||':'||value,',') FROM items;",
                        "SELECT range_sum FROM items "
                        "WHERE key=2 AND right_key=5;",
                    ]
                ),
                database,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(
                second.stdout.strip().splitlines(),
                ["1:10.0,3:30.0,5:50.0", "2:22.0,5:50.0", "72.0"],
            )

    def test_virtual_table_savepoint_rollback_matches_oracle(self) -> None:
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        with tempfile.TemporaryDirectory() as directory:
            extension = build_sqlite_extension(
                Path(directory) / f"certigap{suffix}"
            )
            completed = self.run_sql(
                extension,
                "\n".join(
                    [
                        "CREATE VIRTUAL TABLE items USING certigap_vtab;",
                        "INSERT INTO items VALUES(1,1),(2,2),(3,3);",
                        "BEGIN;",
                        "SAVEPOINT before_changes;",
                        "UPDATE items SET value=200 WHERE key=2;",
                        "DELETE FROM items WHERE key=3;",
                        "ROLLBACK TO before_changes;",
                        "RELEASE before_changes;",
                        "COMMIT;",
                        "SELECT range_sum FROM items "
                        "WHERE key=1 AND right_key=3;",
                    ]
                ),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip(), "6.0")

    def test_virtual_table_serializes_concurrent_writers(self) -> None:
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            extension = build_sqlite_extension(root / f"certigap{suffix}")
            database = str(root / "concurrent.db")
            setup = self.run_sql(
                extension,
                "PRAGMA journal_mode=WAL;\n"
                "CREATE VIRTUAL TABLE items USING certigap_vtab;",
                database,
            )
            self.assertEqual(setup.returncode, 0, setup.stderr)

            first = subprocess.Popen(
                [self.sqlite, database],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            assert first.stdin is not None
            first.stdin.write(
                f".load {extension}\n"
                "PRAGMA busy_timeout=3000;\n"
                "BEGIN IMMEDIATE;\n"
                "INSERT INTO items VALUES(1,10);\n"
                ".shell sleep 1\n"
                "COMMIT;\n"
            )
            first.stdin.close()
            time.sleep(0.2)
            second = self.run_sql(
                extension,
                "PRAGMA busy_timeout=3000;\n"
                "INSERT INTO items VALUES(2,20);\n"
                "SELECT group_concat(key||':'||value,',') FROM items;",
                database,
            )
            first.wait(timeout=5)
            first_stderr = first.stderr.read() if first.stderr is not None else ""
            if first.stdout is not None:
                first.stdout.close()
            if first.stderr is not None:
                first.stderr.close()

            self.assertEqual(first.returncode, 0, first_stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertIn("1:10.0,2:20.0", second.stdout)

    def test_virtual_table_random_mutations_match_map_oracle(self) -> None:
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        generator = random.Random(20260802)
        values = {key: float(key) for key in range(1, 21)}
        next_key = 21
        sql = [
            "CREATE VIRTUAL TABLE items USING certigap_vtab;",
            "INSERT INTO items VALUES "
            + ",".join(f"({key},{value})" for key, value in values.items())
            + ";",
        ]
        expected = []
        for _ in range(100):
            choice = generator.random()
            if choice < 0.55:
                key = generator.choice(list(values))
                number = float(generator.randint(-500, 500)) / 10.0
                values[key] = number
                sql.append(f"UPDATE items SET value={number} WHERE key={key};")
            elif choice < 0.75 and len(values) > 5:
                key = generator.choice(list(values))
                del values[key]
                sql.append(f"DELETE FROM items WHERE key={key};")
            else:
                number = float(generator.randint(-500, 500)) / 10.0
                values[next_key] = number
                sql.append(f"INSERT INTO items VALUES({next_key},{number});")
                next_key += 1
            left, right = sorted(generator.sample(list(values), 2))
            expected.append(sum(
                number
                for key, number in values.items()
                if left <= key <= right
            ))
            sql.append(
                "SELECT printf('%.9f',range_sum) FROM items "
                f"WHERE key={left} AND right_key={right};"
            )

        with tempfile.TemporaryDirectory() as directory:
            extension = build_sqlite_extension(
                Path(directory) / f"certigap{suffix}"
            )
            completed = self.run_sql(extension, "\n".join(sql))
            self.assertEqual(completed.returncode, 0, completed.stderr)
            observed = [float(line) for line in completed.stdout.splitlines()]
            self.assertEqual(len(observed), len(expected))
            for actual, wanted in zip(observed, expected):
                self.assertAlmostEqual(actual, wanted, places=7)

    def test_virtual_table_rename_and_drop_manage_shadow_table(self) -> None:
        suffix = ".dylib" if sys.platform == "darwin" else ".so"
        with tempfile.TemporaryDirectory() as directory:
            extension = build_sqlite_extension(
                Path(directory) / f"certigap{suffix}"
            )
            completed = self.run_sql(
                extension,
                "\n".join(
                    [
                        "CREATE VIRTUAL TABLE items USING certigap_vtab;",
                        "INSERT INTO items VALUES(1,10),(2,20);",
                        "ALTER TABLE items RENAME TO moved;",
                        "SELECT range_sum FROM moved "
                        "WHERE key=1 AND right_key=2;",
                        "DROP TABLE moved;",
                        "SELECT count(*) FROM sqlite_master "
                        "WHERE name IN ('items_data','moved_data');",
                    ]
                ),
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertEqual(completed.stdout.strip().splitlines(), ["30.0", "0"])


if __name__ == "__main__":
    unittest.main()
