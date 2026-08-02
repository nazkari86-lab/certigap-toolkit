# Changelog

All notable changes are documented here. Scientific claim changes are also
recorded in [`docs/CLAIMS.md`](docs/CLAIMS.md).

## Unreleased

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
