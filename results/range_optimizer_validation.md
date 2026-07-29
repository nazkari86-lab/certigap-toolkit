# Range-aware optimizer validation

- Rows: `114`
- Complete small-space oracle matches: `6/6`
- Scaling groups where range-aware is tied for best or best: `36/36`
- Strict improvements over point/endpoint proxy: `18/36`
- Every objective is recomputed by the exact mixed-trace evaluator.
- Scaling rows are bounded beam results, not global optimality claims.

The complete-tree-space checks validate the search implementation on n=8. The scaling matrix tests whether direct range-cost optimization improves over the former endpoint proxy without hiding cases where it ties or loses.
