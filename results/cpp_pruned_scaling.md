# C++ Pruned-Beam Scaling

This measures the candidate-pruned C++ heuristic, not an exact solver. It evaluates at most 32 thresholds per leaf and exports its executable tree, but it does not produce an optimality certificate.

| Distribution | n | Median ms | Objective |
|---|---:|---:|---:|
| zipf | 1000 | 3.951 | 8.266015 |
| hot_middle | 1000 | 6.854 | 9.700063 |
| uniform | 1000 | 6.753 | 10.000000 |
| zipf | 10000 | 7.587 | 10.603766 |
| hot_middle | 10000 | 9.135 | 13.246270 |
| uniform | 10000 | 9.333 | 13.544825 |
| zipf | 100000 | 31.672 | 12.958285 |
| hot_middle | 100000 | 32.451 | 16.669531 |
| uniform | 100000 | 32.691 | 16.760351 |
