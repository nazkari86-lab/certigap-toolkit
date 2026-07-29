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
| zipf | 32 | greedy | 0 | 5 | 1.381 | 1.517 | 0.100 | 4.69102 |
| zipf | 32 | beam | 1 | 5 | 5.553 | 5.595 | 0.254 | 4.55812 |
| zipf | 32 | beam | 4 | 5 | 20.790 | 20.928 | 0.348 | 4.55812 |
| zipf | 32 | beam | 16 | 5 | 85.007 | 85.358 | 0.670 | 4.47086 |
| zipf | 32 | beam | 32 | 5 | 180.700 | 195.956 | 1.673 | 4.47086 |
| zipf | 32 | balanced | 0 | 5 | 0.043 | 0.059 | 0.004 | 5.00000 |
| zipf | 32 | weighted | 0 | 5 | 0.080 | 0.091 | 0.005 | 4.84711 |
| zipf | 32 | binary_search | 0 | 5 | 0.101 | 0.109 | 0.009 | 5.00000 |
| zipf | 32 | learned_segment | 0 | 5 | 0.044 | 0.046 | 0.004 | 5.41415 |
| zipf | 64 | greedy | 0 | 5 | 4.715 | 4.887 | 0.254 | 5.50685 |
| zipf | 64 | beam | 1 | 5 | 17.074 | 17.131 | 0.347 | 5.50685 |
| zipf | 64 | beam | 4 | 5 | 60.554 | 60.639 | 0.483 | 5.26521 |
| zipf | 64 | beam | 16 | 5 | 257.648 | 259.760 | 1.930 | 5.29303 |
| zipf | 64 | beam | 32 | 5 | 540.379 | 556.593 | 3.825 | 5.26521 |
| zipf | 64 | balanced | 0 | 5 | 0.082 | 0.098 | 0.007 | 6.00000 |
| zipf | 64 | weighted | 0 | 5 | 0.135 | 0.146 | 0.009 | 5.68844 |
| zipf | 64 | binary_search | 0 | 5 | 0.240 | 0.245 | 0.031 | 6.00000 |
| zipf | 64 | learned_segment | 0 | 5 | 0.084 | 0.090 | 0.007 | 6.96982 |
| zipf | 128 | greedy | 0 | 5 | 24.961 | 25.538 | 0.486 | 6.25506 |
| zipf | 128 | beam | 1 | 5 | 54.555 | 54.733 | 0.695 | 6.17683 |
| zipf | 128 | beam | 4 | 5 | 196.816 | 204.158 | 1.275 | 6.13297 |
| zipf | 128 | beam | 16 | 5 | 817.988 | 840.289 | 4.490 | 6.12997 |
| zipf | 128 | beam | 32 | 5 | 1660.826 | 1661.810 | 8.230 | 6.10491 |
| zipf | 128 | balanced | 0 | 5 | 0.165 | 0.193 | 0.014 | 7.00000 |
| zipf | 128 | weighted | 0 | 5 | 0.270 | 0.290 | 0.018 | 6.31671 |
| zipf | 128 | binary_search | 0 | 5 | 0.548 | 0.559 | 0.082 | 7.00000 |
| zipf | 128 | learned_segment | 0 | 5 | 0.174 | 0.180 | 0.014 | 7.97497 |
| zipf | 256 | greedy | 0 | 5 | 135.430 | 137.637 | 1.358 | 7.04774 |
| zipf | 256 | beam | 1 | 5 | 209.662 | 213.432 | 1.908 | 6.97835 |
| zipf | 256 | beam | 4 | 5 | 739.843 | 757.051 | 3.426 | 6.88974 |
| zipf | 256 | beam | 16 | 5 | 2962.618 | 3106.843 | 9.459 | 6.88974 |
| zipf | 256 | beam | 32 | 5 | 5967.744 | 5969.622 | 17.546 | 6.87514 |
| zipf | 256 | balanced | 0 | 5 | 0.371 | 0.398 | 0.028 | 8.00000 |
| zipf | 256 | weighted | 0 | 5 | 0.600 | 0.621 | 0.037 | 7.27501 |
| zipf | 256 | binary_search | 0 | 5 | 1.174 | 1.203 | 0.183 | 8.00000 |
| zipf | 256 | learned_segment | 0 | 5 | 0.370 | 0.372 | 0.029 | 8.97838 |
| zipf | 512 | greedy | 0 | 5 | 849.752 | 866.026 | 4.308 | 7.66898 |
| zipf | 512 | beam | 1 | 5 | 825.122 | 861.892 | 4.832 | 7.66898 |
| zipf | 512 | beam | 4 | 5 | 3028.502 | 3131.337 | 7.951 | 7.70063 |
| zipf | 512 | beam | 16 | 5 | 11982.473 | 12228.859 | 20.366 | 7.62327 |
| zipf | 512 | beam | 32 | 5 | 24104.962 | 24544.702 | 36.911 | 7.62435 |
| zipf | 512 | balanced | 0 | 5 | 0.762 | 0.857 | 0.054 | 9.00000 |
| zipf | 512 | weighted | 0 | 5 | 1.280 | 1.285 | 0.070 | 7.92749 |
| zipf | 512 | binary_search | 0 | 5 | 2.673 | 2.796 | 0.394 | 9.00000 |
| zipf | 512 | learned_segment | 0 | 5 | 0.763 | 0.775 | 0.054 | 9.98055 |
| movielens_100k | 32 | greedy | 0 | 5 | 0.655 | 0.685 | 0.052 | 5.00000 |
| movielens_100k | 32 | beam | 1 | 5 | 5.679 | 5.948 | 0.253 | 5.00000 |
| movielens_100k | 32 | beam | 4 | 5 | 20.977 | 21.468 | 0.349 | 4.76379 |
| movielens_100k | 32 | beam | 16 | 5 | 85.661 | 94.140 | 0.761 | 4.76379 |
| movielens_100k | 32 | beam | 32 | 5 | 182.572 | 189.474 | 1.445 | 4.76379 |
| movielens_100k | 32 | balanced | 0 | 5 | 0.043 | 0.056 | 0.004 | 5.00000 |
| movielens_100k | 32 | weighted | 0 | 5 | 0.085 | 0.095 | 0.005 | 5.01585 |
| movielens_100k | 32 | binary_search | 0 | 5 | 0.093 | 0.096 | 0.009 | 5.00000 |
| movielens_100k | 32 | learned_segment | 0 | 5 | 0.044 | 0.051 | 0.004 | 5.53380 |
| movielens_100k | 64 | greedy | 0 | 5 | 2.291 | 2.422 | 0.139 | 6.00000 |
| movielens_100k | 64 | beam | 1 | 5 | 17.085 | 17.301 | 0.347 | 6.00000 |
| movielens_100k | 64 | beam | 4 | 5 | 61.618 | 70.106 | 0.685 | 5.76379 |
| movielens_100k | 64 | beam | 16 | 5 | 255.155 | 275.627 | 1.931 | 5.76379 |
| movielens_100k | 64 | beam | 32 | 5 | 528.492 | 548.749 | 3.810 | 5.75740 |
| movielens_100k | 64 | balanced | 0 | 5 | 0.082 | 0.097 | 0.007 | 6.00000 |
| movielens_100k | 64 | weighted | 0 | 5 | 0.150 | 0.158 | 0.009 | 6.19668 |
| movielens_100k | 64 | binary_search | 0 | 5 | 0.243 | 0.247 | 0.031 | 6.00000 |
| movielens_100k | 64 | learned_segment | 0 | 5 | 0.088 | 0.090 | 0.007 | 6.99281 |
| movielens_100k | 128 | greedy | 0 | 5 | 8.013 | 8.135 | 0.355 | 7.00000 |
| movielens_100k | 128 | beam | 1 | 5 | 54.957 | 58.679 | 0.820 | 7.00000 |
| movielens_100k | 128 | beam | 4 | 5 | 194.803 | 209.096 | 1.412 | 6.76379 |
| movielens_100k | 128 | beam | 16 | 5 | 813.177 | 817.925 | 4.308 | 6.76379 |
| movielens_100k | 128 | beam | 32 | 5 | 1663.406 | 1684.543 | 8.219 | 6.75740 |
| movielens_100k | 128 | balanced | 0 | 5 | 0.164 | 0.183 | 0.014 | 7.00000 |
| movielens_100k | 128 | weighted | 0 | 5 | 0.296 | 0.304 | 0.018 | 7.21087 |
| movielens_100k | 128 | binary_search | 0 | 5 | 0.538 | 0.555 | 0.082 | 7.00000 |
| movielens_100k | 128 | learned_segment | 0 | 5 | 0.165 | 0.169 | 0.014 | 7.99344 |
| movielens_100k | 256 | greedy | 0 | 5 | 31.705 | 32.121 | 0.930 | 8.00000 |
| movielens_100k | 256 | beam | 1 | 5 | 204.195 | 217.209 | 1.898 | 8.00000 |
| movielens_100k | 256 | beam | 4 | 5 | 742.207 | 754.071 | 3.276 | 7.76379 |
| movielens_100k | 256 | beam | 16 | 5 | 3050.128 | 3175.657 | 9.440 | 7.76379 |
| movielens_100k | 256 | beam | 32 | 5 | 6258.930 | 6451.507 | 17.466 | 7.75740 |
| movielens_100k | 256 | balanced | 0 | 5 | 0.371 | 0.411 | 0.028 | 8.00000 |
| movielens_100k | 256 | weighted | 0 | 5 | 0.642 | 0.712 | 0.037 | 8.19140 |
| movielens_100k | 256 | binary_search | 0 | 5 | 1.185 | 1.204 | 0.183 | 8.00000 |
| movielens_100k | 256 | learned_segment | 0 | 5 | 0.376 | 0.381 | 0.029 | 8.99379 |
| movielens_100k | 512 | greedy | 0 | 5 | 133.900 | 141.399 | 2.822 | 9.00000 |
| movielens_100k | 512 | beam | 1 | 5 | 871.542 | 890.248 | 4.833 | 9.00000 |
| movielens_100k | 512 | beam | 4 | 5 | 3075.919 | 3141.949 | 7.948 | 8.76379 |
| movielens_100k | 512 | beam | 16 | 5 | 12236.976 | 13675.137 | 20.378 | 8.76379 |
| movielens_100k | 512 | beam | 32 | 5 | 24055.840 | 24391.350 | 36.967 | 8.75740 |
| movielens_100k | 512 | balanced | 0 | 5 | 0.760 | 0.811 | 0.054 | 9.00000 |
| movielens_100k | 512 | weighted | 0 | 5 | 1.251 | 1.260 | 0.070 | 9.19813 |
| movielens_100k | 512 | binary_search | 0 | 5 | 2.653 | 2.742 | 0.394 | 9.00000 |
| movielens_100k | 512 | learned_segment | 0 | 5 | 0.734 | 0.741 | 0.054 | 9.99379 |
