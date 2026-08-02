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
| uniform | certigap_pruned | 1000 | 6 | 8.949 | 9.259 | 1 | 48 | 4048 |
| uniform | balanced_budgeted | 1000 | 6 | 10.097 | 10.427 | 13 | 624 | 4624 |
| uniform | weighted_budgeted | 1000 | 6 | 10.074 | 11.305 | 13 | 624 | 4624 |
| uniform | balanced_full_reference | 1000 | 999 | 8.934 | 9.365 | 1999 | 95952 | 99952 |
| uniform | std_lower_bound | 1000 | 0 | 8.541 | 8.830 | 0 | 0 | 4000 |
| zipf | certigap_pruned | 1000 | 6 | 13.905 | 14.909 | 11 | 528 | 4528 |
| zipf | balanced_budgeted | 1000 | 6 | 8.629 | 8.844 | 13 | 624 | 4624 |
| zipf | weighted_budgeted | 1000 | 6 | 13.653 | 14.171 | 13 | 624 | 4624 |
| zipf | balanced_full_reference | 1000 | 999 | 8.612 | 8.869 | 1999 | 95952 | 99952 |
| zipf | std_lower_bound | 1000 | 0 | 8.231 | 8.465 | 0 | 0 | 4000 |
| hot_tail | certigap_pruned | 1000 | 6 | 11.810 | 12.731 | 13 | 624 | 4624 |
| hot_tail | balanced_budgeted | 1000 | 6 | 8.290 | 9.006 | 13 | 624 | 4624 |
| hot_tail | weighted_budgeted | 1000 | 6 | 13.040 | 13.756 | 13 | 624 | 4624 |
| hot_tail | balanced_full_reference | 1000 | 999 | 8.686 | 9.255 | 1999 | 95952 | 99952 |
| hot_tail | std_lower_bound | 1000 | 0 | 8.444 | 8.849 | 0 | 0 | 4000 |
| ycsb_hotspot_80_20 | certigap_pruned | 1000 | 6 | 13.404 | 13.803 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | balanced_budgeted | 1000 | 6 | 9.188 | 9.479 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | weighted_budgeted | 1000 | 6 | 8.707 | 8.969 | 13 | 624 | 4624 |
| ycsb_hotspot_80_20 | balanced_full_reference | 1000 | 999 | 8.677 | 8.950 | 1999 | 95952 | 99952 |
| ycsb_hotspot_80_20 | std_lower_bound | 1000 | 0 | 8.429 | 8.880 | 0 | 0 | 4000 |
| ycsb_latest_biased | certigap_pruned | 1000 | 6 | 15.528 | 16.012 | 13 | 624 | 4624 |
| ycsb_latest_biased | balanced_budgeted | 1000 | 6 | 8.057 | 8.426 | 13 | 624 | 4624 |
| ycsb_latest_biased | weighted_budgeted | 1000 | 6 | 14.263 | 14.898 | 13 | 624 | 4624 |
| ycsb_latest_biased | balanced_full_reference | 1000 | 999 | 8.750 | 9.024 | 1999 | 95952 | 99952 |
| ycsb_latest_biased | std_lower_bound | 1000 | 0 | 8.531 | 8.799 | 0 | 0 | 4000 |
| uniform | certigap_pruned | 10000 | 6 | 15.239 | 15.827 | 5 | 240 | 40240 |
| uniform | balanced_budgeted | 10000 | 6 | 14.732 | 15.192 | 13 | 624 | 40624 |
| uniform | weighted_budgeted | 10000 | 6 | 14.797 | 15.059 | 13 | 624 | 40624 |
| uniform | balanced_full_reference | 10000 | 9999 | 29.893 | 30.804 | 19999 | 959952 | 999952 |
| uniform | std_lower_bound | 10000 | 0 | 20.933 | 21.291 | 0 | 0 | 40000 |
| zipf | certigap_pruned | 10000 | 6 | 15.223 | 15.872 | 13 | 624 | 40624 |
| zipf | balanced_budgeted | 10000 | 6 | 12.891 | 13.183 | 13 | 624 | 40624 |
| zipf | weighted_budgeted | 10000 | 6 | 15.512 | 16.038 | 13 | 624 | 40624 |
| zipf | balanced_full_reference | 10000 | 9999 | 27.974 | 28.412 | 19999 | 959952 | 999952 |
| zipf | std_lower_bound | 10000 | 0 | 23.908 | 24.221 | 0 | 0 | 40000 |
| hot_tail | certigap_pruned | 10000 | 6 | 12.259 | 12.674 | 13 | 624 | 40624 |
| hot_tail | balanced_budgeted | 10000 | 6 | 13.474 | 13.831 | 13 | 624 | 40624 |
| hot_tail | weighted_budgeted | 10000 | 6 | 14.598 | 14.829 | 13 | 624 | 40624 |
| hot_tail | balanced_full_reference | 10000 | 9999 | 26.450 | 27.018 | 19999 | 959952 | 999952 |
| hot_tail | std_lower_bound | 10000 | 0 | 20.885 | 21.177 | 0 | 0 | 40000 |
| ycsb_hotspot_80_20 | certigap_pruned | 10000 | 6 | 11.807 | 12.105 | 3 | 144 | 40144 |
| ycsb_hotspot_80_20 | balanced_budgeted | 10000 | 6 | 13.731 | 14.008 | 13 | 624 | 40624 |
| ycsb_hotspot_80_20 | weighted_budgeted | 10000 | 6 | 12.916 | 13.127 | 13 | 624 | 40624 |
| ycsb_hotspot_80_20 | balanced_full_reference | 10000 | 9999 | 27.691 | 28.388 | 19999 | 959952 | 999952 |
| ycsb_hotspot_80_20 | std_lower_bound | 10000 | 0 | 20.964 | 21.316 | 0 | 0 | 40000 |
| ycsb_latest_biased | certigap_pruned | 10000 | 6 | 16.590 | 17.881 | 7 | 336 | 40336 |
| ycsb_latest_biased | balanced_budgeted | 10000 | 6 | 13.137 | 13.438 | 13 | 624 | 40624 |
| ycsb_latest_biased | weighted_budgeted | 10000 | 6 | 17.536 | 18.007 | 13 | 624 | 40624 |
| ycsb_latest_biased | balanced_full_reference | 10000 | 9999 | 27.387 | 28.099 | 19999 | 959952 | 999952 |
| ycsb_latest_biased | std_lower_bound | 10000 | 0 | 20.904 | 21.430 | 0 | 0 | 40000 |

## Matched-Budget Interpretation

- CertiGap has lower median batch lookup time than `balanced_budgeted` in `3/10` measured workload-size cases.
- CertiGap has lower median batch lookup time than `weighted_budgeted` in `6/10` measured workload-size cases.

## Limits

This is not an official YCSB, RocksDB, hardware-routing, cache-miss, or external-library benchmark. It is reproducible CPU-level evidence that the exported CertiGap decision tree executes real lookups with an explicit storage footprint. Production claims require a target storage engine, key encoding, allocator, CPU, and independent external baselines.
