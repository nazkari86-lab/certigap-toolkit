# Scalable Anytime TV-DRO Search

## Purpose

`anytime_tv_branch_and_bound` extends direct TV-DRO optimization beyond the
proof-sized exhaustive regime. It always returns:

- a feasible incumbent with objective `U`;
- an admissible global lower bound `L`;
- absolute and relative optimality gaps;
- a deterministic replay certificate.

The result is globally exact only when the reported gap is zero. Otherwise the
interval is the claim.

## Search State

A state contains a partial ordered tree, its split count, and a canonical
ordered set of unresolved leaves. Expanding the first unresolved leaf
enumerates closing it with the fallback and every legal threshold split if
budget remains. These alternatives are exhaustive and disjoint.

## Admissible Lower Bounds

Three independently valid bounds are combined by taking their maximum.

### Componentwise TV Bound

For a key in an unresolved leaf, its optimistic cost includes routing
comparisons already incurred and zero future fallback cost. This is no larger
than its cost in any completion. Componentwise monotonicity therefore gives

`sup_q E_q[c_optimistic] <= sup_q E_q[c_completion]`

over the same TV ball. Already materialized memory and build costs are added.

### Information-Theoretic Bound

Every successful binary search code has nominal expected comparison count at
least `H(p)` and maximum depth at least `ceil(log2(n))`. Multiplication by the
smaller calibrated comparison cost preserves a valid execution-cost bound.

### Conditional-Entropy Bound

Closed leaves contribute their exact nominal execution cost. An unresolved
interval with mass `m`, current depth `d`, and conditional distribution `p_I`
contributes at least

`m * d * routing_cost + m * H(p_I) * min_comparison_cost`.

This state-dependent bound distinguishes weak partial trees and tightens during
best-first search.

## Theorem H: Certified Anytime Interval

Let `U` be the score of the best feasible incumbent and let `L_s` be the
combined admissible lower bound of every state remaining in the frontier.
Then

`min(U, min_s L_s) <= OPT <= U`.

The upper inequality follows from feasibility. The lower inequality follows
because the frontier partitions every unexplored completion and each `L_s` is
admissible. Pruned states cannot beat the final incumbent. `QED`

## Replay Verification

The certificate records the initial incumbent, deterministic best-first event
sequence, final incumbent, structural frontier digest, and stopping condition.
The independent verifier reconstructs every state, bound, transition,
incumbent, frontier, gap, and stopping reason.

Floating-point bounds are verified numerically but excluded from the SHA-256
digest. The digest binds structural state identities, avoiding false failures
across supported Python versions.

## Online Corollary

For distributions `p` and `q`, `delta = TV(p,q)`, and any bounded cost vector,

`|E_p[c] - E_q[c]| <= delta * (max(c) - min(c))`.

If a reference solution is within `g` of its optimum and every feasible policy
has cost range at most `R`, its current-distribution regret is at most

`g + 2 * delta * R`.

`online_regret_certificate` implements this mean-execution-cost guarantee. It
does not certify mutation latency or the full TV-DRO plus memory objective.

## Evidence

`results/anytime_validation.csv` contains 12 complete-tree-space oracle
comparisons and 36 trajectories over `n = 16, 32, 64`. Every row is replay
verified. The current matrix reports all 12 oracle matches and monotone
certified intervals. Nonzero gaps remain nonzero claims.

