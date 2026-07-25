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
