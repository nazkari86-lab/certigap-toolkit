# C++ Dynamic CertiRange benchmark

- Rows: `36`
- Same deterministic mixed get/range-sum/update trace for every method.
- Latency is post-build median and p95 across whole-batch per-operation means.
- CertiRange uses contiguous nodes and a workload-shaped routing prefix.
- This local microbenchmark is not independent-hardware evidence.

| n | workload | fastest | CertiRange rank | CertiRange ns/op | fastest ns/op | hot depth vs balanced |
|---:|---|---|---:|---:|---:|---:|
| 1024 | clustered_range | fenwick | 4/4 | 78.3 | 12.8 | 12 vs 10 |
| 1024 | hotspot_point | array | 4/4 | 27.4 | 4.5 | 7 vs 10 |
| 1024 | uniform_mixed | fenwick | 4/4 | 63.6 | 14.1 | 10 vs 10 |
| 16384 | clustered_range | fenwick | 3/4 | 141.3 | 15.5 | 16 vs 14 |
| 16384 | hotspot_point | segment_tree | 3/4 | 55.1 | 9.2 | 11 vs 14 |
| 16384 | uniform_mixed | fenwick | 3/4 | 143.9 | 17.0 | 14 vs 14 |
| 100000 | clustered_range | fenwick | 3/4 | 201.0 | 16.9 | 18 vs 17 |
| 100000 | hotspot_point | segment_tree | 3/4 | 65.4 | 11.8 | 14 vs 17 |
| 100000 | uniform_mixed | fenwick | 3/4 | 178.3 | 18.1 | 17 vs 17 |

## Honest result

Fenwick or an iterative segment tree wins raw range-sum throughput in this matrix. CertiRange reduces hot-key depth on skewed traces, but irregular routing and recursive range traversal currently outweigh that comparison saving. The result rejects a blanket speed claim and motivates portfolio selection rather than replacing classical structures.
