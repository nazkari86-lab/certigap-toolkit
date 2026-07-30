# CertiGap-X native holdout benchmark

| Scenario | Fastest | CertiGap-X ns/op | Uniform ns/op | X vs uniform | X / fastest |
|---|---:|---:|---:|---:|---:|
| left_hot | fenwick | 21.805 | 18.076 | -17.1% | 2.95x |
| two_hot | fenwick | 24.722 | 18.347 | -25.8% | 2.38x |
| uniform | fenwick | 35.438 | 35.792 | +1.0% | 2.00x |
| adversarial_edges | fenwick | 33.097 | 23.917 | -27.7% | 2.58x |
| temporal_shift | fenwick | 27.007 | 21.278 | -21.2% | 1.48x |
| movielens_100k_frequency_derived | fenwick | 21.201 | 18.035 | -14.9% | 1.88x |
| uci_online_retail_frequency_derived | fenwick | 26.625 | 19.555 | -26.6% | 2.35x |
| wikimedia_pageviews_frequency_derived | fenwick | 24.042 | 23.243 | -3.3% | 2.10x |

- CertiGap-X beats the model-selected uniform block baseline in `1/8` holdout scenarios.
- CertiGap-X is the fastest tested implementation in `0/8` scenarios.
- Timings are post-build medians of nine complete trace executions; p95 is the nearest-rank batch statistic and MAD reports robust spread. Each method receives a separate untimed warm-up trace.
- Public datasets provide observed key-frequency distributions, not native range-query traces. Their range/get/update operations are deterministically generated and labelled `frequency_derived`.
- These measurements describe this machine and compiler only. They are not a portable speed guarantee.
