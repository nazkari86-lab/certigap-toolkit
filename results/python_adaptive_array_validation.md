# Python AdaptiveArray Validation

Deterministic semantic and lifecycle checks for the public Python API.

| Scenario | Selected | Optimized | Passed |
|---|---|---:|---:|
| automatic_range_warmup | prefix_sum | True | True |
| automatic_point_warmup | sorted_array | True | True |
| mixed_update_workload | fenwick | True | True |
| deployment_threshold_rejection | sorted_array | False | True |
| explicit_maintenance | sparse_table | True | True |
| profile_writer | prefix_sum | True | True |
| profile_reader | prefix_sum | True | True |
