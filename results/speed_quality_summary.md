# CertiGap Speed and Quality Summary

## Small Cases With Exact Reference

- Exact mean time: `2.526 ms`
- Beam mean time: `3.889 ms`
- Greedy mean time: `0.166 ms`
- Balanced mean time: `0.009 ms`
- Weighted mean time: `0.013 ms`
- Beam mean gap vs exact: `0.000979`
- Greedy mean gap vs exact: `0.114157`
- Balanced mean gap vs exact: `0.447373`
- Weighted mean gap vs exact: `0.198609`

## Large Cases Without Exact Reference

- Beam mean time: `39.587 ms`
- Greedy mean time: `0.927 ms`
- Balanced mean time: `0.014 ms`
- Weighted mean time: `0.028 ms`

## Solver Tradeoff

- `exact` is the reference solver for small and medium instances, but it is much slower.
- `beam` is the strongest practical heuristic: near-exact quality on small cases with much lower runtime than `exact`.
- `greedy` is usually faster but can be substantially worse on structured skewed tasks.
- `balanced` and `weighted` are cheap baselines, but quality is systematically weaker on skewed workloads.
