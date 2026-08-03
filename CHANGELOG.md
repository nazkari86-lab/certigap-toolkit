# Changelog

All notable changes are documented here. Scientific claim changes are also
recorded in [`docs/CLAIMS.md`](docs/CLAIMS.md).

## Unreleased

- Harden the official YCSB/RocksDB path with a runnable binary distribution,
  Python 3 launcher support, native-build/cross-runtime Docker stages, explicit
  amd64 execution for the pinned RocksDB JNI, resumable workloads, compact raw
  metrics, provenance hashes, database cleanup, and optional Docker VM reclaim.
- Reject invalid numeric parameters, insufficient host disk, worker exceptions,
  error returns, zero throughput, incomplete operation counts, and incomplete
  A/B/C/D/F result sets instead of accepting a successful container exit code.
- Record that the local full-scale attempt was storage-blocked and is not
  performance evidence; no partial YCSB result is committed.

## 1.16.0 - 2026-08-03

- Add the proof-carrying ordered-map delta layer with insert, update, erase,
  inclusive key ranges, deterministic compaction, strict mutation
  preconditions, and an independently implemented full-history replay verifier.
- Add a 12-case `sum/min/max` delta matrix over four compaction thresholds,
  rehashed semantic-tamper rejection, and a committed example certificate.
- Add an 80-row SOSD-derived native benchmark over all four downloaded 200M
  distributions, deterministic rank sampling, correctness checks, build and
  memory fields, STL/Eytzinger/guarded-interpolation baselines, and official
  pinned SOSD RadixSpline. CertiGap beats `std::lower_bound` in `10/16` cases,
  while RadixSpline and Eytzinger are fastest in `9` and `7` cases.
- Add a pinned one-command official YCSB/RocksDB container protocol. No YCSB
  result is claimed because the local Docker daemon was unavailable.

## 1.15.0 - 2026-08-01

- Add the proof-carrying typed DSL with canonical `sum`, `min`, and `max`
  capability laws, a complete eight-design grammar, strict operation/resource
  contracts, deterministic C++17 generation, and independent replay.
- Add `certigap-dsl compile/verify`, unified CLI verification/explanation, a
  strict JSON schema, rehashed-tamper tests, and generated-header execution.
- Add a provenance-checked 36-case matrix over three algebras, four operation
  contracts, and three resource regimes. All cases verify grammar completeness
  and match a list oracle over 160 replay operations.

- Add `ConcurrentPrefixIndex` with an authoritative Fenwick core, immutable
  Prefix snapshots, bounded versioned update log, `O(n+u)` catch-up rounds,
  atomic publication/invalidation, epoch-delayed reclamation, and explicit
  asynchronous rebuild lifecycle.
- Add `SnapshotReadView` to amortize read-side epoch entry across a versioned
  batch, platform lock-free-atomic introspection, memory-budget rejection, and
  fail-closed behavior when a retained view or journal gap prevents publication.
- Add ASan/UBSan and ThreadSanitizer concurrency validation plus a 48-row native
  benchmark with checksums and provenance. On this machine, immutable per-call
  snapshots are `3.14x` median faster than locked Fenwick fallback and unchecked
  batched views cost `1.46x` median versus direct Prefix.

- Add direct native runtime dispatch, checked and unchecked hot paths, separated
  `hot_*` data-plane operations with externally sampled `observe_sample()`
  control, and deferred specialist activation through explicit `maintenance()`.
- Add dynamic `FrozenTrackingIndex` and compile-time
  `StaticTrackingIndex<Backend, Aggregate>` deployment. In the paired
  50,000-operation benchmark, checked static Fenwick records `1.01x` median and
  `1.23x` maximum latency versus direct Fenwick.
- Add a 448-row paired hot-path benchmark, alternating candidate/baseline order,
  seven repetitions, checksum validation, source/header hashes, and mandatory
  artifact auditing. Full automatic Fast tracking now records `1.21x` median,
  `1.59x` p95, and `1.90x` maximum overhead versus Fenwick.

- Add `FastTrackingAutoIndex`, a sampled epoch controller with precomputed cost
  tables, directed target rebuild costs, minimum residence, stable-workload
  leases, and an always-current Fenwick/segment-tree shadow for immediate safe
  fallback. The expanded direct-dispatch implementation and current 384-row
  runtime artifact supersede the initial overhead measurements.
- Expand native randomized ASan/UBSan validation from 24,000 to 48,000
  operations, including sum/min/max Fast-mode differential tests, phase
  fallback, policy rejection, generated single-header compilation, and
  benchmark provenance verification.

- Add header-only native C++17 `TrackingAutoIndexCpp` with batched WFA
  execution, real backend rebuilds, reusable scratch buffers, optional audit
  history, exact K-switch/unrestricted oracles, metric validation, and explicit
  fail-closed theorem boundaries for directed migration matrices.
- Add a rebuild-aware symmetric migration metric, 24,000-operation randomized
  ASan/UBSan validation, Python/C++ structural-cost differential tests, and a
  reproducible matching runtime benchmark. Native production is
  `113.2x-13053.2x` faster than Python tracking on the recorded streams while
  remaining `13.1x` median slower than the fastest fixed C++ backend.

- Add causal `TrackingAutoIndex` using the Work Function Algorithm, real
  backend migration, exact K-switch and unrestricted offline oracles,
  independently replayed certificates, CLI support, exhaustive path tests,
  and a 15-scenario phase-shift validation matrix.
- Add a 126-configuration maximum tracking comparison against four online/static
  policies, every feasible fixed backend, exact K-switch/unrestricted oracles,
  and a 90-row checksum-validated Python timing audit; remove repeated manifest
  verification and topology preparation from the migration hot path.

- Expand Certified AutoIndex from five to eight executable candidates with
  prefix sums, square-root decomposition, and sparse tables.
- Add Python and generated C++17 runtimes, calibrated cost fields, capability
  filtering, complete-portfolio replay verification, and cross-language tests
  for the new backends.
- Upgrade selection artifacts to `certigap-autoindex-v2` and regenerate the
  24-scenario validation matrix with 192 candidate rows.
- Add Safe AutoIndex with train/validation/test isolation, a one-sided
  Hoeffding no-regression gate, build/migration amortization, conventional
  fallback, independently replayed certificates, and a 16-case validation
  matrix.
- Add Sequential SafeAutoIndex with alpha-spending Hoeffding confidence
  sequences, first-crossing replay verification, optional-stopping diagnostics,
  strict JSON compilation, and deployment-specific C++17 output.
- Add Martingale SafeAutoIndex with mixture Hoeffding e-process deployment,
  post-deployment harm revocation, replayed lifecycle events, adapted-null
  diagnostics, strict compilation, and C++17 baseline restoration.
- Add a Python-free SQLite loadable C++ extension, installed build command,
  connection-local lifecycle registry, strict SQL validation, CMake option,
  and real SQLite CLI integration tests.
- Add the `certigap_vtab` SQLite virtual table with planner-visible equality
  and range strategies, inclusive range-sum pushdown, durable shadow storage,
  mutations, rollback/savepoints, reconnect, and two-process WAL validation.
- Add zero-based `adaptive_array<T>` with automatic profiling, configurable
  warmup/drift checks, fail-closed modeled-improvement threshold, strict
  cross-run profile persistence, explicit-maintenance mode, and explanations.
- Add the zero-based Python `AdaptiveArray` over the complete eight-candidate
  portfolio, bounded profiles, atomic cross-run warm starts, thread-safe public
  operations, deterministic lifecycle validation, and `pkg-config` metadata.
- Expand the standalone C++ runtime from five to all eight executable AutoIndex
  candidates, including capability/resource models and native oracle coverage.
- Add declarative fixed-size `AdaptiveSpec` contracts plus paired measured
  baseline/candidate replay, migration amortization, a bounded-harm Hoeffding
  gate, digest-protected artifacts, and an independent decision verifier.

## 1.10.1 - 2026-07-30

- Make installed `certigap reproduce` discover a source checkout from the
  working directory or `CERTIGAP_SOURCE_ROOT`.
- Add a regression test for the installed-CLI Docker execution path.

## 1.10.0 - 2026-07-30

- Add the unified `certigap` CLI with compile, verify, explain, calibrate,
  include-dir, and reproduction commands.
- Add artifact auto-detection and fail-closed verification for all
  self-describing artifact families.
- Add a standalone Rust verifier for candidate-pruned C++ artifacts and a
  solver-independent Python replay implementation.
- Add certified entropy/max-cost lower bounds to the scalable C++ path and
  publish large-instance upper/lower intervals instead of bare heuristic
  scores.
- Replace floating-point CertiGap-H DP comparisons with deterministic
  fixed-point score units.
- Add a real in-memory SQLite application pilot with five YCSB-compatible
  operation mixes, repeated measurements, checksums, and bootstrap intervals.
- Add a pinned Lean 4 kernel proof for safe fixed-point Pareto pruning.
- Add a versioned scientific claim register and explicit forbidden claims.
- Add portable CI, Windows header compilation, sanitizer validation, Ruff,
  Docker reproduction, and citation metadata.

## 1.9.0 - 2026-07-30

- Add CertiGap-H, an exact representation-aware two-level prefix synthesis
  path.
- Add independent complete-frontier replay and runtime oracle validation.
- Add an 11-scenario native train/holdout benchmark with explicit temporal
  shift and frequency-derived public workloads.
- Publish wheel, source archive, and manuscript artifacts with SHA-256
  digests.

Earlier releases are available from the repository's GitHub Releases page.
