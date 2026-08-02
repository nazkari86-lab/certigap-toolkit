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

The registry is isolated per SQLite connection, protected by a mutex, and
released when the connection closes. SQL argument types, finite values, key
ranges, JSON array syntax, and unknown names fail closed with SQLite errors.
The generated extension has no Python runtime dependency.

## Exact Boundary

This is a real `sqlite3_load_extension` integration and executes adaptive C++
operations from SQL. It is not yet:

- a virtual table;
- integrated with SQLite `xBestIndex` or the query planner;
- durable across connection restart;
- synchronized transactionally with an ordinary SQLite table;
- evidence of a performance improvement over SQLite B-trees.

Those distinctions are intentional. The next storage step is a virtual-table
module with planner-visible equality/range constraints and an official YCSB
protocol.
