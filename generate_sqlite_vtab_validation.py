from __future__ import annotations

import csv
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from certigap.sqlite_extension import build_sqlite_extension


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def sqlite_cli() -> str:
    candidates = [
        shutil.which("sqlite3"),
        "/opt/homebrew/opt/sqlite/bin/sqlite3",
        "/usr/local/opt/sqlite/bin/sqlite3",
    ]
    for candidate in candidates:
        if candidate is None or not Path(candidate).is_file():
            continue
        probe = subprocess.run(
            [candidate, ":memory:", ".help load"],
            text=True,
            capture_output=True,
            check=False,
        )
        if ".load FILE" in probe.stdout:
            return candidate
    raise RuntimeError("a loadable-extension SQLite CLI is required")


def run_sql(
    executable: str,
    extension: Path,
    sql: str,
    database: str = ":memory:",
) -> str:
    completed = subprocess.run(
        [executable, database],
        input=f".load {extension}\n{sql}\n",
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip())
    return completed.stdout.strip()


def record(
    scenario: str,
    expected: str,
    observed: str,
    planner_strategy: str = "",
) -> dict[str, str]:
    return {
        "scenario": scenario,
        "expected": expected,
        "observed": observed,
        "planner_strategy": planner_strategy,
        "passed": str(expected == observed),
        "scope": "SQLite ABI result; no portable latency claim",
    }


def main() -> None:
    executable = sqlite_cli()
    suffix = ".dylib" if sys.platform == "darwin" else ".so"
    rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        extension = build_sqlite_extension(root / f"certigap{suffix}")
        setup = (
            "CREATE VIRTUAL TABLE items USING certigap_vtab;\n"
            "INSERT INTO items VALUES(1,10),(2,20),(3,30),(5,50);\n"
        )
        equality = run_sql(
            executable,
            extension,
            setup
            + "EXPLAIN QUERY PLAN SELECT value FROM items WHERE key=3;",
        )
        equality_plan = equality.splitlines()[-1].strip()
        rows.append(
            record(
                "planner_equality",
                "`--SCAN items VIRTUAL TABLE INDEX 1:key_eq",
                equality_plan,
                "key_eq",
            )
        )

        bounded = run_sql(
            executable,
            extension,
            setup
            + "EXPLAIN QUERY PLAN SELECT value FROM items "
            "WHERE key>=2 AND key<=5 ORDER BY key;",
        )
        bounded_plan = bounded.splitlines()[-1].strip()
        rows.append(
            record(
                "planner_bounded_range",
                "`--SCAN items VIRTUAL TABLE INDEX 10:key_ge_key_le",
                bounded_plan,
                "key_ge_key_le",
            )
        )

        range_sum = run_sql(
            executable,
            extension,
            setup
            + "SELECT printf('%.1f',range_sum) FROM items "
            "WHERE key=2 AND right_key=5;",
        ).splitlines()[-1]
        rows.append(record("range_sum_pushdown", "100.0", range_sum, "range_sum"))

        database = str(root / "persistent.db")
        first = run_sql(
            executable,
            extension,
            "CREATE VIRTUAL TABLE persistent USING certigap_vtab;\n"
            "INSERT INTO persistent VALUES(1,10),(3,30),(5,50);\n"
            "BEGIN;\nUPDATE persistent SET value=300 WHERE key=3;\n"
            "INSERT INTO persistent VALUES(4,40);\nROLLBACK;",
            database,
        )
        if first:
            raise RuntimeError("persistent setup emitted unexpected output")
        reloaded = run_sql(
            executable,
            extension,
            "SELECT printf('%.1f',range_sum) FROM persistent "
            "WHERE key=1 AND right_key=5;",
            database,
        )
        rows.append(record("rollback_after_reconnect", "90.0", reloaded))

        mutation = run_sql(
            executable,
            extension,
            "DELETE FROM persistent WHERE key=3;\n"
            "UPDATE persistent SET key=2,value=22 WHERE key=1;\n"
            "SELECT group_concat(key||':'||printf('%.1f',value),',') "
            "FROM persistent;",
            database,
        )
        rows.append(record("insert_update_delete", "2:22.0,5:50.0", mutation))

        shadow = run_sql(
            executable,
            extension,
            "SELECT group_concat(key||':'||printf('%.1f',value),',') "
            "FROM persistent_data;",
            database,
        )
        rows.append(record("durable_shadow_consistency", mutation, shadow))

    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / "sqlite_vtab_validation.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(row["passed"] == "True" for row in rows)
    (RESULTS / "sqlite_vtab_validation.md").write_text(
        "\n".join(
            [
                "# SQLite Virtual-Table Validation",
                "",
                f"- Scenarios: `{len(rows)}`",
                f"- Passed: `{passed}/{len(rows)}`",
                "- Boundary: planner, durability, and transactional correctness; "
                "no cross-machine latency claim.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {output} ({passed}/{len(rows)} passed)")


if __name__ == "__main__":
    main()
