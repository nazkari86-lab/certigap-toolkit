# Certified AutoIndex validation

- Rows: `192` (`24` complete portfolios).
- Candidate count per portfolio: `8`.
- Independently replay-verified portfolios: `24/24`.
- Selection distribution: `{'certirange_range': 4, 'prefix_sum': 4, 'sorted_array': 12, 'sparse_table': 4}`.
- Mean chronological-holdout regret: `9.724479` primitive visits.
- Maximum chronological-holdout regret: `119.550000` primitive visits.

Selection uses training operations only. Holdout measures temporal generalization and is never consulted by the compiler. Scores are declared structural primitive visits, not wall-clock latency.
