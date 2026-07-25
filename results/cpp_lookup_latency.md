# C++ Post-Build Lookup Microbenchmark

This measures only rank lookup after each structure is built. Times are local-machine measurements, not cross-machine or production claims.

- Queries are sampled from each workload distribution with a deterministic PRNG.
- CertiGap uses the candidate-pruned C++ beam (`B=min(6,n-1)`, `eta=0.15`, width 32, candidate limit 16).
- A CertiGap leaf completes its contiguous interval with binary search; balanced and weighted-median trees have singleton leaves.
- `routing_bytes` is reachable-node count times `sizeof(Node)`, excluding allocator and key-array overhead.

| Workload | Solver | n | Median ns/query | p95 ns/query | Routing nodes | Routing bytes |
|---|---|---:|---:|---:|---:|---:|
| uniform | certigap_pruned | 1000 | 12.598 | 12.838 | 1 | 48 |
| uniform | balanced_tree | 1000 | 16.142 | 16.415 | 1999 | 95952 |
| uniform | weighted_median | 1000 | 16.298 | 16.501 | 1999 | 95952 |
| uniform | std_lower_bound | 1000 | 16.229 | 17.193 | 0 | 0 |
| zipf | certigap_pruned | 1000 | 28.646 | 29.354 | 11 | 528 |
| zipf | balanced_tree | 1000 | 15.341 | 15.844 | 1999 | 95952 |
| zipf | weighted_median | 1000 | 40.386 | 41.216 | 1999 | 95952 |
| zipf | std_lower_bound | 1000 | 15.629 | 16.086 | 0 | 0 |
| hot_tail | certigap_pruned | 1000 | 19.833 | 20.583 | 13 | 624 |
| hot_tail | balanced_tree | 1000 | 16.392 | 17.040 | 1999 | 95952 |
| hot_tail | weighted_median | 1000 | 19.026 | 19.547 | 1999 | 95952 |
| hot_tail | std_lower_bound | 1000 | 16.301 | 16.807 | 0 | 0 |
| uniform | certigap_pruned | 10000 | 29.816 | 30.528 | 5 | 240 |
| uniform | balanced_tree | 10000 | 54.126 | 56.171 | 19999 | 959952 |
| uniform | weighted_median | 10000 | 54.536 | 56.540 | 19999 | 959952 |
| uniform | std_lower_bound | 10000 | 40.461 | 40.981 | 0 | 0 |
| zipf | certigap_pruned | 10000 | 30.522 | 31.627 | 13 | 624 |
| zipf | balanced_tree | 10000 | 51.938 | 53.620 | 19999 | 959952 |
| zipf | weighted_median | 10000 | 53.937 | 56.537 | 19999 | 959952 |
| zipf | std_lower_bound | 10000 | 45.088 | 45.585 | 0 | 0 |
| hot_tail | certigap_pruned | 10000 | 22.677 | 23.376 | 13 | 624 |
| hot_tail | balanced_tree | 10000 | 47.624 | 51.397 | 19999 | 959952 |
| hot_tail | weighted_median | 10000 | 58.955 | 62.113 | 19999 | 959952 |
| hot_tail | std_lower_bound | 10000 | 39.823 | 40.335 | 0 | 0 |

## Limits

This is not a hardware-routing, cache-miss, or external-library benchmark. It is reproducible CPU-level evidence that the exported CertiGap decision tree executes real lookups with an explicit storage footprint. Production claims require a target key encoding, allocator, CPU, and independent external baselines.
