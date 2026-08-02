# SQLite Loadable Extension

CertiGap ships an actual SQLite loadable extension implemented against
`sqlite3ext.h`. It exposes connection-local named C++ adaptive indexes through
SQL functions:

```sql
.load ./certigap

SELECT certigap_build('catalog', '[0,1,2,3,4,5,6,7]');
SELECT certigap_range_sum('catalog', 2, 7);
SELECT certigap_optimize('catalog');
SELECT certigap_update('catalog', 4, 100);
SELECT certigap_get('catalog', 4);
SELECT certigap_selected('catalog');
SELECT certigap_drop('catalog');
```

Keys and range endpoints are 1-based, and both range endpoints are inclusive.
For example, `certigap_range_sum('catalog', 2, 7)` covers keys 2 through 7.

Build from a checkout:

```bash
python3 build_sqlite_extension.py --output build/certigap.so
```

After package installation:

```bash
certigap-sqlite-build --output certigap.so
```

On macOS use the `.dylib` suffix. If `sqlite3ext.h` is outside the standard
locations, set `SQLITE_INCLUDE_DIR`. CMake users can set
`-DCERTIGAP_BUILD_SQLITE_EXTENSION=ON`.

The function registry is isolated per SQLite connection, protected by a mutex, and
released when the connection closes. SQL argument types, finite values, key
ranges, JSON array syntax, and unknown names fail closed with SQLite errors.
The generated extension has no Python runtime dependency.

## Planner-Native Virtual Table

The same extension registers `certigap_vtab`:

```sql
CREATE VIRTUAL TABLE catalog_index USING certigap_vtab;
INSERT INTO catalog_index(key, value) VALUES (1, 10), (2, 20), (5, 50);

SELECT value FROM catalog_index WHERE key = 2;
SELECT value FROM catalog_index WHERE key >= 2 AND key <= 5 ORDER BY key;
SELECT range_sum FROM catalog_index WHERE key = 1 AND right_key = 5;
```

`xBestIndex` exposes equality, lower-bound, upper-bound, and combined bounded
range strategies to SQLite. The hidden `right_key` column activates one-call
inclusive range-sum pushdown. `EXPLAIN QUERY PLAN` reports the selected
strategy, for example `VIRTUAL TABLE INDEX 1:key_eq`.

Each virtual table owns a SQLite shadow table named `<table>_data`. It is the
durable source of truth. The C++ index is reconstructed on connection and
refreshed at transaction/read boundaries, so commits by another connection
cannot leave it as the authoritative stale copy. INSERT, key/value UPDATE,
DELETE, rollback, savepoint rollback, rename, drop, and reconnect are covered
by real SQLite CLI tests. WAL writers are serialized by SQLite and a
two-process test verifies visibility after lock handoff.

## Exact Boundary

This is a real `sqlite3_load_extension` and virtual-table integration. It is
not yet:

- an official YCSB binding;
- a replacement for SQLite's native B-tree storage;
- optimized for large insert/delete-heavy or multi-writer workloads;
- a disk-page-aware CertiGap layout;
- evidence of a performance improvement over SQLite B-trees.

The deterministic six-scenario artifact verifies planner selection,
range-sum pushdown, rollback/reconnect, mutation lifecycle, and shadow-table
agreement. It establishes integration correctness, not portable latency.
