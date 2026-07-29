# Certified AutoIndex

`compile_autoindex` turns an ordered workload trace and explicit constraints
into an executable index. It evaluates a fixed, deterministic portfolio:

1. contiguous sorted array;
2. Fenwick tree;
3. iterative segment tree;
4. point-proxy CertiRange;
5. range-aware CertiRange.

Every candidate remains in the exported artifact, including infeasible ones
and their rejection reasons. The independent verifier reconstructs all five
candidates, recomputes resources and scores, and rejects omitted candidates,
changed winners, changed holdout results, or a modified digest.

```python
from certigap import AutoIndexConstraints, WorkloadTrace, compile_autoindex

trace = WorkloadTrace(32)
for _ in range(100):
    trace.add_range(3, 30)

index = compile_autoindex(
    range(32),
    trace,
    constraints=AutoIndexConstraints(aggregate="sum", budget=4),
)
print(index.summary())
print(index.range_query(3, 30))
```

## Selection Contract

The objective is

`(1-eta) * mean_visits + eta * max_visits + memory_weight * slots + build_weight * build_units`.

The compiler selects the feasible minimum on the training trace. Ties are
resolved by memory and then the published portfolio order. A chronological
holdout may be attached, but it is evaluation-only and cannot affect the
winner.

By default the unit is one declared structural primitive visit. It makes the
selection replayable, but it is not a nanosecond model. Production selection
can set `array_unit_cost`, `fenwick_unit_cost`,
`segment_tree_unit_cost`, and `certirange_unit_cost` from target-system
measurements. The verifier includes these coefficients in regeneration.

## Constraints And Capabilities

- `aggregate`: `sum`, `min`, or `max`; Fenwick is infeasible outside `sum`.
- `memory_limit_slots`: excludes structures exceeding the declared model.
- `max_depth`: bounds candidate height.
- `require_persistent_snapshots`: restricts selection to CertiRange.
- `budget`: controls the adaptive CertiRange routing prefix.
- `*_unit_cost`: calibrates one structural visit for each backend family.

The current universe is static and rank-addressed. Insert/delete, disk-page
layouts, concurrency, and storage-engine latency remain outside the verified
scope.

For deterministic JSON-to-C++ code generation and CMake wiring, see
[`COMPILER_INTEGRATION.md`](COMPILER_INTEGRATION.md).
