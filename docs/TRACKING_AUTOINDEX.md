# TrackingAutoIndex: Certified Causal Representation Tracking

## Problem

Train-only AutoIndex selects one representation. `TrackingAutoIndex` instead
keeps the complete feasible AutoIndex portfolio and may migrate while the
workload changes. A state is an executable backend such as a sorted array,
prefix sum, Fenwick tree, segment tree, or CertiRange. The current operation
reveals a non-negative structural service-cost vector over these states.

For state path `s_1,...,s_T`, initial state `s_0`, service costs `c_t`, and
positive uniform migration cost `d`, total modeled cost is

```text
sum_t c_t(s_t) + d * [s_t != s_(t-1)].
```

This is a finite metrical task system. The implementation uses the
deterministic Work Function Algorithm (WFA):

```text
w_0(s) = d(s_0, s)
w_t(s) = c_t(s) + min_y (w_(t-1)(y) + d(y, s))
s_t = argmin_s (w_t(s) + d(s_(t-1), s)).
```

The selected backend is actually materialized from canonical values before
the operation executes. Future operations are never inspected.

## Exact Comparator

The certificate computes an exact offline comparator allowed at most `K`
switches:

```text
D[t,s,k] = c_t(s) + min_y (
    D[t-1,y,k-[y != s]] + d(y,s)
).
```

Every predecessor is retained, so the verifier reconstructs both minimum cost
and the deterministic optimal path. Complexity is `O(T K m^2)` time and
`O(Km)` working memory for `m` feasible backends. Setting `K=T` gives the exact
unrestricted offline oracle. The artifact reports exact ex-post dynamic regret
against the declared K-switch comparator.

## Python API

```python
from certigap import (
    AdaptiveSpec,
    TrackingPolicy,
    WorkloadTrace,
    start_tracking_autoindex,
)

train = WorkloadTrace(32)
for key in range(1, 33):
    train.add_get(key)

index = start_tracking_autoindex(
    range(32),
    train,
    AdaptiveSpec(),
    policy=TrackingPolicy(
        migration_cost_units=8.0,
        max_comparator_switches=3,
    ),
)

for _ in range(20):
    index.range_query(1, 32)
index.point_update(1, 100.0)

certificate = index.export_certificate()
print(index.explain())
```

Verify or explain the emitted JSON with the unified CLI:

```bash
certigap verify tracking.json
certigap explain tracking.json
```

## What The Certificate Establishes

- The nested AutoIndex portfolio and every feasible candidate are replayed.
- Every operation's complete service-cost vector is regenerated.
- Every WFA work vector, tie-break, migration, and cumulative cost is replayed.
- Exact constrained and unrestricted offline oracles are independently
  recomputed.
- Digest-preserving modification of a trajectory still fails verification.

The classical WFA result is `(2m-1)`-competitiveness for finite metrical task
systems under the theorem's standard conventions, including an
initialization-dependent additive term. The artifact records this factor and
whether the stronger factor-only inequality happens to hold on the observed
trace. It does not present that observed Boolean as a universal theorem proof.
See Borodin, Linial, and Saks, [An optimal on-line algorithm for metrical task
systems](https://doi.org/10.1145/28395.28435), and the
[MTS survey summary](https://drops.dagstuhl.de/entities/document/10.4230/DagSemProc.05031.29).

## Boundaries

- Structural units are not portable nanoseconds. Target measurements should
  calibrate candidate unit costs and migration cost.
- The portfolio and operation grammar remain fixed and explicit.
- The current migration metric is positive and uniform; measured asymmetric
  conversion costs are future work.
- WFA observes the current operation cost before moving, but never future cost.
- The K-switch oracle is retrospective and is used for evaluation, not routing.
- Runtime switching has no statistical no-regression gate. Use measured or
  martingale-safe deployment paths when that is the required guarantee.
- Inserts, deletes, concurrency, durability, and disk-page layouts are outside
  the current runtime contract.

The committed 15-scenario matrix includes stationary workloads, phase shifts,
alternation, and three migration costs. All certificates replay. Maximum exact
K-switch regret is `121` structural units and maximum observed ratio to the
unrestricted oracle is `2.657534`; both wins and losses are therefore visible.
