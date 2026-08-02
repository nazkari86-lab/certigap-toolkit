# Concurrent Tracking Runtime Benchmark

This benchmark compares the immutable Prefix snapshot, locked Fenwick fallback,
direct Fenwick, and direct Prefix paths for one and four reader threads. Every row
is the median of five repetitions over 500,000 deterministic operations; structure
construction and snapshot publication are excluded.

## Results

- Correctness checksum agreement: `True` across all `8` configurations.
- Pointer/reader-count atomics report lock-free on this platform: `True`.
- Epoch snapshot speedup over locked fallback: `2.05x` to `3.84x`, `3.14x` median.
- Snapshot overhead versus direct Prefix: `4.97x` to `86.55x`, `32.36x` median.
- Batched snapshot-view overhead versus direct Prefix: `1.39x` to `4.64x`, `2.33x` median.
- Unchecked batched-view overhead versus direct Prefix: `1.02x` to `4.53x`, `1.46x` median.

## Boundary

Individual snapshot reads use an atomic epoch entry/exit. A snapshot view amortizes
that pair across a caller-defined read batch. Fallback reads use a shared mutex and
point updates use its exclusive side. Results are machine-specific;
the benchmark does not establish wait-free progress, multi-writer scalability, or a
portable latency theorem.

Raw data: `concurrent_tracking_runtime.csv`.
