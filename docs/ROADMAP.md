# Roadmap

## Phase 1: Core Correctness

- exact frontier DP
- brute-force oracle
- checker
- lower bounds
- tests for exactness and validity

## Phase 2: Certified Evaluation

- benchmark tables on tiny and medium cases
- gap histograms
- failure cases for greedy and balanced baselines
- wrong-prediction experiments

## Phase 3: Strongest Theory Layer

- Theorems A and B proof drafts
- Theorem C proved infinite greedy counterexample family
- independent cost-cap DP and proof-carrying branch-and-bound

## Phase 4: Competition Package

- abstract
- report
- poster
- slide deck
- appendix with checker format and reproducibility instructions

## Phase 5: Direct TV-DRO And Complete Artifacts

- exhaustive direct TV optimization for proof-sized instances
- complete tree-space theorem and strict Huber-portfolio separation witness
- version 2 manifest with deterministic portfolio regeneration
- fair tuned TV-versus-nominal benchmark
- temporal, finite-sample coverage, and online rebuild-threshold validation

## Phase 6: Scalable Certified Robust Search

- best-first anytime TV-DRO Branch-and-Bound
- componentwise, entropy, and conditional-entropy lower bounds
- independently replayed frontier and optimality-gap certificate
- exact-oracle agreement and monotone scaling trajectories
- formal online TV-drift regret bound
- YCSB-inspired post-build C++ lookup workloads

## Phase 7: Dynamic CertiRange

- complete ordered point/range/update API
- sum, minimum, and maximum monoids
- persistent immutable snapshots
- deterministic maximum-depth enforcement
- drift-triggered structural rebuilding
- declarative mixed-workload compiler
- range-aware beam with exact trace evaluator
- independent structural and optimizer certificates
- complete small-space oracle validation
- Python and contiguous-node C++ benchmarks against Fenwick and segment tree

## Phase 8: Certified AutoIndex

- executable array, Fenwick, segment-tree, and CertiRange portfolio
- sum, minimum, and maximum capability filtering
- memory, depth, and persistent-snapshot constraints
- deterministic training-only selection and stable tie-breaking
- chronological holdout without selection leakage
- omission-resistant complete-portfolio artifacts
- independent candidate regeneration and tamper tests
- 120-row temporal and constraint validation matrix

## Phase 9: Profile-Guided C++ Compilation

- strict versioned JSON trace schema
- installed `certigap-compile` CLI
- independently verified artifact before code generation
- deterministic C++17 header generation
- compile-time backend and aggregate selection
- emitted complete CertiRange topology
- reusable array, Fenwick, segment-tree, and CertiRange runtime
- source-checkout and installed-package CMake integration
- cross-language sum/min/max/update/snapshot tests
- 24-row deterministic code-generation validation

## Phase 10: Single-Header Adaptive C++

- one standalone `certigap.hpp`
- no Python or generated-file requirement
- tracked operations and explicit profile warmup
- array, Fenwick, segment-tree, and two CertiRange runtime candidates
- sum, minimum, maximum, updates, ranges, and isolated snapshots
- deterministic five-row leaderboard
- opt-in TV-drift reoptimization without hidden query latency
- root CMake target, install export, `find_package`, and FetchContent
- native 24-row validation plus online-compiler example

## Phase 11: Certified Structure Synthesis

- exact synthesis of unequal contiguous aggregate blocks;
- target-hardware primitive calibration;
- independent regeneration of every DP frontier candidate;
- deterministic C++17 configuration export;
- amortized migration gate with an explicit confidence margin;
- exhaustive small-space and best-uniform-block ablations.

Completed in `v1.7.0`. Learned routing, storage-engine integration,
concurrency, and independently reproduced wall-clock gains remain external.

## Phase 12: Native Transfer Audit

- train-only partition selection and separately seeded holdout timing;
- identical C++ operations and checksum oracle across five implementations;
- skew, uniform, adversarial-boundary, temporal-shift, and three public
  frequency-derived scenarios;
- median, nearest-rank p95, MAD, memory slots, compiler and source hashes;
- explicit negative result: Fenwick wins every committed range-sum scenario;
- fail-safe deployment rule retaining the classical AutoIndex candidate.

Completed in `v1.8.0`. Independent machines, production traces, concurrency,
storage integration, and a pre-registered domain-owner pilot remain external.

## Phase 13: Representation-Aware Hybrid Synthesis

- two-level prefix runtime with `O(1)` range sums;
- exact DP over every legal variable-width partition;
- independent statistics, frontier, tie-break, and winner regeneration;
- global-prefix and high-update crossover baselines;
- 24-case exact matrix and 11-scenario native holdout matrix;
- train-only native selection across global prefix, Fenwick, and CertiGap-H;
- explicit temporal-shift failure and fail-safe migration boundary.

Completed in `v1.9.0`. The remaining work requires external evidence or a
larger grammar: independent hardware reproduction, production traces,
concurrency, persistence, inserts/deletes, and storage-engine integration.

## External Closure

- independent proof review or machine-assisted formalization
- matched external robust-BST and learned-index implementations
- independent hardware reproduction
- prospective domain-owner trace and production pilot
- tighter large-instance bounds and approximation ratios
- official YCSB integration with RocksDB or SQLite
- insert/delete, lazy range updates, disk pages, and concurrent-writer protocol
