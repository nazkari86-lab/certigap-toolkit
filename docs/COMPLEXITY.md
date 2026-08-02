# Complexity Of The Exact Frontier DP

Let `n` be the number of ordered keys, `B` the split budget, and
`D = B + ceil(log2(n))`. Every achievable maximum cost lies in `0..D`, so a
Pareto frontier contains at most `D + 1` states after compression: at most one
minimum-average state is retained for each integer maximum cost.

There are `O(n^2 B)` interval-budget subproblems. For one subproblem, the
reference recurrence considers `O(n)` thresholds, `O(B)` budget partitions,
and at most `O(D^2)` pairs of frontier states. Therefore its arithmetic time
is `O(n^3 B^2 D^2)` and its compressed-state storage is `O(n^2 B D)`, not
counting persistent tree objects used for witness export.

Substituting `D = B + O(log n)` gives
`O(n^3 B^2 (B + log n)^2)`. Thus the reference frontier DP is fixed-parameter
tractable in `B`: its exponent of `n` is independent of `B` (the logarithmic
factor can be absorbed into a polynomial bound). For fixed `B`, this coarse
bound is `O(n^3 log^2 n)`.

The independent cost-cap DP has the same `O(n^2 B D)` state count, but each
state considers `O(n B)` threshold/budget choices without a Cartesian product
of two frontiers. Its corresponding conservative arithmetic bound is
`O(n^3 B^2 D)` with `O(n^2 B D)` memo storage.

These are worst-case bounds for numerically validated floating-point reference
implementations; the recurrence is mathematically exact, but finite `EPS`
dominance comparisons are not rational-arithmetic proofs. The candidate-pruned
C++ path is a separate heuristic and has no exactness guarantee or
approximation ratio. It exports a feasible upper bound and a separately
replayed entropy/max-cost lower bound, giving a valid but potentially loose
instance-specific interval.

The generalized executable-fallback DP has the same asymptotic recurrence after
fallback profiles have been precomputed. A direct midpoint-profile
precomputation takes `O(n^3)` time over all intervals and keys in the reference
implementation; fixed-round profiles are constant-time per interval. This
precomputation does not increase the displayed frontier-DP worst-case bound.

## Dynamic CertiRange

After deterministic completion, the range tree contains `2n-1` nodes and has
height `h <= max_depth`. Point lookup takes `O(h)`. Persistent point update
copies `O(h)` nodes. An inclusive range aggregate visits `O(h)` boundary
nodes, with executable bound `4h+1`. The current root occupies `O(n)` memory;
each retained persistent update adds `O(h)` nodes.

For range-aware beam width `W`, split budget `B`, threshold limit `K`, and
`Q` compressed workload records, the reference implementation evaluates at
most `O(B W B K)` generated candidates. A direct candidate replay costs
`O(n + Qh)`, so a conservative bound is
`O(B^2 W K (n + Qh))`. This is a bounded heuristic, not an exact large-instance
algorithm.

## Certified AutoIndex

For `m` trace operations and fixed portfolio size eight, direct array, prefix
sum, Fenwick, square-root decomposition, segment-tree, and sparse-table scoring
takes `O(m + n)` after constant-time formula setup. Each CertiRange candidate
first performs its existing bounded routing search and then replays the trace
in `O(mh)`, where `h` is completed-tree height. Runtime construction is
`O(n log n)` for the reference Fenwick and sparse-table builds and `O(n)` for
array, prefix sum, square-root decomposition, segment tree, and completed
CertiRange state after routing is fixed.

The verifier intentionally repeats candidate generation and scoring rather
than trusting compiler summaries. It therefore has the same asymptotic cost
as selection. Portfolio storage is `O(m+n)` because the certificate includes
the complete training and optional holdout traces plus two routing trees.

Generated non-CertiRange headers have `O(1)` configuration size. A generated
CertiRange header contains its complete `2n-1` topology and therefore has
`O(n)` source size. Runtime bounds match the selected backend.
The generated C++ snapshot operation copies runtime vectors and takes `O(n)`
time and space; it is semantic snapshot isolation, not path-copy persistence.

Tracking freeze construction rebuilds the selected backend and therefore costs
that backend's normal build time and memory. After construction,
`StaticTrackingIndex` has the same asymptotic operations as its compile-time
backend and performs no tracking, sampling, migration, or shadow maintenance.
Dynamic `FrozenTrackingIndex` adds one indirect dispatch but has the same
asymptotic bounds. Deferred `maintenance()` performs a full specialist rebuild.

`ConcurrentPrefixIndex` keeps `O(n)` canonical/Fenwick state and a bounded
`O(L)` update journal. Building a Prefix snapshot costs `O(n)`. Each catch-up
round applies `u` journal entries and rebuilds once in `O(n+u)`, for at most the
configured `R` rounds. An active Prefix point/range read is `O(1)`; Fenwick
fallback range reads are `O(log n)` and point updates are `O(log n)`. A
`SnapshotReadView` pays one epoch entry/exit per batch and retains `O(n)`
snapshot memory until release.

## Adaptive Single-Header Runtime

Let `q` be the number of distinct observed ranges. Point and update profiling
take `O(1)`; exact range-record profiling takes `O(log q)`. Range-aware
coverage weights are computed with a difference array in `O(n+q)`, without
expanding every range. Prefix construction is `O(n)`, and depth-safe weighted
topology construction is `O(n log n)` because each of `O(n)` nodes performs a
prefix lower bound.

Scoring array, Fenwick, and segment tree takes `O(n+q)`. Each CertiRange score
also replays exact range visits and costs `O(n+qh)`, where `h` is bounded by
the configured maximum depth. Adaptive snapshots copy canonical values,
runtime state, point/update profiles, and the range map in `O(n+q)` logical
space and time.

## Variable-Block Synthesis

Let `w` be `max_block_width`, `b` be `max_blocks`, and `m` be the trace
length. Computing every legal interval score takes `O(nwm)` time and `O(nw)`
stored scores. Exact partition dynamic programming takes `O(bnw)` time and
`O(bn)` state. Runtime construction is `O(n)`, point access is `O(1)`, and
updates are `O(1)` for sum or `O(w)` for minimum/maximum. A range query costs
the number of fully covered blocks plus scanned boundary elements. Runtime
memory is `2n+2b` declared scalar slots.
