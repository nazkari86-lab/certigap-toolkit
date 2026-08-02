# Tracking Hot-Path Benchmark

This benchmark isolates controller and API overhead from algorithm selection. It
compares the direct Fenwick runtime with checked/unchecked frozen and adaptive
paths over 64 configurations. Construction is excluded; each row is the median
of seven native repetitions.

## Results

- Correctness checksum agreement: `True`.
- `fast_checked`: `2.68x` median, `6.24x` p95, `7.96x` maximum.
- `fast_detached_data_plane`: `1.67x` median, `3.37x` p95, `4.64x` maximum.
- `fast_unchecked`: `2.46x` median, `6.40x` p95, `6.56x` maximum.
- `frozen_fenwick_checked`: `1.30x` median, `1.90x` p95, `1.98x` maximum.
- `frozen_fenwick_unchecked`: `1.16x` median, `1.64x` p95, `1.69x` maximum.
- `static_fenwick_checked`: `1.00x` median, `1.18x` p95, `1.38x` maximum.
- `static_fenwick_unchecked`: `1.01x` median, `1.16x` p95, `1.53x` maximum.

### 50,000-operation horizon

- `fast_checked`: `2.79x` median, `5.84x` p95, `7.96x` maximum.
- `fast_detached_data_plane`: `1.63x` median, `2.99x` p95, `4.64x` maximum.
- `fast_unchecked`: `2.46x` median, `6.08x` p95, `6.47x` maximum.
- `frozen_fenwick_checked`: `1.26x` median, `1.90x` p95, `1.95x` maximum.
- `frozen_fenwick_unchecked`: `1.19x` median, `1.55x` p95, `1.65x` maximum.
- `static_fenwick_checked`: `1.01x` median, `1.18x` p95, `1.23x` maximum.
- `static_fenwick_unchecked`: `1.01x` median, `1.15x` p95, `1.53x` maximum.

## Boundary

Frozen mode removes sampling, switching, leases, and the robust shadow. It still
uses one indirect function dispatch because the backend is selected at runtime.
Unchecked methods require one-based keys, valid inclusive ranges, and finite update
values; violating those preconditions is outside the API contract. Measurements are
machine-specific and are not a universal latency theorem.

Raw data: `tracking_hot_path_runtime.csv`.
