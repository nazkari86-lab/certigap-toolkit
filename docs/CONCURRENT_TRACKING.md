# Concurrent Prefix Tracking

`ConcurrentPrefixIndex` is the first concurrent specialist-view runtime in
CertiGap. It combines a mutable Fenwick core with an immutable Prefix snapshot.
The current contract supports a fixed-size sum array, one-based point updates,
point reads, and inclusive range sums.

```cpp
#include <certigap_concurrent.hpp>

certigap::ConcurrentPrefixIndex index({1, 2, 3, 4});
double fallback = index.range_query(1, 4);  // Fenwick under shared lock

if (index.rebuild_recommended()) index.request_rebuild();
index.wait_for_rebuild();
double snapshot = index.range_query(1, 4);  // immutable Prefix path

index.point_update(2, 10);                  // atomically invalidates Prefix
double current = index.range_query(1, 4);   // correct Fenwick fallback: 18
```

## Publication Protocol

1. The builder copies canonical values and version `V` under a shared core lock.
2. It builds Prefix state without holding the writer lock.
3. Concurrent point updates append bounded `(version, key, value)` records.
4. Catch-up applies a journal batch in `O(u)` and rebuilds Prefix once in `O(n)`.
5. Publication takes the exclusive core lock and succeeds only when the
   candidate version equals the current core version.
6. The immutable pointer is published atomically. An update exchanges it with
   null before mutating Fenwick, so new readers cannot enter stale state.

If the journal no longer contains a complete suffix, the catch-up round limit
is exhausted, the memory budget is exceeded, or an old view still retains the
retired snapshot, rebuilding fails closed. Fenwick remains authoritative.

## Read Semantics

Ordinary `get()` and `range_query()` calls are linearizable under the documented
lifetime contract. A reader that acquired the old immutable pointer overlaps
the invalidating update and can be ordered immediately before it. A reader that
sees null takes the shared Fenwick lock and is ordered while holding that lock.

For batches, enter one versioned read-side epoch:

```cpp
auto view = index.snapshot_view();
if (view.active()) {
    for (const auto& range : batch) {
        consume(view.unchecked_range_query(range.left, range.right));
    }
}
```

`SnapshotReadView` provides snapshot isolation, not a fresh linearization point
for every call. It can continue reading version `V` after a writer has published
version `V+1`. Destroying the view releases that epoch. A long-lived view does
not block point updates, but it can retain snapshot memory and delay a new build.

## Progress And Memory

- Snapshot pointer and reader-counter atomics can be inspected with
  `snapshot_atomics_lock_free()`. Lock-free status is platform-dependent.
- Individual snapshot reads perform epoch entry/exit atomics. A view amortizes
  them across a batch.
- Fallback readers use `std::shared_mutex`; writers use its exclusive side.
- Writers are serialized. This is not a lock-free multi-writer structure.
- The update journal is bounded by `max_update_log_entries`.
- Catch-up is bounded by `max_catchup_rounds` and costs `O(n+u)` per round.
- `max_snapshot_bytes` limits one specialist snapshot allocation. Canonical
  values, Fenwick state, the update journal, and thread-stack memory are separate.
- All operations and views must finish before the index is destroyed.

## Evidence Boundary

The committed validation uses four concurrent readers, 4,000 point updates,
background publication, snapshot invalidation, catch-up, bounded-memory rejection,
ASan/UBSan, and ThreadSanitizer. The runtime benchmark covers one and four readers
on one Apple M4 machine. It is not evidence for portable latency, writer fairness,
insert/delete workloads, process-shared memory, durability, or wait-free progress.
