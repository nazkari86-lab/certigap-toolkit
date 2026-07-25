# Scientific Validation Artifacts

- Exact cross-validation rows: `336` (frontier DP = cost-cap DP = brute force).
- Branch-and-bound proof trace nodes: `143`.
- Branch-and-bound pruned nodes: `69`.
- Proven greedy-family rows: `8` for `m=3..10`.
- The branch-and-bound JSON trace is independently checked by `verify_branch_and_bound_certificate` without importing a solver.
