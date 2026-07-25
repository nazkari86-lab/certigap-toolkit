# CertiGap Speed and Quality Summary

## Small Cases With Exact Reference

- Exact mean time: `3.028 ms`
- Beam mean time: `5.181 ms`
- Greedy mean time: `0.242 ms`
- Balanced mean time: `0.014 ms`
- Weighted mean time: `0.019 ms`
- Beam mean absolute objective gap vs exact: `0.000979`
- Greedy mean absolute objective gap vs exact: `0.114157`
- Balanced mean absolute objective gap vs exact: `0.447373`
- Weighted mean absolute objective gap vs exact: `0.198609`
- Beam mean relative objective gap vs exact: `0.03%`
- Greedy mean relative objective gap vs exact: `3.48%`

## Large Cases Without Exact Reference

- Beam mean time: `53.550 ms`
- Greedy mean time: `1.452 ms`
- Balanced mean time: `0.024 ms`
- Weighted mean time: `0.040 ms`

## Solver Tradeoff

- `exact` is the reference solver for the measured small instances.
- `beam` is near-exact on the measured small cases, but is not faster than exact there; this benchmark does not establish a crossover point.
- `greedy` is usually faster but can be substantially worse on structured skewed tasks.
- `balanced` and `weighted` are cheap baselines, but quality is systematically weaker on skewed workloads.
