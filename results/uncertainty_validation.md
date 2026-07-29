# Finite-Sample TV Radius Validation

Each row uses 250 deterministic i.i.d. multinomial repetitions. Coverage checks whether the known generating distribution lies inside the reported smoothed TV ball. This validates implementation and conservatism under the i.i.d. model only; it is not evidence for dependent production traces.

| Distribution | n | N | Coverage | Mean radius | Mean true TV |
|---|---:|---:|---:|---:|---:|
| uniform | 8 | 100 | 1.000 | 0.21073 | 0.10190 |
| uniform | 8 | 1000 | 1.000 | 0.06548 | 0.03198 |
| uniform | 8 | 10000 | 0.996 | 0.02067 | 0.01046 |
| uniform | 32 | 100 | 1.000 | 0.38516 | 0.18976 |
| uniform | 32 | 1000 | 1.000 | 0.11332 | 0.07017 |
| uniform | 32 | 10000 | 1.000 | 0.03552 | 0.02233 |
| zipf | 8 | 100 | 1.000 | 0.21895 | 0.09070 |
| zipf | 8 | 1000 | 1.000 | 0.06656 | 0.03134 |
| zipf | 8 | 10000 | 1.000 | 0.02079 | 0.00954 |
| zipf | 32 | 100 | 1.000 | 0.41790 | 0.17026 |
| zipf | 32 | 1000 | 1.000 | 0.11890 | 0.05989 |
| zipf | 32 | 10000 | 1.000 | 0.03615 | 0.01897 |
