# Fast TrackingAutoIndex Runtime Benchmark

This benchmark covers 4 sizes, 8 stationary/adversarial workloads, and 2 stream
horizons. Every row is the median of five native C++ repetitions. Construction is
excluded; controller sampling, fallback, leases, and in-stream migrations are included.

## Results

- Correctness checksum agreement: `True` across all `64` configurations.
- Versus robust Fenwick: `1.21x` median, `1.59x` p95, `1.90x` maximum.
- Versus fastest fixed backend chosen with hindsight: `1.35x` median, `3.76x` p95, `5.40x` maximum.

## Interpretation

The robust comparison answers the deployment question: overhead relative to a backend
that safely supports arbitrary future point updates and range sums. The hindsight
comparison is deliberately stricter and includes structures such as an O(1)-update
array on update-only streams, even though it may need O(n) for an unexpected range.
No causal online selector can know that the future will remain update-only. Fast mode
therefore keeps a current Fenwick shadow and immediately abandons a static specialized
view when an unsafe update arrives. It guarantees runtime semantics, not a universal
competitive latency factor.

Raw data: `tracking_autoindex_fast_runtime.csv`.
