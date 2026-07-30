# Changelog

All notable changes are documented here. Scientific claim changes are also
recorded in [`docs/CLAIMS.md`](docs/CLAIMS.md).

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
