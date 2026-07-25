# CertiGap Appendix

## Certificate Examples

# CertiGap Certificate Examples

## zipf, n=8, B=2, eta=0.15

- Upper bound: `2.879325`
- Lower bound: `2.879325`
- Certified gap: `0.000000`
- Exact gap: `0.000000`
- Bound source: `lagrangian`
- Splits: `[{'interval': [1, 8], 'threshold': 2}, {'interval': [3, 8], 'threshold': 4}]`

## hot_middle, n=12, B=3, eta=0.15

- Upper bound: `3.291667`
- Lower bound: `3.291667`
- Certified gap: `0.000000`
- Exact gap: `0.000000`
- Bound source: `lagrangian`
- Splits: `[{'interval': [1, 12], 'threshold': 6}, {'interval': [7, 12], 'threshold': 8}, {'interval': [1, 6], 'threshold': 4}]`

## hot_tail, n=16, B=4, eta=0.30

- Upper bound: `3.854545`
- Lower bound: `3.854545`
- Certified gap: `0.000000`
- Exact gap: `0.000000`
- Bound source: `lagrangian`
- Splits: `[{'interval': [1, 16], 'threshold': 13}, {'interval': [14, 16], 'threshold': 14}, {'interval': [1, 13], 'threshold': 8}, {'interval': [9, 13], 'threshold': 12}]`

# CertiGap Speed and Quality Summary

## Small Cases With Exact Reference

- Exact mean time: `2.567 ms`
- Beam mean time: `4.573 ms`
- Greedy mean time: `0.212 ms`
- Balanced mean time: `0.012 ms`
- Weighted mean time: `0.017 ms`
- Beam mean absolute objective gap vs exact: `0.000979`
- Greedy mean absolute objective gap vs exact: `0.114157`
- Balanced mean absolute objective gap vs exact: `0.447373`
- Weighted mean absolute objective gap vs exact: `0.198609`
- Beam mean relative objective gap vs exact: `0.03%`
- Greedy mean relative objective gap vs exact: `3.48%`

## Large Cases Without Exact Reference

- Beam mean time: `50.828 ms`
- Greedy mean time: `1.341 ms`
- Balanced mean time: `0.022 ms`
- Weighted mean time: `0.037 ms`

## Solver Tradeoff

- `exact` is the reference solver for the measured small instances.
- `beam` is near-exact on the measured small cases, but is not faster than exact there; this benchmark does not establish a crossover point.
- `greedy` is usually faster but can be substantially worse on structured skewed tasks.
- `balanced` and `weighted` are cheap baselines, but quality is systematically weaker on skewed workloads.

# Greedy Counterexamples

Top automatically discovered hot-block instances where one-step greedy is much worse than exact.

| n | B | eta | hot start | hot width | hot weight | greedy absolute gap | beam absolute gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 3 | 0.00 | 5 | 2 | 24.0 | 1.6429 | 0.0000 |
| 10 | 4 | 0.00 | 5 | 2 | 24.0 | 1.6429 | 0.0000 |
| 12 | 4 | 0.00 | 7 | 2 | 24.0 | 1.5172 | 0.0000 |
| 10 | 3 | 0.00 | 5 | 2 | 16.0 | 1.5000 | 0.0000 |
| 10 | 4 | 0.00 | 5 | 2 | 16.0 | 1.5000 | 0.0000 |
| 12 | 3 | 0.00 | 7 | 2 | 24.0 | 1.4828 | 0.0000 |
| 12 | 4 | 0.00 | 6 | 2 | 24.0 | 1.4483 | 0.0000 |
| 12 | 3 | 0.00 | 6 | 2 | 24.0 | 1.4138 | 0.0000 |
| 10 | 3 | 0.15 | 5 | 2 | 24.0 | 1.3964 | 0.0000 |
| 10 | 4 | 0.15 | 5 | 2 | 24.0 | 1.3964 | 0.0000 |
| 16 | 4 | 0.00 | 7 | 2 | 24.0 | 1.3548 | 0.0000 |
| 16 | 4 | 0.00 | 9 | 2 | 24.0 | 1.3548 | 0.0000 |
| 12 | 4 | 0.00 | 7 | 2 | 16.0 | 1.3333 | 0.0000 |
| 16 | 3 | 0.00 | 7 | 2 | 24.0 | 1.3226 | 0.0000 |
| 16 | 3 | 0.00 | 8 | 2 | 24.0 | 1.3226 | 0.0000 |
| 16 | 3 | 0.00 | 9 | 2 | 24.0 | 1.3226 | 0.0000 |
| 16 | 4 | 0.00 | 8 | 2 | 24.0 | 1.3226 | 0.0000 |
| 12 | 4 | 0.00 | 6 | 3 | 24.0 | 1.3210 | 0.0000 |
| 16 | 4 | 0.00 | 5 | 2 | 24.0 | 1.2903 | 0.0000 |
| 16 | 4 | 0.00 | 11 | 2 | 24.0 | 1.2903 | 0.0000 |

## Best Found Instance

- `n = 10`, `B = 3`, `eta = 0.00`
- hot block: start `5`, width `2`, hot weight `24.0`
- greedy absolute objective gap: `1.642857`
- beam absolute objective gap: `0.000000`
- greedy relative objective gap: `71.88%`
- beam relative objective gap: `0.00%`
- exact tree: `{'type': 'split', 'interval': [1, 10], 'threshold': 5, 'left': {'type': 'split', 'interval': [1, 5], 'threshold': 4, 'left': {'type': 'leaf', 'interval': [1, 4]}, 'right': {'type': 'leaf', 'interval': [5, 5]}}, 'right': {'type': 'split', 'interval': [6, 10], 'threshold': 6, 'left': {'type': 'leaf', 'interval': [6, 6]}, 'right': {'type': 'leaf', 'interval': [7, 10]}}}`
- greedy tree: `{'type': 'split', 'interval': [1, 10], 'threshold': 2, 'left': {'type': 'leaf', 'interval': [1, 2]}, 'right': {'type': 'leaf', 'interval': [3, 10]}}`
- beam tree: `{'type': 'split', 'interval': [1, 10], 'threshold': 5, 'left': {'type': 'split', 'interval': [1, 5], 'threshold': 4, 'left': {'type': 'leaf', 'interval': [1, 4]}, 'right': {'type': 'leaf', 'interval': [5, 5]}}, 'right': {'type': 'split', 'interval': [6, 10], 'threshold': 6, 'left': {'type': 'leaf', 'interval': [6, 6]}, 'right': {'type': 'leaf', 'interval': [7, 10]}}}`

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

## Roadmap

# Roadmap

## Phase 1: Core Correctness

- exact frontier DP
- brute-force oracle
- checker
- lower bounds
- tests for exactness and validity

## Phase 2: Certified Evaluation

- benchmark tables on tiny and medium cases
- gap histograms
- failure cases for greedy and balanced baselines
- wrong-prediction experiments

## Phase 3: Strongest Theory Layer

- Theorems A and B proof drafts
- Theorem C proved infinite greedy counterexample family
- independent cost-cap DP and proof-carrying branch-and-bound

## Phase 4: Competition Package

- abstract
- report
- poster
- slide deck
- appendix with checker format and reproducibility instructions
