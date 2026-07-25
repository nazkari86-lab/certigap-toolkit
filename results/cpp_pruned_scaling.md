# C++ Pruned-Beam Scaling

This measures the candidate-pruned C++ heuristic, not an exact solver. It evaluates at most 32 thresholds per leaf and preserves no certificate/tree export.

| Distribution | n | Median ms | Objective |
|---|---:|---:|---:|
| zipf | 1000 | 2.381 | 8.266015 |
| hot_middle | 1000 | 3.618 | 9.700063 |
| uniform | 1000 | 3.654 | 10.000000 |
| zipf | 10000 | 5.316 | 10.603766 |
| hot_middle | 10000 | 6.101 | 13.247099 |
| uniform | 10000 | 5.957 | 13.524085 |
| zipf | 100000 | 32.598 | 12.958285 |
| hot_middle | 100000 | 40.718 | 16.703192 |
| uniform | 100000 | 41.437 | 16.760351 |
