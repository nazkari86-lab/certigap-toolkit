# Certified AutoIndex validation

- Rows: `120` (`24` complete portfolios).
- Candidate count per portfolio: `5`.
- Independently replay-verified portfolios: `24/24`.
- Selection distribution: `{'certirange_range': 5, 'fenwick': 4, 'segment_tree': 3, 'sorted_array': 12}`.
- Mean chronological-holdout regret: `9.744583` primitive visits.
- Maximum chronological-holdout regret: `118.320000` primitive visits.

Selection uses training operations only. Holdout measures temporal generalization and is never consulted by the compiler. Scores are declared structural primitive visits, not wall-clock latency.
