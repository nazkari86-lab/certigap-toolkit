# C++ Pruning Gap Decomposition

The unrestricted frontier DP is the exact oracle. The candidate-restricted frontier DP is exact only over the deterministic C++ mass-quantile threshold grammar. Therefore `total gap = candidate-pruning gap + beam-truncation gap` on every row. This is an empirical decomposition, not an approximation guarantee for the C++ beam.

| Candidate limit | Mean candidate-pruning gap | Mean beam-truncation gap | Mean total gap | Max absolute residual |
|---:|---:|---:|---:|---:|
| 4 | 0.033191 | -0.000000 | 0.033191 | 0.00e+00 |
| 8 | 0.011777 | 0.000000 | 0.011777 | 0.00e+00 |
| 16 | 0.000000 | 0.001429 | 0.001429 | 0.00e+00 |
| 32 | 0.000000 | 0.001429 | 0.001429 | 0.00e+00 |
