# CertiGap Technical Note

## Formal Model

Let the sorted keys be `x_1 < x_2 < ... < x_n`.
A valid CertiGap tree consists of:

- internal split nodes of the form `x <= x_k?`;
- interval leaves `[l, r]`, each representing an unresolved contiguous rank interval.

If key `x_i` lands in interval leaf `I = [l, r]` at depth `d`, then

`C_T(i) = d + ceil(log2(|I|))`.

For a predicted query distribution `p_hat` and distrust parameter `eta`, the robust objective is

`J_eta(T) = (1 - eta) * sum_i p_hat_i C_T(i) + eta * max_i C_T(i)`.

The budget constraint is

`|T| <= B`,

where `|T|` is the number of split nodes.

## Frontier DP State

For interval `[l, r]` and split budget `b`, define the Pareto frontier

`F(l, r, b)`

as the set of nondominated pairs `(A, M)` where:

- `A` is achievable average cost contribution on `[l, r]`;
- `M` is achievable worst-case cost contribution on `[l, r]`.

A pair `(A1, M1)` dominates `(A2, M2)` if:

- `A1 <= A2`,
- `M1 <= M2`,
- and at least one inequality is strict.

Only nondominated states need to be kept, because for every `eta in [0,1]`,

`(1 - eta) * A1 + eta * M1 <= (1 - eta) * A2 + eta * M2`.

## DP Recurrence

Every valid solution is either:

1. a stop state:
   - one leaf `[l, r]`;
2. or a split at `k` with budgets `b_L + b_R = b - 1`.

Therefore:

- stop state contributes
  `A = P(l, r) * ceil(log2(r - l + 1))`,
  `M = ceil(log2(r - l + 1))`;
- split state contributes
  `A = P(l, r) + A_L + A_R`,
  `M = 1 + max(M_L, M_R)`.

This is exactly the recurrence implemented in the prototype.

## Independent Cost-Cap DP

The second exact solver stores `A[l, r, b, h]`: the minimum average-cost contribution for interval `[l, r]`, budget `b`, and relative maximum-cost cap `h`. For a split, both children receive cap `h - 1`; no Cartesian product of Pareto states is required. Minimizing across feasible caps recovers the robust objective.

## Proof-Carrying Branch And Bound

For proof-sized instances, `branch_and_bound_exact` returns an exhaustive trace. Every state either terminates one open leaf, branches on every legal threshold of that leaf, or is pruned only when its local depth-based lower bound is no better than the submitted incumbent. `verify_branch_and_bound_certificate` reconstructs all legal branches and validates every pruning inequality without importing a search solver.

## Why Greedy Fails

A one-step greedy policy asks whether a split is immediately beneficial.
But CertiGap has complementarities:

- a first split can look weak or neutral by itself;
- after that split, a second split may isolate a hot interval and become highly profitable.

Therefore local gain is not sufficient to recover the global optimum.

The automatically generated counterexample search in `generate_counterexamples.py` is intended to turn this into a formal proposition family.

## Lower Bounds

The prototype currently combines:

1. an entropy-style lower bound for the average-cost component;
2. a Lagrangian lower bound obtained from unconstrained optima across budgets.

For small instances, the report generator also computes the exact optimum. This is a diagnostic comparison, not an independent certificate check. The standalone verifier only checks a submitted tree and certificate arithmetic; it does not run a search solver.

## Current Mathematical Status

- exact solver: implemented, checked against brute force on a systematic small-instance random family, and cross-checked against the C++ exact solver on reference cases;
- robustness identity: proof draft included in `FORMAL_RESULTS.md`;
- greedy counterexample family: Theorem C proves an unbounded absolute-gap family for the implemented one-step rule;
- Theorems A and B: proof drafts are included, but they are not machine-verified or externally peer-reviewed.
