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
| zipf | 32 | greedy | 0 | 5 | 1.431 | 1.637 | 0.100 | 4.69102 |
| zipf | 32 | beam | 1 | 5 | 5.829 | 5.969 | 0.254 | 4.55812 |
| zipf | 32 | beam | 4 | 5 | 21.526 | 21.935 | 0.348 | 4.55812 |
| zipf | 32 | beam | 16 | 5 | 87.520 | 87.862 | 0.672 | 4.47086 |
| zipf | 32 | beam | 32 | 5 | 186.121 | 197.472 | 1.588 | 4.47086 |
| zipf | 32 | balanced | 0 | 5 | 0.042 | 0.054 | 0.004 | 5.00000 |
| zipf | 32 | weighted | 0 | 5 | 0.079 | 0.086 | 0.005 | 4.84711 |
| zipf | 32 | binary_search | 0 | 5 | 0.097 | 0.098 | 0.009 | 5.00000 |
| zipf | 32 | learned_segment | 0 | 5 | 0.043 | 0.045 | 0.004 | 5.41415 |
| zipf | 64 | greedy | 0 | 5 | 4.710 | 4.979 | 0.254 | 5.50685 |
| zipf | 64 | beam | 1 | 5 | 17.268 | 17.429 | 0.347 | 5.50685 |
| zipf | 64 | beam | 4 | 5 | 61.756 | 61.812 | 0.483 | 5.26521 |
| zipf | 64 | beam | 16 | 5 | 260.165 | 268.082 | 1.890 | 5.29303 |
| zipf | 64 | beam | 32 | 5 | 547.038 | 570.498 | 3.749 | 5.26521 |
| zipf | 64 | balanced | 0 | 5 | 0.081 | 0.108 | 0.007 | 6.00000 |
| zipf | 64 | weighted | 0 | 5 | 0.134 | 0.143 | 0.009 | 5.68844 |
| zipf | 64 | binary_search | 0 | 5 | 0.238 | 0.245 | 0.031 | 6.00000 |
| zipf | 64 | learned_segment | 0 | 5 | 0.081 | 0.087 | 0.007 | 6.96982 |
| zipf | 128 | greedy | 0 | 5 | 24.672 | 25.220 | 0.484 | 6.25506 |
| zipf | 128 | beam | 1 | 5 | 54.090 | 54.347 | 0.695 | 6.17683 |
| zipf | 128 | beam | 4 | 5 | 196.494 | 203.912 | 1.434 | 6.13297 |
| zipf | 128 | beam | 16 | 5 | 814.900 | 850.635 | 4.365 | 6.12997 |
| zipf | 128 | beam | 32 | 5 | 1688.771 | 1695.139 | 8.369 | 6.10491 |
| zipf | 128 | balanced | 0 | 5 | 0.162 | 0.185 | 0.014 | 7.00000 |
| zipf | 128 | weighted | 0 | 5 | 0.270 | 0.278 | 0.018 | 6.31671 |
| zipf | 128 | binary_search | 0 | 5 | 0.546 | 0.561 | 0.082 | 7.00000 |
| zipf | 128 | learned_segment | 0 | 5 | 0.172 | 0.189 | 0.014 | 7.97497 |
| zipf | 256 | greedy | 0 | 5 | 133.858 | 139.051 | 1.366 | 7.04774 |
| zipf | 256 | beam | 1 | 5 | 204.958 | 208.750 | 1.890 | 6.97835 |
| zipf | 256 | beam | 4 | 5 | 755.584 | 770.848 | 3.418 | 6.88974 |
| zipf | 256 | beam | 16 | 5 | 3028.731 | 3066.911 | 9.470 | 6.88974 |
| zipf | 256 | beam | 32 | 5 | 6110.284 | 6140.106 | 17.529 | 6.87514 |
| zipf | 256 | balanced | 0 | 5 | 0.373 | 0.402 | 0.028 | 8.00000 |
| zipf | 256 | weighted | 0 | 5 | 0.626 | 0.651 | 0.037 | 7.27501 |
| zipf | 256 | binary_search | 0 | 5 | 1.197 | 1.243 | 0.183 | 8.00000 |
| zipf | 256 | learned_segment | 0 | 5 | 0.377 | 0.382 | 0.029 | 8.97838 |
| zipf | 512 | greedy | 0 | 5 | 871.193 | 885.586 | 4.301 | 7.66898 |
| zipf | 512 | beam | 1 | 5 | 843.006 | 886.421 | 4.842 | 7.66898 |
| zipf | 512 | beam | 4 | 5 | 3113.114 | 3128.726 | 7.957 | 7.70063 |
| zipf | 512 | beam | 16 | 5 | 12189.738 | 12208.355 | 20.369 | 7.62327 |
| zipf | 512 | beam | 32 | 5 | 24471.853 | 24632.854 | 36.899 | 7.62435 |
| zipf | 512 | balanced | 0 | 5 | 0.767 | 0.834 | 0.054 | 9.00000 |
| zipf | 512 | weighted | 0 | 5 | 1.283 | 1.314 | 0.070 | 7.92749 |
| zipf | 512 | binary_search | 0 | 5 | 2.668 | 2.770 | 0.394 | 9.00000 |
| zipf | 512 | learned_segment | 0 | 5 | 0.749 | 0.817 | 0.054 | 9.98055 |
| movielens_100k | 32 | greedy | 0 | 5 | 0.672 | 0.716 | 0.052 | 5.00000 |
| movielens_100k | 32 | beam | 1 | 5 | 5.879 | 6.862 | 0.253 | 5.00000 |
| movielens_100k | 32 | beam | 4 | 5 | 21.681 | 23.808 | 0.349 | 4.76379 |
| movielens_100k | 32 | beam | 16 | 5 | 89.125 | 96.101 | 0.761 | 4.76379 |
| movielens_100k | 32 | beam | 32 | 5 | 189.779 | 201.884 | 1.445 | 4.76379 |
| movielens_100k | 32 | balanced | 0 | 5 | 0.044 | 0.056 | 0.004 | 5.00000 |
| movielens_100k | 32 | weighted | 0 | 5 | 0.087 | 0.095 | 0.005 | 5.01585 |
| movielens_100k | 32 | binary_search | 0 | 5 | 0.098 | 0.098 | 0.009 | 5.00000 |
| movielens_100k | 32 | learned_segment | 0 | 5 | 0.043 | 0.050 | 0.004 | 5.53380 |
| movielens_100k | 64 | greedy | 0 | 5 | 2.282 | 2.505 | 0.139 | 6.00000 |
| movielens_100k | 64 | beam | 1 | 5 | 17.559 | 17.792 | 0.347 | 6.00000 |
| movielens_100k | 64 | beam | 4 | 5 | 62.401 | 71.100 | 0.685 | 5.76379 |
| movielens_100k | 64 | beam | 16 | 5 | 266.302 | 314.920 | 1.931 | 5.76379 |
| movielens_100k | 64 | beam | 32 | 5 | 557.948 | 592.022 | 3.810 | 5.75740 |
| movielens_100k | 64 | balanced | 0 | 5 | 0.082 | 0.097 | 0.007 | 6.00000 |
| movielens_100k | 64 | weighted | 0 | 5 | 0.148 | 0.161 | 0.009 | 6.19668 |
| movielens_100k | 64 | binary_search | 0 | 5 | 0.234 | 0.242 | 0.031 | 6.00000 |
| movielens_100k | 64 | learned_segment | 0 | 5 | 0.084 | 0.086 | 0.007 | 6.99281 |
| movielens_100k | 128 | greedy | 0 | 5 | 7.999 | 8.170 | 0.355 | 7.00000 |
| movielens_100k | 128 | beam | 1 | 5 | 55.326 | 59.338 | 0.820 | 7.00000 |
| movielens_100k | 128 | beam | 4 | 5 | 200.272 | 216.033 | 1.412 | 6.76379 |
| movielens_100k | 128 | beam | 16 | 5 | 843.926 | 861.850 | 4.308 | 6.76379 |
| movielens_100k | 128 | beam | 32 | 5 | 1758.530 | 1788.574 | 8.219 | 6.75740 |
| movielens_100k | 128 | balanced | 0 | 5 | 0.183 | 0.364 | 0.014 | 7.00000 |
| movielens_100k | 128 | weighted | 0 | 5 | 0.630 | 0.873 | 0.018 | 7.21087 |
| movielens_100k | 128 | binary_search | 0 | 5 | 1.358 | 1.724 | 0.082 | 7.00000 |
| movielens_100k | 128 | learned_segment | 0 | 5 | 0.191 | 0.496 | 0.014 | 7.99344 |
| movielens_100k | 256 | greedy | 0 | 5 | 32.749 | 33.680 | 0.930 | 8.00000 |
| movielens_100k | 256 | beam | 1 | 5 | 207.383 | 227.381 | 1.898 | 8.00000 |
| movielens_100k | 256 | beam | 4 | 5 | 748.741 | 770.358 | 3.276 | 7.76379 |
| movielens_100k | 256 | beam | 16 | 5 | 3115.356 | 3194.498 | 9.440 | 7.76379 |
| movielens_100k | 256 | beam | 32 | 5 | 6147.419 | 6274.031 | 17.466 | 7.75740 |
| movielens_100k | 256 | balanced | 0 | 5 | 0.372 | 0.403 | 0.028 | 8.00000 |
| movielens_100k | 256 | weighted | 0 | 5 | 0.607 | 0.642 | 0.037 | 8.19140 |
| movielens_100k | 256 | binary_search | 0 | 5 | 1.174 | 1.208 | 0.183 | 8.00000 |
| movielens_100k | 256 | learned_segment | 0 | 5 | 0.368 | 0.374 | 0.029 | 8.99379 |
| movielens_100k | 512 | greedy | 0 | 5 | 132.974 | 135.548 | 2.822 | 9.00000 |
| movielens_100k | 512 | beam | 1 | 5 | 842.072 | 874.456 | 4.833 | 9.00000 |
| movielens_100k | 512 | beam | 4 | 5 | 3096.494 | 3141.584 | 7.948 | 8.76379 |
| movielens_100k | 512 | beam | 16 | 5 | 12254.939 | 12959.137 | 20.378 | 8.76379 |
| movielens_100k | 512 | beam | 32 | 5 | 24740.594 | 25850.161 | 36.967 | 8.75740 |
| movielens_100k | 512 | balanced | 0 | 5 | 0.748 | 0.797 | 0.054 | 9.00000 |
| movielens_100k | 512 | weighted | 0 | 5 | 1.261 | 1.276 | 0.070 | 9.19813 |
| movielens_100k | 512 | binary_search | 0 | 5 | 2.669 | 2.763 | 0.394 | 9.00000 |
| movielens_100k | 512 | learned_segment | 0 | 5 | 0.758 | 0.777 | 0.054 | 9.99379 |
