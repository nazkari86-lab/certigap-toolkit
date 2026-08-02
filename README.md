# CertiGap Toolkit

[![CI](https://github.com/nazkari86-lab/certigap-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/nazkari86-lab/certigap-toolkit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

CertiGap is a toolkit for **certified workload-adaptive synthesis and selection
of ordered in-memory structures**.

The precise claim register is [`docs/CLAIMS.md`](docs/CLAIMS.md). Certificates
prove results only inside their declared structural grammar or candidate
portfolio; native timings are separate machine-specific evidence. Exact
reproduction roles and commands are in
[`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

CertiGap-X can synthesize a new variable-block aggregate index instead of
selecting only a named backend. Its exact dynamic program and independent
verifier cover every legal partition in the declared grammar; see
[`docs/SYNTHESIS.md`](docs/SYNTHESIS.md).
CertiGap-H adds a representation-aware two-level prefix layout. Its exact
compiler optimizes range-boundary separation and update suffix work; the
independent verifier reconstructs the full legal frontier. See
[`docs/HYBRID.md`](docs/HYBRID.md).

Sequential SafeAutoIndex supports continuous validation inspection without
invalid repeated use of a fixed-time interval. It records and replays the first
alpha-spending Hoeffding crossing; see
[`docs/SEQUENTIAL_SAFE_AUTOINDEX.md`](docs/SEQUENTIAL_SAFE_AUTOINDEX.md).
Martingale SafeAutoIndex adds mixture e-process deployment and revocation for
bounded adapted observations under declared conditional-mean nulls; see
[`docs/MARTINGALE_SAFE_AUTOINDEX.md`](docs/MARTINGALE_SAFE_AUTOINDEX.md).
An actual SQLite loadable extension exposes adaptive C++ indexes through SQL.
Its `certigap_vtab` module adds planner-visible key constraints, durable shadow
storage, transactions, and mutations with no Python runtime; see
[`docs/SQLITE_EXTENSION.md`](docs/SQLITE_EXTENSION.md).

The easiest C++ mode is one header:

```cpp
#include "certigap.hpp"

certigap::Index index(values);
index.observe_range(1, 10, 100);
index.optimize();
auto answer = index.range_query(1, 10);
```

It runs in any C++17 environment without Python. See
[`docs/ADAPTIVE_CPP.md`](docs/ADAPTIVE_CPP.md).

The lowest-friction adaptive mode needs no manual observations or selection:

```cpp
certigap::AutoTunePolicy policy;
policy.profile_path = "catalog.profile";
certigap::adaptive_array<double> data(values, policy);

auto answer = data.range_sum(10, 40); // Zero-based [10,40).
std::cout << data.explain() << '\n';
```

Profiles survive restarts, weak modeled migrations fail closed, and automatic
maintenance can be disabled for latency-critical paths. See
[`docs/ADAPTIVE_ARRAY.md`](docs/ADAPTIVE_ARRAY.md).

The same zero-configuration path is available in Python over the complete
eight-candidate portfolio:

```python
from certigap import AdaptiveArray, AdaptiveArrayPolicy

data = AdaptiveArray(
    range(1_000),
    policy=AdaptiveArrayPolicy(warmup_operations=256),
)
answer = data.range_sum(10, 40)  # Zero-based [10, 40).
print(answer, data.explain())
```

See [`docs/PYTHON_ADAPTIVE_ARRAY.md`](docs/PYTHON_ADAPTIVE_ARRAY.md).

For an explicit operation/resource contract and measured fail-closed rollout:

```python
from certigap import (
    AdaptiveSpec,
    MeasuredDeploymentPolicy,
    compile_measured_autoindex,
)

spec = AdaptiveSpec(
    operations=("get", "range", "update"),
    memory_limit_slots=50_000,
)
index = compile_measured_autoindex(
    values,
    training_trace,
    independent_validation_trace,
    spec,
    policy=MeasuredDeploymentPolicy(alpha=0.05, repetitions=64),
)
print(index.explain())
```

The candidate executes only when its paired bounded-harm upper bound passes;
otherwise the conventional baseline remains active. See
[`docs/MEASURED_DEPLOYMENT.md`](docs/MEASURED_DEPLOYMENT.md).

Representation-aware Python compilation:

```python
from certigap import HybridConstraints, WorkloadTrace, compile_hybrid_index

trace = WorkloadTrace(256)
for _ in range(900):
    trace.add_range(1, 80)
for key in range(1, 101):
    trace.add_update(key, float(key))

index = compile_hybrid_index(
    range(256),
    trace,
    constraints=HybridConstraints(max_blocks=16, max_block_width=64),
)
print(index.selected_boundaries)
print(index.range_query(1, 80))
```

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
- a C++ core plus Python bindings;
- a candidate-pruned C++ beam heuristic for large ordered workloads.
- AutoDRO selection across budgets, solvers, and executable fallbacks.
- direct TV-DRO exhaustive optimization with global small-instance guarantees;
- scalable anytime TV-DRO Branch-and-Bound with independently verified gaps;
- version 2 artifacts with deterministic portfolio regeneration;
- cumulative, decayed, and sliding-window adaptation policies;
- distribution-drift regret certificates for rebuild decisions.
- Dynamic CertiRange point/range/update indexes with persistent snapshots.
- range-aware workload optimization with independently replayed artifacts.
- contiguous-node C++ range benchmarks against Fenwick and segment trees.
- Certified AutoIndex selection across array, Fenwick, segment tree, and two
  workload-adaptive CertiRange variants.
- Optional-stopping-safe sequential deployment over the complete eight-backend
  portfolio, with fail-closed conventional fallback.
- Adapted-data e-process deployment plus post-deployment harm revocation with
  separately controlled false-decision risks.
- Zero-based `adaptive_array<T>` with automatic warmup, deployment threshold,
  explicit-maintenance mode, cross-run profiles, and one-line explanations.
- SQLite `sqlite3_load_extension` integration for SQL build/get/range/update/
  optimize lifecycle operations.
- Planner-native `certigap_vtab` with equality/range `xBestIndex` strategies,
  durable reconnect, rollback/savepoint support, and serialized WAL writers.
- CertiGap-H `O(1)` range sums with exact representation-aware partition
  synthesis and a train-only native backend tuner.

License:

- [MIT](LICENSE)

## Why Use It

Simple practitioner story:

> When memory or split budget is tight and access is skewed, CertiGap beats naive structures by spending structural effort only where queries are concentrated.

Here, "naive" means untuned or linearly scanned alternatives. It does not mean
Fenwick or segment trees: the compiler keeps those classical candidates when
they are faster.

Native evidence is workload-specific: CertiGap-H beats Fenwick in `9/11`
committed scenarios, while Fenwick wins the `30%` and `50%` update cases and a
global prefix array is usually strongest when reads dominate.

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

## AutoDRO API

Use query counts rather than manually choosing one structure:

```python
from certigap import CertiGapAutoDRO, ExecutionCostModel

cost_model = ExecutionCostModel.from_samples(
    routing_samples=[2.8, 2.9, 3.0],
    fallback_samples=[4.1, 4.0, 4.2],
    cost_unit="ns",
)

model = CertiGapAutoDRO().fit(
    counts=[1200, 430, 90, 20, 4],
    max_budget=4,
    confidence=0.95,
    memory_limit_bytes=4096,
    cost_model=cost_model,
)

print(model.summary())
print(model.estimated_query_cost(1))
artifact = model.export_selection_artifact()

# Rebuild only after a material empirical distribution shift.
model.update_window(
    window_counts=[1100, 500, 120, 30, 5],
    min_tv_drift=0.05,
)
```

AutoDRO enumerates the configured portfolio, rejects candidates above the
memory limit, evaluates each candidate exactly over a total-variation ambiguity
ball, and returns the minimum verified portfolio score. It does not claim
global optimality outside that portfolio for large instances. For
`n <= direct_tv_limit`, it exhaustively enumerates every feasible partial tree
and provides a global TV-DRO optimum over the configured fallbacks. See
[`docs/AUTODRO.md`](docs/AUTODRO.md).

## Anytime TV-DRO API

For larger tree spaces, request bounded search and retain a valid optimality
interval:

```python
from certigap import anytime_tv_branch_and_bound, verify_anytime_tv_certificate

result = anytime_tv_branch_and_bound(
    weights=[1200, 430, 90, 20, 4, 2, 1],
    budget=4,
    tv_radius=0.1,
    max_expansions=5_000,
    target_relative_gap=0.02,
)

print(result["score"])               # feasible upper bound
print(result["global_lower_bound"])  # admissible lower bound
print(result["relative_gap"])
print(verify_anytime_tv_certificate(result["certificate"]))
```

The solver combines componentwise TV, entropy, and conditional-entropy lower
bounds. A zero gap proves global optimality for the declared objective and
constraints; a nonzero gap remains an unresolved interval. See
[`docs/ANYTIME_TV.md`](docs/ANYTIME_TV.md).

## Dynamic CertiRange API

Compile a full range index from point, range, and update workload counts:

```python
from certigap import CertiRangeWorkload

workload = CertiRangeWorkload(32)
workload.add_point(1, 1000)
workload.add_range(1, 10, 500)
workload.add_update(2, 100)

index = workload.compile(
    values=list(range(32)),
    budget=6,
    eta=0.10,
    aggregate="sum",       # sum, min, or max
    max_depth=10,
    routing="range_aware",
)

snapshot = index.snapshot()
index.point_update(2, 1000)

print(index.get(1))
print(index.range_query(1, 10))
print(snapshot.get(2))     # immutable pre-update view
print(index.export_certificate())
```

The range-aware solver evaluates mixed-trace node visits rather than only an
endpoint proxy. Its balanced candidate is always retained, but large-instance
beam results are not claimed globally optimal. See
[`docs/DYNAMIC_RANGE.md`](docs/DYNAMIC_RANGE.md).

## Certified AutoIndex API

Compile the best feasible executable structure from one fixed portfolio:

```python
from certigap import AutoIndexConstraints, WorkloadTrace, compile_autoindex

trace = WorkloadTrace(32)
for _ in range(100):
    trace.add_range(3, 30)

index = compile_autoindex(
    range(32),
    trace,
    constraints=AutoIndexConstraints(
        aggregate="sum",
        budget=4,
        memory_limit_slots=128,
        fenwick_unit_cost=0.8,  # optional measured backend calibration
    ),
)

print(index.summary())
print(index.range_query(3, 30))
print(index.export_selection_artifact())
```

The artifact retains all eight candidates and their infeasibility reasons. An
independent verifier regenerates the portfolio and proves that the selected
candidate has minimum declared training score. Chronological holdout is
evaluation-only. Default structural visits are not presented as nanoseconds;
per-backend unit costs can be calibrated from target measurements. See
[`docs/AUTOINDEX.md`](docs/AUTOINDEX.md) and the objective
[`portfolio expansion policy`](docs/PORTFOLIO_EXPANSION.md).

## Safe AutoIndex

Add a no-regression deployment gate with separate training, validation, and
evaluation traces:

```python
from certigap import SafeSelectionPolicy, compile_safe_autoindex

safe = compile_safe_autoindex(
    values,
    train_trace,
    validation_trace,
    test_trace=test_trace,
    policy=SafeSelectionPolicy(
        confidence_alpha=0.05,
        horizon_operations=1_000_000,
        migration_cost_units=500.0,
    ),
)
print(safe.summary())
```

Specialization is deployed only when a one-sided bounded-sample confidence
limit remains better than the declared conventional baseline after amortized
build and migration cost. Otherwise selection fails closed to that baseline.
The guarantee is conditional on independent IID validation operations and the
declared structural model, not portable latency or arbitrary drift. See
[`docs/SAFE_AUTOINDEX.md`](docs/SAFE_AUTOINDEX.md).

For C++ deployment:

```bash
certigap safe-compile safe_trace.json \
  --artifact build/safe-selection.json \
  --header build/safe-index.hpp
```

## C++ Compiler Integration

Compile a strict JSON trace into a verified artifact and C++17 header:

```bash
certigap compile trace.json \
  --artifact build/selection.json \
  --header build/generated_index.hpp

certigap verify build/selection.json
certigap explain build/selection.json
certigap include-dir
```

The unified CLI auto-detects AutoIndex, CertiGap-X, CertiGap-H, Dynamic
CertiRange, range-optimizer, AutoDRO, and anytime-TV artifacts. Verification
fails closed for unknown schemas or modified digests. The legacy
`certigap-compile` and `certigap-calibrate` commands remain supported.

Large-instance C++ beam artifacts additionally have a solver-independent Rust
verifier:

```bash
cargo build --release --manifest-path rust-verifier/Cargo.toml
rust-verifier/target/release/certigap-verifier \
  results/pruned_beam_certificate_example.json
```

See [`docs/RUST_VERIFIER.md`](docs/RUST_VERIFIER.md).

A real SQLite application-level pilot covers YCSB-compatible A/B/C/F mixes and
a range-heavy workload with raw repetitions, checksum agreement, and bootstrap
confidence intervals:

```bash
PYTHONPATH=. python3 benchmarks/sqlite_ycsb.py --mode quick
```

It is explicitly not presented as the official Java YCSB harness or as a
portable performance result. See
[`results/sqlite_ycsb_pilot.md`](results/sqlite_ycsb_pilot.md).

Build and use the planner-visible virtual table:

```bash
certigap-sqlite-build --output certigap.so
sqlite3 catalog.db
```

```sql
.load ./certigap.so
CREATE VIRTUAL TABLE catalog USING certigap_vtab;
INSERT INTO catalog(key, value) VALUES (1, 10), (2, 20), (5, 50);
SELECT value FROM catalog WHERE key = 2;
SELECT range_sum FROM catalog WHERE key = 1 AND right_key = 5;
```

The virtual table uses inclusive key ranges. Its shadow table is durable and
SQLite transactions remain the source of truth; see
[`results/sqlite_vtab_validation.md`](results/sqlite_vtab_validation.md).

The generated `Index` exposes `get`, `range_query`, `point_update`, and
`snapshot`. Selection is resolved at C++ compile time. A complete buildable
CMake project is available in
[`examples/cmake_autoindex`](examples/cmake_autoindex); see
[`docs/COMPILER_INTEGRATION.md`](docs/COMPILER_INTEGRATION.md).

Installed header-only builds also expose `pkg-config` metadata:

```bash
c++ -std=c++17 main.cpp $(pkg-config --cflags certigap) -o app
```

For simpler runtime selection without generated files, use the standalone
[`cpp/certigap.hpp`](cpp/certigap.hpp). It profiles normal operations,
supports explicit warmup observations, returns all eight candidate reports,
and performs opt-in TV-drift reoptimization.

## Quick Start

Run the tests through the installed command:

```bash
certigap reproduce --mode tests
```

Verify every committed scientific artifact:

```bash
certigap reproduce --mode artifacts
```

Run a complete source-checkout rebuild:

```bash
certigap reproduce --mode full --benchmark-mode max
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

Run the distribution-shift selection benchmark:

```bash
PYTHONPATH=. python3 generate_autodro_benchmark.py
```

Run the exact generalized model with executable midpoint-binary fallback:

```python
from certigap import generalized_frontier_dp_best

result = generalized_frontier_dp_best(
    weights=[5, 2, 20, 3, 1],
    budget=2,
    eta=0.15,
    fallback="midpoint_binary",
)
```

See [`GENERALIZED_FALLBACK.md`](docs/GENERALIZED_FALLBACK.md) for Theorem E
and the exact relationship to classical alphabetic trees.

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
- [`examples/anytime_certified_search.py`](examples/anytime_certified_search.py)
- [`examples/online_regret_certificate.py`](examples/online_regret_certificate.py)
- [`examples/dynamic_certirange.py`](examples/dynamic_certirange.py)

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
- [`autodro_shift.md`](results/autodro_shift.md): fair TV-vs-nominal tuned-portfolio ablation
- [`direct_tv_validation.md`](results/direct_tv_validation.md): complete-tree-space validation and strict separation witness
- [`uncertainty_validation.md`](results/uncertainty_validation.md): 3,000 finite-sample i.i.d. coverage trials
- [`online_adaptation.md`](results/online_adaptation.md): drift-threshold rebuild/regret simulation
- [`dynamic_range_benchmark.md`](results/dynamic_range_benchmark.md): Python point/range/update baselines
- [`cpp_dynamic_range.md`](results/cpp_dynamic_range.md): C++ mixed traces against Fenwick and segment tree
- [`range_optimizer_validation.md`](results/range_optimizer_validation.md): exact-oracle and scaling validation
- [`anytime_validation.md`](results/anytime_validation.md): exact-oracle and scalable certified-gap trajectories
- [`synthesis_native_latency.md`](results/synthesis_native_latency.md): train-only structure selection and native C++ holdout latency
- [`synthesis_native_latency_metadata.json`](results/synthesis_native_latency_metadata.json): compiler, source hashes, seeds, public-data derivation, and limitations
- [`hybrid_validation.md`](results/hybrid_validation.md): exact representation-aware frontier and best-uniform ablation
- [`hybrid_certificate_example.json`](results/hybrid_certificate_example.json): independently replayable CertiGap-H certificate

Figures live in [`figures/`](figures):

- [`mean_gaps.svg`](figures/mean_gaps.svg)
- [`mean_times.svg`](figures/mean_times.svg)

As of **Wednesday, July 29, 2026**:

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
- globally exact direct TV-DRO search on exhaustively enumerable instances
- complete v2 portfolio manifests and omission-resistant verification
- fair tuned TV-vs-nominal distribution-shift ablation
- scalable anytime TV-DRO search with replay-verified optimality intervals
- conditional-entropy lower bounds and drift-regret certificates
- YCSB-inspired read-only C++ lookup workloads

Current limits and open research work:

- tighter scalable bounds for strongly skewed large instances.
- official YCSB or a RocksDB plugin plus independent hardware runs.
- external or machine-assisted formal review of the written proofs.
- approximation guarantees for the candidate-pruned C++ heuristic.

## Repository Map

See [`FINAL_INDEX.md`](FINAL_INDEX.md) for a full index of the package.
