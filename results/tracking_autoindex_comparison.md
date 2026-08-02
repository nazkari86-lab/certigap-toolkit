# TrackingAutoIndex comprehensive comparison

- Certified workload configurations: `126`.
- Structural policy rows: `882`.
- Fixed-candidate rows: `882`.
- Wall-clock method rows: `90`.
- All runtime methods passed identical checksum validation.

## Structural outcomes

- Versus `initial_static`: WFA wins `106`, ties `18`, loses `2`.
- Versus `best_fixed_hindsight`: WFA wins `53`, ties `34`, loses `39`.
- Versus `myopic_current_operation`: WFA wins `29`, ties `62`, loses `35`.
- Versus `cumulative_leader`: WFA wins `55`, ties `39`, loses `32`.
- Mean ratio to exact unrestricted oracle: `1.111103`.
- Median ratio to exact unrestricted oracle: `1.009222`.
- Maximum ratio to exact unrestricted oracle: `2.068306`.
- Best fixed candidate frequency: `{'fenwick': 81, 'prefix_sum': 27, 'sorted_array': 18}`.

### Versus best fixed hindsight by workload

| Workload | Wins | Ties | Losses |
|---|---:|---:|---:|
| `stable_points` | 0 | 9 | 0 |
| `stable_ranges` | 0 | 6 | 3 |
| `stable_updates` | 0 | 9 | 0 |
| `mixed_read_heavy` | 3 | 1 | 5 |
| `mixed_write_heavy` | 5 | 0 | 4 |
| `point_to_range` | 0 | 6 | 3 |
| `range_to_update` | 9 | 0 | 0 |
| `update_to_range` | 9 | 0 | 0 |
| `three_phase` | 8 | 0 | 1 |
| `alternating_range_update` | 3 | 0 | 6 |
| `short_bursts` | 7 | 0 | 2 |
| `random_iid` | 4 | 0 | 5 |
| `markov_bursty` | 5 | 0 | 4 |
| `varying_ranges` | 0 | 3 | 6 |

### Migration sensitivity

| Migration units | Mean oracle ratio | Max oracle ratio | Mean switches |
|---:|---:|---:|---:|
| 2 | 1.003004 | 1.026316 | 12.571 |
| 8 | 1.079540 | 1.545946 | 4.333 |
| 32 | 1.250766 | 2.068306 | 1.714 |

## Runtime boundary

- Median TrackingAutoIndex slowdown versus fastest tested runtime: `288.06x`.
- Maximum TrackingAutoIndex slowdown versus fastest tested runtime: `1952.02x`.
- Median slowdown versus fastest fixed portfolio backend: `280.86x`.
- Maximum slowdown versus fastest fixed portfolio backend: `958.87x`.
- These Python timings include online WFA accounting and in-trace rebuilds, but exclude initial construction and certificate export.
- Structural scores and wall-clock nanoseconds are reported separately; neither is substituted for the other.

| n | Workload | Tracking ns/op | Fastest fixed | Fixed ns/op | Slowdown |
|---:|---|---:|---|---:|---:|
| 64 | `alternating_range_update` | 34211.9 | `sorted_array` | 354.8 | 96.42x |
| 64 | `mixed_read_heavy` | 34074.1 | `prefix_sum` | 268.6 | 126.88x |
| 64 | `point_to_range` | 43244.5 | `prefix_sum` | 167.8 | 257.71x |
| 64 | `stable_points` | 18025.7 | `sorted_array` | 126.3 | 142.72x |
| 64 | `stable_ranges` | 47897.9 | `prefix_sum` | 157.6 | 304.01x |
| 256 | `alternating_range_update` | 132611.0 | `fenwick` | 649.9 | 204.05x |
| 256 | `mixed_read_heavy` | 131029.0 | `fenwick` | 358.1 | 365.93x |
| 256 | `point_to_range` | 129876.5 | `prefix_sum` | 143.6 | 904.72x |
| 256 | `stable_points` | 124540.9 | `prefix_sum` | 129.9 | 958.87x |
| 256 | `stable_ranges` | 135776.9 | `prefix_sum` | 157.9 | 860.03x |
