# C++ Pruned-Beam Scaling

This measures the candidate-pruned C++ heuristic, not an exact solver. It evaluates at most 32 thresholds per leaf and exports its executable tree, but it does not produce an optimality certificate.

| Distribution | n | Median ms | Objective |
|---|---:|---:|---:|
| zipf | 1000 | 3.870 | 8.266015 |
| hot_middle | 1000 | 6.431 | 9.700063 |
| uniform | 1000 | 6.635 | 10.000000 |
| zipf | 10000 | 7.435 | 10.603766 |
| hot_middle | 10000 | 8.874 | 13.246270 |
| uniform | 10000 | 8.976 | 13.544825 |
| zipf | 100000 | 30.679 | 12.958285 |
| hot_middle | 100000 | 31.894 | 16.669531 |
| uniform | 100000 | 31.605 | 16.760351 |
