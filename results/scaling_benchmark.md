# CertiGap Scaling Benchmark

Mode: `max`; datasets: `all`. This measures heuristic and baseline scaling, not exact-optimality quality.

## Coverage

- Workloads completed: `10`
- Rows: `450`
- Sizes: `32, 64, 128, 256, 512`
- Solvers: greedy, beam widths up to `32`, and balanced, weighted, binary_search, learned_segment
- `max` is the largest complete range for this threshold-enumerating Python reference implementation. Exploratory runs above `n=512` were deliberately not published because they did not complete within the benchmark budget.
- Raw-source provenance and SHA-256: [`benchmark_provenance.json`](benchmark_provenance.json)

## Zipf / First Real Workload Snapshot

| Workload | n | Solver | Width | Repeats | Median ms | p95 ms | Peak MB | Objective |
|---|---:|---|---:|---:|---:|---:|---:|
| zipf | 32 | greedy | 0 | 5 | 2.042 | 2.392 | 0.099 | 4.69102 |
| zipf | 32 | beam | 1 | 5 | 8.511 | 8.705 | 0.252 | 4.55812 |
| zipf | 32 | beam | 4 | 5 | 34.609 | 37.565 | 0.347 | 4.55812 |
| zipf | 32 | beam | 16 | 5 | 136.635 | 140.350 | 0.670 | 4.47086 |
| zipf | 32 | beam | 32 | 5 | 308.011 | 354.814 | 1.672 | 4.47086 |
| zipf | 32 | balanced | 0 | 5 | 0.062 | 0.093 | 0.004 | 5.00000 |
| zipf | 32 | weighted | 0 | 5 | 0.125 | 0.128 | 0.005 | 4.84711 |
| zipf | 32 | binary_search | 0 | 5 | 0.166 | 0.176 | 0.009 | 5.00000 |
| zipf | 32 | learned_segment | 0 | 5 | 0.066 | 0.077 | 0.004 | 5.41415 |
| zipf | 64 | greedy | 0 | 5 | 5.216 | 5.723 | 0.251 | 5.50685 |
| zipf | 64 | beam | 1 | 5 | 22.729 | 23.560 | 0.345 | 5.50685 |
| zipf | 64 | beam | 4 | 5 | 84.541 | 84.832 | 0.481 | 5.26521 |
| zipf | 64 | beam | 16 | 5 | 380.048 | 637.371 | 1.930 | 5.29303 |
| zipf | 64 | beam | 32 | 5 | 824.261 | 841.592 | 3.824 | 5.26521 |
| zipf | 64 | balanced | 0 | 5 | 0.075 | 0.135 | 0.005 | 6.00000 |
| zipf | 64 | weighted | 0 | 5 | 0.189 | 0.213 | 0.007 | 5.68844 |
| zipf | 64 | binary_search | 0 | 5 | 0.365 | 0.454 | 0.029 | 6.00000 |
| zipf | 64 | learned_segment | 0 | 5 | 0.092 | 0.107 | 0.005 | 6.96982 |
| zipf | 128 | greedy | 0 | 5 | 25.045 | 25.994 | 0.481 | 6.25506 |
| zipf | 128 | beam | 1 | 5 | 61.387 | 62.857 | 0.694 | 6.17683 |
| zipf | 128 | beam | 4 | 5 | 227.836 | 255.132 | 1.274 | 6.13297 |
| zipf | 128 | beam | 16 | 5 | 1014.801 | 1075.684 | 4.490 | 6.12997 |
| zipf | 128 | beam | 32 | 5 | 2085.902 | 2134.030 | 8.230 | 6.10491 |
| zipf | 128 | balanced | 0 | 5 | 0.136 | 0.167 | 0.007 | 7.00000 |
| zipf | 128 | weighted | 0 | 5 | 0.363 | 0.383 | 0.012 | 6.31671 |
| zipf | 128 | binary_search | 0 | 5 | 0.936 | 0.952 | 0.075 | 7.00000 |
| zipf | 128 | learned_segment | 0 | 5 | 0.141 | 0.152 | 0.008 | 7.97497 |
| zipf | 256 | greedy | 0 | 5 | 108.894 | 116.764 | 1.348 | 7.04774 |
| zipf | 256 | beam | 1 | 5 | 168.629 | 178.604 | 1.904 | 6.97835 |
| zipf | 256 | beam | 4 | 5 | 644.779 | 679.356 | 3.423 | 6.88974 |
| zipf | 256 | beam | 16 | 5 | 2658.421 | 2779.261 | 9.455 | 6.88974 |
| zipf | 256 | beam | 32 | 5 | 8628.976 | 9706.072 | 17.542 | 6.87514 |
| zipf | 256 | balanced | 0 | 5 | 0.322 | 0.385 | 0.014 | 8.00000 |
| zipf | 256 | weighted | 0 | 5 | 0.949 | 1.206 | 0.023 | 7.27501 |
| zipf | 256 | binary_search | 0 | 5 | 2.598 | 2.887 | 0.169 | 8.00000 |
| zipf | 256 | learned_segment | 0 | 5 | 0.298 | 0.680 | 0.015 | 8.97838 |
| zipf | 512 | greedy | 0 | 5 | 1723.664 | 2269.224 | 4.287 | 7.66898 |
| zipf | 512 | beam | 1 | 5 | 1099.101 | 1204.887 | 4.822 | 7.66898 |
| zipf | 512 | beam | 4 | 5 | 3128.585 | 3769.985 | 7.942 | 7.70063 |
| zipf | 512 | beam | 16 | 5 | 11084.761 | 13580.057 | 20.356 | 7.62327 |
| zipf | 512 | beam | 32 | 5 | 20923.975 | 22268.473 | 36.901 | 7.62435 |
| zipf | 512 | balanced | 0 | 5 | 0.365 | 0.482 | 0.028 | 9.00000 |
| zipf | 512 | weighted | 0 | 5 | 1.278 | 1.344 | 0.044 | 7.92749 |
| zipf | 512 | binary_search | 0 | 5 | 3.905 | 4.262 | 0.369 | 9.00000 |
| zipf | 512 | learned_segment | 0 | 5 | 0.374 | 0.402 | 0.028 | 9.98055 |
| movielens_100k | 32 | greedy | 0 | 5 | 1.166 | 2.620 | 0.050 | 5.00000 |
| movielens_100k | 32 | beam | 1 | 5 | 10.246 | 13.824 | 0.252 | 5.00000 |
| movielens_100k | 32 | beam | 4 | 5 | 32.964 | 40.162 | 0.348 | 4.76379 |
| movielens_100k | 32 | beam | 16 | 5 | 133.439 | 146.132 | 0.760 | 4.76379 |
| movielens_100k | 32 | beam | 32 | 5 | 285.096 | 298.570 | 1.444 | 4.76379 |
| movielens_100k | 32 | balanced | 0 | 5 | 0.061 | 0.089 | 0.004 | 5.00000 |
| movielens_100k | 32 | weighted | 0 | 5 | 0.138 | 0.140 | 0.005 | 5.01585 |
| movielens_100k | 32 | binary_search | 0 | 5 | 0.166 | 0.174 | 0.009 | 5.00000 |
| movielens_100k | 32 | learned_segment | 0 | 5 | 0.065 | 0.077 | 0.004 | 5.53380 |
| movielens_100k | 64 | greedy | 0 | 5 | 2.409 | 2.848 | 0.136 | 6.00000 |
| movielens_100k | 64 | beam | 1 | 5 | 22.851 | 22.974 | 0.345 | 6.00000 |
| movielens_100k | 64 | beam | 4 | 5 | 84.576 | 98.681 | 0.684 | 5.76379 |
| movielens_100k | 64 | beam | 16 | 5 | 381.296 | 557.465 | 1.930 | 5.76379 |
| movielens_100k | 64 | beam | 32 | 5 | 877.335 | 951.992 | 3.809 | 5.75740 |
| movielens_100k | 64 | balanced | 0 | 5 | 0.110 | 0.144 | 0.005 | 6.00000 |
| movielens_100k | 64 | weighted | 0 | 5 | 0.307 | 0.375 | 0.007 | 6.19668 |
| movielens_100k | 64 | binary_search | 0 | 5 | 0.638 | 0.813 | 0.029 | 6.00000 |
| movielens_100k | 64 | learned_segment | 0 | 5 | 0.109 | 0.128 | 0.005 | 6.99281 |
| movielens_100k | 128 | greedy | 0 | 5 | 12.751 | 13.658 | 0.350 | 7.00000 |
| movielens_100k | 128 | beam | 1 | 5 | 78.244 | 96.064 | 0.819 | 7.00000 |
| movielens_100k | 128 | beam | 4 | 5 | 311.060 | 382.945 | 1.411 | 6.76379 |
| movielens_100k | 128 | beam | 16 | 5 | 1374.011 | 1427.705 | 4.308 | 6.76379 |
| movielens_100k | 128 | beam | 32 | 5 | 2587.878 | 3526.574 | 8.219 | 6.75740 |
| movielens_100k | 128 | balanced | 0 | 5 | 0.117 | 0.171 | 0.007 | 7.00000 |
| movielens_100k | 128 | weighted | 0 | 5 | 0.360 | 0.454 | 0.012 | 7.21087 |
| movielens_100k | 128 | binary_search | 0 | 5 | 0.807 | 1.010 | 0.075 | 7.00000 |
| movielens_100k | 128 | learned_segment | 0 | 5 | 0.137 | 0.235 | 0.007 | 7.99344 |
| movielens_100k | 256 | greedy | 0 | 5 | 41.619 | 50.531 | 0.916 | 8.00000 |
| movielens_100k | 256 | beam | 1 | 5 | 208.585 | 232.424 | 1.894 | 8.00000 |
| movielens_100k | 256 | beam | 4 | 5 | 872.444 | 1109.331 | 3.272 | 7.76379 |
| movielens_100k | 256 | beam | 16 | 5 | 3165.896 | 4102.438 | 9.436 | 7.76379 |
| movielens_100k | 256 | beam | 32 | 5 | 5918.326 | 6585.688 | 17.462 | 7.75740 |
| movielens_100k | 256 | balanced | 0 | 5 | 0.234 | 0.250 | 0.014 | 8.00000 |
| movielens_100k | 256 | weighted | 0 | 5 | 0.677 | 0.791 | 0.023 | 8.19140 |
| movielens_100k | 256 | binary_search | 0 | 5 | 1.705 | 1.771 | 0.169 | 8.00000 |
| movielens_100k | 256 | learned_segment | 0 | 5 | 0.210 | 0.221 | 0.015 | 8.99379 |
| movielens_100k | 512 | greedy | 0 | 5 | 89.479 | 93.078 | 2.796 | 9.00000 |
| movielens_100k | 512 | beam | 1 | 5 | 617.315 | 663.715 | 4.824 | 9.00000 |
| movielens_100k | 512 | beam | 4 | 5 | 2455.976 | 2676.222 | 7.939 | 8.76379 |
| movielens_100k | 512 | beam | 16 | 5 | 9850.849 | 11053.181 | 20.369 | 8.76379 |
| movielens_100k | 512 | beam | 32 | 5 | 20377.247 | 20865.542 | 36.957 | 8.75740 |
| movielens_100k | 512 | balanced | 0 | 5 | 0.371 | 0.422 | 0.028 | 9.00000 |
| movielens_100k | 512 | weighted | 0 | 5 | 1.330 | 1.368 | 0.044 | 9.19813 |
| movielens_100k | 512 | binary_search | 0 | 5 | 4.195 | 4.273 | 0.369 | 9.00000 |
| movielens_100k | 512 | learned_segment | 0 | 5 | 0.378 | 0.417 | 0.028 | 9.99379 |
