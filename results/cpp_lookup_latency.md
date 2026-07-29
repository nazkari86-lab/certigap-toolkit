# C++ Post-Build Lookup Microbenchmark

This measures only rank lookup after each structure is built. Times are local-machine measurements, not cross-machine or production claims.

- Queries are sampled from each workload distribution with a deterministic PRNG.
- `ycsb_hotspot_80_20` and `ycsb_latest_biased` are YCSB-inspired read-only distributions, not runs of the official YCSB harness.
- CertiGap uses the candidate-pruned C++ beam (`B=min(6,n-1)`, `eta=0.15`, width 32, candidate limit 16).
- CertiGap and budgeted trees use at most `B=min(6,n-1)` materialized splits and fixed-round interval fallback.
- `balanced_full_reference` and `std_lower_bound` are explicitly unconstrained references, not equal-budget competitors.
- Reported p95 is across repeated batch means; it is not single-query tail latency.
- Total index bytes include the shared integer key array; auxiliary bytes exclude allocator overhead.

| Workload | Solver | n | B | Median batch ns/query | p95 batch ns/query | Nodes | Auxiliary bytes | Total bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| uniform | certigap_pruned | 1000 | 6 | 16.436 | 16.866 | 1 | 48 | 4048 |
| uniform | balanced_budgeted | 1000 | 6 | 18.527 | 18.749 | 13 | 624 | 4624 |
| uniform | weighted_budgeted | 1000 | 6 | 18.456 | 18.836 | 13 | 624 | 4624 |
| uniform | balanced_full_reference | 1000 | 999 | 16.151 | 16.679 | 1999 | 95952 | 99952 |
| uniform | std_lower_bound | 1000 | 0 | 15.552 | 15.944 | 0 | 0 | 4000 |
| zipf | certigap_pruned | 1000 | 6 | 25.614 | 26.704 | 11 | 528 | 4528 |
| zipf | balanced_budgeted | 1000 | 6 | 15.678 | 16.225 | 13 | 624 | 4624 |
| zipf | weighted_budgeted | 1000 | 6 | 25.186 | 25.917 | 13 | 624 | 4624 |
| zipf | balanced_full_reference | 1000 | 999 | 15.374 | 16.073 | 1999 | 95952 | 99952 |
| zipf | std_lower_bound | 1000 | 0 | 15.088 | 15.755 | 0 | 0 | 4000 |
| hot_tail | certigap_pruned | 1000 | 6 | 21.831 | 22.519 | 13 | 624 | 4624 |
| hot_tail | balanced_budgeted | 1000 | 6 | 15.522 | 15.876 | 13 | 624 | 4624 |
| hot_tail | weighted_budgeted | 1000 | 6 | 24.192 | 25.346 | 13 | 624 | 4624 |
| hot_tail | balanced_full_reference | 1000 | 999 | 16.106 | 16.577 | 1999 | 95952 | 99952 |
| hot_tail | std_lower_bound | 1000 | 0 | 15.501 | 16.123 | 0 | 0 | 4000 |
| ycsb_hotspot_80_20 | certigap_pruned | 1000 | 6 | 24.692 | 25.643 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | balanced_budgeted | 1000 | 6 | 16.831 | 17.224 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | weighted_budgeted | 1000 | 6 | 16.219 | 16.466 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | balanced_full_reference | 1000 | 999 | 15.893 | 16.260 | 1999 | 95952 | 99952 |
| ycsb_hotspot_80_20 | std_lower_bound | 1000 | 0 | 15.374 | 15.742 | 0 | 0 | 4000 |
| ycsb_latest_biased | certigap_pruned | 1000 | 6 | 28.326 | 29.018 | 13 | 624 | 4624 |
| ycsb_latest_biased | balanced_budgeted | 1000 | 6 | 14.703 | 15.817 | 13 | 624 | 4624 |
| ycsb_latest_biased | weighted_budgeted | 1000 | 6 | 26.401 | 26.918 | 13 | 624 | 4624 |
| ycsb_latest_biased | balanced_full_reference | 1000 | 999 | 18.673 | 26.755 | 1999 | 95952 | 99952 |
| ycsb_latest_biased | std_lower_bound | 1000 | 0 | 19.996 | 29.051 | 0 | 0 | 4000 |
| uniform | certigap_pruned | 10000 | 6 | 29.483 | 42.514 | 5 | 240 | 40240 |
| uniform | balanced_budgeted | 10000 | 6 | 40.318 | 43.050 | 13 | 624 | 40624 |
| uniform | weighted_budgeted | 10000 | 6 | 27.806 | 29.757 | 13 | 624 | 40624 |
| uniform | balanced_full_reference | 10000 | 9999 | 56.518 | 64.310 | 19999 | 959952 | 999952 |
| uniform | std_lower_bound | 10000 | 0 | 40.845 | 46.249 | 0 | 0 | 40000 |
| zipf | certigap_pruned | 10000 | 6 | 29.593 | 34.589 | 13 | 624 | 40624 |
| zipf | balanced_budgeted | 10000 | 6 | 24.563 | 28.187 | 13 | 624 | 40624 |
| zipf | weighted_budgeted | 10000 | 6 | 29.327 | 34.547 | 13 | 624 | 40624 |
| zipf | balanced_full_reference | 10000 | 9999 | 56.032 | 64.146 | 19999 | 959952 | 999952 |
| zipf | std_lower_bound | 10000 | 0 | 44.236 | 46.169 | 0 | 0 | 40000 |
| hot_tail | certigap_pruned | 10000 | 6 | 22.789 | 23.756 | 13 | 624 | 40624 |
| hot_tail | balanced_budgeted | 10000 | 6 | 24.669 | 25.330 | 13 | 624 | 40624 |
| hot_tail | weighted_budgeted | 10000 | 6 | 27.071 | 27.659 | 13 | 624 | 40624 |
| hot_tail | balanced_full_reference | 10000 | 9999 | 48.577 | 50.151 | 19999 | 959952 | 999952 |
| hot_tail | std_lower_bound | 10000 | 0 | 38.813 | 39.600 | 0 | 0 | 40000 |
| ycsb_hotspot_80_20 | certigap_pruned | 10000 | 6 | 21.882 | 22.715 | 3 | 144 | 40144 |
| ycsb_hotspot_80_20 | balanced_budgeted | 10000 | 6 | 25.125 | 25.843 | 13 | 624 | 40624 |
| ycsb_hotspot_80_20 | weighted_budgeted | 10000 | 6 | 23.972 | 24.977 | 13 | 624 | 40624 |
| ycsb_hotspot_80_20 | balanced_full_reference | 10000 | 9999 | 50.989 | 52.120 | 19999 | 959952 | 999952 |
| ycsb_hotspot_80_20 | std_lower_bound | 10000 | 0 | 39.153 | 40.139 | 0 | 0 | 40000 |
| ycsb_latest_biased | certigap_pruned | 10000 | 6 | 30.556 | 31.370 | 7 | 336 | 40336 |
| ycsb_latest_biased | balanced_budgeted | 10000 | 6 | 23.978 | 24.734 | 13 | 624 | 40624 |
| ycsb_latest_biased | weighted_budgeted | 10000 | 6 | 32.435 | 33.242 | 13 | 624 | 40624 |
| ycsb_latest_biased | balanced_full_reference | 10000 | 9999 | 51.153 | 52.214 | 19999 | 959952 | 999952 |
| ycsb_latest_biased | std_lower_bound | 10000 | 0 | 38.882 | 39.963 | 0 | 0 | 40000 |

## Matched-Budget Interpretation

- CertiGap has lower median batch lookup time than `balanced_budgeted` in `4/10` measured workload-size cases.
- CertiGap has lower median batch lookup time than `weighted_budgeted` in `5/10` measured workload-size cases.

## Limits

This is not an official YCSB, RocksDB, hardware-routing, cache-miss, or external-library benchmark. It is reproducible CPU-level evidence that the exported CertiGap decision tree executes real lookups with an explicit storage footprint. Production claims require a target storage engine, key encoding, allocator, CPU, and independent external baselines.
