# Temporal Holdout: MovieLens 100K

Trees are fitted on the earliest 80% of timestamped ratings and evaluated on the final 20%. Movie identifier order is preserved; this is a distribution-shift experiment, not a causal production study.

| n | eta | Train objective | Future average cost | Future max cost |
|---:|---:|---:|---:|---:|
| 32 | 0.00 | 4.446388 | 4.474450 | 9 |
| 32 | 0.15 | 4.760955 | 4.560300 | 6 |
| 32 | 0.30 | 4.979610 | 4.560300 | 6 |
| 64 | 0.00 | 5.446388 | 5.474450 | 10 |
| 64 | 0.15 | 5.760955 | 5.560300 | 7 |
| 64 | 0.30 | 5.979610 | 5.560300 | 7 |
| 128 | 0.00 | 6.483388 | 6.505450 | 10 |
| 128 | 0.15 | 6.760955 | 6.560300 | 8 |
| 128 | 0.30 | 6.979610 | 6.560300 | 8 |
