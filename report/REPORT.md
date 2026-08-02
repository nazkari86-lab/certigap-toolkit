# CertiGap Report

## Topic

**CertiGap: certified workload-adaptive synthesis and selection of ordered
in-memory structures**

## One-Sentence Contribution

We synthesize or select an ordered in-memory structure inside an explicit finite
design space, optimize its structural cost under workload and resource
constraints, and emit a replay-verifiable artifact that states exactly what was
and was not proved.

## Research Question

Given ordered data, supported operations, a measured workload, and resource
constraints, which legal representation should be materialized so that modeled
work is minimized without claiming optimality outside the declared design
space?

## Main Claim

For each declared finite grammar or portfolio, CertiGap aims to produce:

1. an exact optimum and replayable winner when exhaustive dynamic programming
   is tractable;
2. a feasible incumbent and certified interval for supported anytime paths;
3. an explicitly labelled empirical heuristic when neither guarantee is
   available;
4. native measurements separated from structural certificates.

The claim-by-claim source of truth is [`CLAIMS.md`](CLAIMS.md).

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

- Exact mean time: `1.392 ms`
- Beam mean time: `2.516 ms`
- Greedy mean time: `0.119 ms`
- Balanced mean time: `0.007 ms`
- Weighted mean time: `0.009 ms`
- Beam mean absolute objective gap vs exact: `0.000979`
- Greedy mean absolute objective gap vs exact: `0.114157`
- Balanced mean absolute objective gap vs exact: `0.447373`
- Weighted mean absolute objective gap vs exact: `0.198609`
- Beam mean relative objective gap vs exact: `0.03%`
- Greedy mean relative objective gap vs exact: `3.48%`

## Large Cases Without Exact Reference

- Beam mean time: `40.384 ms`
- Greedy mean time: `1.125 ms`
- Balanced mean time: `0.018 ms`
- Weighted mean time: `0.029 ms`

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
| uniform | certigap_pruned | 1000 | 6 | 8.949 | 9.259 | 1 | 48 | 4048 |
| uniform | balanced_budgeted | 1000 | 6 | 10.097 | 10.427 | 13 | 624 | 4624 |
| uniform | weighted_budgeted | 1000 | 6 | 10.074 | 11.305 | 13 | 624 | 4624 |
| uniform | balanced_full_reference | 1000 | 999 | 8.934 | 9.365 | 1999 | 95952 | 99952 |
| uniform | std_lower_bound | 1000 | 0 | 8.541 | 8.830 | 0 | 0 | 4000 |
| zipf | certigap_pruned | 1000 | 6 | 13.905 | 14.909 | 11 | 528 | 4528 |
| zipf | balanced_budgeted | 1000 | 6 | 8.629 | 8.844 | 13 | 624 | 4624 |
| zipf | weighted_budgeted | 1000 | 6 | 13.653 | 14.171 | 13 | 624 | 4624 |
| zipf | balanced_full_reference | 1000 | 999 | 8.612 | 8.869 | 1999 | 95952 | 99952 |
| zipf | std_lower_bound | 1000 | 0 | 8.231 | 8.465 | 0 | 0 | 4000 |
| hot_tail | certigap_pruned | 1000 | 6 | 11.810 | 12.731 | 13 | 624 | 4624 |
| hot_tail | balanced_budgeted | 1000 | 6 | 8.290 | 9.006 | 13 | 624 | 4624 |
| hot_tail | weighted_budgeted | 1000 | 6 | 13.040 | 13.756 | 13 | 624 | 4624 |
| hot_tail | balanced_full_reference | 1000 | 999 | 8.686 | 9.255 | 1999 | 95952 | 99952 |
| hot_tail | std_lower_bound | 1000 | 0 | 8.444 | 8.849 | 0 | 0 | 4000 |
| ycsb_hotspot_80_20 | certigap_pruned | 1000 | 6 | 13.404 | 13.803 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | balanced_budgeted | 1000 | 6 | 9.188 | 9.479 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | weighted_budgeted | 1000 | 6 | 8.707 | 8.969 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | balanced_full_reference | 1000 | 999 | 8.677 | 8.950 | 1999 | 95952 | 99952 |
| ycsb_hotspot_80_20 | std_lower_bound | 1000 | 0 | 8.429 | 8.880 | 0 | 0 | 4000 |
| ycsb_latest_biased | certigap_pruned | 1000 | 6 | 15.528 | 16.012 | 13 | 624 | 4624 |
| ycsb_latest_biased | balanced_budgeted | 1000 | 6 | 8.057 | 8.426 | 13 | 624 | 4624 |
| ycsb_latest_biased | weighted_budgeted | 1000 | 6 | 14.263 | 14.898 | 13 | 624 | 4624 |
| ycsb_latest_biased | balanced_full_reference | 1000 | 999 | 8.750 | 9.024 | 1999 | 95952 | 99952 |
| ycsb_latest_biased | std_lower_bound | 1000 | 0 | 8.531 | 8.799 | 0 | 0 | 4000 |
| uniform | certigap_pruned | 10000 | 6 | 15.239 | 15.827 | 5 | 240 | 40240 |
| uniform | balanced_budgeted | 10000 | 6 | 14.732 | 15.192 | 13 | 624 | 40624 |
| uniform | weighted_budgeted | 10000 | 6 | 14.797 | 15.059 | 13 | 624 | 40624 |
| uniform | balanced_full_reference | 10000 | 9999 | 29.893 | 30.804 | 19999 | 959952 | 999952 |
| uniform | std_lower_bound | 10000 | 0 | 20.933 | 21.291 | 0 | 0 | 40000 |
| zipf | certigap_pruned | 10000 | 6 | 15.223 | 15.872 | 13 | 624 | 40624 |
| zipf | balanced_budgeted | 10000 | 6 | 12.891 | 13.183 | 13 | 624 | 40624 |
| zipf | weighted_budgeted | 10000 | 6 | 15.512 | 16.038 | 13 | 624 | 40624 |
| zipf | balanced_full_reference | 10000 | 9999 | 27.974 | 28.412 | 19999 | 959952 | 999952 |
| zipf | std_lower_bound | 10000 | 0 | 23.908 | 24.221 | 0 | 0 | 40000 |
| hot_tail | certigap_pruned | 10000 | 6 | 12.259 | 12.674 | 13 | 624 | 40624 |
| hot_tail | balanced_budgeted | 10000 | 6 | 13.474 | 13.831 | 13 | 624 | 40624 |
| hot_tail | weighted_budgeted | 10000 | 6 | 14.598 | 14.829 | 13 | 624 | 40624 |
| hot_tail | balanced_full_reference | 10000 | 9999 | 26.450 | 27.018 | 19999 | 959952 | 999952 |
| hot_tail | std_lower_bound | 10000 | 0 | 20.885 | 21.177 | 0 | 0 | 40000 |
| ycsb_hotspot_80_20 | certigap_pruned | 10000 | 6 | 11.807 | 12.105 | 3 | 144 | 40144 |
| ycsb_hotspot_80_20 | balanced_budgeted | 10000 | 6 | 13.731 | 14.008 | 13 | 624 | 40624 |
| ycsb_hotspot_80_20 | weighted_budgeted | 10000 | 6 | 12.916 | 13.127 | 13 | 624 | 40624 |
| ycsb_hotspot_80_20 | balanced_full_reference | 10000 | 9999 | 27.691 | 28.388 | 19999 | 959952 | 999952 |
| ycsb_hotspot_80_20 | std_lower_bound | 10000 | 0 | 20.964 | 21.316 | 0 | 0 | 40000 |
| ycsb_latest_biased | certigap_pruned | 10000 | 6 | 16.590 | 17.881 | 7 | 336 | 40336 |
| ycsb_latest_biased | balanced_budgeted | 10000 | 6 | 13.137 | 13.438 | 13 | 624 | 40624 |
| ycsb_latest_biased | weighted_budgeted | 10000 | 6 | 17.536 | 18.007 | 13 | 624 | 40624 |
| ycsb_latest_biased | balanced_full_reference | 10000 | 9999 | 27.387 | 28.099 | 19999 | 959952 | 999952 |
| ycsb_latest_biased | std_lower_bound | 10000 | 0 | 20.904 | 21.430 | 0 | 0 | 40000 |

## Matched-Budget Interpretation

- CertiGap has lower median batch lookup time than `balanced_budgeted` in `3/10` measured workload-size cases.
- CertiGap has lower median batch lookup time than `weighted_budgeted` in `6/10` measured workload-size cases.

## Limits

This is not an official YCSB, RocksDB, hardware-routing, cache-miss, or external-library benchmark. It is reproducible CPU-level evidence that the exported CertiGap decision tree executes real lookups with an explicit storage footprint. Production claims require a target storage engine, key encoding, allocator, CPU, and independent external baselines.

## AutoDRO Under Distribution Shift

# CertiGap-AutoDRO Fair Distribution-Shift Benchmark

`tuned_tv_dro` and `tuned_nominal` search the identical budgets, eta grid, solver set, and fallback set. Their only selection difference is TV radius `0.2` versus `0.0`; this is the primary DRO ablation.

| Scenario | n | Method | Solver | Fallback | Splits | Bytes | Candidates | Select s | Test mean | Test max |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| hot_reversal | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1142 | 6.63636 | 7.00000 |
| hot_reversal | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1115 | 6.63636 | 7.00000 |
| hot_reversal | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 6.82955 | 7.00000 |
| hot_reversal | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| hot_reversal | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 6.82955 | 7.00000 |
| hot_reversal | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.3269 | 7.67614 | 8.00000 |
| hot_reversal | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.3301 | 7.67614 | 8.00000 |
| hot_reversal | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 7.82955 | 8.00000 |
| hot_reversal | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| hot_reversal | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 7.82955 | 8.00000 |
| hot_reversal | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 0.9843 | 8.71591 | 9.00000 |
| hot_reversal | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 0.9955 | 8.71591 | 9.00000 |
| hot_reversal | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 8.82955 | 9.00000 |
| hot_reversal | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| hot_reversal | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 8.82955 | 9.00000 |
| partial_hot_drift_15 | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1158 | 3.70974 | 7.00000 |
| partial_hot_drift_15 | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1230 | 3.70974 | 7.00000 |
| partial_hot_drift_15 | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 3.76015 | 7.00000 |
| partial_hot_drift_15 | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| partial_hot_drift_15 | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 3.76015 | 7.00000 |
| partial_hot_drift_15 | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.3331 | 4.71571 | 8.00000 |
| partial_hot_drift_15 | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.3264 | 4.71571 | 8.00000 |
| partial_hot_drift_15 | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 4.76015 | 8.00000 |
| partial_hot_drift_15 | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| partial_hot_drift_15 | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 4.76015 | 8.00000 |
| partial_hot_drift_15 | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 0.9923 | 5.72167 | 9.00000 |
| partial_hot_drift_15 | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 0.9913 | 5.72167 | 9.00000 |
| partial_hot_drift_15 | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 5.76015 | 9.00000 |
| partial_hot_drift_15 | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| partial_hot_drift_15 | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 5.76015 | 9.00000 |
| partial_hot_drift_35 | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1205 | 4.39836 | 7.00000 |
| partial_hot_drift_35 | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1188 | 4.39836 | 7.00000 |
| partial_hot_drift_35 | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 4.48236 | 7.00000 |
| partial_hot_drift_35 | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| partial_hot_drift_35 | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 4.48236 | 7.00000 |
| partial_hot_drift_35 | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.3137 | 5.41228 | 8.00000 |
| partial_hot_drift_35 | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.3238 | 5.41228 | 8.00000 |
| partial_hot_drift_35 | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 5.48236 | 8.00000 |
| partial_hot_drift_35 | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| partial_hot_drift_35 | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 5.48236 | 8.00000 |
| partial_hot_drift_35 | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.0235 | 6.42620 | 9.00000 |
| partial_hot_drift_35 | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.0544 | 6.42620 | 9.00000 |
| partial_hot_drift_35 | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 6.48236 | 9.00000 |
| partial_hot_drift_35 | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| partial_hot_drift_35 | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 6.48236 | 9.00000 |
| partial_hot_drift_65 | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1211 | 5.43128 | 7.00000 |
| partial_hot_drift_65 | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1195 | 5.43128 | 7.00000 |
| partial_hot_drift_65 | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 5.56568 | 7.00000 |
| partial_hot_drift_65 | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| partial_hot_drift_65 | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 5.56568 | 7.00000 |
| partial_hot_drift_65 | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.3167 | 6.45714 | 8.00000 |
| partial_hot_drift_65 | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.3160 | 6.45714 | 8.00000 |
| partial_hot_drift_65 | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 6.56568 | 8.00000 |
| partial_hot_drift_65 | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| partial_hot_drift_65 | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.56568 | 8.00000 |
| partial_hot_drift_65 | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.0414 | 7.48299 | 9.00000 |
| partial_hot_drift_65 | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.0217 | 7.48299 | 9.00000 |
| partial_hot_drift_65 | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 7.56568 | 9.00000 |
| partial_hot_drift_65 | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| partial_hot_drift_65 | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.56568 | 9.00000 |
| stationary_hot_head | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1129 | 3.19328 | 7.00000 |
| stationary_hot_head | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1118 | 3.19328 | 7.00000 |
| stationary_hot_head | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 3.21849 | 7.00000 |
| stationary_hot_head | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| stationary_hot_head | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 3.21849 | 7.00000 |
| stationary_hot_head | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.3146 | 4.19328 | 8.00000 |
| stationary_hot_head | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.3117 | 4.19328 | 8.00000 |
| stationary_hot_head | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 4.21849 | 8.00000 |
| stationary_hot_head | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| stationary_hot_head | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 4.21849 | 8.00000 |
| stationary_hot_head | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.0152 | 5.19328 | 9.00000 |
| stationary_hot_head | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 0.9876 | 5.19328 | 9.00000 |
| stationary_hot_head | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 5.21849 | 9.00000 |
| stationary_hot_head | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| stationary_hot_head | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 5.21849 | 9.00000 |
| stationary_zipf | 32 | tuned_tv_dro | beam | fixed_rounds | 3 | 464 | 34 | 0.1183 | 4.30368 | 6.00000 |
| stationary_zipf | 32 | tuned_nominal | beam | midpoint_binary | 4 | 560 | 34 | 0.1127 | 4.20624 | 7.00000 |
| stationary_zipf | 32 | fixed_beam | beam | fixed_rounds | 4 | 560 | 1 | 0.0000 | 4.24755 | 6.00000 |
| stationary_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| stationary_zipf | 32 | fixed_weighted | weighted | fixed_rounds | 4 | 560 | 1 | 0.0000 | 4.34144 | 7.00000 |
| stationary_zipf | 64 | tuned_tv_dro | beam | midpoint_binary | 4 | 688 | 40 | 0.3163 | 4.99841 | 7.00000 |
| stationary_zipf | 64 | tuned_nominal | beam | midpoint_binary | 4 | 688 | 40 | 0.3192 | 4.94234 | 8.00000 |
| stationary_zipf | 64 | fixed_beam | beam | fixed_rounds | 4 | 688 | 1 | 0.0000 | 5.01343 | 7.00000 |
| stationary_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| stationary_zipf | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 5.15870 | 8.00000 |
| stationary_zipf | 128 | tuned_tv_dro | beam | midpoint_binary | 3 | 848 | 38 | 1.0143 | 5.75959 | 8.00000 |
| stationary_zipf | 128 | tuned_nominal | beam | midpoint_binary | 4 | 944 | 38 | 1.0443 | 5.65590 | 9.00000 |
| stationary_zipf | 128 | fixed_beam | beam | fixed_rounds | 3 | 848 | 1 | 0.0000 | 5.79996 | 8.00000 |
| stationary_zipf | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| stationary_zipf | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 5.94223 | 9.00000 |
| uniform_to_zipf | 32 | tuned_tv_dro | beam | fixed_rounds | 0 | 176 | 16 | 0.1168 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | tuned_nominal | beam | fixed_rounds | 0 | 176 | 16 | 0.1187 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_beam | beam | fixed_rounds | 0 | 176 | 1 | 0.0000 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_weighted | weighted | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| uniform_to_zipf | 64 | tuned_tv_dro | beam | fixed_rounds | 0 | 304 | 18 | 0.3073 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | tuned_nominal | beam | fixed_rounds | 0 | 304 | 18 | 0.3063 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_beam | beam | fixed_rounds | 0 | 304 | 1 | 0.0000 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| uniform_to_zipf | 128 | tuned_tv_dro | beam | fixed_rounds | 0 | 560 | 18 | 0.9577 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | tuned_nominal | beam | fixed_rounds | 0 | 560 | 18 | 0.9607 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | fixed_beam | beam | fixed_rounds | 0 | 560 | 1 | 0.0000 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| zipf_to_uniform | 32 | tuned_tv_dro | beam | fixed_rounds | 3 | 464 | 34 | 0.1211 | 5.50000 | 6.00000 |
| zipf_to_uniform | 32 | tuned_nominal | beam | midpoint_binary | 4 | 560 | 34 | 0.1195 | 5.75000 | 7.00000 |
| zipf_to_uniform | 32 | fixed_beam | beam | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.50000 | 6.00000 |
| zipf_to_uniform | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| zipf_to_uniform | 32 | fixed_weighted | weighted | fixed_rounds | 4 | 560 | 1 | 0.0000 | 6.03125 | 7.00000 |
| zipf_to_uniform | 64 | tuned_tv_dro | beam | midpoint_binary | 4 | 688 | 40 | 0.3160 | 6.46875 | 7.00000 |
| zipf_to_uniform | 64 | tuned_nominal | beam | midpoint_binary | 4 | 688 | 40 | 0.3186 | 6.82812 | 8.00000 |
| zipf_to_uniform | 64 | fixed_beam | beam | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.50000 | 7.00000 |
| zipf_to_uniform | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| zipf_to_uniform | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 7.20312 | 8.00000 |
| zipf_to_uniform | 128 | tuned_tv_dro | beam | midpoint_binary | 3 | 848 | 38 | 1.0597 | 7.59375 | 8.00000 |
| zipf_to_uniform | 128 | tuned_nominal | beam | midpoint_binary | 4 | 944 | 38 | 1.0239 | 7.82812 | 9.00000 |
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
| 16 | uniform | 0 | 4.000000 | 4.000000 | 0.000000 | yes | 0.093962 |
| 16 | uniform | 25 | 4.000000 | 4.000000 | 0.000000 | yes | 0.087158 |
| 16 | uniform | 100 | 4.000000 | 4.000000 | 0.000000 | yes | 0.092409 |
| 16 | uniform | 400 | 4.000000 | 4.000000 | 0.000000 | yes | 0.095180 |
| 16 | zipf | 0 | 3.737221 | 3.403220 | 0.089371 | no | 0.094900 |
| 16 | zipf | 25 | 3.737221 | 3.426050 | 0.083263 | no | 0.097786 |
| 16 | zipf | 100 | 3.737221 | 3.437218 | 0.080274 | no | 0.106464 |
| 16 | zipf | 400 | 3.737221 | 3.462515 | 0.073505 | no | 0.126316 |
| 16 | hot_tail | 0 | 3.654545 | 3.277613 | 0.103141 | no | 0.087670 |
| 16 | hot_tail | 25 | 3.654545 | 3.288693 | 0.100109 | no | 0.092019 |
| 16 | hot_tail | 100 | 3.654545 | 3.292455 | 0.099079 | no | 0.095336 |
| 16 | hot_tail | 400 | 3.654545 | 3.297565 | 0.097681 | no | 0.114852 |
| 32 | uniform | 0 | 5.000000 | 5.000000 | 0.000000 | yes | 0.266193 |
| 32 | uniform | 25 | 5.000000 | 5.000000 | 0.000000 | yes | 0.263863 |
| 32 | uniform | 100 | 5.000000 | 5.000000 | 0.000000 | yes | 0.265170 |
| 32 | uniform | 400 | 5.000000 | 5.000000 | 0.000000 | yes | 0.264759 |
| 32 | zipf | 0 | 4.601010 | 4.149104 | 0.098219 | no | 0.262052 |
| 32 | zipf | 25 | 4.601010 | 4.158535 | 0.096169 | no | 0.255145 |
| 32 | zipf | 100 | 4.601010 | 4.168352 | 0.094036 | no | 0.266763 |
| 32 | zipf | 400 | 4.601010 | 4.182008 | 0.091067 | no | 0.305036 |
| 32 | hot_tail | 0 | 4.663636 | 4.277613 | 0.082773 | no | 0.250916 |
| 32 | hot_tail | 25 | 4.663636 | 4.285225 | 0.081141 | no | 0.259912 |
| 32 | hot_tail | 100 | 4.663636 | 4.286757 | 0.080812 | no | 0.271527 |
| 32 | hot_tail | 400 | 4.663636 | 4.288841 | 0.080365 | no | 0.312429 |
| 64 | uniform | 0 | 6.000000 | 6.000000 | 0.000000 | yes | 0.712178 |
| 64 | uniform | 25 | 6.000000 | 6.000000 | 0.000000 | yes | 0.710620 |
| 64 | uniform | 100 | 6.000000 | 6.000000 | 0.000000 | yes | 0.751279 |
| 64 | uniform | 400 | 6.000000 | 6.000000 | 0.000000 | yes | 0.754302 |
| 64 | zipf | 0 | 5.359076 | 4.863833 | 0.092412 | no | 0.749528 |
| 64 | zipf | 25 | 5.359076 | 4.879230 | 0.089539 | no | 0.744300 |
| 64 | zipf | 100 | 5.359076 | 4.884646 | 0.088528 | no | 0.760271 |
| 64 | zipf | 400 | 5.359076 | 4.896088 | 0.086393 | no | 1.121251 |
| 64 | hot_tail | 0 | 5.654545 | 5.277613 | 0.066660 | no | 0.928767 |
| 64 | hot_tail | 25 | 5.654545 | 5.278164 | 0.066563 | no | 0.837380 |
| 64 | hot_tail | 100 | 5.654545 | 5.278815 | 0.066447 | no | 0.821664 |
| 64 | hot_tail | 400 | 5.654545 | 5.280205 | 0.066202 | no | 0.872658 |

## Interpretation

A zero reported gap is a proof for the configured TV radius, fallback, memory/build/tail cost model, and split budget. A nonzero gap is an honest unresolved interval, not an optimality claim.

## Dynamic CertiRange

# Dynamic CertiRange

Dynamic CertiRange extends the static budgeted lookup model into a complete
ordered range index.

It supports:

- point lookup;
- point update;
- inclusive range `sum`, `min`, and `max`;
- immutable snapshots through persistent path copying;
- workload-shaped routing;
- drift-triggered rebuilding;
- deterministic depth caps;
- independently replayed structural and optimizer artifacts.

## Python API

```python
from certigap import CertiRangeWorkload

workload = CertiRangeWorkload(32)
workload.add_point(1, 1000)
workload.add_range(1, 10, 500)
workload.add_update(2, 100)

index = workload.compile(
    values=list(range(32)),
    budget=6,
    eta=0.10,
    aggregate="sum",
    max_depth=10,
    routing="range_aware",
)

print(index.get(1))
print(index.range_query(1, 10))

snapshot = index.snapshot()
index.point_update(2, 1000)
assert snapshot.get(2) != index.get(2)

certificate = index.export_certificate()
```

Keys and ranges are one-based and ranges are inclusive.

## Structure

The routing solver emits a partial alphabetic tree. Every unresolved interval
is deterministically completed by a midpoint tree. If a proposed routing split
cannot fit inside `max_depth`, that interval is replaced by its balanced
completion.

The resulting full tree has exactly one leaf per key. Every internal node
stores the aggregate of its contiguous interval.

## Guarantees

For `n` keys and completed-tree height `h`:

- point lookup takes at most `h` routing steps;
- persistent point update copies `O(h)` nodes;
- range aggregate visits `O(h)` boundary nodes;
- the implementation exports the conservative executable bound `4h + 1`;
- memory is `O(n)` for the current root plus `O(h)` per retained update;
- `h <= max_depth`;
- snapshots acquired before an update remain unchanged.

The structural verifier reconstructs the deterministic completion, checks
every interval and split, recomputes all per-key depths and aggregates, and
validates canonical SHA-256 digests.

## Range-Aware Search

The former endpoint proxy converts range boundaries into point frequencies.
This is cheap but does not optimize actual range traversal.

`range_aware_beam_search` instead evaluates each candidate by replaying the
declared point, update, and range workload on its completed topology. Its
objective is

```text
(1 - eta) * mean_node_visits + eta * (max_point_depth + 1)
```

The balanced completion is always retained as an incumbent. Therefore the
returned bounded-search candidate is never worse than that included candidate
under the exact training-trace evaluator.

This is not a global guarantee for large instances. The repository validates
the implementation against complete routing-tree enumeration on small cases.

## C++ Core

`cpp/certigap_range.hpp` provides a contiguous-node sum implementation. The
C++ benchmark compares identical mixed traces against:

- a direct array;
- Fenwick tree;
- iterative segment tree;
- contiguous Dynamic CertiRange.

The current benchmark rejects a blanket speed claim: Fenwick and segment trees
win raw sum throughput. CertiRange's distinct features are workload-shaped
point paths, generic Python aggregates, persistent snapshots, drift control,
and replayable certificates.

## Scope

Dynamic CertiRange is currently an ordered fixed-key-universe index. It does
not yet support insertion or deletion, lazy range updates, disk pages,
concurrent writers, or an official storage-engine integration.

# Range-aware optimizer validation

- Rows: `114`
- Complete small-space oracle matches: `6/6`
- Scaling groups where range-aware is tied for best or best: `36/36`
- Strict improvements over point/endpoint proxy: `18/36`
- Every objective is recomputed by the exact mixed-trace evaluator.
- Scaling rows are bounded beam results, not global optimality claims.

The complete-tree-space checks validate the search implementation on n=8. The scaling matrix tests whether direct range-cost optimization improves over the former endpoint proxy without hiding cases where it ties or loses.

# C++ Dynamic CertiRange benchmark

- Rows: `36`
- Same deterministic mixed get/range-sum/update trace for every method.
- Latency is post-build median and p95 across whole-batch per-operation means.
- CertiRange uses contiguous nodes and a workload-shaped routing prefix.
- This local microbenchmark is not independent-hardware evidence.

| n | workload | fastest | CertiRange rank | CertiRange ns/op | fastest ns/op | hot depth vs balanced |
|---:|---|---|---:|---:|---:|---:|
| 1024 | clustered_range | fenwick | 4/4 | 78.3 | 12.8 | 12 vs 10 |
| 1024 | hotspot_point | array | 4/4 | 27.4 | 4.5 | 7 vs 10 |
| 1024 | uniform_mixed | fenwick | 4/4 | 63.6 | 14.1 | 10 vs 10 |
| 16384 | clustered_range | fenwick | 3/4 | 141.3 | 15.5 | 16 vs 14 |
| 16384 | hotspot_point | segment_tree | 3/4 | 55.1 | 9.2 | 11 vs 14 |
| 16384 | uniform_mixed | fenwick | 3/4 | 143.9 | 17.0 | 14 vs 14 |
| 100000 | clustered_range | fenwick | 3/4 | 201.0 | 16.9 | 18 vs 17 |
| 100000 | hotspot_point | segment_tree | 3/4 | 65.4 | 11.8 | 14 vs 17 |
| 100000 | uniform_mixed | fenwick | 3/4 | 178.3 | 18.1 | 17 vs 17 |

## Honest result

Fenwick or an iterative segment tree wins raw range-sum throughput in this matrix. CertiRange reduces hot-key depth on skewed traces, but irregular routing and recursive range traversal currently outweigh that comparison saving. The result rejects a blanket speed claim and motivates portfolio selection rather than replacing classical structures.

# Dynamic CertiRange mixed-workload benchmark

- Rows: `36`
- Operations: point get, range sum, and point update on identical deterministic traces.
- Latency: median and p95 across whole-batch per-operation means; Python microbenchmark, not production C++ latency.
- Build time: one untimed-for-operations construction; values are reset outside every measured repeat.
- Memory: `estimated_numeric_slots` is an analytical storage proxy, not measured RSS.
- Range endpoint frequencies are a routing heuristic and do not imply globally optimal range-query shape.

| n | workload | fastest method | CertiRange rank | CertiRange ns/op | fastest ns/op |
|---:|---|---|---:|---:|---:|
| 128 | clustered_range | array | 4/4 | 1563.1 | 139.8 |
| 128 | hotspot_point | array | 4/4 | 920.8 | 66.9 |
| 128 | uniform_mixed | array | 4/4 | 1588.7 | 107.8 |
| 512 | clustered_range | array | 4/4 | 2236.7 | 251.7 |
| 512 | hotspot_point | array | 4/4 | 1191.3 | 81.7 |
| 512 | uniform_mixed | array | 4/4 | 2185.7 | 159.2 |
| 2048 | clustered_range | fenwick | 4/4 | 3206.2 | 523.2 |
| 2048 | hotspot_point | array | 4/4 | 1741.5 | 119.1 |
| 2048 | uniform_mixed | array | 4/4 | 2660.9 | 357.1 |

## Interpretation

Fenwick and iterative segment trees are expected to win raw Python range-sum throughput. CertiRange's measured claim is different: it combines workload-shaped point paths, generic range aggregates, persistent snapshots, drift-aware rebuilding, and a replayable certificate.

A production speed claim requires the same benchmark in the C++ core on independent hardware.

## Certified AutoIndex

# Certified AutoIndex

`compile_autoindex` turns an ordered workload trace and explicit constraints
into an executable index. It evaluates a fixed, deterministic portfolio:

1. contiguous sorted array;
2. global prefix sums;
3. Fenwick tree;
4. square-root decomposition;
5. iterative segment tree;
6. sparse table for idempotent `min`/`max`;
7. point-proxy CertiRange;
8. range-aware CertiRange.

Every candidate remains in the exported artifact, including infeasible ones
and their rejection reasons. The independent verifier reconstructs all eight
candidates, recomputes resources and scores, and rejects omitted candidates,
changed winners, changed holdout results, or a modified digest.

```python
from certigap import AutoIndexConstraints, WorkloadTrace, compile_autoindex

trace = WorkloadTrace(32)
for _ in range(100):
    trace.add_range(3, 30)

index = compile_autoindex(
    range(32),
    trace,
    constraints=AutoIndexConstraints(aggregate="sum", budget=4),
)
print(index.summary())
print(index.range_query(3, 30))
```

## Selection Contract

The objective is

`(1-eta) * mean_visits + eta * max_visits + memory_weight * slots + build_weight * build_units`.

The compiler selects the feasible minimum on the training trace. Ties are
resolved by memory and then the published portfolio order. A chronological
holdout may be attached, but it is evaluation-only and cannot affect the
winner.

By default the unit is one declared structural primitive visit. It makes the
selection replayable, but it is not a nanosecond model. Production selection
can set `array_unit_cost`, `prefix_unit_cost`, `fenwick_unit_cost`,
`sqrt_unit_cost`, `segment_tree_unit_cost`, `sparse_unit_cost`, and
`certirange_unit_cost` from target-system measurements. The verifier includes
these coefficients in regeneration.

## Constraints And Capabilities

- `aggregate`: `sum`, `min`, or `max`; Fenwick and prefix sums require `sum`,
  while sparse tables require idempotent `min` or `max`.
- `memory_limit_slots`: excludes structures exceeding the declared model.
- `max_depth`: bounds candidate height.
- `require_persistent_snapshots`: restricts selection to CertiRange.
- `budget`: controls the adaptive CertiRange routing prefix.
- `*_unit_cost`: calibrates one structural visit for each backend family.

The current universe is static and rank-addressed. Insert/delete, disk-page
layouts, concurrency, and storage-engine latency remain outside the verified
scope.

Adding unrelated structures is intentionally avoided. Hash tables do not
support range aggregates, while B-trees, learned indexes, and wavelet trees
need different key, storage, or query semantics. They require a separate
capability grammar rather than misleading rows in this portfolio.

For deterministic JSON-to-C++ code generation and CMake wiring, see
[`COMPILER_INTEGRATION.md`](COMPILER_INTEGRATION.md).
The admission rules and capability-separated roadmap are in
[`PORTFOLIO_EXPANSION.md`](PORTFOLIO_EXPANSION.md).

# Certified AutoIndex validation

- Rows: `192` (`24` complete portfolios).
- Candidate count per portfolio: `8`.
- Independently replay-verified portfolios: `24/24`.
- Selection distribution: `{'certirange_range': 4, 'prefix_sum': 4, 'sorted_array': 12, 'sparse_table': 4}`.
- Mean chronological-holdout regret: `9.724479` primitive visits.
- Maximum chronological-holdout regret: `119.550000` primitive visits.

Selection uses training operations only. Holdout measures temporal generalization and is never consulted by the compiler. Scores are declared structural primitive visits, not wall-clock latency.

# Safe AutoIndex

`compile_safe_autoindex` adds a fail-closed deployment gate to the complete
AutoIndex portfolio. It separates data chronologically or experimentally into:

- `train`: constructs candidates and selects the minimum modeled score;
- `validation`: decides whether specialization has enough evidence;
- `test`: reports final behavior and never changes deployment.

The safe baseline is chosen on training data from a declared ordered set whose
default is array, Fenwick, and segment tree. If no baseline satisfies the
constraints, compilation fails instead of silently weakening the policy.

```python
from certigap import (
    SafeSelectionPolicy,
    WorkloadTrace,
    compile_safe_autoindex,
)

train = WorkloadTrace(32)
validation = WorkloadTrace(32)
test = WorkloadTrace(32)
for _ in range(200):
    train.add_range(3, 30)
for _ in range(50_000):
    validation.add_range(3, 30)
for _ in range(1_000):
    test.add_range(4, 29)

index = compile_safe_autoindex(
    range(32),
    train,
    validation,
    test_trace=test,
    policy=SafeSelectionPolicy(
        confidence_alpha=0.05,
        horizon_operations=1_000_000,
        migration_cost_units=500.0,
    ),
)
print(index.summary())
print(index.export_certificate())
```

The same workflow can emit a deployment-specific C++17 header without a
Python runtime:

```bash
certigap safe-compile safe_trace.json \
  --artifact build/safe-selection.json \
  --header build/safe-index.hpp

certigap verify build/safe-selection.json
certigap explain build/safe-selection.json
```

The strict input schema is
[`certigap_safe_compile_input_v1.schema.json`](../schemas/certigap_safe_compile_input_v1.schema.json).
The emitted backend is the validation-approved candidate or the actual safe
fallback, not necessarily the raw training winner. Its C++ configuration
embeds the outer safe-certificate digest.

## Decision Rule

For paired candidate-minus-baseline validation cost with sample mean
`mean_difference`, declared range width `B`, validation size `m`, and
one-sided error probability `alpha`, the certificate computes

`radius = B * sqrt(log(1/alpha) / (2m))`.

It deploys the candidate only when

`mean_difference + radius + (build + migration) / horizon < -minimum_improvement`.

Otherwise the conventional baseline remains deployed. The range bound is
deliberately conservative and covers every supported operation in the current
eight-backend grammar. The verifier independently recomputes the baseline,
bound, confidence radius, transition amortization, decision, test evaluation,
and both artifact digests.

## Claim Boundary

This is a Hoeffding guarantee conditional on independent IID bounded validation
operations and the declared structural-cost model. It does not prove:

- generalization under arbitrary temporal drift;
- portable wall-clock latency;
- correctness of manually supplied hardware coefficients;
- optimality outside the declared eight-candidate portfolio.

Temporal dependence needs a block-bootstrap, martingale, or mixing-process
certificate in a future schema. Until then, the IID condition must remain
visible in every scientific claim.

# Safe AutoIndex validation

- Cases: `16`.
- Candidate approvals: `4`.
- Safe fallbacks: `12`.
- Replay-verified certificates: `16/16`.
- Stable large validation approves specialization.
- Small samples, workload shift, and migration-dominated horizons retain the declared safe baseline.

The Hoeffding statement is conditional on independent IID bounded validation operations. Structural work is not portable wall-clock latency.

# Sequential Safe AutoIndex

`compile_sequential_safe_autoindex` permits inspection after every validation
operation without reusing a fixed-time confidence interval. It selects from
the complete eight-candidate AutoIndex portfolio, chooses a conventional safe
baseline from training data, and evaluates paired candidate-minus-baseline
structural costs in chronological order.

```python
from certigap import (
    SequentialSafeSelectionPolicy,
    WorkloadTrace,
    compile_sequential_safe_autoindex,
)

train = WorkloadTrace(8)
validation = WorkloadTrace(8)
for _ in range(100):
    train.add_range(2, 7)
for _ in range(2_000):
    validation.add_range(2, 7)

index = compile_sequential_safe_autoindex(
    range(8),
    train,
    validation,
    policy=SequentialSafeSelectionPolicy(
        confidence_alpha=0.05,
        minimum_observations=100,
        horizon_operations=1_000_000,
    ),
)
print(index.summary())
```

The deployment compiler is:

```bash
certigap sequential-safe-compile input.json \
  --artifact build/sequential-selection.json \
  --header build/sequential-index.hpp

certigap verify build/sequential-selection.json
certigap explain build/sequential-selection.json
```

The input is validated against
[`certigap_sequential_safe_compile_input_v1.schema.json`](../schemas/certigap_sequential_safe_compile_input_v1.schema.json).
The generated C++17 header embeds the outer sequential-certificate digest and
materializes the actually deployed candidate.

## Confidence Sequence

For operation `t`, let `X_t` be candidate work minus baseline work and let all
differences lie in an interval of width `B`. The compiler allocates

`alpha_t = alpha / (t(t+1))`.

At every eligible prefix it computes

`U_t = mean(X_1,...,X_t) + B sqrt(log(1/alpha_t)/(2t)) + transition/horizon`.

The candidate is deployed at the first prefix for which

`U_t < -minimum_improvement`.

Because `sum_t alpha_t = alpha`, fixed-time Hoeffding bounds and a union bound
give simultaneous coverage for every finite prefix. Therefore inspecting the
sequence continuously or stopping at its first crossing does not increase the
declared type-I error above `alpha`.

The certificate records the first eligible crossing, alpha allocated at that
operation, cumulative alpha spent, the final full-stream audit, and the number
of post-stop operations. The verifier reconstructs the complete first-crossing
decision. Editing only the stopping operation and recomputing the outer digest
is rejected.

## Exact Boundary

The theorem assumes independent identically distributed bounded validation
operations and a fixed candidate selected only from training data. It certifies
optional stopping during validation. It does not certify:

- arbitrary future workload drift;
- dependent or adversarial validation operations;
- measured nanosecond latency from structural work;
- correctness of manually calibrated unit costs;
- global optimality beyond the declared candidate portfolio.

The post-stop reversal experiment is intentionally an audit witness: it shows
that later observations cannot retroactively alter the recorded decision. It
does not claim that an old deployment remains safe after distribution shift.

# Sequential Safe AutoIndex validation

- Deployment scenarios: `4`.
- Candidate approvals: `2`.
- Replay-verified certificates: `4/4`.
- Stable evidence approves at the first valid prefix.
- Small samples and migration-dominated horizons fail closed.
- Post-stop reversal does not retroactively change deployment; `6512` operations remain evaluation-only.
- Mean-zero Monte Carlo false approvals: `0/5000` for alpha spending versus `576/5000` for invalid repeated fixed-time checks.

The confidence-sequence theorem is conditional on independent IID bounded validation operations. The Monte Carlo row is a diagnostic, not a proof and not evidence for arbitrary drift.

# Martingale Safe AutoIndex

Martingale Safe AutoIndex extends sequential deployment from IID validation to
bounded adapted observations under explicit conditional-mean null hypotheses.
It has two independently budgeted lifecycle gates:

- deployment rejects the null that specialization has no conditional expected
  advantage after required improvement and amortized transition cost;
- revocation rejects the null that the deployed candidate remains no worse
  than a declared tolerance.

If deployment evidence is insufficient, the conventional baseline remains
active. If post-deployment harm evidence crosses its threshold, the emitted
configuration returns to that baseline.

```python
from certigap import (
    MartingaleSafeSelectionPolicy,
    WorkloadTrace,
    compile_martingale_safe_autoindex,
)

train = WorkloadTrace(8)
monitoring = WorkloadTrace(8)
for _ in range(100):
    train.add_range(2, 7)
for _ in range(1_000):
    monitoring.add_range(2, 7)
for index in range(3_000):
    monitoring.add_update(1 + index % 8, float(index))

index = compile_martingale_safe_autoindex(
    range(8),
    train,
    monitoring,
    policy=MartingaleSafeSelectionPolicy(minimum_observations=50),
)
print(index.summary())
```

The example first deploys the training winner and later revokes it after an
update-heavy workload shift. Compilation to a verified C++17 configuration is:

```bash
certigap martingale-safe-compile input.json \
  --artifact build/martingale-selection.json \
  --header build/martingale-index.hpp
```

## E-process

Let `Y_t` be adapted to filtration `F_t`, have conditional mean at most zero,
and lie in an interval of width `B`. For fixed positive `lambda`, Hoeffding's
lemma makes

`E_t(lambda) = exp(lambda sum_{i<=t} Y_i - lambda^2 B^2 t / 8)`

a non-negative supermartingale. The implementation uses an equal-weight
mixture over declared dimensionless betting fractions `c_j`, with
`lambda_j = c_j/B`. A fixed mixture of supermartingales is again a
supermartingale. Ville's inequality therefore gives

`Pr(sup_t E_t >= 1/alpha) <= alpha`.

For deployment, `Y_t = -(D_t + A + m)`, where `D_t` is candidate work minus
baseline work, `A` is amortized transition cost, and `m` is required
improvement. For revocation, `Y_t = D_t - r`, where `r` is the allowed harm
tolerance. Deployment and revocation have separate alpha budgets and separate
e-processes.

## Certificate

The artifact contains the complete policy, first deployment crossing, first
revocation crossing, final audits, monitoring trace, selected baseline, final
backend, and outer digest. The replay verifier reconstructs both lifecycle
crossings and rejects edited decisions even if the outer digest is recomputed.

## Claim Boundary

The result permits adapted, non-IID bounded observations only under the stated
conditional-mean null. It does not prove:

- that arbitrary adversarial drift is harmless;
- that the candidate remains safe before harm is detected;
- correctness under unbounded or incorrectly bounded costs;
- wall-clock performance from structural work;
- global optimality outside the eight-backend portfolio.

Revocation controls false alarms under its null. It cannot eliminate detection
delay or losses accumulated before crossing.

# Martingale Safe AutoIndex validation

- Lifecycle scenarios: `4/4` replay-verified.
- Stable benefit deploys specialization.
- Insufficient evidence and migration cost fail closed.
- Update-heavy post-deployment harm revokes to baseline.
- Adapted-null false deployments: `101/5000` at nominal alpha `0.05`.

The Monte Carlo process has history-dependent amplitude and fresh mean-zero signs. It is diagnostic only; the formal claim follows from the e-process supermartingale and Ville inequality under the declared conditional-mean null.

# Proof-Carrying Data-Structure DSL

`ProofCarryingSpec` binds operation semantics, one canonical aggregate algebra,
resource constraints, a complete typed design grammar, deterministic selection,
and generated C++ into one digest-protected certificate.

```python
from certigap import (
    ProofCarryingSpec,
    WorkloadTrace,
    compile_proof_carrying_index,
    verify_dsl_certificate,
)

trace = WorkloadTrace(32)
for _ in range(100):
    trace.add_range(3, 29)

model = compile_proof_carrying_index(
    range(32),
    trace,
    ProofCarryingSpec(
        operations=("range",),
        algebra="sum",
        memory_limit_slots=96,
    ),
)
certificate = model.export_certificate()
print(verify_dsl_certificate(certificate))
header = model.render_cpp_header("my_index")
```

## Typed Grammar

The compiler enumerates exactly eight declarations:

| Design | Backend | Required laws |
|---|---|---|
| `flat_fold` | sorted array | monoid |
| `prefix_group` | prefix sum | commutative group |
| `fenwick_group` | Fenwick tree | commutative group |
| `sqrt_monoid` | square-root decomposition | monoid |
| `segment_monoid` | segment tree | monoid |
| `sparse_semilattice` | sparse table | idempotent semilattice |
| `certirange_point_monoid` | point-trained CertiRange | monoid |
| `certirange_range_monoid` | range-trained CertiRange | monoid |

The canonical `sum` model supplies a commutative group. Canonical `min` and
`max` supply idempotent commutative monoids. The artifact records both algebraic
eligibility and all ordinary memory, depth, and snapshot constraints. A design
is not silently removed when it is ineligible.

The Python wrapper rejects undeclared operations at runtime. Generated C++ uses
a contract-specific wrapper and does not expose undeclared methods, so an
attempted call fails at C++ compilation rather than silently leaving the
certified interface.

## Independent Verification

`verify_dsl_certificate()` does not trust the compiler summary. It:

1. checks the outer and grammar SHA-256 digests;
2. reconstructs the canonical algebra declaration;
3. independently regenerates all eight typed design rows;
4. verifies operation-contract conformance;
5. invokes the separate AutoIndex replay verifier for candidate costs,
   resources, routing trees, tie-breaking, and winner selection;
6. confirms that the selected DSL design maps to the verified backend.

Removing an infeasible design, changing a law, substituting a trace, or changing
the selected backend fails verification even if the attacker recomputes the
outer digest.

## One-Command Compilation

```bash
certigap-dsl compile input.json \
  --artifact certificate.json \
  --header generated.hpp \
  --namespace my_index

certigap-dsl verify certificate.json
certigap verify certificate.json
certigap explain certificate.json
```

The input schema is
`schemas/certigap_dsl_input_v1.schema.json`. Package consumers include the
generated header and link the ordinary `CertiGap::certigap` CMake target.
A ready input is available at `examples/proof_carrying_dsl.json`; the equivalent
Python API flow is `examples/proof_carrying_dsl.py`. Install the package first
with `python3 -m pip install -e .` when running examples from a source checkout.

## Evidence And Boundaries

The committed 36-case matrix covers all three built-in algebras, four operation
contracts, and default, tight-memory, and persistent-snapshot regimes. Every
case verifies grammar completeness and replays 160 runtime operations against a
list oracle.

The algebra declaration is a capability contract, not a machine proof of a
user-supplied function. In particular, `sum` uses mathematical real-addition
laws for structural reasoning, while the runtime uses `double`; IEEE-754
addition is not associative and can vary with evaluation order. DSL v1 does not
support arbitrary operators, insert/erase, lazy range updates, unbounded design
discovery, or portable wall-clock optimality.

# Proof-Carrying DSL Validation

The deterministic matrix covers `36` configurations: three canonical
algebras, four operation contracts, and three resource regimes. Every
configuration regenerates the complete typed grammar, independently verifies the
certificate, and replays 160 operations against a list oracle.

## Results

- Typed capability verification: `True`.
- Grammar completeness verification: `True`.
- Runtime/oracle checksum agreement: `True`.
- Selected backend diversity: `6` backends.
- Selection counts: `{"certirange_point": 3, "certirange_range": 9, "prefix_sum": 1, "segment_tree": 6, "sorted_array": 15, "sparse_table": 2}`.

## Boundary

The matrix validates the fixed-size DSL v1 grammar and built-in `sum`, `min`, and
`max` semantics. It does not establish portable latency optimality, arbitrary
user-defined algebra laws, insert/erase support, or global optimality outside the
declared eight-design grammar.

# SQLite Loadable Extension

CertiGap ships an actual SQLite loadable extension implemented against
`sqlite3ext.h`. It exposes connection-local named C++ adaptive indexes through
SQL functions:

```sql
.load ./certigap

SELECT certigap_build('catalog', '[0,1,2,3,4,5,6,7]');
SELECT certigap_range_sum('catalog', 2, 7);
SELECT certigap_optimize('catalog');
SELECT certigap_update('catalog', 4, 100);
SELECT certigap_get('catalog', 4);
SELECT certigap_selected('catalog');
SELECT certigap_drop('catalog');
```

Keys and range endpoints are 1-based, and both range endpoints are inclusive.
For example, `certigap_range_sum('catalog', 2, 7)` covers keys 2 through 7.

Build from a checkout:

```bash
python3 build_sqlite_extension.py --output build/certigap.so
```

After package installation:

```bash
certigap-sqlite-build --output certigap.so
```

On macOS use the `.dylib` suffix. If `sqlite3ext.h` is outside the standard
locations, set `SQLITE_INCLUDE_DIR`. CMake users can set
`-DCERTIGAP_BUILD_SQLITE_EXTENSION=ON`.

The function registry is isolated per SQLite connection, protected by a mutex, and
released when the connection closes. SQL argument types, finite values, key
ranges, JSON array syntax, and unknown names fail closed with SQLite errors.
The generated extension has no Python runtime dependency.

## Planner-Native Virtual Table

The same extension registers `certigap_vtab`:

```sql
CREATE VIRTUAL TABLE catalog_index USING certigap_vtab;
INSERT INTO catalog_index(key, value) VALUES (1, 10), (2, 20), (5, 50);

SELECT value FROM catalog_index WHERE key = 2;
SELECT value FROM catalog_index WHERE key >= 2 AND key <= 5 ORDER BY key;
SELECT range_sum FROM catalog_index WHERE key = 1 AND right_key = 5;
```

`xBestIndex` exposes equality, lower-bound, upper-bound, and combined bounded
range strategies to SQLite. The hidden `right_key` column activates one-call
inclusive range-sum pushdown. `EXPLAIN QUERY PLAN` reports the selected
strategy, for example `VIRTUAL TABLE INDEX 1:key_eq`.

Each virtual table owns a SQLite shadow table named `<table>_data`. It is the
durable source of truth. The C++ index is reconstructed on connection and
refreshed at transaction/read boundaries, so commits by another connection
cannot leave it as the authoritative stale copy. INSERT, key/value UPDATE,
DELETE, rollback, savepoint rollback, rename, drop, and reconnect are covered
by real SQLite CLI tests. WAL writers are serialized by SQLite and a
two-process test verifies visibility after lock handoff.

## Exact Boundary

This is a real `sqlite3_load_extension` and virtual-table integration. It is
not yet:

- an official YCSB binding;
- a replacement for SQLite's native B-tree storage;
- optimized for large insert/delete-heavy or multi-writer workloads;
- a disk-page-aware CertiGap layout;
- evidence of a performance improvement over SQLite B-trees.

The deterministic six-scenario artifact verifies planner selection,
range-sum pushdown, rollback/reconnect, mutation lifecycle, and shadow-table
agreement. It establishes integration correctness, not portable latency.

# SQLite Virtual-Table Validation

- Scenarios: `6`
- Passed: `6/6`
- Boundary: planner, durability, and transactional correctness; no cross-machine latency claim.

# Compiler And CMake Integration

CertiGap uses a profile-guided build step. It is not a GCC or Clang plugin:
the compiler consumes an operation trace before the C++ build, verifies all
eight portfolio candidates, and emits a normal C++17 configuration header.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install certigap_toolkit-1.10.1-py3-none-any.whl

certigap-compile include-dir
```

The last command prints the directory containing
`certigap_autoindex.hpp`.

For a simpler no-Python runtime mode, the same directory also contains the
standalone [`certigap.hpp`](ADAPTIVE_CPP.md).

## Input

The strict schema is
[`schemas/certigap_compile_input_v1.schema.json`](../schemas/certigap_compile_input_v1.schema.json).
Keys are 1-based ranks in a fixed ordered universe.

```json
{
  "schema": "certigap-compile-input-v1",
  "values": [0, 1, 2, 3],
  "train_trace": {
    "n": 4,
    "operations": [
      {"kind": "range", "left": 1, "right": 3},
      {"kind": "get", "left": 1},
      {"kind": "update", "left": 2, "value": 10}
    ]
  },
  "holdout_trace": {
    "n": 4,
    "operations": [{"kind": "range", "left": 2, "right": 4}]
  },
  "constraints": {
    "aggregate": "sum",
    "budget": 3,
    "memory_limit_slots": 64
  }
}
```

`right` defaults to `left`; `value` defaults to zero. Unknown fields, invalid
ranges, non-finite values, unsupported constraints, and conflicting output
paths fail closed.

## Compile And Verify

```bash
certigap-compile compile trace.json \
  --artifact build/selection.json \
  --header build/generated_index.hpp \
  --namespace my_project::generated

certigap-compile verify build/selection.json
```

The generated header embeds:

- selected backend and aggregate;
- key-universe size;
- verified artifact SHA-256;
- exact completed topology for a selected CertiRange backend;
- verified training score.

The verifier is run before code generation. Repeating compilation with the
same input and namespace produces byte-identical header text.

## C++ Usage

```cpp
#include "generated_index.hpp"

std::vector<double> values = load_values();
my_project::generated::Index index(values);

double item = index.get(1);
double total = index.range_query(1, 10);
index.point_update(2, 100.0);

auto old_view = index.snapshot();
```

The reusable header supports array, Fenwick, segment tree, and both CertiRange
variants. Selection is compile-time through `if constexpr`; no runtime
portfolio dispatch remains. `sum`, `min`, and `max` are supported, while
Fenwick is statically restricted to `sum`.

C++ `snapshot()` currently returns an independent value-copy in `O(n)` space
and time. It preserves old values correctly but does not claim the Python
CertiRange runtime's `O(h)` path-copy efficiency.

## CMake

The complete source-checkout example is in
[`examples/cmake_autoindex`](../examples/cmake_autoindex).

```bash
cmake -S examples/cmake_autoindex -B build/cmake-autoindex
cmake --build build/cmake-autoindex
build/cmake-autoindex/certigap_autoindex_example
```

For an installed package, obtain the include path during configuration:

```cmake
execute_process(
    COMMAND certigap-compile include-dir
    OUTPUT_VARIABLE CERTIGAP_INCLUDE_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    COMMAND_ERROR_IS_FATAL ANY
)

add_custom_command(
    OUTPUT "${CMAKE_CURRENT_BINARY_DIR}/generated_index.hpp"
           "${CMAKE_CURRENT_BINARY_DIR}/selection.json"
    COMMAND certigap-compile compile "${CMAKE_SOURCE_DIR}/trace.json"
            --artifact "${CMAKE_CURRENT_BINARY_DIR}/selection.json"
            --header "${CMAKE_CURRENT_BINARY_DIR}/generated_index.hpp"
    DEPENDS "${CMAKE_SOURCE_DIR}/trace.json"
    VERBATIM
)

target_include_directories(
    app PRIVATE
    "${CMAKE_CURRENT_BINARY_DIR}"
    "${CERTIGAP_INCLUDE_DIR}"
)
```

Header-only CMake installs also provide relocatable `pkg-config` metadata for
non-CMake consumers:

```bash
c++ -std=c++17 main.cpp $(pkg-config --cflags certigap) -o app
```

## Claim Boundary

The artifact certifies selection over the declared fixed portfolio and
analytical/calibrated work model. The generated header preserves that selected
configuration. It does not prove that GCC and Clang emit identical machine
code, nor that analytical work units equal production latency. Backend unit
costs should be calibrated on the target system when latency matters.

# Compiler integration validation

- Deterministic generated headers: `24/24`.
- Independently verified source artifacts: `24/24`.
- Candidate count per artifact: `8`.
- Selected backend distribution: `{'certirange_range': 4, 'prefix_sum': 4, 'sorted_array': 12, 'sparse_table': 4}`.
- Cross-language executable coverage is enforced by `tests/test_compiler_integration.py`.
- The CMake example compiles a generated CertiRange topology and checks snapshot isolation.

Header hashes cover exact generated C++ source. They certify deterministic code generation from a verified artifact, not compiler binary equivalence across toolchains.

# Adaptive Single-Header C++

`certigap.hpp` is the lowest-friction CertiGap interface. It requires only a
C++17 compiler: no Python, generated file, JSON, or custom compiler.

For the simplest container-like interface, use `adaptive_array<T>`:

```cpp
certigap::AutoTunePolicy policy;
policy.profile_path = "workload.profile";
certigap::adaptive_array<double> data(values, policy);

auto total = data.range_sum(2, 30);  // Zero-based [2,30).
std::cout << data.explain() << '\n';
```

It profiles operations, automatically evaluates deployment after warmup,
rejects backend changes below a declared score improvement, and restores the
profile on the next run. See [`ADAPTIVE_ARRAY.md`](ADAPTIVE_ARRAY.md).

## Online Compiler

Download
[`cpp/certigap.hpp`](../cpp/certigap.hpp), add it beside the program, and use:

```cpp
#include <iostream>
#include <vector>
#include "certigap.hpp"

int main() {
    std::vector<double> values{1, 2, 3, 4, 5};
    certigap::Index index(values);

    for (int repetition = 0; repetition < 100; ++repetition) {
        index.observe_range(1, 4);
    }
    index.optimize();

    std::cout << index.selected_name() << '\n';
    std::cout << index.range_query(1, 4) << '\n';
}
```

Compile as C++17:

```bash
g++ -std=c++17 -O2 main.cpp -o app
./app
```

## Automatic Profiling

Normal operations record themselves:

```cpp
index.get(key);
index.range_query(left, right);
index.point_update(key, value);
```

Use `peek` and `peek_range` for const, untracked inspection:

```cpp
double value = index.peek(key);
double total = index.peek_range(left, right);
```

Explicit observations warm the profile without executing an operation:

```cpp
index.observe_get(key, count);
index.observe_range(left, right, count);
index.observe_update(key, count);
```

Do not record an operation explicitly and then execute its tracked form unless
double weight is intended.

## Selection

```cpp
certigap::OptimizeOptions options;
options.aggregate = certigap::Aggregate::Sum;
options.memory_limit_slots = 4096;
options.tail_weight = 0.10;

auto backend = index.optimize(options);
std::cout << certigap::backend_name(backend) << '\n';

for (const auto& row : index.leaderboard()) {
    std::cout << certigap::backend_name(row.backend)
              << " score=" << row.score
              << " feasible=" << row.feasible << '\n';
}
```

The deterministic runtime portfolio contains a contiguous array, Fenwick
tree, iterative segment tree, point-weighted CertiRange, and
range-coverage-weighted CertiRange.

The range topology uses a difference-array coverage profile, prefix sums, and
depth-safe weighted splits. Profiling does not expand every range over every
covered key. Backend unit costs, memory/build penalties, maximum depth, and a
mandatory CertiRange constraint are configurable. Fenwick is automatically
infeasible for minimum and maximum aggregates.

## Drift Reoptimization

```cpp
certigap::RebuildPolicy policy;
policy.minimum_new_operations = 10'000;
policy.minimum_tv_drift = 0.10;

if (index.maybe_reoptimize(policy)) {
    std::cout << "new backend=" << index.selected_name() << '\n';
}
```

Reoptimization is explicit rather than silently occurring inside a query.
This avoids unpredictable latency spikes. TV drift is measured over the
current range-coverage routing distribution relative to the profile at the
previous optimization.

This statement applies to the lower-level `Index`. `adaptive_array` offers an
opt-in automatic policy; disable `automatic_maintenance` to preserve explicit
maintenance boundaries.

## Snapshots

```cpp
auto snapshot = index.snapshot();
index.point_update(2, 100);

assert(snapshot.peek(2) != index.peek(2));
```

Adaptive snapshots are independent value-copies. They copy the active runtime,
canonical values, point/update counts, and `q` distinct range records, taking
`O(n+q)` logical space. This is semantic isolation, not the Python CertiRange
path-copy implementation.

## CMake FetchContent

```cmake
include(FetchContent)
FetchContent_Declare(
    certigap
    GIT_REPOSITORY https://github.com/nazkari86-lab/certigap-toolkit.git
    GIT_TAG v1.10.1
)
FetchContent_MakeAvailable(certigap)

add_executable(app main.cpp)
target_link_libraries(app PRIVATE CertiGap::certigap)
```

Installed packages support:

```cmake
find_package(CertiGap 1.7 REQUIRED)
target_link_libraries(app PRIVATE CertiGap::certigap)
```

## Which Mode To Use

- Use `certigap.hpp` for learning, online compilers, prototypes, and simple
  application integration.
- Use `certigap-compile` when selection must be reproduced, independently
  verified, embedded into generated C++, and separated from runtime latency.
- Use the Python research API for exact/anytime algorithms, certificates, and
  benchmark reproduction.

The adaptive runtime returns all eight candidate reports and a deterministic
minimum under its declared model, but it does not export the independently
replayed omission-resistant certificate of `certigap-compile`.

# Adaptive single-header C++ validation

- Native C++ rows: `24`.
- Correct point/range/update/snapshot cases: `24/24`.
- Complete candidate reports per case: `8/8`.
- Selected backend distribution: `{'certirange_point': 4, 'prefix_sum': 4, 'segment_tree': 12, 'sorted_array': 4}`.
- Sizes: `16, 32, 64, 128`.
- Modes: point-hot, range-hot, calibrated segment tree, required CertiRange, minimum, and maximum.

This validates deterministic reference behavior and selection contracts. It is not a production latency benchmark.

# Adaptive Array

`certigap::adaptive_array<T>` is the low-friction runtime interface for users
who want automatic profiling without manually calling `observe_*` or
`optimize()`.

```cpp
#include <vector>
#include "certigap.hpp"

certigap::AutoTunePolicy policy;
policy.profile_path = "catalog.certigap-profile";

certigap::adaptive_array<double> data(values, policy);
auto value = data.get(4);
auto total = data.range_sum(10, 30);
data.update(4, 100.0);
```

The wrapper follows normal C++ indexing: positions are zero-based and ranges
are half-open `[first,last)`. The lower-level `certigap::Index` retains its
existing one-based inclusive API.

## Automatic Policy

Tracked operations build the workload profile. At `warmup_operations`, the
wrapper scores the eight native runtime candidates. A backend change is retained
only when its modeled relative improvement reaches
`minimum_relative_improvement`; otherwise the complete previous index is
restored. Later checks require both `check_interval` new operations and the
declared TV-drift threshold.

```cpp
policy.warmup_operations = 256;
policy.check_interval = 10'000;
policy.minimum_tv_drift = 0.10;
policy.minimum_relative_improvement = 0.05;
```

Automatic maintenance runs synchronously after a tracked operation. For a
latency-critical request path, disable it and move work to an application-safe
boundary:

```cpp
policy.automatic_maintenance = false;
// Request path records operations only.
data.range_sum(10, 30);
// Maintenance thread or explicit lifecycle boundary:
data.maintenance();
```

This is not an internally managed background thread. The application retains
control over scheduling and synchronization.

## Persistent Profiles

When `profile_path` is set, a prior workload profile is loaded during
construction and saved after decisions and, by default, on destruction. Values
are never written to this file; the calling application remains their source of
truth. Explicit persistence reports I/O errors:

```cpp
data.save_profile();
```

The strict text format records version, array size, aggregate, and positive
get/update/range weights. Import is transactional: malformed headers, size or
aggregate mismatches, invalid keys, non-finite weights, trailing content,
record-limit violations, and total-weight overflow are rejected before profile
state changes.

## Explainability

```cpp
std::cout << data.explain() << '\n';
```

Example:

```text
selected=fenwick observed=256 attempted=true switched=true improvement=81.2% reason="candidate passed deployment threshold"
```

Inspect a persisted profile without compiling the application:

```bash
certigap profile-explain catalog.certigap-profile
```

The percentage is improvement in the declared structural cost model. It is not
a measured latency prediction or a statistical no-regression guarantee. Use
SafeAutoIndex or Martingale SafeAutoIndex when deployment requires a
statistical gate.

The native validation artifact covers automatic point/range selection,
threshold rejection, explicit maintenance, and profile restoration in six
deterministic scenarios.

# Adaptive Array Validation

- Native scenarios: `6`
- Passed: `6/6`
- Covers: automatic warmup, point/range selection, deployment threshold, explicit maintenance, and cross-instance profile persistence.
- Boundary: model-score deployment gate; not a statistical no-regression or portable latency guarantee.

# Python AdaptiveArray

`AdaptiveArray` is the lowest-friction Python interface to the complete
eight-candidate AutoIndex portfolio. It observes normal operations, selects a
feasible backend after warmup, and preserves ordinary zero-based Python
indexing with half-open ranges.

```python
from pathlib import Path

from certigap import AdaptiveArray, AdaptiveArrayPolicy

policy = AdaptiveArrayPolicy(profile_path=Path("catalog.profile"))
with AdaptiveArray(range(1_000), policy=policy) as data:
    total = data.range_sum(10, 40)
    data.update(12, 100.0)
    print(total, data.get(12), data.explain())
```

The portfolio contains sorted array, prefix sum, Fenwick, segment tree,
square-root decomposition, sparse table, and two CertiRange variants.
Unsupported candidates are filtered by aggregate and memory constraints.

## Deployment Policy

```python
policy = AdaptiveArrayPolicy(
    warmup_operations=256,
    check_interval=10_000,
    minimum_tv_drift=0.10,
    minimum_relative_improvement=0.05,
    max_profile_operations=100_000,
)
```

The bounded profile decays before exceeding its configured capacity. The
modeled winner replaces the current backend only when it clears the relative
improvement threshold. `automatic_maintenance=False` moves compilation to an
explicit `data.maintenance()` call. Public operations and lifecycle methods
are serialized by a reentrant lock; this is correctness-oriented thread
safety, not a parallel-throughput claim.

## Persistent Warm Start

When `profile_path` is configured, construction reads the same strict
`CERTIGAP_PROFILE_V1` format used by the C++ container. `close()` or a context
manager writes it atomically using a temporary file and `os.replace`. The
profile stores operation counts, never array values.

The deployment threshold compares declared structural scores. It is neither a
wall-clock guarantee nor a statistical no-regression certificate. Use the Safe
or Martingale SafeAutoIndex APIs when those assumptions and guarantees match
the deployment.

Reproduce the seven Python lifecycle scenarios with:

```bash
python3 generate_python_adaptive_array_validation.py
```

The committed output is
[`results/python_adaptive_array_validation.csv`](../results/python_adaptive_array_validation.csv).

# Python AdaptiveArray Validation

Deterministic semantic and lifecycle checks for the public Python API.

| Scenario | Selected | Optimized | Passed |
|---|---|---:|---:|
| automatic_range_warmup | prefix_sum | True | True |
| automatic_point_warmup | sorted_array | True | True |
| mixed_update_workload | fenwick | True | True |
| deployment_threshold_rejection | sorted_array | False | True |
| explicit_maintenance | sparse_table | True | True |
| profile_writer | prefix_sum | True | True |
| profile_reader | prefix_sum | True | True |

# Measured Safe Deployment

`compile_measured_autoindex` separates three roles:

1. a training trace selects the analytical candidate;
2. an independent validation trace is replayed against the conventional
   baseline and candidate with alternating execution order;
3. a bounded paired-harm gate decides whether to deploy the candidate.

```python
from certigap import (
    AdaptiveSpec,
    MeasuredDeploymentPolicy,
    WorkloadTrace,
    compile_measured_autoindex,
)

train = WorkloadTrace(1_000)
validation = WorkloadTrace(1_000)
for _ in range(200):
    train.add_range(10, 900)
    validation.add_range(20, 850)

index = compile_measured_autoindex(
    range(1_000),
    train,
    validation,
    AdaptiveSpec(operations=("range",), memory_limit_slots=4_000),
    policy=MeasuredDeploymentPolicy(
        alpha=0.05,
        repetitions=64,
        amortization_operations=100_000,
    ),
)
print(index.explain())
```

For each paired batch, normalized harm is

`(candidate_ns - baseline_ns) / max(candidate_ns, baseline_ns)`.

It lies in `[-1,1]`. The candidate is deployed only if a one-sided Hoeffding
upper bound on mean harm clears the configured improvement threshold. Positive
candidate build overhead is amortized over the declared operation horizon.
The artifact stores every pair, policy, trace, environment, structural
selection, decision, and digest. The independent verifier recomputes the bound
and rejects rewritten measurements or decisions.

## Boundary

The statistical interpretation requires representative independent bounded
repetitions. Replays from one process may contain autocorrelation, timer noise,
thermal effects, and scheduler interference. The certificate therefore does
not establish p99 latency, future-drift safety, cross-machine transfer, or a
production service-level objective. It is a fail-closed measured prototype,
not a replacement for a prospective production experiment.

`results/measured_deployment_validation.csv` contains deterministic synthetic
decision-boundary cases. Real timer replay is covered by the runtime test suite
but is deliberately not committed as portable benchmark evidence.

# Measured Deployment Gate Validation

Deterministic boundary cases for the paired bounded-harm decision.
These are synthetic latency pairs, not hardware benchmark results.

| Scenario | Mean harm | Upper bound | Deploy | Passed |
|---|---:|---:|---:|---:|
| strong_win | -0.900000 | -0.594032 | True | True |
| weak_win | -0.100000 | 0.205968 | False | True |
| parity | 0.000000 | 0.305968 | False | True |
| regression | 0.166667 | 0.472635 | False | True |

# TrackingAutoIndex: Certified Causal Representation Tracking

## Problem

Train-only AutoIndex selects one representation. `TrackingAutoIndex` instead
keeps the complete feasible AutoIndex portfolio and may migrate while the
workload changes. A state is an executable backend such as a sorted array,
prefix sum, Fenwick tree, segment tree, or CertiRange. The current operation
reveals a non-negative structural service-cost vector over these states.

For state path `s_1,...,s_T`, initial state `s_0`, service costs `c_t`, and
positive migration metric `d`, total modeled cost is

```text
sum_t c_t(s_t) + d(s_(t-1), s_t).
```

This is a finite metrical task system. The implementation uses the
deterministic Work Function Algorithm (WFA):

```text
w_0(s) = d(s_0, s)
w_t(s) = c_t(s) + min_y (w_(t-1)(y) + d(y, s))
s_t = argmin_s (w_t(s) + d(s_(t-1), s)).
```

The selected backend is actually materialized from canonical values before
the operation executes. Future operations are never inspected.

## Exact Comparator

The certificate computes an exact offline comparator allowed at most `K`
switches:

```text
D[t,s,k] = c_t(s) + min_y (
    D[t-1,y,k-[y != s]] + d(y,s)
).
```

Every predecessor is retained, so the verifier reconstructs both minimum cost
and the deterministic optimal path. Complexity is `O(T K m^2)` time and
`O(Km)` working memory for `m` feasible backends. Setting `K=T` gives the exact
unrestricted offline oracle. The artifact reports exact ex-post dynamic regret
against the declared K-switch comparator.

## Python API

```python
from certigap import (
    AdaptiveSpec,
    TrackingPolicy,
    WorkloadTrace,
    start_tracking_autoindex,
)

train = WorkloadTrace(32)
for key in range(1, 33):
    train.add_get(key)

index = start_tracking_autoindex(
    range(32),
    train,
    AdaptiveSpec(),
    policy=TrackingPolicy(
        migration_cost_units=8.0,
        max_comparator_switches=3,
    ),
)

for _ in range(20):
    index.range_query(1, 32)
index.point_update(1, 100.0)

certificate = index.export_certificate()
print(index.explain())
```

Verify or explain the emitted JSON with the unified CLI:

```bash
certigap verify tracking.json
certigap explain tracking.json
```

## Native C++ API

`certigap_tracking.hpp` provides a dependency-free C++17 implementation over
the conventional array, prefix, Fenwick, square-root, segment-tree, and sparse
table runtimes. Sum portfolios exclude sparse tables; min/max portfolios
exclude prefix sums and Fenwick trees.

```cpp
#include <certigap_tracking.hpp>

std::vector<double> values(4096, 1.0);
certigap::TrackingPolicy policy;
policy.backends = {
    certigap::Backend::SortedArray,
    certigap::Backend::PrefixSum,
    certigap::Backend::Fenwick,
    certigap::Backend::SqrtDecomposition,
    certigap::Backend::SegmentTree,
};
policy.migration_matrix = certigap::tracking_rebuild_metric(
    values.size(), policy.backends);
policy.record_history = false;

certigap::TrackingAutoIndex index(values, certigap::Aggregate::Sum, policy);
auto answers = index.run_batch({
    certigap::TrackingOperation::range(1, 4096),
    certigap::TrackingOperation::update(10, 7.0),
    certigap::TrackingOperation::get(10),
});
```

For low-overhead deployment without full per-operation WFA accounting, use the
sampled controller. It keeps an always-current Fenwick shadow for sums (segment
tree for min/max), evaluates candidates once per 32 operations, and enters a
4096-operation lease after four stable decisions. An update that invalidates a
static prefix/sparse view falls back to the robust shadow immediately.

```cpp
certigap::FastTrackingAutoIndex fast(values, certigap::Aggregate::Sum);
double total = fast.range_query(1, 4096);
fast.point_update(10, 7.0);
fast.flush();  // process a partial sampling epoch before inspection
auto explanation = fast.explain();
```

### Detached data and control planes

Applications that already have sampled telemetry can remove observation from
the request path. `hot_*` methods execute only data-structure work and safe
fallback; `observe_sample(operation, represented_operations)` updates the
controller without executing the operation. Samples should represent equal-size
batches inside an epoch.

```cpp
double total = fast.hot_range_query(1, 4096);  // valid one-based input required
fast.observe_sample(certigap::TrackingOperation::range(1, 4096), 4096);
if (fast.maintenance_pending()) {
    fast.maintenance();
}
```

Set `FastTrackingPolicy::defer_specialist_rebuilds=true` to keep rebuilds out
of the request that made the decision. `maintenance()` constructs the pending
specialist from current canonical values. The class is not internally
thread-safe: call maintenance only when no operation is concurrent, or protect
the entire index with external synchronization. This is an explicit maintenance
boundary, not a claimed lock-free RCU implementation.

### Frozen deployment

`freeze()` returns a fixed dynamic backend with no controller, sampling, shadow,
or switching. When the deployment backend is known at compile time,
`freeze_static<Backend, Aggregate>()` additionally removes indirect dispatch.

```cpp
auto dynamic = fast.freeze();
auto compiled = fast.freeze_static<
    certigap::Backend::Fenwick,
    certigap::Aggregate::Sum>();
double answer = compiled.range_query(1, 4096);
```

`unchecked_*` and `hot_*` require valid one-based keys, valid inclusive ranges,
and finite update values. Use checked methods at trust boundaries.

`FastTrackingAutoIndex` guarantees the same query/update semantics, validates
its policy fail-closed, and is covered by randomized ASan/UBSan differential
tests. It deliberately does not claim WFA competitiveness: sampling, leases,
directed rebuild costs, and robust fallback are runtime engineering choices.
Use `TrackingAutoIndex` when full trajectories, exact offline comparators, or
the metrical-task-system theorem are required.

The rebuild helper uses `max(build(i), build(j))` off the diagonal. This is a
positive symmetric metric satisfying the triangle inequality, unlike a raw
directed conversion table. General non-negative directed matrices are allowed,
but `wfa_competitive_factor()` returns zero because the classical MTS theorem
does not apply. Production mode reuses WFA scratch buffers and omits trajectory
allocation. Exact oracles fail closed unless `record_history=true`.

## What The Certificate Establishes

- The nested AutoIndex portfolio and every feasible candidate are replayed.
- Every operation's complete service-cost vector is regenerated.
- Every WFA work vector, tie-break, migration, and cumulative cost is replayed.
- Exact constrained and unrestricted offline oracles are independently
  recomputed.
- Digest-preserving modification of a trajectory still fails verification.

The classical WFA result is `(2m-1)`-competitiveness for finite metrical task
systems under the theorem's standard conventions, including an
initialization-dependent additive term. The artifact records this factor and
whether the stronger factor-only inequality happens to hold on the observed
trace. It does not present that observed Boolean as a universal theorem proof.
See Borodin, Linial, and Saks, [An optimal on-line algorithm for metrical task
systems](https://doi.org/10.1145/28395.28435), and the
[MTS survey summary](https://drops.dagstuhl.de/entities/document/10.4230/DagSemProc.05031.29).

## Boundaries

- Structural units are not portable nanoseconds. Target measurements should
  calibrate candidate unit costs and migration cost.
- The portfolio and operation grammar remain fixed and explicit.
- Python certificates currently use a positive uniform metric. Native C++ also
  accepts a verified rebuild-aware metric or an explicitly non-theorem directed
  matrix.
- WFA observes the current operation cost before moving, but never future cost.
- The K-switch oracle is retrospective and is used for evaluation, not routing.
- Runtime switching has no statistical no-regression gate. Use measured or
  martingale-safe deployment paths when that is the required guarantee.
- Inserts, deletes, concurrency, durability, and disk-page layouts are outside
  the current runtime contract.

The committed 15-scenario matrix includes stationary workloads, phase shifts,
alternation, and three migration costs. All certificates replay. Maximum exact
K-switch regret is `121` structural units and maximum observed ratio to the
unrestricted oracle is `2.657534`; both wins and losses are therefore visible.

## Comprehensive Comparison

The broader maximum matrix adds 126 certified configurations over 14 workload
families, three key-universe sizes, and migration costs `2`, `8`, and `32`.
Every policy uses exactly the same per-operation service rows.

- Against the unchanged initial representation, WFA records `106` wins, `18`
  ties, and `2` losses.
- Against the best fixed representation selected with hindsight, it records
  `53` wins, `34` ties, and `39` losses.
- Against myopic current-operation switching, it records `29/62/35`.
- Against a cumulative-service leader, it records `55/39/32`.
- Median ratio to the exact unrestricted oracle is `1.009222`; mean is
  `1.111103`, and maximum is `2.068306`.
- At migration cost `2`, mean oracle ratio is `1.003004`. At cost `32`, it is
  `1.250766`, showing that migration calibration materially changes quality.

The Python wall-clock matrix has 90 method rows, five workloads, two sizes,
five repetitions, and identical checksum validation. Tracking is `96.42x` to
`958.87x` slower than the fastest fixed portfolio backend in these runs. The
gap includes online cost-vector construction, WFA accounting, trace recording,
and in-trace rebuilds, but excludes initial construction and certificate
export. Therefore the present Python path is a research reference, not a
low-latency replacement for Fenwick or prefix sums.

The native matching benchmark adds four phased workloads at `n=64,256,4096`.
Rebuild-aware production runs at `61.23-317.23 ns/op` on the recorded machine
and uniform native mode is `173.2x-15952.7x` faster than the matching Python
reference. It still costs `11.2x` median versus the fastest fixed C++ backend,
so tracking is useful when the best representation changes or is unknown, not
as a universal Fenwick replacement. Full audit history adds `2.04x` median.
On larger read-mostly streams, rebuild-aware migration cuts switches by
`360x-394x` and improves runtime by `3.6x-16.4x` over naive uniform migration.

The separate Fast matrix covers 64 configurations: four sizes, eight stationary
or adversarial workloads, and 5,000/50,000-operation horizons. All implementation
checksums agree. Relative to Fenwick, Fast is `1.21x` median, `1.59x` p95, and
`1.90x` worst-case. Relative to the fastest fixed backend selected with hindsight,
the same figures are `1.35x` median and `5.40x` worst-case. The second comparator
can choose an O(1)-update array after seeing that no future range query arrives;
a causal online system cannot safely make that assumption.

See `results/tracking_autoindex_comparison.md` for the complete outcome tables,
`tracking_autoindex_comparison.csv` for policy rows,
`tracking_autoindex_candidates.csv` for every fixed backend, and
`tracking_autoindex_runtime.csv` for Python timing. Native raw rows and
provenance are in `tracking_autoindex_native_runtime.csv` and its metadata JSON.
Fast-mode rows and provenance are in `tracking_autoindex_fast_runtime.csv` and
`tracking_autoindex_fast_runtime.metadata.json`.
The paired hot-path matrix is in `tracking_hot_path_runtime.csv`; at the
50,000-operation horizon checked static Fenwick records `1.01x` median and
`1.23x` maximum versus a direct Fenwick runtime on this machine.

# TrackingAutoIndex validation

- Scenarios: `15`.
- Independently replay-verified certificates: `15/15`.
- Maximum exact K-switch dynamic regret: `121.000000` structural units.
- Maximum observed unrestricted-oracle ratio: `2.657534`.
- Migration costs tested: `2`, `8`, and `32` structural units.

Every row executes the selected backend and independently replays the causal Work Function Algorithm. The comparator is an exact dynamic-programming oracle with at most three switches. Costs are analytical structural work, not portable wall-clock latency.

# TrackingAutoIndex comprehensive comparison

- Certified workload configurations: `126`.
- Structural policy rows: `882`.
- Fixed-candidate rows: `882`.
- Wall-clock method rows: `90`.
- All runtime methods passed identical checksum validation.

## Structural outcomes

- Versus `initial_static`: WFA wins `106`, ties `18`, loses `2`.
- Versus `best_fixed_hindsight`: WFA wins `53`, ties `34`, loses `39`.
- Versus `myopic_current_operation`: WFA wins `29`, ties `62`, loses `35`.
- Versus `cumulative_leader`: WFA wins `55`, ties `39`, loses `32`.
- Mean ratio to exact unrestricted oracle: `1.111103`.
- Median ratio to exact unrestricted oracle: `1.009222`.
- Maximum ratio to exact unrestricted oracle: `2.068306`.
- Best fixed candidate frequency: `{'fenwick': 81, 'prefix_sum': 27, 'sorted_array': 18}`.

### Versus best fixed hindsight by workload

| Workload | Wins | Ties | Losses |
|---|---:|---:|---:|
| `stable_points` | 0 | 9 | 0 |
| `stable_ranges` | 0 | 6 | 3 |
| `stable_updates` | 0 | 9 | 0 |
| `mixed_read_heavy` | 3 | 1 | 5 |
| `mixed_write_heavy` | 5 | 0 | 4 |
| `point_to_range` | 0 | 6 | 3 |
| `range_to_update` | 9 | 0 | 0 |
| `update_to_range` | 9 | 0 | 0 |
| `three_phase` | 8 | 0 | 1 |
| `alternating_range_update` | 3 | 0 | 6 |
| `short_bursts` | 7 | 0 | 2 |
| `random_iid` | 4 | 0 | 5 |
| `markov_bursty` | 5 | 0 | 4 |
| `varying_ranges` | 0 | 3 | 6 |

### Migration sensitivity

| Migration units | Mean oracle ratio | Max oracle ratio | Mean switches |
|---:|---:|---:|---:|
| 2 | 1.003004 | 1.026316 | 12.571 |
| 8 | 1.079540 | 1.545946 | 4.333 |
| 32 | 1.250766 | 2.068306 | 1.714 |

## Runtime boundary

- Median TrackingAutoIndex slowdown versus fastest tested runtime: `288.06x`.
- Maximum TrackingAutoIndex slowdown versus fastest tested runtime: `1952.02x`.
- Median slowdown versus fastest fixed portfolio backend: `280.86x`.
- Maximum slowdown versus fastest fixed portfolio backend: `958.87x`.
- These Python timings include online WFA accounting and in-trace rebuilds, but exclude initial construction and certificate export.
- Structural scores and wall-clock nanoseconds are reported separately; neither is substituted for the other.

| n | Workload | Tracking ns/op | Fastest fixed | Fixed ns/op | Slowdown |
|---:|---|---:|---|---:|---:|
| 64 | `alternating_range_update` | 34211.9 | `sorted_array` | 354.8 | 96.42x |
| 64 | `mixed_read_heavy` | 34074.1 | `prefix_sum` | 268.6 | 126.88x |
| 64 | `point_to_range` | 43244.5 | `prefix_sum` | 167.8 | 257.71x |
| 64 | `stable_points` | 18025.7 | `sorted_array` | 126.3 | 142.72x |
| 64 | `stable_ranges` | 47897.9 | `prefix_sum` | 157.6 | 304.01x |
| 256 | `alternating_range_update` | 132611.0 | `fenwick` | 649.9 | 204.05x |
| 256 | `mixed_read_heavy` | 131029.0 | `fenwick` | 358.1 | 365.93x |
| 256 | `point_to_range` | 129876.5 | `prefix_sum` | 143.6 | 904.72x |
| 256 | `stable_points` | 124540.9 | `prefix_sum` | 129.9 | 958.87x |
| 256 | `stable_ranges` | 135776.9 | `prefix_sum` | 157.9 | 860.03x |

# CertiGap-X Certified Structure Synthesis

CertiGap-X extends fixed-portfolio selection with a synthesized
`VariableBlockIndex`. It partitions ordered keys into unequal contiguous
blocks. A range query reads one precomputed aggregate for each fully covered
block and scans only partially covered block fragments.

```python
from certigap import SynthesisConstraints, WorkloadTrace
from certigap import compile_synthesized_index, verify_synthesis_certificate

trace = WorkloadTrace(32)
for _ in range(100):
    trace.add_range(2, 11)

model = compile_synthesized_index(
    range(32),
    trace,
    constraints=SynthesisConstraints(max_blocks=12, max_block_width=16),
)
print(model.selected_boundaries)
print(verify_synthesis_certificate(model.export_certificate()))
```

## Exact Grammar

For every block count up to `max_blocks`, the compiler considers every
contiguous partition whose blocks do not exceed `max_block_width`. Dynamic
programming returns the exact minimum for each block count. The final winner
is the feasible minimum across that complete frontier.

For operation `o` and block `B`, let `c(o,B)` be the declared calibrated
primitive cost contributed by that block. Whole-operation cost is
`C(o,P)=sum_B c(o,B)`. Therefore:

`mean_o C(o,P) = sum_B mean_o c(o,B)`

and

`max_o C(o,P) <= sum_B max_o c(o,B)`.

The optimized additive objective is consequently a certified upper bound on
the requested mean/tail objective. It is intentionally conservative: the
partition minimizing this upper bound need not minimize measured `p99`.

## Hardware Calibration

```bash
python3 calibrate_hardware.py --output hardware_profile.json
```

The C++17 calibrator records median primitive costs. A certificate is
conditional on these supplied measurements. The verifier checks their digest
and recomputes the complete frontier, but cannot prove that another machine
has the same latency.

## C++ Export

`model.render_cpp_header("my_index")` emits a deterministic configuration that
uses `cpp/certigap_synth.hpp`. Python and generated C++ share inclusive
1-based point/range/update semantics. Memory accounting is `2n+2b` scalar
slots: values, key-to-block mapping, boundaries, and block aggregates.

## Safe Migration

`migration_decision` permits rebuilding only when projected horizon savings
strictly exceed rebuild cost plus an explicit confidence margin. This is an
amortization rule, not a workload forecast or statistical confidence
estimator.

## Native Holdout Result And Successor

The structural theorem does not imply wall-clock speed. The matched native
benchmark selects partitions from `800` train operations and measures five C++
implementations on `6000` separately seeded holdout operations. It covers four
stationary synthetic cases, one temporal shift, and three public
frequency-derived cases.

The original committed audit found that CertiGap-X did not beat Fenwick. That
negative result motivated CertiGap-H, which replaces the covered-block loop
with local and top-level prefix arrays and changes the exact objective to
model range-boundary separation and update suffix writes.

The practical policy remains fail-safe: AutoIndex chooses between global
prefix, Fenwick, and the synthesized hybrid from train measurements. See
[`results/synthesis_native_latency.md`](../results/synthesis_native_latency.md)
and [`HYBRID.md`](HYBRID.md).

## Claim Boundary

The current grammar synthesizes in-memory rank-addressed block indexes. It
does not yet include PGM/ALEX, concurrency, inserts/deletes, disk pages, SIMD
layouts, or a storage-engine integration. Committed validation uses portable
unit primitive costs; target-specific nanoseconds must be measured locally.

# CertiGap-X synthesis validation

- Exact independently verified portfolios: `24/24`.
- Runtime oracle passes: `24/24`.
- Nonuniform selected designs: `20/24`.
- Mean certified gain over best uniform blocks: `31.79%`.
- Maximum certified gain over best uniform blocks: `91.67%`.
- Minimum certified gain over best uniform blocks: `0.00%`.

The committed matrix uses unit primitive costs for deterministic reproduction. Machine-specific nanosecond profiles are conditional inputs produced by `calibrate_hardware.py`, not portable facts.

# CertiGap-H: Certified Hybrid Prefix Index

CertiGap-H is the representation-aware successor to the original
variable-block aggregate index. It stores:

- the original values;
- one local prefix array restarted at every synthesized block;
- one prefix array over complete block sums;
- a key-to-block map and block boundaries.

A range sum uses at most two local-prefix differences and one block-prefix
difference. It does not loop over covered blocks.

## Complexity

For `n` values, `b` blocks, and the updated key's remaining block suffix `w`:

| Operation | Time |
|---|---:|
| `get` | `O(1)` |
| `range_query` | `O(1)` |
| `point_update` | `O(w + b)` |
| build | `O(n + b)` |
| memory | `3n + 2b` scalar slots |

This deliberately targets read-heavy mixed workloads. A global prefix array
is simpler and usually faster when updates are absent. Fenwick becomes safer
as update frequency increases.

## Exact Representation-Aware Synthesis

For a candidate block `[l,r]` at position `j` in a `b`-block partition, the
partition-dependent work model charges:

- a range only when its endpoints are separated by the boundary after this
  block;
- an update at key `k` for `r-k+1` local-prefix writes and `b-j+1`
  block-prefix writes;
- declared primitive costs and memory penalties.

Every range-separation charge belongs to exactly the block containing its left
endpoint. Every update belongs to exactly one block. Mean work is therefore
additive. The sum of per-block maxima remains a conservative upper bound on
the whole-operation maximum.

For every legal block count, dynamic programming evaluates all contiguous
partitions respecting `max_block_width`. The independent verifier separately
reconstructs statistics, the complete frontier, tie-breaking, and the winner.
Proof-critical interval scores and DP comparisons use integer fixed-point units
of `1e-12`; floating-point values are retained only at the public artifact and
runtime boundary.

```python
from certigap import (
    HybridConstraints,
    WorkloadTrace,
    compile_hybrid_index,
    verify_hybrid_certificate,
)

trace = WorkloadTrace(256)
for _ in range(900):
    trace.add_range(1, 80)
for key in range(1, 101):
    trace.add_update(key, float(key))

index = compile_hybrid_index(
    range(256),
    trace,
    constraints=HybridConstraints(
        max_blocks=16,
        max_block_width=64,
    ),
)
print(index.selected_boundaries)
print(verify_hybrid_certificate(index.export_certificate()))
```

`render_cpp_header()` emits a C++17 `certigap::PrefixBlockIndex`
configuration.

## Verified Evidence

The deterministic exact matrix contains `24` workloads across four sizes and
six operation families:

- `24/24` independently replayed complete frontiers;
- `24/24` runtime oracle passes;
- `10/24` selected nonuniform designs;
- `6.73%` mean certified score gain over the best uniform-prefix partition;
- `33.43%` maximum certified gain.

The native Apple M4 holdout matrix has `11` scenarios and `110` method rows.
Partitions and AutoIndex backend choices use only `800` train operations;
`6000` independently seeded operations are used for post-build timing.

In the committed run:

- CertiGap-H beats Fenwick in `9/11` scenarios;
- it beats uniform-prefix in `10/11`;
- global prefix is generally best for read-heavy stationary workloads;
- Fenwick wins the `30%` and `50%` update scenarios;
- the nonuniform CertiGap-H layout is the fastest specialized backend on the
  left-hot scenario;
- the declared temporal shift exposes the need for online re-selection.

The train-only three-backend selector has `1.02%` mean and `6.42%` maximum
holdout regret on the ten stationary scenarios. The explicit temporal shift
raises regret to `219.69%`; this is the documented trigger for drift detection
and re-selection, not evidence of a portable guarantee.

## Claim Boundary

The certificate proves optimality only for the declared additive structural
model and partition grammar. It does not prove nanosecond latency. The native
results are single-machine evidence, not a portable speed guarantee.

The current implementation supports sum, point updates, and rank-addressed
in-memory arrays. It does not yet provide inserts/deletes, concurrency,
durability, disk pages, lazy range updates, or an independent external
reproduction.

# CertiGap-H exact validation

- Independently replayed frontiers: `24/24`.
- Runtime oracle passes: `24/24`.
- Nonuniform selected designs: `10/24`.
- Mean certified gain over best uniform-prefix partition: `6.73%`.
- Maximum certified gain: `33.43%`.
- Minimum certified gain: `-0.00%`.

Scores use deterministic unit primitive costs. Native latency is evaluated separately on train/holdout traces.

# CertiGap-H native holdout benchmark

| Scenario | Auto selected | Auto ns/op | Holdout oracle | Auto regret | Hybrid vs Fenwick |
|---|---:|---:|---:|---:|---:|
| left_hot | certigap_hybrid | 3.882 | certigap_hybrid | +0.0% | +35.1% |
| two_hot | global_prefix | 3.354 | certigap_hybrid | +2.8% | +67.9% |
| uniform | global_prefix | 3.347 | global_prefix | +0.0% | +40.8% |
| adversarial_edges | global_prefix | 3.028 | global_prefix | +0.0% | +87.5% |
| temporal_shift | fenwick | 7.326 | global_prefix | +219.7% | +111.0% |
| read_only_skew | global_prefix | 1.458 | global_prefix | +0.0% | +73.0% |
| update_30_uniform | fenwick | 6.194 | fenwick | +0.0% | -1.2% |
| update_50_uniform | fenwick | 5.778 | fenwick | +0.0% | -24.8% |
| movielens_100k_frequency_derived | certigap_hybrid | 4.257 | global_prefix | +6.4% | +49.4% |
| uci_online_retail_frequency_derived | global_prefix | 3.500 | certigap_hybrid | +1.0% | +63.7% |
| wikimedia_pageviews_frequency_derived | certigap_hybrid | 4.035 | certigap_hybrid | +0.0% | +36.8% |

- CertiGap-H beats Fenwick in `9/11` holdout scenarios.
- CertiGap-H beats uniform-prefix in `10/11` holdout scenarios.
- CertiGap-H is the fastest tested implementation in `4/11` scenarios.
- Train-only AutoIndex matches the three-candidate holdout oracle in `7/11` scenarios.
- Mean AutoIndex holdout regret is `20.90%`; maximum is `219.69%`.
- Excluding the declared `temporal_shift` stress case, mean AutoIndex regret is `1.02%` and maximum is `6.42%`.
- Timings are post-build medians of nine complete trace executions; p95 is the nearest-rank batch statistic and MAD reports robust spread. Each method receives a separate untimed warm-up trace.
- Public datasets provide observed key-frequency distributions, not native range-query traces. Their range/get/update operations are deterministically generated and labelled `frequency_derived`.
- These measurements describe this machine and compiler only. They are not a portable speed guarantee.

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
