# Generalized Executable Fallback Model

## Motivation

The original CertiGap model assigns every key in an unresolved interval
`[l,r]` the conservative fixed-round cost `ceil(log2(r-l+1))`. Real fallback
implementations may have different per-key costs. For example, midpoint
lower-bound search on three keys has costs `(2,2,1)`.

The generalized model closes that model/runtime gap without changing the
materialized-prefix interpretation.

## Definition

Let `F(l,r,i)` be the non-negative integer comparison cost of a deterministic
fallback policy for key `i` in interval `[l,r]`. If key `i` reaches that leaf
at materialized depth `d`, define

`C_T^F(i) = d + F(l,r,i)`.

The robust objective remains

`J_eta^F(T) = (1-eta) sum_i p_hat_i C_T^F(i) + eta max_i C_T^F(i)`.

`fixed_rounds` and the exact comparison profile of executable midpoint binary
search are included. A user may also supply a deterministic custom profile.

## Theorem E: Exactness For Any Fixed Fallback

For every deterministic fallback profile `F`, the generalized frontier dynamic
program returns a tree with at most `B` materialized splits minimizing
`J_eta^F`.

### Proof

For a leaf `[l,r]`, its achievable state is exactly

- `A_F(l,r) = sum_{i=l}^r p_hat_i F(l,r,i)`;
- `M_F(l,r) = max_{i=l}^r F(l,r,i)`.

For a materialized split at `k`, every key pays one new comparison. Therefore
the recurrence remains

- `A = P(l,r) + A_left + A_right`;
- `M = 1 + max(M_left,M_right)`.

The structural decomposition of every valid partial tree is unchanged. By
induction on interval length and budget, the recurrence enumerates every
achievable `(A,M)` pair. Pareto dominance is safe because both coefficients in
`(1-eta)A + eta M` are non-negative. Selecting the minimum retained state is
therefore globally optimal. `QED`

## Relation To Classical Alphabetic Trees

Expanding every unresolved interval leaf with its deterministic fallback tree
maps a CertiGap solution to a full alphabetic decision tree. CertiGap optimizes
over the restricted class in which:

1. at most `B` prefix comparisons are freely materialized;
2. every remaining subtree must equal the selected fallback completion.

This differs from a height-limited alphabetic tree, where all internal nodes
are optimized and the constraint is maximum depth rather than the number of
freely materialized prefix nodes.

## Implementation And Verification

- `generalized_frontier_dp_best` implements Theorem E.
- `midpoint_binary_profile` reproduces per-key comparison counts of midpoint
  lower-bound search.
- `verify_serialized_tree_exact` independently recomputes fixed-round tree
  objectives from integer counts and rational `eta`, without floating-point
  dominance or `EPS`.

The rational verifier proves submitted-tree arithmetic, not global optimality.
Global exactness is established by the DP proof and small-instance independent
cross-validation.
