# CertiGap-AutoDRO Fair Distribution-Shift Benchmark

`tuned_tv_dro` and `tuned_nominal` search the identical budgets, eta grid, solver set, and fallback set. Their only selection difference is TV radius `0.2` versus `0.0`; this is the primary DRO ablation.

| Scenario | n | Method | Solver | Fallback | Splits | Bytes | Candidates | Select s | Test mean | Test max |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|
| hot_reversal | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1680 | 6.63636 | 7.00000 |
| hot_reversal | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1629 | 6.63636 | 7.00000 |
| hot_reversal | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 6.82955 | 7.00000 |
| hot_reversal | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| hot_reversal | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 6.82955 | 7.00000 |
| hot_reversal | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4513 | 7.67614 | 8.00000 |
| hot_reversal | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.4485 | 7.67614 | 8.00000 |
| hot_reversal | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 7.82955 | 8.00000 |
| hot_reversal | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| hot_reversal | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 7.82955 | 8.00000 |
| hot_reversal | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.4242 | 8.71591 | 9.00000 |
| hot_reversal | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.4239 | 8.71591 | 9.00000 |
| hot_reversal | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 8.82955 | 9.00000 |
| hot_reversal | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| hot_reversal | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 8.82955 | 9.00000 |
| partial_hot_drift_15 | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1620 | 3.70974 | 7.00000 |
| partial_hot_drift_15 | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1676 | 3.70974 | 7.00000 |
| partial_hot_drift_15 | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 3.76015 | 7.00000 |
| partial_hot_drift_15 | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| partial_hot_drift_15 | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 3.76015 | 7.00000 |
| partial_hot_drift_15 | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4535 | 4.71571 | 8.00000 |
| partial_hot_drift_15 | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.4500 | 4.71571 | 8.00000 |
| partial_hot_drift_15 | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 4.76015 | 8.00000 |
| partial_hot_drift_15 | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| partial_hot_drift_15 | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 4.76015 | 8.00000 |
| partial_hot_drift_15 | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.4309 | 5.72167 | 9.00000 |
| partial_hot_drift_15 | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.4299 | 5.72167 | 9.00000 |
| partial_hot_drift_15 | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 5.76015 | 9.00000 |
| partial_hot_drift_15 | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| partial_hot_drift_15 | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 5.76015 | 9.00000 |
| partial_hot_drift_35 | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1623 | 4.39836 | 7.00000 |
| partial_hot_drift_35 | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1628 | 4.39836 | 7.00000 |
| partial_hot_drift_35 | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 4.48236 | 7.00000 |
| partial_hot_drift_35 | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| partial_hot_drift_35 | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 4.48236 | 7.00000 |
| partial_hot_drift_35 | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4534 | 5.41228 | 8.00000 |
| partial_hot_drift_35 | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.4505 | 5.41228 | 8.00000 |
| partial_hot_drift_35 | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 5.48236 | 8.00000 |
| partial_hot_drift_35 | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| partial_hot_drift_35 | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 5.48236 | 8.00000 |
| partial_hot_drift_35 | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.4258 | 6.42620 | 9.00000 |
| partial_hot_drift_35 | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.4193 | 6.42620 | 9.00000 |
| partial_hot_drift_35 | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 6.48236 | 9.00000 |
| partial_hot_drift_35 | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| partial_hot_drift_35 | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 6.48236 | 9.00000 |
| partial_hot_drift_65 | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1638 | 5.43128 | 7.00000 |
| partial_hot_drift_65 | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1619 | 5.43128 | 7.00000 |
| partial_hot_drift_65 | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 5.56568 | 7.00000 |
| partial_hot_drift_65 | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| partial_hot_drift_65 | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 5.56568 | 7.00000 |
| partial_hot_drift_65 | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4527 | 6.45714 | 8.00000 |
| partial_hot_drift_65 | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.4548 | 6.45714 | 8.00000 |
| partial_hot_drift_65 | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 6.56568 | 8.00000 |
| partial_hot_drift_65 | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| partial_hot_drift_65 | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.56568 | 8.00000 |
| partial_hot_drift_65 | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.4232 | 7.48299 | 9.00000 |
| partial_hot_drift_65 | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.4225 | 7.48299 | 9.00000 |
| partial_hot_drift_65 | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 7.56568 | 9.00000 |
| partial_hot_drift_65 | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| partial_hot_drift_65 | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.56568 | 9.00000 |
| stationary_hot_head | 32 | tuned_tv_dro | beam | midpoint_binary | 2 | 368 | 24 | 0.1612 | 3.19328 | 7.00000 |
| stationary_hot_head | 32 | tuned_nominal | beam | midpoint_binary | 2 | 368 | 24 | 0.1612 | 3.19328 | 7.00000 |
| stationary_hot_head | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 1 | 0.0000 | 3.21849 | 7.00000 |
| stationary_hot_head | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| stationary_hot_head | 32 | fixed_weighted | weighted | fixed_rounds | 3 | 464 | 1 | 0.0000 | 3.21849 | 7.00000 |
| stationary_hot_head | 64 | tuned_tv_dro | beam | midpoint_binary | 2 | 496 | 26 | 0.4504 | 4.19328 | 8.00000 |
| stationary_hot_head | 64 | tuned_nominal | beam | midpoint_binary | 2 | 496 | 26 | 0.4502 | 4.19328 | 8.00000 |
| stationary_hot_head | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 1 | 0.0000 | 4.21849 | 8.00000 |
| stationary_hot_head | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| stationary_hot_head | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 4.21849 | 8.00000 |
| stationary_hot_head | 128 | tuned_tv_dro | beam | midpoint_binary | 2 | 752 | 26 | 1.4274 | 5.19328 | 9.00000 |
| stationary_hot_head | 128 | tuned_nominal | beam | midpoint_binary | 2 | 752 | 26 | 1.4237 | 5.19328 | 9.00000 |
| stationary_hot_head | 128 | fixed_beam | beam | fixed_rounds | 2 | 752 | 1 | 0.0000 | 5.21849 | 9.00000 |
| stationary_hot_head | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| stationary_hot_head | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 5.21849 | 9.00000 |
| stationary_zipf | 32 | tuned_tv_dro | beam | fixed_rounds | 3 | 464 | 34 | 0.1669 | 4.30368 | 6.00000 |
| stationary_zipf | 32 | tuned_nominal | beam | midpoint_binary | 4 | 560 | 34 | 0.1634 | 4.20624 | 7.00000 |
| stationary_zipf | 32 | fixed_beam | beam | fixed_rounds | 4 | 560 | 1 | 0.0000 | 4.24755 | 6.00000 |
| stationary_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| stationary_zipf | 32 | fixed_weighted | weighted | fixed_rounds | 4 | 560 | 1 | 0.0000 | 4.34144 | 7.00000 |
| stationary_zipf | 64 | tuned_tv_dro | beam | midpoint_binary | 4 | 688 | 40 | 0.4574 | 4.99841 | 7.00000 |
| stationary_zipf | 64 | tuned_nominal | beam | midpoint_binary | 4 | 688 | 40 | 0.4578 | 4.94234 | 8.00000 |
| stationary_zipf | 64 | fixed_beam | beam | fixed_rounds | 4 | 688 | 1 | 0.0000 | 5.01343 | 7.00000 |
| stationary_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| stationary_zipf | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 5.15870 | 8.00000 |
| stationary_zipf | 128 | tuned_tv_dro | beam | midpoint_binary | 3 | 848 | 38 | 1.4491 | 5.75959 | 8.00000 |
| stationary_zipf | 128 | tuned_nominal | beam | midpoint_binary | 4 | 944 | 38 | 1.4503 | 5.65590 | 9.00000 |
| stationary_zipf | 128 | fixed_beam | beam | fixed_rounds | 3 | 848 | 1 | 0.0000 | 5.79996 | 8.00000 |
| stationary_zipf | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| stationary_zipf | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 5.94223 | 9.00000 |
| uniform_to_zipf | 32 | tuned_tv_dro | beam | fixed_rounds | 0 | 176 | 16 | 0.1573 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | tuned_nominal | beam | fixed_rounds | 0 | 176 | 16 | 0.1575 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_beam | beam | fixed_rounds | 0 | 176 | 1 | 0.0000 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_weighted | weighted | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| uniform_to_zipf | 64 | tuned_tv_dro | beam | fixed_rounds | 0 | 304 | 18 | 0.4407 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | tuned_nominal | beam | fixed_rounds | 0 | 304 | 18 | 0.4446 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_beam | beam | fixed_rounds | 0 | 304 | 1 | 0.0000 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| uniform_to_zipf | 128 | tuned_tv_dro | beam | fixed_rounds | 0 | 560 | 18 | 1.3832 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | tuned_nominal | beam | fixed_rounds | 0 | 560 | 18 | 1.3854 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | fixed_beam | beam | fixed_rounds | 0 | 560 | 1 | 0.0000 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| uniform_to_zipf | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| zipf_to_uniform | 32 | tuned_tv_dro | beam | fixed_rounds | 3 | 464 | 34 | 0.1657 | 5.50000 | 6.00000 |
| zipf_to_uniform | 32 | tuned_nominal | beam | midpoint_binary | 4 | 560 | 34 | 0.1667 | 5.75000 | 7.00000 |
| zipf_to_uniform | 32 | fixed_beam | beam | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.50000 | 6.00000 |
| zipf_to_uniform | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 1 | 0.0000 | 5.00000 | 5.00000 |
| zipf_to_uniform | 32 | fixed_weighted | weighted | fixed_rounds | 4 | 560 | 1 | 0.0000 | 6.03125 | 7.00000 |
| zipf_to_uniform | 64 | tuned_tv_dro | beam | midpoint_binary | 4 | 688 | 40 | 0.4641 | 6.46875 | 7.00000 |
| zipf_to_uniform | 64 | tuned_nominal | beam | midpoint_binary | 4 | 688 | 40 | 0.4580 | 6.82812 | 8.00000 |
| zipf_to_uniform | 64 | fixed_beam | beam | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.50000 | 7.00000 |
| zipf_to_uniform | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 1 | 0.0000 | 6.00000 | 6.00000 |
| zipf_to_uniform | 64 | fixed_weighted | weighted | fixed_rounds | 4 | 688 | 1 | 0.0000 | 7.20312 | 8.00000 |
| zipf_to_uniform | 128 | tuned_tv_dro | beam | midpoint_binary | 3 | 848 | 38 | 1.4474 | 7.59375 | 8.00000 |
| zipf_to_uniform | 128 | tuned_nominal | beam | midpoint_binary | 4 | 944 | 38 | 1.4472 | 7.82812 | 9.00000 |
| zipf_to_uniform | 128 | fixed_beam | beam | fixed_rounds | 3 | 848 | 1 | 0.0000 | 7.70312 | 8.00000 |
| zipf_to_uniform | 128 | fixed_balanced | balanced | fixed_rounds | 4 | 944 | 1 | 0.0000 | 7.00000 | 7.00000 |
| zipf_to_uniform | 128 | fixed_weighted | weighted | fixed_rounds | 4 | 944 | 1 | 0.0000 | 8.32812 | 9.00000 |

## Paired Outcomes

- tuned TV-DRO vs `tuned_nominal`: `3` wins, `3` losses, `18` ties across `24` pairs.
- tuned TV-DRO vs `fixed_beam`: `19` wins, `1` losses, `4` ties across `24` pairs.
- tuned TV-DRO vs `fixed_balanced`: `12` wins, `9` losses, `3` ties across `24` pairs.
- tuned TV-DRO vs `fixed_weighted`: `21` wins, `0` losses, `3` ties across `24` pairs.

## Scope

Expected comparison cost is deterministic for each supplied test distribution, so sampling confidence intervals are not applicable to this table. Construction timings are local-machine measurements. External implementations, real request latency, and prospective traces remain separate experiments.
