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

These are conservative worst-case bounds for the implemented Pareto-frontier
reference solver. They establish fixed-parameter tractability in `B` only when
`D` is treated as a parameter as well; they are not a claim that the current
Python implementation is practical for large `n`. The candidate-pruned C++
path is a separate heuristic and has no exactness guarantee.
