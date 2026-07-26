# C++ Post-Build Lookup Microbenchmark

This measures only rank lookup after each structure is built. Times are local-machine measurements, not cross-machine or production claims.

- Queries are sampled from each workload distribution with a deterministic PRNG.
- CertiGap uses the candidate-pruned C++ beam (`B=min(6,n-1)`, `eta=0.15`, width 32, candidate limit 16).
- CertiGap and budgeted trees use at most `B=min(6,n-1)` materialized splits and fixed-round interval fallback.
- `balanced_full_reference` and `std_lower_bound` are explicitly unconstrained references, not equal-budget competitors.
- Reported p95 is across repeated batch means; it is not single-query tail latency.
- Total index bytes include the shared integer key array; auxiliary bytes exclude allocator overhead.

| Workload | Solver | n | B | Median batch ns/query | p95 batch ns/query | Nodes | Auxiliary bytes | Total bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| uniform | certigap_pruned | 1000 | 6 | 16.574 | 16.909 | 1 | 48 | 4048 |
| uniform | balanced_budgeted | 1000 | 6 | 18.637 | 19.711 | 13 | 624 | 4624 |
| uniform | weighted_budgeted | 1000 | 6 | 18.592 | 19.480 | 13 | 624 | 4624 |
| uniform | balanced_full_reference | 1000 | 999 | 16.546 | 18.773 | 1999 | 95952 | 99952 |
| uniform | std_lower_bound | 1000 | 0 | 15.670 | 15.947 | 0 | 0 | 4000 |
| zipf | certigap_pruned | 1000 | 6 | 26.138 | 27.782 | 11 | 528 | 4528 |
| zipf | balanced_budgeted | 1000 | 6 | 15.908 | 16.136 | 13 | 624 | 4624 |
| zipf | weighted_budgeted | 1000 | 6 | 25.656 | 27.144 | 13 | 624 | 4624 |
| zipf | balanced_full_reference | 1000 | 999 | 15.514 | 15.666 | 1999 | 95952 | 99952 |
| zipf | std_lower_bound | 1000 | 0 | 15.312 | 17.053 | 0 | 0 | 4000 |
| hot_tail | certigap_pruned | 1000 | 6 | 22.645 | 31.178 | 13 | 624 | 4624 |
| hot_tail | balanced_budgeted | 1000 | 6 | 15.471 | 15.593 | 13 | 624 | 4624 |
| hot_tail | weighted_budgeted | 1000 | 6 | 24.494 | 24.996 | 13 | 624 | 4624 |
| hot_tail | balanced_full_reference | 1000 | 999 | 16.198 | 16.809 | 1999 | 95952 | 99952 |
| hot_tail | std_lower_bound | 1000 | 0 | 15.600 | 16.460 | 0 | 0 | 4000 |
| uniform | certigap_pruned | 10000 | 6 | 28.711 | 41.829 | 5 | 240 | 40240 |
| uniform | balanced_budgeted | 10000 | 6 | 27.275 | 29.340 | 13 | 624 | 40624 |
| uniform | weighted_budgeted | 10000 | 6 | 27.286 | 31.902 | 13 | 624 | 40624 |
| uniform | balanced_full_reference | 10000 | 9999 | 55.459 | 58.687 | 19999 | 959952 | 999952 |
| uniform | std_lower_bound | 10000 | 0 | 38.827 | 40.326 | 0 | 0 | 40000 |
| zipf | certigap_pruned | 10000 | 6 | 27.978 | 28.682 | 13 | 624 | 40624 |
| zipf | balanced_budgeted | 10000 | 6 | 23.843 | 24.185 | 13 | 624 | 40624 |
| zipf | weighted_budgeted | 10000 | 6 | 28.185 | 29.325 | 13 | 624 | 40624 |
| zipf | balanced_full_reference | 10000 | 9999 | 51.785 | 52.753 | 19999 | 959952 | 999952 |
| zipf | std_lower_bound | 10000 | 0 | 44.082 | 46.504 | 0 | 0 | 40000 |
| hot_tail | certigap_pruned | 10000 | 6 | 23.108 | 24.370 | 13 | 624 | 40624 |
| hot_tail | balanced_budgeted | 10000 | 6 | 25.067 | 27.748 | 13 | 624 | 40624 |
| hot_tail | weighted_budgeted | 10000 | 6 | 26.932 | 27.520 | 13 | 624 | 40624 |
| hot_tail | balanced_full_reference | 10000 | 9999 | 49.320 | 51.558 | 19999 | 959952 | 999952 |
| hot_tail | std_lower_bound | 10000 | 0 | 38.837 | 47.130 | 0 | 0 | 40000 |

## Matched-Budget Interpretation

- CertiGap has lower median batch lookup time than `balanced_budgeted` in `2/6` measured workload-size cases.
- CertiGap has lower median batch lookup time than `weighted_budgeted` in `4/6` measured workload-size cases.

## Limits

This is not a hardware-routing, cache-miss, or external-library benchmark. It is reproducible CPU-level evidence that the exported CertiGap decision tree executes real lookups with an explicit storage footprint. Production claims require a target key encoding, allocator, CPU, and independent external baselines.
