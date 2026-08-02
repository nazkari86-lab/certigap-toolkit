# TrackingAutoIndex: Certified Causal Representation Tracking

## Problem

Train-only AutoIndex selects one representation. `TrackingAutoIndex` instead
keeps the complete feasible AutoIndex portfolio and may migrate while the
workload changes. A state is an executable backend such as a sorted array,
prefix sum, Fenwick tree, segment tree, or CertiRange. The current operation
reveals a non-negative structural service-cost vector over these states.

For state path `s_1,...,s_T`, initial state `s_0`, service costs `c_t`, and
positive migration metric `d`, total modeled cost is

```text
sum_t c_t(s_t) + d(s_(t-1), s_t).
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

## Native C++ API

`certigap_tracking.hpp` provides a dependency-free C++17 implementation over
the conventional array, prefix, Fenwick, square-root, segment-tree, and sparse
table runtimes. Sum portfolios exclude sparse tables; min/max portfolios
exclude prefix sums and Fenwick trees.

```cpp
#include <certigap_tracking.hpp>

std::vector<double> values(4096, 1.0);
certigap::TrackingPolicy policy;
policy.backends = {
    certigap::Backend::SortedArray,
    certigap::Backend::PrefixSum,
    certigap::Backend::Fenwick,
    certigap::Backend::SqrtDecomposition,
    certigap::Backend::SegmentTree,
};
policy.migration_matrix = certigap::tracking_rebuild_metric(
    values.size(), policy.backends);
policy.record_history = false;

certigap::TrackingAutoIndex index(values, certigap::Aggregate::Sum, policy);
auto answers = index.run_batch({
    certigap::TrackingOperation::range(1, 4096),
    certigap::TrackingOperation::update(10, 7.0),
    certigap::TrackingOperation::get(10),
});
```

For low-overhead deployment without full per-operation WFA accounting, use the
sampled controller. It keeps an always-current Fenwick shadow for sums (segment
tree for min/max), evaluates candidates once per 32 operations, and enters a
4096-operation lease after four stable decisions. An update that invalidates a
static prefix/sparse view falls back to the robust shadow immediately.

```cpp
certigap::FastTrackingAutoIndex fast(values, certigap::Aggregate::Sum);
double total = fast.range_query(1, 4096);
fast.point_update(10, 7.0);
fast.flush();  // process a partial sampling epoch before inspection
auto explanation = fast.explain();
```

### Detached data and control planes

Applications that already have sampled telemetry can remove observation from
the request path. `hot_*` methods execute only data-structure work and safe
fallback; `observe_sample(operation, represented_operations)` updates the
controller without executing the operation. Samples should represent equal-size
batches inside an epoch.

```cpp
double total = fast.hot_range_query(1, 4096);  // valid one-based input required
fast.observe_sample(certigap::TrackingOperation::range(1, 4096), 4096);
if (fast.maintenance_pending()) {
    fast.maintenance();
}
```

Set `FastTrackingPolicy::defer_specialist_rebuilds=true` to keep rebuilds out
of the request that made the decision. `maintenance()` constructs the pending
specialist from current canonical values. The class is not internally
thread-safe: call maintenance only when no operation is concurrent, or protect
the entire index with external synchronization. This is an explicit maintenance
boundary, not a claimed lock-free RCU implementation.

### Frozen deployment

`freeze()` returns a fixed dynamic backend with no controller, sampling, shadow,
or switching. When the deployment backend is known at compile time,
`freeze_static<Backend, Aggregate>()` additionally removes indirect dispatch.

```cpp
auto dynamic = fast.freeze();
auto compiled = fast.freeze_static<
    certigap::Backend::Fenwick,
    certigap::Aggregate::Sum>();
double answer = compiled.range_query(1, 4096);
```

`unchecked_*` and `hot_*` require valid one-based keys, valid inclusive ranges,
and finite update values. Use checked methods at trust boundaries.

`FastTrackingAutoIndex` guarantees the same query/update semantics, validates
its policy fail-closed, and is covered by randomized ASan/UBSan differential
tests. It deliberately does not claim WFA competitiveness: sampling, leases,
directed rebuild costs, and robust fallback are runtime engineering choices.
Use `TrackingAutoIndex` when full trajectories, exact offline comparators, or
the metrical-task-system theorem are required.

The rebuild helper uses `max(build(i), build(j))` off the diagonal. This is a
positive symmetric metric satisfying the triangle inequality, unlike a raw
directed conversion table. General non-negative directed matrices are allowed,
but `wfa_competitive_factor()` returns zero because the classical MTS theorem
does not apply. Production mode reuses WFA scratch buffers and omits trajectory
allocation. Exact oracles fail closed unless `record_history=true`.

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
- Python certificates currently use a positive uniform metric. Native C++ also
  accepts a verified rebuild-aware metric or an explicitly non-theorem directed
  matrix.
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

## Comprehensive Comparison

The broader maximum matrix adds 126 certified configurations over 14 workload
families, three key-universe sizes, and migration costs `2`, `8`, and `32`.
Every policy uses exactly the same per-operation service rows.

- Against the unchanged initial representation, WFA records `106` wins, `18`
  ties, and `2` losses.
- Against the best fixed representation selected with hindsight, it records
  `53` wins, `34` ties, and `39` losses.
- Against myopic current-operation switching, it records `29/62/35`.
- Against a cumulative-service leader, it records `55/39/32`.
- Median ratio to the exact unrestricted oracle is `1.009222`; mean is
  `1.111103`, and maximum is `2.068306`.
- At migration cost `2`, mean oracle ratio is `1.003004`. At cost `32`, it is
  `1.250766`, showing that migration calibration materially changes quality.

The Python wall-clock matrix has 90 method rows, five workloads, two sizes,
five repetitions, and identical checksum validation. Tracking is `96.42x` to
`958.87x` slower than the fastest fixed portfolio backend in these runs. The
gap includes online cost-vector construction, WFA accounting, trace recording,
and in-trace rebuilds, but excludes initial construction and certificate
export. Therefore the present Python path is a research reference, not a
low-latency replacement for Fenwick or prefix sums.

The native matching benchmark adds four phased workloads at `n=64,256,4096`.
Rebuild-aware production runs at `61.23-317.23 ns/op` on the recorded machine
and uniform native mode is `173.2x-15952.7x` faster than the matching Python
reference. It still costs `11.2x` median versus the fastest fixed C++ backend,
so tracking is useful when the best representation changes or is unknown, not
as a universal Fenwick replacement. Full audit history adds `2.04x` median.
On larger read-mostly streams, rebuild-aware migration cuts switches by
`360x-394x` and improves runtime by `3.6x-16.4x` over naive uniform migration.

The separate Fast matrix covers 64 configurations: four sizes, eight stationary
or adversarial workloads, and 5,000/50,000-operation horizons. All implementation
checksums agree. Relative to Fenwick, Fast is `1.21x` median, `1.59x` p95, and
`1.90x` worst-case. Relative to the fastest fixed backend selected with hindsight,
the same figures are `1.35x` median and `5.40x` worst-case. The second comparator
can choose an O(1)-update array after seeing that no future range query arrives;
a causal online system cannot safely make that assumption.

See `results/tracking_autoindex_comparison.md` for the complete outcome tables,
`tracking_autoindex_comparison.csv` for policy rows,
`tracking_autoindex_candidates.csv` for every fixed backend, and
`tracking_autoindex_runtime.csv` for Python timing. Native raw rows and
provenance are in `tracking_autoindex_native_runtime.csv` and its metadata JSON.
Fast-mode rows and provenance are in `tracking_autoindex_fast_runtime.csv` and
`tracking_autoindex_fast_runtime.metadata.json`.
The paired hot-path matrix is in `tracking_hot_path_runtime.csv`; at the
50,000-operation horizon checked static Fenwick records `1.01x` median and
`1.23x` maximum versus a direct Fenwick runtime on this machine.
