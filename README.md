# CertiGap Prototype

Research prototype for a high-potential informatics project:

- exact frontier dynamic programming for the budgeted partial search-tree problem;
- greedy baseline and stronger beam-search heuristic for larger instances;
- brute-force oracle for tiny instances;
- two simple baselines;
- independent structural checker that validates a candidate tree, recomputes its cost, and attaches lower bounds plus certified gaps;
- synthetic benchmark script.

## Toolkit Story

CertiGap is now usable as a small toolkit, not only as paper code.

Simple practitioner story:

> when memory or split budget is tight and access is skewed, CertiGap beats naive structures by spending structure only where queries are concentrated.

Main use cases:

1. skewed key-value lookup;
2. static hot/cold catalogs;
3. read-heavy embedded indexes.

Examples:

- [skewed_kv_lookup.py](/Users/dulatnurlanuly/Downloads/certigap-prototype/examples/skewed_kv_lookup.py)
- [static_hot_cold_catalog.py](/Users/dulatnurlanuly/Downloads/certigap-prototype/examples/static_hot_cold_catalog.py)
- [read_heavy_embedded_index.py](/Users/dulatnurlanuly/Downloads/certigap-prototype/examples/read_heavy_embedded_index.py)

Python API:

```python
from certigap import CertiGapToolkit

model = CertiGapToolkit().fit(
    weights=[0.05, 0.10, 0.30, 0.55],
    budget=2,
    eta=0.15,
    solver="beam",
)

print(model.query_cost(4))
print(model.export_certificate())
print(model.compare_baselines())
```

Available solver modes:

- `exact`
- `beam`
- `greedy`
- `balanced`
- `weighted`
- `binary_search`
- `learned_segment`

## Model

Keys are ranks `1..n`. A split node stores a threshold `k` and asks `x <= x_k?`.
Each leaf is an unresolved interval `[l, r]` with fallback cost `ceil(log2(|I|))`.

For a tree `T`:

- `average_cost(T) = sum_i p_i * C_T(i)`
- `max_cost(T) = max_i C_T(i)`
- `objective(T) = (1 - eta) * average_cost(T) + eta * max_cost(T)`

The prototype computes the exact Pareto frontier `(average_cost, max_cost)` for each interval and budget, then picks the best point for a chosen `eta`.

## What Is New In This Full Build

- `frontier_dp_best`: exact optimizer for a fixed split budget;
- `greedy_best`: simple one-step local baseline;
- `beam_search_best`: stronger multi-step heuristic that can keep temporarily worse trees if they lead to better later allocations;
- `heuristic_best`: exact on small instances, beam search otherwise;
- `combined_lower_bound`: entropy + Lagrangian lower bounds;
- `certify_tree`: structural validation plus `upper_bound`, `lower_bound`, `certified_gap`, and exact gap on small instances.

## Run

```bash
cd /Users/dulatnurlanuly/Downloads/certigap-prototype
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 benchmark.py
PYTHONPATH=. python3 run_experiments.py
PYTHONPATH=. python3 generate_results.py
PYTHONPATH=. python3 analyze_experiments.py
PYTHONPATH=. python3 generate_speed_quality.py
PYTHONPATH=. python3 build_report.py
PYTHONPATH=. python3 build_rknp_package.py
PYTHONPATH=. python3 generate_counterexamples.py
PYTHONPATH=. python3 build_cpp_core.py
PYTHONPATH=. python3 generate_figures.py
PYTHONPATH=. python3 build_all.py
```

## Results Artifacts

Generated files land in `/Users/dulatnurlanuly/Downloads/certigap-prototype/results`:

- `experiment_sweep.csv`: exact/greedy/beam/baseline values over a fixed grid;
- `summary.md`: aggregated beam-vs-greedy summary for the report;
- `certificate_examples.md`: report-ready certified examples.
- `speed_quality.csv` and `speed_quality_summary.md`: timing and quality tradeoff across different task families.
- `counterexamples.csv` and `counterexamples.md`: automatically discovered greedy-failure instances.

Generated files land in `/Users/dulatnurlanuly/Downloads/certigap-prototype/figures`:

- `mean_gaps.svg`
- `mean_times.svg`

Generated files land in `/Users/dulatnurlanuly/Downloads/certigap-prototype/report`:

- `ABSTRACT.md`: concise contest abstract built from real metrics;
- `REPORT.md`: main report draft assembled from docs plus generated results;
- `APPENDIX.md`: certificate examples and roadmap;
- `FORMAL_RESULTS.md`: formal theorem writeup for Theorem A and Theorem B;
- `POSTER_OUTLINE.md`: report-ready poster structure.

Generated files land in `/Users/dulatnurlanuly/Downloads/certigap-prototype/rknp_package`:

- `ABSTRACT_RU.md`: русская аннотация;
- `REPORT_RU.md`: русскоязычный черновик отчёта;
- `THESES_RU.md`: тезисы для защиты;
- `SLIDES_RU.md`: план слайдов.

For a one-command rebuild of the whole project package, run:

```bash
cd /Users/dulatnurlanuly/Downloads/certigap-prototype
PYTHONPATH=. python3 build_all.py
```

## Scope limits

This is a prototype, not a full paper implementation:

- no full large-scale experimental harness yet;
- no advanced repair heuristic for big `n`;
- synthetic benchmarks only.
