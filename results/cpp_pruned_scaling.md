# C++ Pruned-Beam Scaling

This measures the candidate-pruned C++ heuristic, not an exact solver. It evaluates at most 32 thresholds per leaf and preserves no certificate/tree export.

| Distribution | n | Median ms | Objective |
|---|---:|---:|---:|
| zipf | 1000 | 7.040 | 8.266015 |
| hot_middle | 1000 | 11.276 | 9.700063 |
| uniform | 1000 | 10.894 | 10.000000 |
| zipf | 10000 | 12.632 | 10.603766 |
| hot_middle | 10000 | 16.987 | 13.246270 |
| uniform | 10000 | 17.878 | 13.544825 |
| zipf | 100000 | 55.619 | 12.958285 |
| hot_middle | 100000 | 59.095 | 16.669531 |
| uniform | 100000 | 58.701 | 16.760351 |
