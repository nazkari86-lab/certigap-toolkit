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

## External Closure

- independent proof review or machine-assisted formalization
- matched external robust-BST and learned-index implementations
- independent hardware reproduction
- prospective domain-owner trace and production pilot
- tighter large-instance bounds and approximation ratios
- official YCSB integration with RocksDB or SQLite
- insert/delete, lazy range updates, disk pages, and concurrent-writer protocol
