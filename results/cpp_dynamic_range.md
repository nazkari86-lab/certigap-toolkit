# C++ Dynamic CertiRange benchmark

- Rows: `36`
- Same deterministic mixed get/range-sum/update trace for every method.
- Latency is post-build median and p95 across whole-batch per-operation means.
- CertiRange uses contiguous nodes and a workload-shaped routing prefix.
- This local microbenchmark is not independent-hardware evidence.

| n | workload | fastest | CertiRange rank | CertiRange ns/op | fastest ns/op | hot depth vs balanced |
|---:|---|---|---:|---:|---:|---:|
| 1024 | clustered_range | fenwick | 4/4 | 80.5 | 13.3 | 12 vs 10 |
| 1024 | hotspot_point | array | 4/4 | 28.4 | 4.6 | 7 vs 10 |
| 1024 | uniform_mixed | fenwick | 4/4 | 65.7 | 14.7 | 10 vs 10 |
| 16384 | clustered_range | fenwick | 3/4 | 145.4 | 15.1 | 16 vs 14 |
| 16384 | hotspot_point | segment_tree | 3/4 | 53.8 | 8.9 | 11 vs 14 |
| 16384 | uniform_mixed | fenwick | 3/4 | 147.9 | 17.6 | 14 vs 14 |
| 100000 | clustered_range | fenwick | 3/4 | 264.5 | 16.9 | 18 vs 17 |
| 100000 | hotspot_point | segment_tree | 3/4 | 91.2 | 11.7 | 14 vs 17 |
| 100000 | uniform_mixed | fenwick | 3/4 | 215.2 | 25.1 | 17 vs 17 |

## Honest result

Fenwick or an iterative segment tree wins raw range-sum throughput in this matrix. CertiRange reduces hot-key depth on skewed traces, but irregular routing and recursive range traversal currently outweigh that comparison saving. The result rejects a blanket speed claim and motivates portfolio selection rather than replacing classical structures.
