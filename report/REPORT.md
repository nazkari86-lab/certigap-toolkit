# CertiGap Report

## Topic

**CertiGap-AutoDRO: automatic portfolio selection for budgeted robust partial search**

## One-Sentence Contribution

We automatically select **how much order to materialize**, which solver and fallback to use, and how to trade latency against memory under statistically uncertain query predictions, with exact fixed-candidate TV-DRO evaluation and independently verifiable portfolio arithmetic.

## Research Question

Given sorted keys, a predicted query distribution, and a budget `B` on materialized threshold comparisons, which parts of the order should be resolved in advance and which should remain unresolved intervals, so that the resulting search structure is both efficient under the prediction and robust when the prediction is wrong?

## Main Claim

For the budgeted partial-search model with interval leaves and contamination robustness, CertiGap can produce:

1. an exact optimum on small and medium instances;
2. a scalable heuristic on larger instances;
3. a certificate containing an upper bound, a lower bound, and a gap between them.

## Theorem Targets

# Theorem Goals

## Best Main Theorem

**Theorem A: Exact optimality of the frontier dynamic program**

For the static budgeted partial-search model, the frontier DP returns a tree minimizing

`(1 - eta) * average_cost + eta * max_cost`

among all valid trees with at most `B` splits.

Why this is the best first theorem:

- it is clean;
- it is central, not peripheral;
- it matches the code directly;
- it is easy for judges to understand.

## Best Secondary Theorem

**Theorem B: Robustness under contamination**

If the true distribution is

`p = (1 - eta) * p_hat + eta * q`,

then the CertiGap objective exactly matches worst-case expected cost under that contamination model.

Why it matters:

- it justifies the robustness parameter mathematically;
- it turns `eta` from a tuning knob into a formal model parameter.

## Proven Negative Result

**Theorem C: The implemented one-step greedy baseline can be arbitrarily suboptimal**

The proved family uses `n=2^m`, two central hot keys of weight `n*m`, `B=3`, and `eta=0`. Greedy rejects every first split, while an explicit three-split tree has an absolute gap lower bound asymptotic to `m-2`.

Why it matters:

- it proves the problem is not solved by local improvement;
- it makes the project look like research, not engineering.

## Strong Optional Result

**Theorem D: Exact optimality on a restricted distribution family**

Identify a clean family, such as single hot interval or symmetric bimodal mass, where a specific constructive policy is provably optimal.

This is strong, but optional. It should not delay Theorems A and B.

## Generalized Positive Result

**Theorem E: exact optimality for any deterministic executable interval fallback**

The leaf base case may use a full per-key cost profile rather than a uniform
`ceil(log2 |I|)` bound. The materialized split recurrence and Pareto-dominance
proof remain exact. This closes the mathematical/runtime gap and makes the
fixed-round formulation a special case.

## Fixed-Candidate DRO Result

**Theorem F: exact worst-case expectation in a finite total-variation ball**

Sorted probability-mass transfer computes the exact maximum expected
per-key execution cost over the TV ambiguity set. The implementation is
cross-checked against exhaustive probability grids.

This certifies each generated candidate's robust score. It does not prove that
a heuristic portfolio contains the globally optimal tree.

## Highest-Value Open Theorem

Prove an additive approximation guarantee for mass-quantile candidate pruning
with mandatory size-boundary thresholds. This is intentionally still marked
open; empirical 0.04% mean relative gap is not a theorem.

## Executable Fallback Generalization

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

## Experimental Design

# Experiment Plan

## Goal

Show that CertiGap is:

1. correct on small instances;
2. competitive on medium instances;
3. meaningfully better than simple baselines on skewed workloads;
4. honest about uncertainty through independently recomputed entropy bounds.

## Instance Families

- `uniform`
- `zipf`
- `hot_middle`
- `hot_tail`
- adversarial two-peak instances
- deliberately wrong predictions

## Size Regimes

### Tiny

- `n = 2..10`
- compare against brute force
- target: exact agreement

### Medium

- `n = 12..32`
- compare exact DP, greedy, balanced, weighted median
- report entropy-bound gaps and label them as bounds, not optimality certificates

### Large Prototype Regime

- `n = 64..512`
- run greedy and simple baselines only
- report heuristic behavior, not exact optimality claims

## Metrics

- objective value
- average cost
- worst-case cost
- lower bound
- reported entropy-bound gap
- exact gap when exact optimum is available
- build time

## Required Ablations

- no robustness: `eta = 0`
- moderate robustness: `eta = 0.15`
- high robustness: `eta = 0.30`
- no certificate comparison: upper bound only versus upper+lower
- greedy versus exact

## Honest Success Criteria

- exact DP matches brute force on all tiny cases;
- exact beats or matches simple baselines on skewed families;
- gains disappear or shrink on uniform workloads;
- entropy-bound gaps stay reasonably small on medium cases.

## Current Results

# CertiGap Experiment Summary

## Global Summary

- Rows analyzed: `240`
- Mean greedy absolute objective gap vs exact: `0.0986`
- Mean beam absolute objective gap vs exact: `0.0006`
- Mean greedy relative objective gap vs exact: `2.80%`
- Mean beam relative objective gap vs exact: `0.02%`
- Beam strictly improves on greedy in `104` rows
- Beam matches exact in `237` rows

## By Distribution

| Distribution | Mean Greedy Absolute Gap | Mean Beam Absolute Gap | Mean Greedy Relative Gap | Mean Beam Relative Gap | Beam Better Rows |
|---|---:|---:|---:|---:|
| hot_middle | 0.2485 | 0.0000 | 7.13% | 0.00% | 40 |
| hot_tail | 0.0446 | 0.0023 | 1.32% | 0.06% | 17 |
| uniform | 0.0255 | 0.0000 | 0.57% | 0.00% | 9 |
| zipf | 0.0758 | 0.0000 | 2.20% | 0.00% | 38 |

## Top Beam Improvements

| Distribution | n | B | eta | Greedy Absolute Gap | Beam Absolute Gap |
|---|---:|---:|---:|---:|---:|
| hot_middle | 12 | 4 | 0.00 | 0.8750 | 0.0000 |
| hot_middle | 24 | 4 | 0.00 | 0.8750 | 0.0000 |
| hot_middle | 12 | 3 | 0.00 | 0.7500 | 0.0000 |
| hot_middle | 24 | 3 | 0.00 | 0.7500 | 0.0000 |
| hot_middle | 12 | 3 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 12 | 4 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 24 | 3 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 24 | 4 | 0.15 | 0.6375 | 0.0000 |
| hot_middle | 16 | 4 | 0.00 | 0.6154 | 0.0000 |
| hot_middle | 8 | 4 | 0.00 | 0.5769 | 0.0000 |

## Counterexample Note

See `counterexamples.md` for automatically discovered hot-block families where one-step greedy is much worse than exact while beam recovers the optimum.

## Speed And Quality

# CertiGap Speed and Quality Summary

## Small Cases With Exact Reference

- Exact mean time: `2.479 ms`
- Beam mean time: `4.646 ms`
- Greedy mean time: `0.222 ms`
- Balanced mean time: `0.013 ms`
- Weighted mean time: `0.017 ms`
- Beam mean absolute objective gap vs exact: `0.000979`
- Greedy mean absolute objective gap vs exact: `0.114157`
- Balanced mean absolute objective gap vs exact: `0.447373`
- Weighted mean absolute objective gap vs exact: `0.198609`
- Beam mean relative objective gap vs exact: `0.03%`
- Greedy mean relative objective gap vs exact: `3.48%`

## Large Cases Without Exact Reference

- Beam mean time: `57.052 ms`
- Greedy mean time: `1.654 ms`
- Balanced mean time: `0.027 ms`
- Weighted mean time: `0.043 ms`

## Solver Tradeoff

- `exact` is the reference solver for the measured small instances.
- `beam` is near-exact on the measured small cases, but is not faster than exact there; this benchmark does not establish a crossover point.
- `greedy` is usually faster but can be substantially worse on structured skewed tasks.
- `balanced` and `weighted` are cheap baselines, but quality is systematically weaker on skewed workloads.

## Counterexamples

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

## Matched-Budget Lookup Evidence

# C++ Post-Build Lookup Microbenchmark

This measures only rank lookup after each structure is built. Times are local-machine measurements, not cross-machine or production claims.

- Queries are sampled from each workload distribution with a deterministic PRNG.
- `ycsb_hotspot_80_20` and `ycsb_latest_biased` are YCSB-inspired read-only distributions, not runs of the official YCSB harness.
- CertiGap uses the candidate-pruned C++ beam (`B=min(6,n-1)`, `eta=0.15`, width 32, candidate limit 16).
- CertiGap and budgeted trees use at most `B=min(6,n-1)` materialized splits and fixed-round interval fallback.
- `balanced_full_reference` and `std_lower_bound` are explicitly unconstrained references, not equal-budget competitors.
- Reported p95 is across repeated batch means; it is not single-query tail latency.
- Total index bytes include the shared integer key array; auxiliary bytes exclude allocator overhead.

| Workload | Solver | n | B | Median batch ns/query | p95 batch ns/query | Nodes | Auxiliary bytes | Total bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| uniform | certigap_pruned | 1000 | 6 | 16.436 | 16.866 | 1 | 48 | 4048 |
| uniform | balanced_budgeted | 1000 | 6 | 18.527 | 18.749 | 13 | 624 | 4624 |
| uniform | weighted_budgeted | 1000 | 6 | 18.456 | 18.836 | 13 | 624 | 4624 |
| uniform | balanced_full_reference | 1000 | 999 | 16.151 | 16.679 | 1999 | 95952 | 99952 |
| uniform | std_lower_bound | 1000 | 0 | 15.552 | 15.944 | 0 | 0 | 4000 |
| zipf | certigap_pruned | 1000 | 6 | 25.614 | 26.704 | 11 | 528 | 4528 |
| zipf | balanced_budgeted | 1000 | 6 | 15.678 | 16.225 | 13 | 624 | 4624 |
| zipf | weighted_budgeted | 1000 | 6 | 25.186 | 25.917 | 13 | 624 | 4624 |
| zipf | balanced_full_reference | 1000 | 999 | 15.374 | 16.073 | 1999 | 95952 | 99952 |
| zipf | std_lower_bound | 1000 | 0 | 15.088 | 15.755 | 0 | 0 | 4000 |
| hot_tail | certigap_pruned | 1000 | 6 | 21.831 | 22.519 | 13 | 624 | 4624 |
| hot_tail | balanced_budgeted | 1000 | 6 | 15.522 | 15.876 | 13 | 624 | 4624 |
| hot_tail | weighted_budgeted | 1000 | 6 | 24.192 | 25.346 | 13 | 624 | 4624 |
| hot_tail | balanced_full_reference | 1000 | 999 | 16.106 | 16.577 | 1999 | 95952 | 99952 |
| hot_tail | std_lower_bound | 1000 | 0 | 15.501 | 16.123 | 0 | 0 | 4000 |
| ycsb_hotspot_80_20 | certigap_pruned | 1000 | 6 | 24.692 | 25.643 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | balanced_budgeted | 1000 | 6 | 16.831 | 17.224 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | weighted_budgeted | 1000 | 6 | 16.219 | 16.466 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | balanced_full_reference | 1000 | 999 | 15.893 | 16.260 | 1999 | 95952 | 99952 |
| ycsb_hotspot_80_20 | std_lower_bound | 1000 | 0 | 15.374 | 15.742 | 0 | 0 | 4000 |
| ycsb_latest_biased | certigap_pruned | 1000 | 6 | 28.326 | 29.018 | 13 | 624 | 4624 |
| ycsb_latest_biased | balanced_budgeted | 1000 | 6 | 14.703 | 15.817 | 13 | 624 | 4624 |
| ycsb_latest_biased | weighted_budgeted | 1000 | 6 | 26.401 | 26.918 | 13 | 624 | 4624 |
| ycsb_latest_biased | balanced_full_reference | 1000 | 999 | 18.673 | 26.755 | 1999 | 95952 | 99952 |
| ycsb_latest_biased | std_lower_bound | 1000 | 0 | 19.996 | 29.051 | 0 | 0 | 4000 |
| uniform | certigap_pruned | 10000 | 6 | 29.483 | 42.514 | 5 | 240 | 40240 |
| uniform | balanced_budgeted | 10000 | 6 | 40.318 | 43.050 | 13 | 624 | 40624 |
| uniform | weighted_budgeted | 10000 | 6 | 27.806 | 29.757 | 13 | 624 | 40624 |
| uniform | balanced_full_reference | 10000 | 9999 | 56.518 | 64.310 | 19999 | 959952 | 999952 |
| uniform | std_lower_bound | 10000 | 0 | 40.845 | 46.249 | 0 | 0 | 40000 |
| zipf | certigap_pruned | 10000 | 6 | 29.593 | 34.589 | 13 | 624 | 40624 |
| zipf | balanced_budgeted | 10000 | 6 | 24.563 | 28.187 | 13 | 624 | 40624 |
| zipf | weighted_budgeted | 10000 | 6 | 29.327 | 34.547 | 13 | 624 | 40624 |
| zipf | balanced_full_reference | 10000 | 9999 | 56.032 | 64.146 | 19999 | 959952 | 999952 |
| zipf | std_lower_bound | 10000 | 0 | 44.236 | 46.169 | 0 | 0 | 40000 |
| hot_tail | certigap_pruned | 10000 | 6 | 22.789 | 23.756 | 13 | 624 | 40624 |
| hot_tail | balanced_budgeted | 10000 | 6 | 24.669 | 25.330 | 13 | 624 | 40624 |
| hot_tail | weighted_budgeted | 10000 | 6 | 27.071 | 27.659 | 13 | 624 | 40624 |
| hot_tail | balanced_full_reference | 10000 | 9999 | 48.577 | 50.151 | 19999 | 959952 | 999952 |
| hot_tail | std_lower_bound | 10000 | 0 | 38.813 | 39.600 | 0 | 0 | 40000 |
| ycsb_hotspot_80_20 | certigap_pruned | 10000 | 6 | 21.882 | 22.715 | 3 | 144 | 40144 |
| ycsb_hotspot_80_20 | balanced_budgeted | 10000 | 6 | 25.125 | 25.843 | 13 | 624 | 40624 |
| ycsb_hotspot_80_20 | weighted_budgeted | 10000 | 6 | 23.972 | 24.977 | 13 | 624 | 40624 |
| ycsb_hotspot_80_20 | balanced_full_reference | 10000 | 9999 | 50.989 | 52.120 | 19999 | 959952 | 999952 |
| ycsb_hotspot_80_20 | std_lower_bound | 10000 | 0 | 39.153 | 40.139 | 0 | 0 | 40000 |
| ycsb_latest_biased | certigap_pruned | 10000 | 6 | 30.556 | 31.370 | 7 | 336 | 40336 |
| ycsb_latest_biased | balanced_budgeted | 10000 | 6 | 23.978 | 24.734 | 13 | 624 | 40624 |
| ycsb_latest_biased | weighted_budgeted | 10000 | 6 | 32.435 | 33.242 | 13 | 624 | 40624 |
| ycsb_latest_biased | balanced_full_reference | 10000 | 9999 | 51.153 | 52.214 | 19999 | 959952 | 999952 |
| ycsb_latest_biased | std_lower_bound | 10000 | 0 | 38.882 | 39.963 | 0 | 0 | 40000 |

## Matched-Budget Interpretation

- CertiGap has lower median batch lookup time than `balanced_budgeted` in `4/10` measured workload-size cases.
- CertiGap has lower median batch lookup time than `weighted_budgeted` in `5/10` measured workload-size cases.

## Limits

This is not an official YCSB, RocksDB, hardware-routing, cache-miss, or external-library benchmark. It is reproducible CPU-level evidence that the exported CertiGap decision tree executes real lookups with an explicit storage footprint. Production claims require a target storage engine, key encoding, allocator, CPU, and independent external baselines.

## AutoDRO Under Distribution Shift

# CertiGap-AutoDRO Fair Distribution-Shift Benchmark

`tuned_tv_dro` and `tuned_nominal` search the identical budgets, eta grid, solver set, and fallback set. Their only selection difference is TV radius `0.2` versus `0.0`; this is the primary DRO ablation.

| Scenario | n | Method | Solver | Fallback | Splits | Bytes | Candidates | Select s | Test mean | Test max |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| hot_reversal | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1823 | 6.63636 | 7.00000 |
| hot_reversal | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1681 | 6.63636 | 7.00000 |
| hot_reversal | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 6.82955 | 7.00000 |
| hot_reversal | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| hot_reversal | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 6.82955 | 7.00000 |
| hot_reversal | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4764 | 7.67614 | 8.00000 |
| hot_reversal | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.4806 | 7.67614 | 8.00000 |
| hot_reversal | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 7.82955 | 8.00000 |
| hot_reversal | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| hot_reversal | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 7.82955 | 8.00000 |
| hot_reversal | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 2.0555 | 8.71591 | 9.00000 |
| hot_reversal | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.6337 | 8.71591 | 9.00000 |
| hot_reversal | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 8.82955 | 9.00000 |
| hot_reversal | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| hot_reversal | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 8.82955 | 9.00000 |
| partial_hot_drift_15 | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1686 | 3.70974 | 7.00000 |
| partial_hot_drift_15 | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1762 | 3.70974 | 7.00000 |
| partial_hot_drift_15 | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 3.76015 | 7.00000 |
| partial_hot_drift_15 | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| partial_hot_drift_15 | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 3.76015 | 7.00000 |
| partial_hot_drift_15 | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4863 | 4.71571 | 8.00000 |
| partial_hot_drift_15 | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.4544 | 4.71571 | 8.00000 |
| partial_hot_drift_15 | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 4.76015 | 8.00000 |
| partial_hot_drift_15 | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| partial_hot_drift_15 | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 4.76015 | 8.00000 |
| partial_hot_drift_15 | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.4143 | 5.72167 | 9.00000 |
| partial_hot_drift_15 | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.4126 | 5.72167 | 9.00000 |
| partial_hot_drift_15 | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 5.76015 | 9.00000 |
| partial_hot_drift_15 | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| partial_hot_drift_15 | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 5.76015 | 9.00000 |
| partial_hot_drift_35 | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1644 | 4.39836 | 7.00000 |
| partial_hot_drift_35 | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1660 | 4.39836 | 7.00000 |
| partial_hot_drift_35 | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 4.48236 | 7.00000 |
| partial_hot_drift_35 | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| partial_hot_drift_35 | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 4.48236 | 7.00000 |
| partial_hot_drift_35 | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4627 | 5.41228 | 8.00000 |
| partial_hot_drift_35 | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.4549 | 5.41228 | 8.00000 |
| partial_hot_drift_35 | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 5.48236 | 8.00000 |
| partial_hot_drift_35 | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| partial_hot_drift_35 | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 5.48236 | 8.00000 |
| partial_hot_drift_35 | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.4352 | 6.42620 | 9.00000 |
| partial_hot_drift_35 | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.4112 | 6.42620 | 9.00000 |
| partial_hot_drift_35 | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 6.48236 | 9.00000 |
| partial_hot_drift_35 | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| partial_hot_drift_35 | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 6.48236 | 9.00000 |
| partial_hot_drift_65 | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1674 | 5.43128 | 7.00000 |
| partial_hot_drift_65 | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1642 | 5.43128 | 7.00000 |
| partial_hot_drift_65 | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 5.56568 | 7.00000 |
| partial_hot_drift_65 | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| partial_hot_drift_65 | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 5.56568 | 7.00000 |
| partial_hot_drift_65 | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4917 | 6.45714 | 8.00000 |
| partial_hot_drift_65 | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.5225 | 6.45714 | 8.00000 |
| partial_hot_drift_65 | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 6.56568 | 8.00000 |
| partial_hot_drift_65 | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| partial_hot_drift_65 | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.56568 | 8.00000 |
| partial_hot_drift_65 | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.4535 | 7.48299 | 9.00000 |
| partial_hot_drift_65 | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.4124 | 7.48299 | 9.00000 |
| partial_hot_drift_65 | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 7.56568 | 9.00000 |
| partial_hot_drift_65 | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| partial_hot_drift_65 | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.56568 | 9.00000 |
| stationary_hot_head | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1645 | 3.19328 | 7.00000 |
| stationary_hot_head | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1751 | 3.19328 | 7.00000 |
| stationary_hot_head | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 3.21849 | 7.00000 |
| stationary_hot_head | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| stationary_hot_head | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 3.21849 | 7.00000 |
| stationary_hot_head | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4644 | 4.19328 | 8.00000 |
| stationary_hot_head | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.4680 | 4.19328 | 8.00000 |
| stationary_hot_head | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 4.21849 | 8.00000 |
| stationary_hot_head | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| stationary_hot_head | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 4.21849 | 8.00000 |
| stationary_hot_head | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.6080 | 5.19328 | 9.00000 |
| stationary_hot_head | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.7111 | 5.19328 | 9.00000 |
| stationary_hot_head | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 5.21849 | 9.00000 |
| stationary_hot_head | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| stationary_hot_head | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 5.21849 | 9.00000 |
| stationary_zipf | 32 | tuned_tv_dro | beam | fixed_rounds | 3 | 464 | 34 | 0.1688 | 4.30368 | 6.00000 |
| stationary_zipf | 32 | tuned_nominal | beam | midpoint_binary | 4 | 560 | 34 | 0.1663 | 4.20624 | 7.00000 |
| stationary_zipf | 32 | fixed_beam | beam | fixed_rounds | 4 | 560 | 1 | 0.0000 | 4.24755 | 6.00000 |
| stationary_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| stationary_zipf | 32 | fixed_weighted | weighted | fixed_rounds | 4 | 560 | 1 | 0.0000 | 4.34144 | 7.00000 |
| stationary_zipf | 64 | tuned_tv_dro | beam | midpoint_binary | 4 | 688 | 40 | 0.4598 | 4.99841 | 7.00000 |
| stationary_zipf | 64 | tuned_nominal | beam | midpoint_binary | 4 | 688 | 40 | 0.4612 | 4.94234 | 8.00000 |
| stationary_zipf | 64 | fixed_beam | beam | fixed_rounds | 4 | 688 | 1 | 0.0000 | 5.01343 | 7.00000 |
| stationary_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| stationary_zipf | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 5.15870 | 8.00000 |
| stationary_zipf | 128 | tuned_tv_dro | beam | midpoint_binary | 3 | 848 | 38 | 1.5862 | 5.75959 | 8.00000 |
| stationary_zipf | 128 | tuned_nominal | beam | midpoint_binary | 4 | 944 | 38 | 1.9753 | 5.65590 | 9.00000 |
| stationary_zipf | 128 | fixed_beam | beam | fixed_rounds | 3 | 848 | 1 | 0.0000 | 5.79996 | 8.00000 |
| stationary_zipf | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| stationary_zipf | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 5.94223 | 9.00000 |
| uniform_to_zipf | 32 | tuned_tv_dro | beam | fixed_rounds | 0 | 176 | 16 | 0.1613 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | tuned_nominal | beam | fixed_rounds | 0 | 176 | 16 | 0.1612 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_beam | beam | fixed_rounds | 0 | 176 | 1 | 0.0000 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_weighted | weighted | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| uniform_to_zipf | 64 | tuned_tv_dro | beam | fixed_rounds | 0 | 304 | 18 | 0.4539 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | tuned_nominal | beam | fixed_rounds | 0 | 304 | 18 | 0.5167 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_beam | beam | fixed_rounds | 0 | 304 | 1 | 0.0000 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| uniform_to_zipf | 128 | tuned_tv_dro | beam | fixed_rounds | 0 | 560 | 18 | 1.3985 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | tuned_nominal | beam | fixed_rounds | 0 | 560 | 18 | 1.3781 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | fixed_beam | beam | fixed_rounds | 0 | 560 | 1 | 0.0000 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| zipf_to_uniform | 32 | tuned_tv_dro | beam | fixed_rounds | 3 | 464 | 34 | 0.1674 | 5.50000 | 6.00000 |
| zipf_to_uniform | 32 | tuned_nominal | beam | midpoint_binary | 4 | 560 | 34 | 0.1672 | 5.75000 | 7.00000 |
| zipf_to_uniform | 32 | fixed_beam | beam | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.50000 | 6.00000 |
| zipf_to_uniform | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| zipf_to_uniform | 32 | fixed_weighted | weighted | fixed_rounds | 4 | 560 | 1 | 0.0000 | 6.03125 | 7.00000 |
| zipf_to_uniform | 64 | tuned_tv_dro | beam | midpoint_binary | 4 | 688 | 40 | 0.5040 | 6.46875 | 7.00000 |
| zipf_to_uniform | 64 | tuned_nominal | beam | midpoint_binary | 4 | 688 | 40 | 0.4842 | 6.82812 | 8.00000 |
| zipf_to_uniform | 64 | fixed_beam | beam | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.50000 | 7.00000 |
| zipf_to_uniform | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| zipf_to_uniform | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 7.20312 | 8.00000 |
| zipf_to_uniform | 128 | tuned_tv_dro | beam | midpoint_binary | 3 | 848 | 38 | 1.4367 | 7.59375 | 8.00000 |
| zipf_to_uniform | 128 | tuned_nominal | beam | midpoint_binary | 4 | 944 | 38 | 1.4488 | 7.82812 | 9.00000 |
| zipf_to_uniform | 128 | fixed_beam | beam | fixed_rounds | 3 | 848 | 1 | 0.0000 | 7.70312 | 8.00000 |
| zipf_to_uniform | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| zipf_to_uniform | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 8.32812 | 9.00000 |

## Paired Outcomes

- tuned TV-DRO vs `tuned_nominal`: `3` wins, `3` losses, `18` ties across `24` pairs.
- tuned TV-DRO vs `fixed_beam`: `19` wins, `1` losses, `4` ties across `24` pairs.
- tuned TV-DRO vs `fixed_balanced`: `12` wins, `9` losses, `3` ties across `24` pairs.
- tuned TV-DRO vs `fixed_weighted`: `21` wins, `0` losses, `3` ties across `24` pairs.

## Scope

Expected comparison cost is deterministic for each supplied test distribution, so sampling confidence intervals are not applicable to this table. Construction timings are local-machine measurements. External implementations, real request latency, and prospective traces remain separate experiments.

# Direct TV-DRO Exact-Space Validation

Every row exhaustively enumerates all ordered partial trees up to the split budget and both built-in fallbacks. The heuristic portfolio is a subset, so a negative gap is a test failure.

- Cases: `181`
- Exact improvements over the heuristic portfolio: `1`
- Maximum heuristic minus exact robust score: `0.067334968`
- Largest enumerated tree space: `225`
- The fixed separation witness is retained as a regression case showing that direct TV optimization can beat every candidate generated from the Huber frontier and heuristic portfolio.

| n | B | rho | Cases | Exact improvements | Mean gap | Max gap |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 4 | 1 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 4 | 1 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 4 | 2 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 4 | 2 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 4 | 2 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 4 | 3 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 4 | 3 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 4 | 3 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 5 | 1 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 5 | 1 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 5 | 1 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 5 | 2 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 5 | 2 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 5 | 2 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 5 | 3 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 5 | 3 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 5 | 3 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 6 | 1 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 6 | 1 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 6 | 1 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 6 | 2 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 6 | 2 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 6 | 2 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 6 | 3 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 6 | 3 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 6 | 3 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 7 | 1 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 7 | 1 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 7 | 1 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 7 | 2 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 7 | 2 | 0.10 | 1 | 1 | 0.067334968 | 0.067334968 |
| 7 | 2 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 7 | 2 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 7 | 3 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 7 | 3 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 7 | 3 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 8 | 1 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 8 | 1 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 8 | 1 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 8 | 2 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 8 | 2 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 8 | 2 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |
| 8 | 3 | 0.05 | 4 | 0 | 0.000000000 | 0.000000000 |
| 8 | 3 | 0.20 | 4 | 0 | 0.000000000 | 0.000000000 |
| 8 | 3 | 0.40 | 4 | 0 | 0.000000000 | 0.000000000 |

# Temporal Holdout: MovieLens 100K

Identical tuned portfolios are fitted on the earliest 80% of timestamped ratings and evaluated on the final 20%. Only the TV selection radius changes. Movie identifier order is preserved; this is a public temporal shift test, not a production latency study.

| n | Method | rho | Solver | Fallback | Splits | Future average | Future max |
|---:|---|---:|---|---|---:|---:|---:|
| 32 | tuned_nominal | 0.00 | beam | fixed_rounds | 6 | 4.474450 | 9 |
| 32 | tuned_tv_010 | 0.10 | beam | fixed_rounds | 2 | 4.560300 | 6 |
| 32 | tuned_tv_020 | 0.20 | beam | fixed_rounds | 2 | 4.560300 | 6 |
| 64 | tuned_nominal | 0.00 | beam | fixed_rounds | 6 | 5.474450 | 10 |
| 64 | tuned_tv_010 | 0.10 | beam | fixed_rounds | 2 | 5.560300 | 7 |
| 64 | tuned_tv_020 | 0.20 | beam | fixed_rounds | 2 | 5.560300 | 7 |
| 128 | tuned_nominal | 0.00 | beam | fixed_rounds | 5 | 6.505450 | 10 |
| 128 | tuned_tv_010 | 0.10 | beam | fixed_rounds | 2 | 6.560300 | 8 |
| 128 | tuned_tv_020 | 0.20 | beam | fixed_rounds | 2 | 6.560300 | 8 |

# Finite-Sample TV Radius Validation

Each row uses 250 deterministic i.i.d. multinomial repetitions. Coverage checks whether the known generating distribution lies inside the reported smoothed TV ball. This validates implementation and conservatism under the i.i.d. model only; it is not evidence for dependent production traces.

| Distribution | n | N | Coverage | Mean radius | Mean true TV |
|---|---:|---:|---:|---:|---:|
| uniform | 8 | 100 | 1.000 | 0.21073 | 0.10190 |
| uniform | 8 | 1000 | 1.000 | 0.06548 | 0.03198 |
| uniform | 8 | 10000 | 0.996 | 0.02067 | 0.01046 |
| uniform | 32 | 100 | 1.000 | 0.38516 | 0.18976 |
| uniform | 32 | 1000 | 1.000 | 0.11332 | 0.07017 |
| uniform | 32 | 10000 | 1.000 | 0.03552 | 0.02233 |
| zipf | 8 | 100 | 1.000 | 0.21895 | 0.09070 |
| zipf | 8 | 1000 | 1.000 | 0.06656 | 0.03134 |
| zipf | 8 | 10000 | 1.000 | 0.02079 | 0.00954 |
| zipf | 32 | 100 | 1.000 | 0.41790 | 0.17026 |
| zipf | 32 | 1000 | 1.000 | 0.11890 | 0.05989 |
| zipf | 32 | 10000 | 1.000 | 0.03615 | 0.01897 |

# Online Rebuild Threshold Simulation

A deterministic 12-window stream moves from a hot head to a hot tail and then to Zipf access. The always-refit tuned portfolio is the per-window oracle. This measures rebuild/regret trade-offs, not in-place mutation.

| TV threshold | Rebuilds | Mean cost | Mean oracle | Mean regret | Max regret |
|---:|---:|---:|---:|---:|---:|
| 0.00 | 13 | 4.185059 | 4.185059 | -0.000000 | 0.000000 |
| 0.03 | 7 | 4.185059 | 4.185059 | -0.000000 | 0.000000 |
| 0.08 | 7 | 4.185059 | 4.185059 | -0.000000 | 0.000000 |
| 0.15 | 4 | 4.216119 | 4.185059 | 0.031061 | 0.272727 |

# Anytime TV-DRO Validation

The exact phase compares against independent complete-tree-space enumeration. The scaling phase reports certified intervals, not unverified solution quality.

- Exact oracle matches: `12/12`.
- Verified scaling trajectory rows: `36`.
- Exact after 400 expansions: `3/9`.

| n | Workload | Expansions | Upper | Lower | Relative gap | Exact | Seconds |
|---:|---|---:|---:|---:|---:|:---:|---:|
| 16 | uniform | 0 | 4.000000 | 4.000000 | 0.000000 | yes | 0.117373 |
| 16 | uniform | 25 | 4.000000 | 4.000000 | 0.000000 | yes | 0.117894 |
| 16 | uniform | 100 | 4.000000 | 4.000000 | 0.000000 | yes | 0.118819 |
| 16 | uniform | 400 | 4.000000 | 4.000000 | 0.000000 | yes | 0.116961 |
| 16 | zipf | 0 | 3.737221 | 3.403220 | 0.089371 | no | 0.117693 |
| 16 | zipf | 25 | 3.737221 | 3.426050 | 0.083263 | no | 0.120681 |
| 16 | zipf | 100 | 3.737221 | 3.437218 | 0.080274 | no | 0.133157 |
| 16 | zipf | 400 | 3.737221 | 3.462515 | 0.073505 | no | 0.167574 |
| 16 | hot_tail | 0 | 3.654545 | 3.277613 | 0.103141 | no | 0.117135 |
| 16 | hot_tail | 25 | 3.654545 | 3.288693 | 0.100109 | no | 0.131423 |
| 16 | hot_tail | 100 | 3.654545 | 3.292455 | 0.099079 | no | 0.132691 |
| 16 | hot_tail | 400 | 3.654545 | 3.297565 | 0.097681 | no | 0.154480 |
| 32 | uniform | 0 | 5.000000 | 5.000000 | 0.000000 | yes | 0.357397 |
| 32 | uniform | 25 | 5.000000 | 5.000000 | 0.000000 | yes | 0.356258 |
| 32 | uniform | 100 | 5.000000 | 5.000000 | 0.000000 | yes | 0.357127 |
| 32 | uniform | 400 | 5.000000 | 5.000000 | 0.000000 | yes | 0.357596 |
| 32 | zipf | 0 | 4.601010 | 4.149104 | 0.098219 | no | 0.358605 |
| 32 | zipf | 25 | 4.601010 | 4.158535 | 0.096169 | no | 0.366051 |
| 32 | zipf | 100 | 4.601010 | 4.168352 | 0.094036 | no | 0.387354 |
| 32 | zipf | 400 | 4.601010 | 4.182008 | 0.091067 | no | 0.438515 |
| 32 | hot_tail | 0 | 4.663636 | 4.277613 | 0.082773 | no | 0.362069 |
| 32 | hot_tail | 25 | 4.663636 | 4.285225 | 0.081141 | no | 0.375709 |
| 32 | hot_tail | 100 | 4.663636 | 4.286757 | 0.080812 | no | 0.387345 |
| 32 | hot_tail | 400 | 4.663636 | 4.288841 | 0.080365 | no | 0.442064 |
| 64 | uniform | 0 | 6.000000 | 6.000000 | 0.000000 | yes | 1.019489 |
| 64 | uniform | 25 | 6.000000 | 6.000000 | 0.000000 | yes | 1.015215 |
| 64 | uniform | 100 | 6.000000 | 6.000000 | 0.000000 | yes | 1.016750 |
| 64 | uniform | 400 | 6.000000 | 6.000000 | 0.000000 | yes | 1.012382 |
| 64 | zipf | 0 | 5.359076 | 4.863833 | 0.092412 | no | 1.012885 |
| 64 | zipf | 25 | 5.359076 | 4.879230 | 0.089539 | no | 1.026160 |
| 64 | zipf | 100 | 5.359076 | 4.884646 | 0.088528 | no | 1.077165 |
| 64 | zipf | 400 | 5.359076 | 4.896088 | 0.086393 | no | 1.197354 |
| 64 | hot_tail | 0 | 5.654545 | 5.277613 | 0.066660 | no | 1.012403 |
| 64 | hot_tail | 25 | 5.654545 | 5.278164 | 0.066563 | no | 1.052370 |
| 64 | hot_tail | 100 | 5.654545 | 5.278815 | 0.066447 | no | 1.115870 |
| 64 | hot_tail | 400 | 5.654545 | 5.280205 | 0.066202 | no | 1.262895 |

## Interpretation

A zero reported gap is a proof for the configured TV radius, fallback, memory/build/tail cost model, and split budget. A nonzero gap is an honest unresolved interval, not an optimality claim.

## Competition Positioning

# RKNP and ISEF Positioning

## Why This Is Strong For RKNP

- narrow and defensible novelty claim;
- concrete algorithmic contribution;
- theorem-friendly structure;
- reproducible experiments without closed data;
- easy to distinguish from generic AI projects.

## Why This Is Strong For ISEF

- clear formal problem statement;
- exact algorithm plus scalable heuristic;
- independent certificate checker;
- honest comparison between proofs, experiments, and limits.

## What Would Weaken The Project

- mixing CertiGap with unrelated learned-index directions in one title;
- inflating claims to “first ever” language;
- adding dynamic updates before finishing the static theory;
- claiming systems-level speedups without a serious systems benchmark.

## Best Short Pitch

Most search structures decide **how to arrange all data**.
CertiGap decides **how much of the order is worth materializing at all** under
a strict budget and unreliable predictions. It proves global TV-DRO optimality
on exhaustively enumerable instances and reports an explicit portfolio
boundary on larger heuristic instances.
