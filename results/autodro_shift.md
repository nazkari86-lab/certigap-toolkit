# CertiGap-AutoDRO Distribution-Shift Benchmark

Selection uses only the training counts and a fixed TV radius of `0.2`. The test distribution is used only after selection.

| Scenario | n | Method | Selected solver | Fallback | Splits | Bytes | Test mean | Test max |
|---|---:|---|---|---|---:|---:|---:|---:|
| hot_reversal | 32 | autodro | beam | midpoint_binary | 2 | 368 | 6.63636 | 7.00000 |
| hot_reversal | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 6.82955 | 7.00000 |
| hot_reversal | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 5.00000 | 5.00000 |
| hot_reversal | 64 | autodro | beam | midpoint_binary | 2 | 496 | 7.67614 | 8.00000 |
| hot_reversal | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 7.82955 | 8.00000 |
| hot_reversal | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 6.00000 | 6.00000 |
| partial_hot_drift | 32 | autodro | beam | midpoint_binary | 2 | 368 | 4.39836 | 7.00000 |
| partial_hot_drift | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 4.48236 | 7.00000 |
| partial_hot_drift | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 5.00000 | 5.00000 |
| partial_hot_drift | 64 | autodro | beam | midpoint_binary | 2 | 496 | 5.41228 | 8.00000 |
| partial_hot_drift | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 5.48236 | 8.00000 |
| partial_hot_drift | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 6.00000 | 6.00000 |
| stationary_zipf | 32 | autodro | beam | fixed_rounds | 3 | 464 | 4.30368 | 6.00000 |
| stationary_zipf | 32 | fixed_beam | beam | fixed_rounds | 4 | 560 | 4.24755 | 6.00000 |
| stationary_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 5.00000 | 5.00000 |
| stationary_zipf | 64 | autodro | beam | midpoint_binary | 4 | 688 | 4.99841 | 7.00000 |
| stationary_zipf | 64 | fixed_beam | beam | fixed_rounds | 4 | 688 | 5.01343 | 7.00000 |
| stationary_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 6.00000 | 6.00000 |
| uniform_to_zipf | 32 | autodro | beam | fixed_rounds | 0 | 176 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_beam | beam | fixed_rounds | 0 | 176 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 5.00000 | 5.00000 |
| uniform_to_zipf | 64 | autodro | beam | fixed_rounds | 0 | 304 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_beam | beam | fixed_rounds | 0 | 304 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 6.00000 | 6.00000 |

## Aggregate

- AutoDRO beats fixed beam on shifted/stationary test mean in `5/8` cases.
- AutoDRO beats fixed balanced on shifted/stationary test mean in `4/8` cases.

## Scope

This is a deterministic comparison-cost experiment, not a hardware-latency claim. It tests selection under distribution shift; an external trace replay remains required.
