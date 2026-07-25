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

Theorems A and B are now proof-complete at the mathematical level used by the prototype.
What still remains open is not the correctness of the implemented exact DP or the contamination identity,
but the strongest negative and asymptotic statements about greedy baselines and larger structural families.