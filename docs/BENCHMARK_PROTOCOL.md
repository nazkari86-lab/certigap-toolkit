# Benchmark Protocol

## Research Question

How do CertiGap's greedy and beam-search construction methods trade objective
quality, runtime, and peak Python allocation against fixed structural baselines
as the ordered key space grows?

This benchmark is not an exact-solver study above small `n`: exact dynamic
programs are excluded from the scaling table because their purpose is optimality
validation, not large-instance throughput.

## Workloads

Synthetic stress families are deterministic under seed `20260725`:

- uniform, Zipf, and Dirichlet skew;
- one hot middle block, one hot tail, and two separated hot blocks;
- alternating hot/cold keys, which tests whether locality assumptions fail.

Real observed-frequency workloads are downloaded on demand and cached outside
version control. The generated provenance file records source URL, retrieval
time, byte size, SHA-256, aggregation rule, and key order.

| Workload | Observed event | Ordered key definition | Important limit |
|---|---|---|---|
| MovieLens 100K | ratings | ascending numeric movie id | movie id is an identifier order, not content similarity |
| UCI Online Retail | non-cancelled positive-quantity order rows | ascending lexical `StockCode` | transactions are a historical UK retailer sample |
| Wikimedia Pageviews | one pinned day of English Wikipedia page views | API top-pages rank | rank order is already popularity-oriented, so it is a locality-favourable sensitivity case |

For every source, a large workload is converted to `n` keys by contiguous
aggregation. No source is shuffled, sorted by frequency, or otherwise changed
after its declared ordering. A real source with fewer than `n` keys is skipped;
it is never padded with synthetic keys.

## Solvers And Metrics

Every compatible workload evaluates greedy, beam widths, balanced, weighted
median, full binary search, and learned-segment baselines. The objective is the
same robust objective used throughout CertiGap, with `eta=0.15` and
`budget=min(6,n-1)`.

Wall-clock times use `perf_counter`; peak memory uses `tracemalloc`. Each CSV
row reports median runtime, nearest-rank p95, maximum observed peak allocation,
and objective. These timings are machine-specific and must not be used as a
cross-machine speed claim.

`max` mode uses five repetitions and beam widths through 32 up to `n=512`.
This is the largest complete range for the current Python reference code:
both greedy and beam enumerate candidate thresholds, and exploratory larger
runs did not complete within the benchmark budget. This limitation is a
result, not a hidden exclusion; a compiled/pruned candidate generator is the
next engineering requirement before making large-n throughput claims.

## Reproduction

```bash
PYTHONPATH=. python3 generate_scaling_benchmark.py --mode max --datasets all
```

Use `--datasets real` to fail closed when any real source cannot be fetched.
Use `--datasets synthetic` only for offline stress testing; it must not be
described as a real-data result.
