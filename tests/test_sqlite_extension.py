from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from certigap.sqlite_extension import (
    build_sqlite_extension,
    extension_source_path,
    sqlite_include_dir,
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

    def run_sql(self, extension: Path, sql: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.sqlite, ":memory:"],
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
            self.assertIn(lines[2], {"sorted_array", "fenwick", "segment_tree", "certirange_point", "certirange_range"})
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


if __name__ == "__main__":
    unittest.main()
