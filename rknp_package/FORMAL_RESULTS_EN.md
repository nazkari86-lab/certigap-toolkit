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
`(array, prefix sum, Fenwick, square-root decomposition, segment tree, sparse
table, point-proxy CertiRange, range-aware CertiRange)`
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
complete eight-candidate portfolio.

The standalone verifier regenerates all eight rows from the trace and
constraints and compares the complete ordered candidate list before checking
the winner and canonical digest. Removing a candidate or changing a score,
feasibility decision, routing tree, holdout evaluation, or selected name is
therefore rejected even if an attacker recomputes the outer digest.

Holdout operations are scored only after candidate construction and do not
enter the selection key. Thus they cannot affect the selected winner. This
theorem is a portfolio-completeness guarantee in declared primitive visits,
not global optimality over unlisted data structures and not a wall-clock
latency guarantee. `QED`

## Corollary L.1: Conditional Safe-Deployment Bound

Let `D_i = C_candidate(i) - C_baseline(i)` for `m` independent IID validation
operations. Suppose `D_i` lies in an interval of width at most `B`, as
recomputed from the declared backend bounds. Hoeffding's inequality gives

`Pr(E[D] > mean(D) + B sqrt(log(1/alpha)/(2m))) <= alpha`.

Adding deterministic amortized build and migration cost `A` preserves the
inequality. Therefore, when Safe AutoIndex deploys specialization only if

`mean(D) + B sqrt(log(1/alpha)/(2m)) + A < -minimum_improvement`,

the probability that its declared expected improvement fails to exceed the
minimum is at most `alpha`, conditional on the stated IID and bounded-cost
assumptions. If the inequality does not hold, the declared safe baseline is
retained. Test data is evaluated only after this decision and cannot alter it.

The verifier independently recomputes the baseline, `B`, confidence radius,
transition cost, deployment decision, and test scores. The result does not
cover dependent temporal traces, inaccurate hardware calibration, or
unmodeled wall-clock effects. `QED`

## Corollary L.2: Optional-Stopping-Safe Validation

Let `X_1, X_2, ...` be independent identically distributed
candidate-minus-baseline costs with mean `mu`, contained in an interval of
width `B`. Fix `alpha` in `(0,1)` and allocate

`alpha_t = alpha / (t(t+1))`.

Define

`U_t = mean(X_1,...,X_t) + B sqrt(log(1/alpha_t)/(2t))`.

Then

`Pr(exists t >= 1 such that mu > U_t) <= alpha`.

For each fixed `t`, the one-sided Hoeffding inequality bounds the corresponding
failure probability by `alpha_t`. The telescoping identity

`sum_{t=1}^infinity 1/(t(t+1)) = 1`

gives `sum_t alpha_t = alpha`; a union bound therefore proves simultaneous
coverage over every finite prefix. Consequently `U_tau` remains valid at any
data-dependent stopping time `tau`, including the first prefix crossing a
deployment threshold.

Adding deterministic amortized transition cost and a non-negative required
improvement preserves the comparison. This result does not establish
generalization after distribution change and does not cover dependent
validation operations. `QED`

## Theorem L.3: Adapted E-process Deployment And Revocation

Let `Y_t` be adapted to filtration `F_t`, satisfy
`E[Y_t | F_{t-1}] <= 0`, and lie almost surely in an interval of width `B`.
For every fixed `lambda > 0`, define

`E_t(lambda) = exp(lambda sum_{i=1}^t Y_i - lambda^2 B^2 t / 8)`.

Conditional Hoeffding's lemma gives

`E[exp(lambda Y_t - lambda^2 B^2/8) | F_{t-1}] <= 1`.

Thus `E_t(lambda)` is a non-negative supermartingale beginning at one. Any
fixed convex mixture over declared lambda values is also a non-negative
supermartingale beginning at one. Ville's inequality yields

`Pr(sup_t E_t >= 1/alpha) <= alpha`.

For deployment the implementation takes
`Y_t = -(D_t + A + m)`, so the null is
`E[D_t | F_{t-1}] >= -(A+m)` at every monitored step. For revocation it starts
a new process after deployment with `Y_t = D_t-r`, whose null is
`E[D_t | F_{t-1}] <= r`. Here `D_t` is candidate-minus-baseline work, `A` is
amortized transition cost, `m` is required improvement, and `r` is tolerated
harm. Each process has its own alpha budget. Crossing controls the
corresponding false decision under its null at arbitrary stopping times.

The theorem does not bound detection delay, losses before revocation, future
behavior after monitoring ends, or observations outside the declared bounded
structural model. `QED`

## Theorem M: Generated C++ Configuration Fidelity

Let `A` be an AutoIndex artifact accepted by the independent verifier. The
code generator first verifies `A`, then emits its selected backend, aggregate,
key count, artifact digest, and, for CertiRange, the deterministically completed
topology. Identical artifact and namespace inputs therefore emit identical
header bytes.

For array, prefix sum, Fenwick, square-root decomposition, segment-tree, and
sparse-table backends, the generated configuration selects the corresponding
executable recurrence directly. For CertiRange, the emitted topology is the
same completion whose canonical hash was checked in `A`. Structural induction
over that topology proves every internal state is the configured monoid
aggregate of its interval. The same induction proves range queries and point
updates agree with the array specification.

A C++ snapshot is an independent value-copy of all runtime state. Subsequent
updates cannot mutate the copy, so snapshot observations preserve the
pre-update state. This proves semantic isolation but only with `O(n)` copying;
the stronger Python path-copy complexity is not claimed for generated C++.

Thus generated C++ execution preserves the selected configuration and
point/range/update semantics. This is source-level fidelity, not equivalence
of machine code across C++ compilers. `QED`

## Proposition N: Adaptive Runtime Portfolio Minimum

Given a nonempty accumulated runtime profile and valid options, the
single-header selector constructs exactly eight ordered candidate reports:
array, prefix sum, Fenwick, square-root decomposition, segment tree, sparse
table, point-weighted CertiRange, and range-coverage-weighted CertiRange. It
computes every report with the same
declared mean/tail/resource objective, filters infeasible candidates, and scans
the complete list with deterministic score, memory, and order tie-breaking.
The returned backend is therefore the minimum reported feasible candidate.

Capability filtering rejects prefix sum and Fenwick outside sum workloads and
sparse tables outside idempotent min/max workloads. Both adaptive CertiRange
candidates are completed into singleton leaves under
the declared depth cap. The aggregate, query, and update correctness argument
from Theorem J applies to these completed topologies. `snapshot()` copies all
value, runtime, and profile state, so later mutation cannot change the copy.

This is an in-process portfolio statement. Unlike Theorems L and M, it has no
independent artifact regeneration and makes no global claim over omitted data
structures. The two adaptive routing builders are deterministic weighted
heuristics, not globally optimal topology solvers.

## Theorem O: Exact Variable-Block Robust-Upper Synthesis

Fix a trace, hardware profile, aggregate, maximum block count, and maximum
block width. For operation `o`, legal partition `P`, and block `B` in `P`,
let the nonnegative declared contribution be `c(o,B)`. Runtime work is
additive: `C(o,P) = sum_{B in P} c(o,B)`.

Linearity gives
`mean_o C(o,P) = sum_{B in P} mean_o c(o,B)`, while the maximum of sums is at
most the sum of maxima:
`max_o C(o,P) <= sum_{B in P} max_o c(o,B)`.

Thus the sum of per-block `(1-eta) mean + eta max` terms, plus additive
memory/build penalties, is an upper bound on the whole-partition robust
objective. The recurrence
`DP[b,r] = min_l DP[b-1,l-1] + block_score(l,r)` enumerates every legal final
block `[l,r]`; induction on `b` proves that it returns the minimum certified
upper score for every exact block count. Taking the feasible minimum over all
published block counts proves completeness in the declared grammar. The
independent verifier reconstructs this recurrence and rejects a changed or
omitted frontier. `QED`

This theorem does not claim that the conservative upper-bound minimizer is the
minimum measured tail-latency design, nor that supplied hardware measurements
transfer to another machine.

## Theorem P: Exact Switch-Budget Tracking Oracle

Fix a finite candidate set `S`, initial candidate `s0`, non-negative operation
costs `c_t(s)`, a positive uniform migration cost `d`, and switch budget `K`.
Let `D[t,s,k]` be the minimum total service plus migration cost through
operation `t`, ending in `s` after exactly `k` changes of state, counting a
change from `s0` at the first operation. Initialization assigns zero only to
`(s0,0)` and infinity to every other state. The recurrence

`D[t,s,k] = c_t(s) + min_y D[t-1,y,k-[y != s]] + d[y != s]`

enumerates every possible predecessor of every feasible path exactly once.
Induction on `t` therefore proves each table entry is optimal for its endpoint
and exact switch count. Taking the minimum over `s` and `k <= K` returns the
global K-switch optimum. Stored predecessors reconstruct an optimal path.
`QED`

The tracking verifier implements this recurrence independently and also
replays the causal Work Function Algorithm trajectory. The classical
`(2|S|-1)` WFA competitive theorem is cited from the metrical-task-system
literature; it is not newly proved here. The certificate's exact new
instance-level statement is realized cost minus exact K-switch oracle cost.

## Theorem Q: Exactness in a Fixed Candidate-Threshold Grammar

Fix a normalized weight vector `p`, a split budget `B`, distrust parameter
`eta in [0,1]`, and integer candidate limit `K >= 4`. For each non-singleton
interval `[l,r]`, let `t = r-l` be its number of legal thresholds and define
the ordered candidate set `C_K(l,r)` exactly as in the C++ implementation:

1. if `t <= K`, `C_K(l,r) = {l,...,r-1}`;
2. otherwise include `l`, `r-1`, midpoint `floor((l+r-1)/2)`, every
   `l + floor(qt/(K-1))` for `q=1,...,K-3`, and the first prefix index at or
   after each of the seven targets `P(l-1)+q P(l,r)/8`, `q=1,...,7`.

Duplicate candidates are removed, and values outside `[l,r-1]` are excluded.
Thus `C_K(l,r)` is a fixed, nonempty subset of the legal thresholds before
the recurrence starts. Let `G_K(l,r,b)` be the family of valid CertiGap trees
on `[l,r]` with at most `b` splits such that each split threshold on every
visited interval belongs to that interval's `C_K` set.

Then `candidate_restricted_frontier_dp_best(p,B,eta,K)` returns a tree
minimizing `J_eta(T)` over `G_K(1,n,B)`.

### Lemma Q.1: Restricted Structural Decomposition

Every tree in `G_K(l,r,b)` is exactly one of:

1. the unsplit leaf `[l,r]`; or
2. a root split at one `k in C_K(l,r)` and two trees in
   `G_K(l,k,b_L)` and `G_K(k+1,r,b_R)` for some nonnegative `b_L,b_R` with
   `b_L+b_R <= b-1`.

Conversely, combining any two such children under any `k in C_K(l,r)` gives a
tree in `G_K(l,r,b)`.

### Proof of Lemma Q.1

The root of a valid ordered partial tree is either its single unresolved leaf
or a legal threshold split. Membership in `G_K` restricts that threshold to
`C_K(l,r)`. The two child intervals are uniquely `[l,k]` and `[k+1,r]`; the
root consumes one split, so their actual split counts sum to at most `b-1`.
The candidate rule depends only on `p,l,r,K`, hence the same definition applies
recursively to both children. The converse follows by attaching the two valid
children beneath the permitted root split. `QED`

### Proof of Theorem Q

Use induction on the lexicographically ordered pair `(r-l,b)`.

If `l=r` or `b=0`, Lemma Q.1 permits only the leaf, which the recurrence
inserts. Assume the statement for every smaller interval-budget pair. For a
non-base subproblem, the recurrence first inserts that same leaf. It then
enumerates every `k in C_K(l,r)` and every exact budget partition
`b_L+b_R=b-1`. Although the model allows *at most* `b` splits, this enumeration
is complete: a tree using child counts `s_L+s_R <= b-1` is included by choosing
`b_L=s_L` and `b_R=b-1-s_L`; the right child may simply leave unused budget.

By the induction hypothesis, each recursive frontier contains a representative
for every nondominated achievable child pair. Lemmas 2 and 3 compute the
combined average and maximum costs exactly. Hence, before compression, the
recurrence contains a state for every tree in `G_K(l,r,b)`.

Compression first retains a minimum-average representative for each integer
maximum cost and then removes only coordinatewise dominated states. Equal
coordinate pairs have identical scalarized objective. Lemma 4 shows that a
strictly dominated pair cannot be optimal for any `eta in [0,1]`. Thus no
minimizer is lost. Selecting the minimum scalarized state from the retained
frontier therefore returns the optimum over `G_K(l,r,b)`, and in particular at
the root over `G_K(1,n,B)`. `QED`

## Corollary Q.1: Full-Grammar Limit

If `K >= n-1`, then every interval `[l,r]` has at most `n-1 <= K` legal
thresholds. By case 1 of the definition, every `C_K(l,r)` contains all legal
thresholds, so `G_K(1,n,B)` is the unrestricted tree family. Therefore the
candidate-restricted frontier DP and Theorem A have the same optimal objective.

The repository validates this equality and independently compares the
candidate-restricted DP with exhaustive enumeration of `G_K` on proof-sized
cases.

## Corollary Q.2: Exact Pruning/Truncation Gap Decomposition

Let `OPT` be the unrestricted optimum, `R` the optimum in `G_K`, and `H` any
tree returned by the C++ beam with the same threshold rule. Since the beam
searches only a subset of `G_K`, `J(OPT) <= J(R) <= J(H)`. Consequently,

`J(H) - J(OPT) = [J(H) - J(R)] + [J(R) - J(OPT)]`,

where both bracketed terms are non-negative. The first is loss from retaining
only finitely many beam states; the second is loss from excluding thresholds.
`generate_pruning_decomposition.py` recomputes these values against the exact
oracle for every published proof-sized row.

This is a diagnostic identity, not an approximation guarantee: neither term
is bounded independently of the input by this theorem.

## Theorem R: Certified Anytime Interval for the Full Threshold Grammar

Fix normalized weights `p`, budget `B`, and `eta in [0,1]`. An ordinary
anytime search state consists of a partial tree `S`, a set `O` of its unresolved
leaves, and its used split count. Define the partial per-key cost vector by

- `d(i)` for a key in an unresolved leaf at routing depth `d(i)`;
- `d(i) + ceil(log2(|I|))` for a key in a closed leaf `I`.

Let `L_local(S)` be the CertiGap objective evaluated on this vector, and let
`L_global` be the entropy/max-cost lower bound for the original instance. The
state lower bound is `L(S) = max(L_local(S), L_global)`.

Suppose the search uses the canonical expansion that either closes the first
unresolved leaf or splits it at every legal threshold, and publishes a replay
certificate containing every processed transition and its remaining frontier.
Let `U` be the score of the best feasible incumbent and

`L = min(U, min_{S in frontier} L(S))`,

with the empty-frontier minimum interpreted as `U`. Then the independently
verified certificate proves `L <= OPT <= U` and `U - OPT <= U - L`.

### Proof

For every unresolved key, any completion either stops the leaf and adds its
non-negative fallback cost, or makes one or more routing comparisons before
eventually adding a non-negative fallback cost. Its final cost is therefore at
least its partial cost. Closed-leaf costs are already final. Both weighted
average cost and maximum cost are monotone under componentwise cost increase;
thus `L_local(S)` lower-bounds every completion of `S`. `L_global` lower-bounds
every feasible tree in the original grammar, so their maximum remains a valid
state lower bound.

The canonical close-or-all-threshold expansion partitions every completion of
a state: its first unresolved leaf is either closed or has one unique root
threshold. Induction over expansion history shows that the unprocessed
frontier, together with previously pruned states, covers the full tree grammar
without overlap. A pruned state has lower bound at least the incumbent present
when it was pruned; the final incumbent can only improve, so it also has lower
bound at least `U`. Every pending completion has score at least its recorded
`L(S)`. Taking the minimum over these alternatives proves `OPT >= L`.
The incumbent is itself feasible, hence `OPT <= U`. Subtracting `OPT >= L`
from `U` proves the additive bound. `QED`

The certificate is exact when `U-L` is zero. This is an a-posteriori additive
guarantee for the full threshold grammar, not a fixed multiplicative ratio and
not a claim that the C++ candidate-pruned beam itself is exact.

## Theorem S: Finite-Portfolio Checkpoint Selection Coverage

Fix `C` candidate training programs and `T` positive checkpoint epochs before
examining validation labels. Assume every program's training path uses only the
training split and that the `m` validation examples are IID. For observed
validation accuracy `a_hat(c,t)`, define

`eps = sqrt(log(2CT/alpha)/(2m))`.

Then, with probability at least `1-alpha`, every candidate/checkpoint program
simultaneously satisfies

`|a_hat(c,t) - a(c,t)| <= eps`.

Let `R` be the set of checkpoint programs actually evaluated by CertiGap-ML
and let `s` be its selected final survivor. With clipped intervals
`LCB(r), UCB(r)`, the certificate's reported quantity

`G = max(0, max_{r in R} UCB(r) - LCB(s))`

satisfies

`max_{r in R} a(r) - a(s) <= G`.

### Proof

For one fixed candidate/checkpoint program, Hoeffding's two-sided inequality
with the displayed `eps` gives failure probability at most
`alpha/(CT)`. The training paths are fixed without validation labels, so this
statement applies to every program even when the policy later chooses which
ones to inspect or continue. A union bound over all predeclared `C*T` programs
gives simultaneous coverage with probability at least `1-alpha`.

On this event, `a(r) <= UCB(r)` for every observed program and
`a(s) >= LCB(s)`. Therefore

`max_{r in R} a(r) - a(s) <= max_{r in R} UCB(r) - LCB(s) <= G`.

Clipping to `[0,1]` preserves validity, and taking the maximum with zero only
expresses the nonnegative nature of regret. `QED`

This theorem compares only *evaluated checkpoint programs*. It does not bound
the quality a pruned candidate might have reached after unobserved future
epochs, and it does not claim general AutoML optimality.