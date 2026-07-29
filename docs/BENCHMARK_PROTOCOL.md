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

## C++ Large-N Heuristic

`generate_cpp_scaling.py` measures a separate candidate-pruned C++ beam path.
It evaluates all thresholds on small leaves and deterministic endpoints,
uniform positions, and mass quantiles on larger leaves. This is a scalable
heuristic, not an exact or proof-carrying solver: it has no approximation
guarantee and does not export a certificate.

## Post-Build Lookup Latency

`generate_lookup_benchmark.py` compiles an executable routing benchmark and
measures only lookup after construction. It compares the exported pruned
CertiGap tree with balanced and weighted-median decision trees plus
`std::lower_bound`, reporting median/p95 nanoseconds per query and a scoped
routing-node footprint. The generated report records CPU-level and allocator
limits; it is not a hardware-routing or external-library claim.

```bash
PYTHONPATH=. python3 generate_lookup_benchmark.py
```

## AutoDRO Distribution Shift

`generate_autodro_benchmark.py` uses eight predefined train/test scenarios at
`n=32`, `64`, and `128`. The primary pair compares TV radius `0.2` with radius
`0.0` over the identical budgets, eta grid, solver set, and fallback set. Fixed
beam, balanced, and weighted trees remain secondary reference lines.

The 120 published rows report selection time, candidate count, test mean and
maximum comparison cost, split count, and analytical bytes. TV selection has
`3` wins, `3` losses, and `18` ties against nominal selection across 24 paired
cases. This mixed result prevents attributing gains from broader tuning to DRO.
The test distribution is never used during selection.

`generate_direct_tv_validation.py` separately exhausts 181 proof-sized tree
spaces. It verifies that direct TV search never loses to the heuristic subset
and retains a strict separation witness where the direct objective improves
the robust score by more than `0.06`.

`generate_uncertainty_validation.py` runs 3,000 deterministic i.i.d.
multinomial trials over uniform/Zipf distributions, two alphabet sizes, and
three sample sizes. It checks empirical coverage and radius contraction. It
does not validate dependent streams.

`generate_online_adaptation.py` evaluates four empirical-TV rebuild thresholds
on a deterministic 12-window drift stream and reports rebuild count and regret
against always refitting.

```bash
PYTHONPATH=. python3 generate_autodro_benchmark.py
```
