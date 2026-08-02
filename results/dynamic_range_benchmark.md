# Dynamic CertiRange mixed-workload benchmark

- Rows: `36`
- Operations: point get, range sum, and point update on identical deterministic traces.
- Latency: median and p95 across whole-batch per-operation means; Python microbenchmark, not production C++ latency.
- Build time: one untimed-for-operations construction; values are reset outside every measured repeat.
- Memory: `estimated_numeric_slots` is an analytical storage proxy, not measured RSS.
- Range endpoint frequencies are a routing heuristic and do not imply globally optimal range-query shape.

| n | workload | fastest method | CertiRange rank | CertiRange ns/op | fastest ns/op |
|---:|---|---|---:|---:|---:|
| 128 | clustered_range | array | 4/4 | 1563.1 | 139.8 |
| 128 | hotspot_point | array | 4/4 | 920.8 | 66.9 |
| 128 | uniform_mixed | array | 4/4 | 1588.7 | 107.8 |
| 512 | clustered_range | array | 4/4 | 2236.7 | 251.7 |
| 512 | hotspot_point | array | 4/4 | 1191.3 | 81.7 |
| 512 | uniform_mixed | array | 4/4 | 2185.7 | 159.2 |
| 2048 | clustered_range | fenwick | 4/4 | 3206.2 | 523.2 |
| 2048 | hotspot_point | array | 4/4 | 1741.5 | 119.1 |
| 2048 | uniform_mixed | array | 4/4 | 2660.9 | 357.1 |

## Interpretation

Fenwick and iterative segment trees are expected to win raw Python range-sum throughput. CertiRange's measured claim is different: it combines workload-shaped point paths, generic range aggregates, persistent snapshots, drift-aware rebuilding, and a replayable certificate.

A production speed claim requires the same benchmark in the C++ core on independent hardware.
