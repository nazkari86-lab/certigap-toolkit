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
C++ path is a separate heuristic and has no exactness guarantee.

The generalized executable-fallback DP has the same asymptotic recurrence after
fallback profiles have been precomputed. A direct midpoint-profile
precomputation takes `O(n^3)` time over all intervals and keys in the reference
implementation; fixed-round profiles are constant-time per interval. This
precomputation does not increase the displayed frontier-DP worst-case bound.
