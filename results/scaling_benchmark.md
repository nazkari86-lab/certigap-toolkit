# CertiGap Scaling Benchmark

Mode: `quick`. Exact solvers are intentionally excluded: this benchmark measures heuristic scaling, not exact quality.

| n | Solver | Width | Median ms | p95 ms | Peak MB |
|---:|---|---:|---:|---:|---:|
| 32 | greedy | 0 | 2.482 | 2.846 | 0.098 |
| 32 | beam | 1 | 10.978 | 11.867 | 0.249 |
| 32 | beam | 4 | 37.860 | 37.880 | 0.395 |
| 64 | greedy | 0 | 7.459 | 7.743 | 0.251 |
| 64 | beam | 1 | 28.680 | 30.872 | 0.345 |
| 64 | beam | 4 | 107.812 | 109.520 | 0.603 |
| 128 | greedy | 0 | 32.701 | 33.660 | 0.477 |
| 128 | beam | 1 | 78.288 | 80.745 | 0.694 |
| 128 | beam | 4 | 278.313 | 282.316 | 1.323 |
