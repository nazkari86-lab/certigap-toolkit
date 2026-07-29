# Dynamic CertiRange mixed-workload benchmark

- Rows: `36`
- Operations: point get, range sum, and point update on identical deterministic traces.
- Latency: median and p95 across whole-batch per-operation means; Python microbenchmark, not production C++ latency.
- Build time: one untimed-for-operations construction; values are reset outside every measured repeat.
- Memory: `estimated_numeric_slots` is an analytical storage proxy, not measured RSS.
- Range endpoint frequencies are a routing heuristic and do not imply globally optimal range-query shape.

| n | workload | fastest method | CertiRange rank | CertiRange ns/op | fastest ns/op |
|---:|---|---|---:|---:|---:|
| 128 | clustered_range | array | 4/4 | 1568.5 | 140.3 |
| 128 | hotspot_point | array | 4/4 | 928.6 | 67.4 |
| 128 | uniform_mixed | array | 4/4 | 1581.8 | 110.5 |
| 512 | clustered_range | array | 4/4 | 2069.7 | 252.3 |
| 512 | hotspot_point | array | 4/4 | 1179.2 | 75.9 |
| 512 | uniform_mixed | array | 4/4 | 2174.6 | 161.4 |
| 2048 | clustered_range | fenwick | 4/4 | 2777.8 | 561.4 |
| 2048 | hotspot_point | array | 4/4 | 1871.1 | 123.7 |
| 2048 | uniform_mixed | array | 4/4 | 2628.4 | 335.0 |

## Interpretation

Fenwick and iterative segment trees are expected to win raw Python range-sum throughput. CertiRange's measured claim is different: it combines workload-shaped point paths, generic range aggregates, persistent snapshots, drift-aware rebuilding, and a replayable certificate.

A production speed claim requires the same benchmark in the C++ core on independent hardware.
