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
