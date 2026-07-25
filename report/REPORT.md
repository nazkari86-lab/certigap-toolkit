# CertiGap Report

## Topic

**CertiGap: budgeted robust partial search trees with certified near-optimality**

## One-Sentence Contribution

We optimize **how much order to materialize** under a strict split budget, under **unreliable query predictions**, and return a solution together with a **verifiable certificate of its quality**.

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

## Experimental Design

# Experiment Plan

## Goal

Show that CertiGap is:

1. correct on small instances;
2. competitive on medium instances;
3. meaningfully better than simple baselines on skewed workloads;
4. honest about uncertainty through certified gaps.

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
- report certified gaps

### Large Prototype Regime

- `n = 64..512`
- run greedy and simple baselines only
- report heuristic behavior, not exact optimality claims

## Metrics

- objective value
- average cost
- worst-case cost
- lower bound
- certified gap
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
- certified gaps stay reasonably small on medium cases.

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
CertiGap decides **how much of the order is worth materializing at all**, under a strict budget and unreliable predictions, and proves how close its answer is to optimal.
