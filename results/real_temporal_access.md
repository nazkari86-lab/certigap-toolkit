# Real Temporal Access Trace: MovieLens 100K

The first 80% of the original timestamped rating events forms the training profile. The final 20% is an untouched chronological test trace. Each event is treated only as a static lookup of its numeric movie identifier; no synthetic query sequence is generated.

| Solver | Splits | Later-trace mean comparisons | Later-trace p95 | Later-trace max |
|---|---:|---:|---:|---:|
| certigap_pruned | 5 | 10.557450 | 11 | 11 |
| balanced_budgeted | 6 | 11.000000 | 11 | 11 |
| weighted_budgeted | 6 | 10.795800 | 13 | 13 |

The comparison is modeled comparison count, not nanoseconds. Movie ID order is not semantic similarity, and this trace does not establish dynamic-range or database-engine performance.
