# Data Evidence And Interpretation

This document prevents three different forms of evidence from being described
as the same thing. The benchmark generator, claim register, report, and slides
must preserve these labels.

## A. Direct Observed Event Trace

`results/real_temporal_access.{csv,json,md}` is the only current static-search
benchmark that consumes an unaggregated chronological public event sequence.
It uses the original MovieLens 100K `u.data` timestamps, with equal timestamps
resolved by source-file order:

- first 80,000 rating events: build the observed movie-ID frequency profile;
- final 20,000 events: untouched evaluation lookups;
- one event: one static lookup of the numeric movie identifier;
- methods: candidate-pruned C++ CertiGap, matched-budget balanced tree, and
  matched-budget weighted-median tree.

The JSON stores the raw-training weights and a `certigap-pruned-beam-v1`
certificate. `verify_artifacts.py` replays that certificate independently.
This is modeled comparison count, not a measurement of database latency,
recommendation quality, application sessions, range queries, updates, or a
production storage engine.

## B. Real Observed Frequencies Or Key Distributions

The regular scaling suite downloads public sources and aggregates each one to a
fixed ordered key universe. The committed
`results/benchmark_provenance.json` records source URL, retrieval time, raw
file hash, aggregation rule, and declared key order. These inputs are real, but
the resulting vector is not automatically a chronological operation trace.

| Source | Observed quantity | Correct interpretation |
|---|---|---|
| MovieLens 100K/32M | rating count by numeric movie ID | static access-frequency proxy |
| UCI Online Retail I/II | completed positive-quantity order-row count by StockCode | static catalogue-frequency proxy |
| HetRec Last.fm/Delicious | reported play weights / distinct bookmark events | static popularity proxy |
| Wikimedia top pages | one pinned-day aggregated pageview count | static popularity-ranked sensitivity case |
| SOSD | sorted real-world keys | search-layout distribution only, not access frequency |

Raw data stays outside version control where redistribution terms require it.
Reproduction fetches the sources and verifies recorded hashes where supplied.

## C. Synthetic And Deterministic Cases

Synthetic data remains intentionally in three roles and must not be replaced by
unrelated public data:

- **proof and differential tests:** small exhaustive instances and adversarial
  witnesses establish correctness or a counterexample;
- **stress families:** uniform, Zipf, Dirichlet, hot-block, and alternating
  distributions isolate a structural assumption under a fixed seed;
- **operation traces derived from real frequencies:** some range/get/update
  benchmarks use deterministic draws after a real frequency vector is loaded.
  They are explicitly labelled `frequency_derived`, not real request logs.

Replacing these with an unlabeled public dataset would weaken the scientific
test: exact tests need known oracles, and controlled stress tests need one
variable to change at a time. Their proper improvement is clear labeling,
source code, fixed seeds, and negative cases, all of which are required here.

## Reproduction And Review

```bash
PYTHONPATH=. python3 generate_real_temporal_access.py
PYTHONPATH=. python3 verify_artifacts.py
```

For a review, verify the source hash in `data/external/manifest.json`, inspect
the real-trace JSON certificate, and use `docs/CLAIMS.md` for the exact scope
of each result. Do not promote a row from category B or C into category A.
