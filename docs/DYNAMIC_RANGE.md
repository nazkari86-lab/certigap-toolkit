# Dynamic CertiRange

Dynamic CertiRange extends the static budgeted lookup model into a complete
ordered range index.

It supports:

- point lookup;
- point update;
- inclusive range `sum`, `min`, and `max`;
- immutable snapshots through persistent path copying;
- workload-shaped routing;
- drift-triggered rebuilding;
- deterministic depth caps;
- independently replayed structural and optimizer artifacts.

## Python API

```python
from certigap import CertiRangeWorkload

workload = CertiRangeWorkload(32)
workload.add_point(1, 1000)
workload.add_range(1, 10, 500)
workload.add_update(2, 100)

index = workload.compile(
    values=list(range(32)),
    budget=6,
    eta=0.10,
    aggregate="sum",
    max_depth=10,
    routing="range_aware",
)

print(index.get(1))
print(index.range_query(1, 10))

snapshot = index.snapshot()
index.point_update(2, 1000)
assert snapshot.get(2) != index.get(2)

certificate = index.export_certificate()
```

Keys and ranges are one-based and ranges are inclusive.

## Structure

The routing solver emits a partial alphabetic tree. Every unresolved interval
is deterministically completed by a midpoint tree. If a proposed routing split
cannot fit inside `max_depth`, that interval is replaced by its balanced
completion.

The resulting full tree has exactly one leaf per key. Every internal node
stores the aggregate of its contiguous interval.

## Guarantees

For `n` keys and completed-tree height `h`:

- point lookup takes at most `h` routing steps;
- persistent point update copies `O(h)` nodes;
- range aggregate visits `O(h)` boundary nodes;
- the implementation exports the conservative executable bound `4h + 1`;
- memory is `O(n)` for the current root plus `O(h)` per retained update;
- `h <= max_depth`;
- snapshots acquired before an update remain unchanged.

The structural verifier reconstructs the deterministic completion, checks
every interval and split, recomputes all per-key depths and aggregates, and
validates canonical SHA-256 digests.

## Range-Aware Search

The former endpoint proxy converts range boundaries into point frequencies.
This is cheap but does not optimize actual range traversal.

`range_aware_beam_search` instead evaluates each candidate by replaying the
declared point, update, and range workload on its completed topology. Its
objective is

```text
(1 - eta) * mean_node_visits + eta * (max_point_depth + 1)
```

The balanced completion is always retained as an incumbent. Therefore the
returned bounded-search candidate is never worse than that included candidate
under the exact training-trace evaluator.

This is not a global guarantee for large instances. The repository validates
the implementation against complete routing-tree enumeration on small cases.

## C++ Core

`cpp/certigap_range.hpp` provides a contiguous-node sum implementation. The
C++ benchmark compares identical mixed traces against:

- a direct array;
- Fenwick tree;
- iterative segment tree;
- contiguous Dynamic CertiRange.

The current benchmark rejects a blanket speed claim: Fenwick and segment trees
win raw sum throughput. CertiRange's distinct features are workload-shaped
point paths, generic Python aggregates, persistent snapshots, drift control,
and replayable certificates.

## Scope

Dynamic CertiRange is currently an ordered fixed-key-universe index. It does
not yet support insertion or deletion, lazy range updates, disk pages,
concurrent writers, or an official storage-engine integration.

