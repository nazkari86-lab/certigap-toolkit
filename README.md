# CertiGap Toolkit

[![CI](https://github.com/nazkari86-lab/certigap-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/nazkari86-lab/certigap-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

CertiGap is a toolkit for **budgeted robust partial search trees**.

Instead of fully refining the whole key space, CertiGap decides **how much order is worth materializing at all** when:

- the split budget is tight;
- access is skewed;
- the predicted query distribution may be wrong.

It ships with:

- an exact dynamic program for small and medium instances;
- an independent exact cost-cap dynamic program for cross-validation;
- a stronger beam-search heuristic for practical use;
- greedy and simple baseline solvers;
- lower bounds and certificate export;
- benchmark, counterexample, and report-generation pipelines;
- a C++ core plus Python bindings.
- a candidate-pruned C++ beam heuristic for large ordered workloads.

License:

- [MIT](LICENSE)

## Why Use It

Simple practitioner story:

> When memory or split budget is tight and access is skewed, CertiGap beats naive structures by spending structural effort only where queries are concentrated.

Good fits:

1. Skewed key-value lookup
2. Static hot/cold catalogs
3. Read-heavy embedded indexes

Less useful:

1. Fully uniform access
2. Highly dynamic insert/delete-heavy settings
3. Situations where a full high-quality index is cheap enough already

## Python API

```python
from certigap import CertiGapToolkit

model = CertiGapToolkit().fit(
    weights=[0.05, 0.10, 0.30, 0.55],
    budget=2,
    eta=0.15,
    solver="beam",
)

print(model.summary())
print(model.query_cost(4))
print(model.export_certificate())
print(model.compare_baselines())
```

Available solver modes:

- `exact`
- `cost_cap`
- `beam`
- `greedy`
- `balanced`
- `weighted`
- `binary_search`
- `learned_segment`

## Quick Start

Run the full project build:

```bash
PYTHONPATH=. python3 build_all.py
```

Run the test suite:

```bash
PYTHONPATH=. python3 -m unittest discover -s tests -v
```

Run the large-instance heuristic scaling benchmark (not part of fast CI):

```bash
PYTHONPATH=. python3 generate_scaling_benchmark.py --mode max --datasets all
```

This runs deterministic stress distributions and public observed-popularity
workloads from MovieLens, UCI Online Retail, and Wikimedia. Raw data is cached
locally; every result records URL, SHA-256, aggregation rule, and key ordering.
See [`docs/BENCHMARK_PROTOCOL.md`](docs/BENCHMARK_PROTOCOL.md) for limitations.

Build the C++ core:

```bash
PYTHONPATH=. python3 build_cpp_core.py
```

Run the C++ large-n scaling artifact:

```bash
PYTHONPATH=. python3 generate_cpp_scaling.py
```

Run the post-build C++ lookup-latency microbenchmark:

```bash
PYTHONPATH=. python3 generate_lookup_benchmark.py
```

## C++ Core And Bindings

The C++ shared library is built from:

- [`cpp/certigap_core.cpp`](cpp/certigap_core.cpp)

Python loads it through:

- [`certigap/cpp_bindings.py`](certigap/cpp_bindings.py)

Smoke-test example:

```python
from certigap.cpp_bindings import CppCertiGap

core = CppCertiGap()
result = core.fit([0.1, 0.2, 0.3, 0.4], budget=2, eta=0.15)
print(result["objective"])
```

## Example Use Cases

- [`examples/skewed_kv_lookup.py`](examples/skewed_kv_lookup.py)
- [`examples/static_hot_cold_catalog.py`](examples/static_hot_cold_catalog.py)
- [`examples/read_heavy_embedded_index.py`](examples/read_heavy_embedded_index.py)

## Main Results

Generated artifacts live in [`results/`](results):

- [`summary.md`](results/summary.md): beam vs greedy quality summary
- [`speed_quality_summary.md`](results/speed_quality_summary.md): solver quality/time tradeoff
- [`counterexamples.md`](results/counterexamples.md): automatically discovered greedy-failure cases
- [`certificate_examples.md`](results/certificate_examples.md): report-ready certificate examples
- [`scientific_validation.md`](results/scientific_validation.md): exact cross-validation, BnB trace, and theorem-family artifacts
- [`scaling_benchmark.md`](results/scaling_benchmark.md): median/p95 runtime and peak-memory scaling evidence
- [`benchmark_provenance.json`](results/benchmark_provenance.json): dataset source, checksum, aggregation, and measurement plan
- [`cpp_pruned_scaling.md`](results/cpp_pruned_scaling.md): C++ pruned-beam measurements through 100,000 keys
- [`cpp_lookup_latency.md`](results/cpp_lookup_latency.md): post-build lookup latency and routing-footprint microbenchmark
- [`pruning_validation.md`](results/pruning_validation.md): candidate-limit ablation against the exact oracle
- [`temporal_holdout.md`](results/temporal_holdout.md): early-to-late MovieLens shift evaluation

Figures live in [`figures/`](figures):

- [`mean_gaps.svg`](figures/mean_gaps.svg)
- [`mean_times.svg`](figures/mean_times.svg)

As of **Saturday, July 25, 2026**:

- `240` benchmark rows were analyzed in the main exact-referenced sweep;
- beam mean absolute objective gap vs exact is `0.0006` (`0.02%` mean relative gap);
- greedy mean absolute objective gap vs exact is `0.0986` (`2.80%` mean relative gap);
- beam strictly improves on greedy in `104` cases;
- beam matches exact in `237` of `240` cases.

The speed/quality summary is machine-specific and regenerated by the benchmark. On the current fast benchmark, beam is near-exact on the measured small cases but is not faster than exact there; the repository does not claim a measured crossover point.

## Reports

English package:

- [`report/ABSTRACT.md`](report/ABSTRACT.md)
- [`report/REPORT.md`](report/REPORT.md)
- [`report/APPENDIX.md`](report/APPENDIX.md)
- [`report/FORMAL_RESULTS.md`](report/FORMAL_RESULTS.md)
- [`report/POSTER_OUTLINE.md`](report/POSTER_OUTLINE.md)

Russian RKNP package:

- [`rknp_package/ABSTRACT_RU.md`](rknp_package/ABSTRACT_RU.md)
- [`rknp_package/REPORT_RU.md`](rknp_package/REPORT_RU.md)
- [`rknp_package/THESES_RU.md`](rknp_package/THESES_RU.md)
- [`rknp_package/SLIDES_RU.md`](rknp_package/SLIDES_RU.md)
- [`rknp_package/FORMAL_RESULTS_EN.md`](rknp_package/FORMAL_RESULTS_EN.md)

## Theory Notes

- [`docs/FORMAL_RESULTS.md`](docs/FORMAL_RESULTS.md)
- [`docs/PROOF_SKETCHES.md`](docs/PROOF_SKETCHES.md)
- [`docs/TECHNICAL_NOTE.md`](docs/TECHNICAL_NOTE.md)
- [`docs/GREEDY_COUNTEREXAMPLE_FAMILY.md`](docs/GREEDY_COUNTEREXAMPLE_FAMILY.md)
- [`docs/PRACTITIONER_GUIDE.md`](docs/PRACTITIONER_GUIDE.md)
- [`docs/TECHNICAL_BLOG.md`](docs/TECHNICAL_BLOG.md)
- [`docs/ARXIV_NOTE.md`](docs/ARXIV_NOTE.md)
- [`docs/COMPLEXITY.md`](docs/COMPLEXITY.md)
- [`docs/RELATED_WORK.md`](docs/RELATED_WORK.md)

## Project Status

This repository is a **reproducible research prototype and reusable toolkit**.

What is already done:

- exact solver
- independent cost-cap exact solver
- proof-carrying branch-and-bound for proof-sized instances
- beam heuristic
- baseline integrations
- `binary_search` is an unbudgeted full-reference line, not a budget-matched competitor
- certificates
- benchmarks
- counterexample search
- C++ core + Python bindings
- report generation
- independent structural and certificate-arithmetic verifier
- systematic small-instance exact validation and Python/C++ reference equivalence checks
- a proved infinite family with an unbounded absolute gap for one-step greedy

Current limits and open research work:

- stronger approximation or structural theorems beyond the current package.
- large-scale performance evidence beyond the documented synthetic benchmark range.
- external or machine-assisted formal review of the written proofs.
- approximation guarantees for the candidate-pruned C++ heuristic.

## Repository Map

See [`FINAL_INDEX.md`](FINAL_INDEX.md) for a full index of the package.
