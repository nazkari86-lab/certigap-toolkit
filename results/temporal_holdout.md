# Temporal Holdout: MovieLens 100K

Identical tuned portfolios are fitted on the earliest 80% of timestamped ratings and evaluated on the final 20%. Only the TV selection radius changes. Movie identifier order is preserved; this is a public temporal shift test, not a production latency study.

| n | Method | rho | Solver | Fallback | Splits | Future average | Future max |
|---:|---|---:|---|---|---:|---:|---:|
| 32 | tuned_nominal | 0.00 | beam | fixed_rounds | 6 | 4.474450 | 9 |
| 32 | tuned_tv_010 | 0.10 | beam | fixed_rounds | 2 | 4.560300 | 6 |
| 32 | tuned_tv_020 | 0.20 | beam | fixed_rounds | 2 | 4.560300 | 6 |
| 64 | tuned_nominal | 0.00 | beam | fixed_rounds | 6 | 5.474450 | 10 |
| 64 | tuned_tv_010 | 0.10 | beam | fixed_rounds | 2 | 5.560300 | 7 |
| 64 | tuned_tv_020 | 0.20 | beam | fixed_rounds | 2 | 5.560300 | 7 |
| 128 | tuned_nominal | 0.00 | beam | fixed_rounds | 5 | 6.505450 | 10 |
| 128 | tuned_tv_010 | 0.10 | beam | fixed_rounds | 2 | 6.560300 | 8 |
| 128 | tuned_tv_020 | 0.20 | beam | fixed_rounds | 2 | 6.560300 | 8 |
