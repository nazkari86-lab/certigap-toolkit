# C++ Pruned-Beam Scaling

This measures the candidate-pruned C++ heuristic, not an exact solver. It exports a feasible tree and an independently replayed information-theoretic lower bound. The gap is instance-specific and is not an approximation ratio.

| Distribution | n | Median ms | Upper | Lower | Gap / upper |
|---|---:|---:|---:|---:|---:|
| zipf | 1000 | 2.012 | 8.266015 | 7.565689 | 8.47% |
| hot_middle | 1000 | 3.391 | 9.700063 | 9.016560 | 7.05% |
| uniform | 1000 | 3.576 | 10.000000 | 9.670917 | 3.29% |
| zipf | 10000 | 4.094 | 10.603766 | 9.752453 | 8.03% |
| hot_middle | 10000 | 4.867 | 13.246270 | 12.291391 | 7.21% |
| uniform | 10000 | 4.980 | 13.544825 | 12.944556 | 4.43% |
| zipf | 100000 | 17.955 | 12.958285 | 11.871090 | 8.39% |
| hot_middle | 100000 | 18.448 | 16.669531 | 15.565149 | 6.63% |
| uniform | 100000 | 18.629 | 16.760351 | 16.218194 | 3.23% |
