# Formal Results

## Definitions

Let `T` be a valid CertiGap tree on ranks `1..n`.

- Every internal node is a threshold comparison `x <= x_k?`.
- Every leaf is a contiguous unresolved interval `[l, r]`.
- The depth of the root is `0`.
- If key `i` reaches interval leaf `I = [l, r]` at depth `d`, then
  `C_T(i) = d + ceil(log2(|I|))`.

For a probability vector `p = (p_1, ..., p_n)`:

- `Avg_p(T) = sum_i p_i C_T(i)`
- `Max(T) = max_i C_T(i)`

For distrust parameter `eta in [0,1]`:

- `J_eta(T) = (1 - eta) Avg_p_hat(T) + eta Max(T)`

The split budget of `T` is the number of internal nodes and must satisfy `|T| <= B`.

## Lemma 1: Structural Decomposition

Every valid CertiGap tree on interval `[l, r]` with budget `b` is exactly one of:

1. a single interval leaf `[l, r]`, or
2. a root split at some `k` with `l <= k < r`, whose left subtree is valid on `[l, k]`,
   whose right subtree is valid on `[k+1, r]`, and whose subtree budgets sum to `b - 1`.

### Proof

If the root is a leaf, we are in case 1.
Otherwise the root is a threshold comparison and so must split the contiguous interval `[l, r]`
into two contiguous subintervals `[l, k]` and `[k+1, r]` for some `k`.
Because CertiGap trees preserve contiguity, the left and right subtrees are valid subtrees on those intervals.
The root itself consumes one split, so the remaining budgets must sum to `b - 1`.
No other form is possible. `QED`

## Lemma 2: Additive Average-Cost Recurrence

Suppose tree `T` on `[l, r]` has root split at `k`, left subtree `T_L`, right subtree `T_R`, and let

- `P(l, r) = sum_{i=l}^r p_hat_i`.

Then

`Avg_p_hat(T) = P(l, r) + Avg_p_hat(T_L) + Avg_p_hat(T_R)`.

### Proof

Every key in `[l, r]` pays one comparison at the root, contributing total mass `P(l, r)`.
After the root, keys routed left incur exactly the cost of `T_L`, and keys routed right incur exactly the cost of `T_R`.
Therefore the expectation decomposes additively. `QED`

## Lemma 3: Worst-Case Recurrence

Under the same assumptions,

`Max(T) = 1 + max(Max(T_L), Max(T_R))`.

### Proof

Every root-to-leaf path in `T` contains the root comparison plus a path entirely inside either `T_L` or `T_R`.
So the largest key cost is exactly one plus the larger subtree maximum. `QED`

## Lemma 4: Dominance Elimination Is Safe

Let states `S1 = (A1, M1)` and `S2 = (A2, M2)` satisfy

- `A1 <= A2`
- `M1 <= M2`
- and at least one inequality is strict.

Then for every `eta in [0,1]`,

`(1 - eta) A1 + eta M1 <= (1 - eta) A2 + eta M2`,

with strict inequality whenever `eta` gives positive weight to a strict component.

### Proof

Both coefficients `(1 - eta)` and `eta` are nonnegative on `[0,1]`.
Multiplying coordinatewise inequalities by nonnegative coefficients and summing preserves the inequality. `QED`

## Theorem A: Exact Optimality of the Frontier Dynamic Program

For every interval `[l, r]`, budget `b`, and distrust parameter `eta in [0,1]`,
the frontier DP returns a tree minimizing

`(1 - eta) Avg_p_hat(T) + eta Max(T)`

among all valid trees on `[l, r]` with at most `b` splits.

### Proof

We proceed by induction on the pair `(r - l, b)` ordered lexicographically.

### Base Cases

If `l = r`, there is only one key. The only valid tree is the leaf `[l, l]`, so the DP is exact.

If `b = 0`, no split is allowed. The only valid tree is the leaf `[l, r]`, so the DP is exact.

### Inductive Step

Assume the theorem holds for all smaller subproblems.
Consider a target subproblem `[l, r]` with budget `b`.

By Lemma 1, every valid tree is either:

1. the stop state `[l, r]`, or
2. a root split at some `k` with a budget partition `b_L + b_R = b - 1`.

For case 1, the DP explicitly includes the corresponding leaf state.

For case 2, by the induction hypothesis the left and right frontiers produced by the DP contain exactly the nondominated achievable states for `[l, k]` and `[k+1, r]`.
Combining any such pair with root split `k` yields a valid achievable state on `[l, r]`.
By Lemma 2 and Lemma 3, its average and maximum components are exactly those used by the recurrence implemented in the DP.

Therefore before compression, the DP enumerates every achievable state of every valid tree on `[l, r]`.

The compression step removes only dominated states.
By Lemma 4, a dominated state can never beat its dominator for any `eta in [0,1]`.
Hence compression preserves the entire set of potentially optimal states.

Finally, the DP selects the state minimizing

`(1 - eta) A + eta M`

over the preserved frontier.
Since every valid tree corresponds to some enumerated state and no potentially optimal state was removed,
the selected tree is globally optimal. `QED`

## Theorem B: Contamination Robustness Identity

Let the true query distribution be

`p = (1 - eta) p_hat + eta q`,

where `q` is any probability distribution over the keys.
Then for every tree `T`,

`max_q Avg_p(T) = (1 - eta) Avg_p_hat(T) + eta Max(T)`.

### Proof

By linearity of expectation,

`Avg_p(T) = (1 - eta) Avg_p_hat(T) + eta Avg_q(T)`.

The first term is independent of `q`.
So maximizing over `q` reduces to maximizing `Avg_q(T)`.

Because `q` ranges over all probability distributions on a finite set, its expectation of `C_T(i)` is maximized by placing all mass on a maximizer of `C_T(i)`.
Hence

`max_q Avg_q(T) = max_i C_T(i) = Max(T)`.

Substituting yields

`max_q Avg_p(T) = (1 - eta) Avg_p_hat(T) + eta Max(T)`.

This is exactly the CertiGap robust objective. `QED`

## Current Formal Status

Theorems A and B are proof-complete at the mathematical level used by the prototype.
Theorem C below gives a concrete asymptotic negative result for the implemented one-step greedy rule.
The remaining open work is stronger approximation/structural results and external or machine-assisted formal review.

## Theorem C: An Infinite Family Where One-Step Greedy Is Arbitrarily Suboptimal

For every integer `m >= 3`, let `n = 2^m`, let `B = 3`, let `eta = 0`, and assign weight
`W = n*m` to keys `n/2` and `n/2 + 1` and weight `1` to every other key.
Then the implemented one-step greedy algorithm makes no split, while a valid three-split tree has objective at least

`[2W(m - 2) - (n - 2)] / [2W + n - 2]`

smaller than greedy. Consequently the greedy absolute objective gap grows without bound as `m` grows.

### Proof

The unsplit leaf has cost `m` for every key because `n = 2^m`.
Consider any first split at threshold `k`.

If `k = n/2`, both children have size `n/2`, so every key still has cost `1 + log2(n/2) = m`; this split has zero gain.

If `k < n/2`, both hot keys lie in the larger right child and their cost rises to `m + 1`.
Let `c = 1 + ceil(log2(k))` be the left-child cost. The unnormalized change in average cost is

`k(c - m) + (n - k - 2) + 2W`.

Since `c >= 1` and `k <= n/2 - 1`, this is at least

`2W - (n/2 - 1)(m - 2) > 0`

for `W = n*m`. The case `k > n/2` is symmetric. Thus no first split strictly improves the objective, and the greedy rule stops at the unsplit leaf.

Now use the explicit tree with root split at `n/2`, a left split at `n/2 - 1`, and a right split at `n/2 + 1`.
Both hot keys have cost `2`; each cold key has cost `m + 1`.
Its objective is therefore

`[4W + (n - 2)(m + 1)] / [2W + n - 2]`.

Subtracting this from greedy's cost `m` gives exactly

`[2W(m - 2) - (n - 2)] / [2W + n - 2]`.

This is positive for every `m >= 3` and is asymptotic to `m - 2`, so the gap is unbounded. Since the optimum is no worse than this explicit tree, the same expression is a valid lower bound on greedy's gap to optimum. `QED`

## Proposition D: Cost-Cap DP Exactness

For a fixed cap `h`, the cost-cap recurrence stores the minimum average cost over all valid trees whose relative maximum cost is at most `h`.
The leaf case is feasible exactly when `ceil(log2(|I|)) <= h`; every split decreases the remaining cap by one for both children.
Induction on interval length and budget proves the recurrence. Minimizing the resulting candidates over `h` recovers the optimum of `J_eta`, because every tree appears at its own maximum cost cap.

The repository cross-validates this recurrence against both the Pareto-frontier DP and brute force on the generated small-instance suite.

## Theorem E: Exact Optimality With Executable Fallback Profiles

Let `F(l,r,i)` be any deterministic non-negative per-key comparison cost for
resolving key `i` inside interval `[l,r]`. Replacing the fixed leaf cost with

- `A_F(l,r) = sum_i p_hat_i F(l,r,i)`;
- `M_F(l,r) = max_i F(l,r,i)`

preserves the split recurrences in Lemmas 2 and 3. The structural induction and
dominance argument of Theorem A therefore apply unchanged. The generalized
frontier DP is exact for every fixed fallback profile.

The full statement, relation to height-limited alphabetic trees, implementation,
and scope are given in `GENERALIZED_FALLBACK.md`.

## Theorem F: Exact Worst-Case Expectation in a Finite TV Ball

Let `p` be a nominal distribution, `c_i` finite per-key execution costs, and
`rho` a total-variation radius. The sorted mass-transfer algorithm implemented
by `worst_case_tv_expectation` returns

`max_q sum_i q_i c_i`

over all distributions satisfying `TV(q,p) <= rho`.

Every feasible probability change decomposes into equal donor-to-receiver mass
transfers. If a solution removes mass from a more expensive donor while a
cheaper donor still has removable mass, exchanging the donors cannot decrease
the objective. The symmetric exchange applies to receivers. Thus an optimum
exists that transfers mass in ascending donor-cost and descending receiver-cost
order. The algorithm performs exactly these transfers until the TV budget or
all profitable capacity is exhausted. `QED`

This theorem certifies the robust score of a fixed candidate.

## Theorem G: Direct TV-DRO Exhaustive Optimality

For a key universe `[1,n]`, split budget `B`, declared memory constraint, and a
finite configured fallback set, direct-TV search returns a globally
minimum-score ordered partial tree.

For exact split total zero, the only tree on interval `[l,r]` is its unresolved
leaf. For `s > 0`, every tree has a unique root threshold `k`, a left subtree
with `s_L` splits, and a right subtree with `s - 1 - s_L` splits. Conversely,
combining any recursively enumerated pair under a legal `k` produces a unique
valid tree. Induction on `s` proves complete, duplicate-free enumeration.

Theorem F gives the exact robust expectation for each enumerated tree and
fallback. Memory-infeasible trees are removed by the declared constraint.
Taking the minimum remaining score is therefore globally optimal. `QED`

The guarantee applies when exhaustive direct search is enabled. For larger
instances, AutoDRO verifies selection over a deterministically regenerated
heuristic portfolio but does not claim global tree-space optimality.

## Theorem H: Certified Anytime TV-DRO Interval

For a partial search state, assign every key in an unresolved leaf its already
incurred routing cost and zero future fallback cost. This vector is
componentwise no larger than the execution-cost vector of any completion.
Worst-case expectation over a fixed TV ball is monotone under componentwise
inequality. Adding only already incurred memory and build penalties therefore
gives an admissible state lower bound.

The information-theoretic and conditional-entropy bounds in
`ANYTIME_TV.md` are independently admissible, so their maximum with the
componentwise bound is admissible.

The canonical close-or-split expansion partitions every feasible completion.
If `U` is a feasible incumbent and `L` is the minimum remaining state bound,
then

`min(U, L) <= OPT <= U`.

The replay verifier reconstructs the complete processed prefix and remaining
frontier, so the reported interval remains valid at every declared expansion
limit. `QED`

## Theorem I: Online Mean-Cost Regret Under TV Drift

Let `delta = TV(p,q)`. For any cost vector with range at most `R`,

`|E_p[c] - E_q[c]| <= delta R`.

Let `T_q` have reference-distribution suboptimality at most `g`, and let `T_p`
be optimal under `p`. Applying the shift inequality to `T_q` and `T_p` gives

`E_p[C(T_q)] - E_p[C(T_p)] <= g + 2 delta R`.

This is the bound implemented by `online_regret_certificate`. It applies to
mean execution cost and does not silently extend to rebuild latency or an
unmodeled storage-engine objective. `QED`

## Theorem J: Dynamic CertiRange Correctness And Height Bound

Let a valid partial routing tree over `[1,n]` be completed recursively. A
routing split is retained only when balanced completion of both children fits
inside the remaining depth. Otherwise the entire current interval is replaced
by its midpoint completion.

Every retained split partitions its parent into `[l,k]` and `[k+1,r]`;
midpoint completion has the same property. Structural induction therefore
shows that the completed leaves are exactly the singleton partition
`[1,1],...,[n,n]`. Midpoint completion of `s` keys has height
`ceil(log2(s))`, and the retention check reserves at least that much depth for
both children. Induction on remaining depth proves completed height at most
the declared `max_depth`.

Each internal aggregate is the monoid combination of its children. Induction
on subtree size proves that it equals the aggregate of its full interval.
Point update replaces exactly the root-to-key path and recomputes those
aggregates, so the new root is correct while every node reachable from an old
root is unchanged. Hence pre-update snapshots remain consistent.

A range query stops at disjoint and fully covered nodes. Only nodes on the two
boundary paths can recurse; at each level there are at most two such nodes and
their checked siblings. Thus it visits `O(h)` nodes for tree height `h`; the
implementation exports the conservative bound `4h+1`. `QED`

## Proposition K: Range-Aware Bounded-Search Dominance

The range-aware beam starts with the unsplit routing tree, whose deterministic
completion is the balanced baseline, and records it as the incumbent. The
incumbent changes only after exact mixed-trace evaluation reports a strictly
smaller objective. Therefore the returned candidate is never worse than this
included balanced completion on the declared training workload.

This proposition is a portfolio-dominance statement, not global optimality.
Complete small routing spaces are separately enumerated to validate the search
implementation.

## Theorem L: Certified AutoIndex Portfolio Minimum

Fix the ordered portfolio
`(array, Fenwick, segment tree, point-proxy CertiRange, range-aware CertiRange)`
and a training trace. For each candidate, the compiler deterministically
reconstructs its topology, declared resources, feasibility, and per-operation
primitive-visit vector. Its score is therefore a deterministic function of the
trace and constraints.
Optional positive per-backend coefficients convert raw visits into calibrated
work units and are part of the independently regenerated constraints.

The compiler retains every candidate, including infeasible candidates and
their rejection reasons. It chooses the lexicographic minimum of training
score, memory slots, and published portfolio position among feasible rows.
Consequently the selected candidate has minimum declared score over the
complete five-candidate portfolio.

The standalone verifier regenerates all five rows from the trace and
constraints and compares the complete ordered candidate list before checking
the winner and canonical digest. Removing a candidate or changing a score,
feasibility decision, routing tree, holdout evaluation, or selected name is
therefore rejected even if an attacker recomputes the outer digest.

Holdout operations are scored only after candidate construction and do not
enter the selection key. Thus they cannot affect the selected winner. This
theorem is a portfolio-completeness guarantee in declared primitive visits,
not global optimality over unlisted data structures and not a wall-clock
latency guarantee. `QED`
