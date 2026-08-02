# Proof-Carrying DSL Validation

The deterministic matrix covers `36` configurations: three canonical
algebras, four operation contracts, and three resource regimes. Every
configuration regenerates the complete typed grammar, independently verifies the
certificate, and replays 160 operations against a list oracle.

## Results

- Typed capability verification: `True`.
- Grammar completeness verification: `True`.
- Runtime/oracle checksum agreement: `True`.
- Selected backend diversity: `6` backends.
- Selection counts: `{"certirange_point": 3, "certirange_range": 9, "prefix_sum": 1, "segment_tree": 6, "sorted_array": 15, "sparse_table": 2}`.

## Boundary

The matrix validates the fixed-size DSL v1 grammar and built-in `sum`, `min`, and
`max` semantics. It does not establish portable latency optimality, arbitrary
user-defined algebra laws, insert/erase support, or global optimality outside the
declared eight-design grammar.
