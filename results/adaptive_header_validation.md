# Adaptive single-header C++ validation

- Native C++ rows: `24`.
- Correct point/range/update/snapshot cases: `24/24`.
- Complete candidate reports per case: `5/5`.
- Selected backend distribution: `{'certirange_point': 4, 'fenwick': 4, 'segment_tree': 12, 'sorted_array': 4}`.
- Sizes: `16, 32, 64, 128`.
- Modes: point-hot, range-hot, calibrated segment tree, required CertiRange, minimum, and maximum.

This validates deterministic reference behavior and selection contracts. It is not a production latency benchmark.
