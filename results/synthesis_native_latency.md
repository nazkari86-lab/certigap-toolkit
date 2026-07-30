# CertiGap-H native holdout benchmark

| Scenario | Auto selected | Auto ns/op | Holdout oracle | Auto regret | Hybrid vs Fenwick |
|---|---:|---:|---:|---:|---:|
| left_hot | certigap_hybrid | 3.882 | certigap_hybrid | +0.0% | +35.1% |
| two_hot | global_prefix | 3.354 | certigap_hybrid | +2.8% | +67.9% |
| uniform | global_prefix | 3.347 | global_prefix | +0.0% | +40.8% |
| adversarial_edges | global_prefix | 3.028 | global_prefix | +0.0% | +87.5% |
| temporal_shift | fenwick | 7.326 | global_prefix | +219.7% | +111.0% |
| read_only_skew | global_prefix | 1.458 | global_prefix | +0.0% | +73.0% |
| update_30_uniform | fenwick | 6.194 | fenwick | +0.0% | -1.2% |
| update_50_uniform | fenwick | 5.778 | fenwick | +0.0% | -24.8% |
| movielens_100k_frequency_derived | certigap_hybrid | 4.257 | global_prefix | +6.4% | +49.4% |
| uci_online_retail_frequency_derived | global_prefix | 3.500 | certigap_hybrid | +1.0% | +63.7% |
| wikimedia_pageviews_frequency_derived | certigap_hybrid | 4.035 | certigap_hybrid | +0.0% | +36.8% |

- CertiGap-H beats Fenwick in `9/11` holdout scenarios.
- CertiGap-H beats uniform-prefix in `10/11` holdout scenarios.
- CertiGap-H is the fastest tested implementation in `4/11` scenarios.
- Train-only AutoIndex matches the three-candidate holdout oracle in `7/11` scenarios.
- Mean AutoIndex holdout regret is `20.90%`; maximum is `219.69%`.
- Excluding the declared `temporal_shift` stress case, mean AutoIndex regret is `1.02%` and maximum is `6.42%`.
- Timings are post-build medians of nine complete trace executions; p95 is the nearest-rank batch statistic and MAD reports robust spread. Each method receives a separate untimed warm-up trace.
- Public datasets provide observed key-frequency distributions, not native range-query traces. Their range/get/update operations are deterministically generated and labelled `frequency_derived`.
- These measurements describe this machine and compiler only. They are not a portable speed guarantee.
