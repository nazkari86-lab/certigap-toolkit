# Scientific Closure Status

## Completed Internally

- Exact frontier DP, independent cost-cap DP, brute-force checks, and proof-carrying exact branch-and-bound.
- Mathematical proofs for the robust objective identity and frontier-DP exactness, plus an infinite unbounded-gap family for one-step greedy.
- Public workload provenance, synthetic stress distributions, and a complete maximum Python benchmark range.
- Candidate-pruned C++ beam with a 432-case exact-oracle ablation: candidate limit 16 has mean relative gap 0.04% on that suite.
- A timestamped MovieLens early-to-late holdout over identical tuned
  portfolios. TV radii 0.1/0.2 reduce future maximum cost by 2--3 comparisons
  while increasing future average cost by 0.055--0.086 comparisons.
- Exact generalized DP for deterministic executable fallback profiles, including
  midpoint binary search, plus an integer-count/rational-eta evaluator.
- Matched-budget C++ lookup comparisons that separate auxiliary and total bytes
  and label batch-level timing quantiles correctly.
- Exact finite-support TV worst-case evaluation for every AutoDRO candidate.
- Automatic portfolio selection over budgets, solvers, and fallbacks with
  explicit memory and execution-cost accounting.
- Direct TV-DRO exhaustive search with a completeness theorem, deterministic
  tree-space digest, and 181-case exact-space validation.
- Version 2 artifacts whose verifier regenerates the declared portfolio and
  rejects candidate omission.
- A 120-row fair shift benchmark over identical tuned TV and nominal
  portfolios. TV-DRO records 3 wins, 3 losses, and 18 ties against nominal
  selection; the mixed result is retained rather than overstated.
- 3,000 deterministic multinomial trials across 12 configurations; empirical
  coverage is at least 0.996 under the stated i.i.d. model and the radius
  shrinks with sample size.
- A 12-window drift simulation showing that threshold 0.03 halves rebuilds
  without measured regret on that stream, while threshold 0.15 reduces
  rebuilds further at measurable regret.
- A scalable best-first TV-DRO solver with componentwise, entropy, and
  conditional-entropy lower bounds and a replay-verified optimality interval.
- Twelve of twelve complete-tree-space oracle matches and 36 monotone
  certified scaling trajectories over 16, 32, and 64 keys.
- A formal mean-cost regret bound `g + 2 delta R` for online distribution
  drift and a horizon-aware rebuild certificate.
- Real C++ post-build lookup measurements on two additional YCSB-inspired
  read-only distributions, explicitly separated from official YCSB evidence.

## Dynamic CertiRange Extension

The fixed-key-universe range layer is executable and validated:

- point lookup, point update, and inclusive sum/min/max;
- persistent immutable snapshots;
- deterministic maximum-depth completion;
- exact aggregate and mixed-trace replay verifiers;
- `6/6` complete small routing-space oracle matches;
- 36 scaling groups with an included balanced incumbent;
- Python and contiguous-node C++ comparisons against array, Fenwick, and
  segment-tree baselines.

The negative performance result is retained: classical Fenwick and iterative
segment trees remain faster for raw range-sum throughput in the current local
matrix. Dynamic CertiRange is not presented as their universal replacement.

## Certified AutoIndex Extension

The executable compiler compares exactly eight declared structures and exports
every feasible and infeasible row. Its verifier independently regenerates the
complete portfolio and proves the selected training minimum. The 192-row
matrix includes temporal drift, aggregate capability filtering, memory limits,
and snapshot requirements. Holdout regret is reported rather than hidden.

This closes candidate-omission and train/holdout-leakage risks for the declared
portfolio. It does not close global structure selection, calibrated
wall-clock prediction, storage-engine integration, or external replication.

## Profile-Guided C++ Compilation

The versioned JSON compiler validates traces, verifies the complete AutoIndex
artifact, and emits deterministic C++17 configuration source. Cross-language
tests execute all backend families, all three aggregates, updates, and
snapshot isolation. Twenty-four generated-header artifacts are byte-stable.

This closes the gap between a Python paper prototype and a build-time reusable
C++ component. The generated C++ snapshot is deliberately documented as an
`O(n)` value-copy. Native path-copy persistence, insert/delete, concurrency,
disk pages, and direct storage-engine integration remain external work.

## Adaptive Single-Header Boundary

The standalone C++17 mode removes Python and generated-file requirements. Its
24-case native matrix verifies complete eight-candidate reporting,
point/range/update behavior, all aggregates, calibrated and constrained
selection, and snapshot isolation. Root CMake install and downstream
`find_package` are executable tests.

Unlike `certigap-compile`, runtime selection has no independent artifact
replay. Range profiles retain one record per distinct interval, snapshots cost
`O(n+q)`, and reoptimization is explicit to avoid hidden latency. These are
intentional usability tradeoffs, not certified build-time claims.

## Honest Boundaries

- The C++ pruned beam is empirical: it has no approximation theorem. Its
  replay certificate establishes only feasibility and a coarse
  entropy/max-cost lower bound.
- The exact DP recurrence is mathematically exact, while the current
  implementation uses floating-point dominance with `EPS`. Rational arithmetic
  verifies submitted-tree costs but does not machine-prove DP enumeration.
- Movie identifier order is not semantic locality; the temporal result is one public dataset, not a production deployment claim.
- Runtime measurements are machine-specific.
- Nonzero anytime gaps are unresolved intervals, not global-optimality claims.
- YCSB-inspired distributions are not an official YCSB or storage-engine run.
- The rational evaluator verifies submitted-tree arithmetic; it is not a
  machine-checked proof that the DP enumerates every feasible tree.

## Causal Tracking Layer

The fixed-choice temporal-shift gap is now addressed by an executable online
layer rather than another retrospective drift statistic. `TrackingAutoIndex`
uses WFA to choose among all feasible backends, pays a positive migration cost,
materializes the chosen backend, and records a complete trajectory. An
independent verifier recomputes every service vector and decision. A separate
exact DP supplies both K-switch and unrestricted ex-post comparators.

This closes the internal causality and exact-comparator gap. It does not close
calibration or deployment safety: current costs are structural, migration is a
uniform metric, and the algorithm has no claim of predicting phase changes.
The 15-case matrix deliberately records positive regret and a worst observed
oracle ratio of `2.657534` rather than hiding losses.

## External Work Required For A Literal 10/10 Claim

These cannot be completed truthfully by local code generation:

1. Independent reproduction on a separate machine and review of raw artifacts.
2. External mathematical or machine-assisted verification of the written proofs.
3. A domain-owner pilot with a naturally ordered production lookup catalog and a preregistered latency/memory protocol.
4. Literature-reviewed comparison against external robust BST and learned-index implementations under matched resource budgets.
5. A non-trivial approximation theorem for the candidate-pruned scalable path.
6. Prospective validation of the inferred TV radius under non-stationary real
   query streams.
7. Tighter large-instance gaps or an approximation ratio beyond the current
   certified anytime intervals.
8. An official YCSB experiment integrated with RocksDB or SQLite.
