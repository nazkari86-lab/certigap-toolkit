# Certified AutoIndex

`compile_autoindex` turns an ordered workload trace and explicit constraints
into an executable index. It evaluates a fixed, deterministic portfolio:

1. contiguous sorted array;
2. global prefix sums;
3. Fenwick tree;
4. square-root decomposition;
5. iterative segment tree;
6. sparse table for idempotent `min`/`max`;
7. point-proxy CertiRange;
8. range-aware CertiRange.

Every candidate remains in the exported artifact, including infeasible ones
and their rejection reasons. The independent verifier reconstructs all eight
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
can set `array_unit_cost`, `prefix_unit_cost`, `fenwick_unit_cost`,
`sqrt_unit_cost`, `segment_tree_unit_cost`, `sparse_unit_cost`, and
`certirange_unit_cost` from target-system measurements. The verifier includes
these coefficients in regeneration.

## Constraints And Capabilities

- `aggregate`: `sum`, `min`, or `max`; Fenwick and prefix sums require `sum`,
  while sparse tables require idempotent `min` or `max`.
- `memory_limit_slots`: excludes structures exceeding the declared model.
- `max_depth`: bounds candidate height.
- `require_persistent_snapshots`: restricts selection to CertiRange.
- `budget`: controls the adaptive CertiRange routing prefix.
- `*_unit_cost`: calibrates one structural visit for each backend family.

The current universe is static and rank-addressed. Insert/delete, disk-page
layouts, concurrency, and storage-engine latency remain outside the verified
scope.

Adding unrelated structures is intentionally avoided. Hash tables do not
support range aggregates, while B-trees, learned indexes, and wavelet trees
need different key, storage, or query semantics. They require a separate
capability grammar rather than misleading rows in this portfolio.

For deterministic JSON-to-C++ code generation and CMake wiring, see
[`COMPILER_INTEGRATION.md`](COMPILER_INTEGRATION.md).
The admission rules and capability-separated roadmap are in
[`PORTFOLIO_EXPANSION.md`](PORTFOLIO_EXPANSION.md).
