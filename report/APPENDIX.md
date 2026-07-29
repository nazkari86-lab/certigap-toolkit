# CertiGap Appendix

## Certificate Examples

# CertiGap Certificate Examples

## zipf, n=8, B=2, eta=0.15

- Upper bound: `2.879325`
- Lower bound: `2.526758`
- Reported entropy-bound gap: `0.139534`
- Reported exact diagnostic gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 8], 'threshold': 2}, {'interval': [3, 8], 'threshold': 4}]`

## hot_middle, n=12, B=3, eta=0.15

- Upper bound: `3.291667`
- Lower bound: `2.694186`
- Reported entropy-bound gap: `0.221767`
- Reported exact diagnostic gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 12], 'threshold': 6}, {'interval': [7, 12], 'threshold': 8}, {'interval': [1, 6], 'threshold': 4}]`

## hot_tail, n=16, B=4, eta=0.30

- Upper bound: `3.854545`
- Lower bound: `2.894329`
- Reported entropy-bound gap: `0.331758`
- Reported exact diagnostic gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 16], 'threshold': 13}, {'interval': [14, 16], 'threshold': 14}, {'interval': [1, 13], 'threshold': 8}, {'interval': [9, 13], 'threshold': 12}]`

# CertiGap Speed and Quality Summary

## Small Cases With Exact Reference

- Exact mean time: `2.479 ms`
- Beam mean time: `4.646 ms`
- Greedy mean time: `0.222 ms`
- Balanced mean time: `0.013 ms`
- Weighted mean time: `0.017 ms`
- Beam mean absolute objective gap vs exact: `0.000979`
- Greedy mean absolute objective gap vs exact: `0.114157`
- Balanced mean absolute objective gap vs exact: `0.447373`
- Weighted mean absolute objective gap vs exact: `0.198609`
- Beam mean relative objective gap vs exact: `0.03%`
- Greedy mean relative objective gap vs exact: `3.48%`

## Large Cases Without Exact Reference

- Beam mean time: `57.052 ms`
- Greedy mean time: `1.654 ms`
- Balanced mean time: `0.027 ms`
- Weighted mean time: `0.043 ms`

## Solver Tradeoff

- `exact` is the reference solver for the measured small instances.
- `beam` is near-exact on the measured small cases, but is not faster than exact there; this benchmark does not establish a crossover point.
- `greedy` is usually faster but can be substantially worse on structured skewed tasks.
- `balanced` and `weighted` are cheap baselines, but quality is systematically weaker on skewed workloads.

# Greedy Counterexamples

Top automatically discovered hot-block instances where one-step greedy is much worse than exact.

| n | B | eta | hot start | hot width | hot weight | greedy absolute gap | beam absolute gap |
|---|---:|---:|---:|---:|---:|---:|---:|
| 10 | 3 | 0.00 | 5 | 2 | 24.0 | 1.6429 | 0.0000 |
| 10 | 4 | 0.00 | 5 | 2 | 24.0 | 1.6429 | 0.0000 |
| 12 | 4 | 0.00 | 7 | 2 | 24.0 | 1.5172 | 0.0000 |
| 10 | 3 | 0.00 | 5 | 2 | 16.0 | 1.5000 | 0.0000 |
| 10 | 4 | 0.00 | 5 | 2 | 16.0 | 1.5000 | 0.0000 |
| 12 | 3 | 0.00 | 7 | 2 | 24.0 | 1.4828 | 0.0000 |
| 12 | 4 | 0.00 | 6 | 2 | 24.0 | 1.4483 | 0.0000 |
| 12 | 3 | 0.00 | 6 | 2 | 24.0 | 1.4138 | 0.0000 |
| 10 | 3 | 0.15 | 5 | 2 | 24.0 | 1.3964 | 0.0000 |
| 10 | 4 | 0.15 | 5 | 2 | 24.0 | 1.3964 | 0.0000 |
| 16 | 4 | 0.00 | 7 | 2 | 24.0 | 1.3548 | 0.0000 |
| 16 | 4 | 0.00 | 9 | 2 | 24.0 | 1.3548 | 0.0000 |
| 12 | 4 | 0.00 | 7 | 2 | 16.0 | 1.3333 | 0.0000 |
| 16 | 3 | 0.00 | 7 | 2 | 24.0 | 1.3226 | 0.0000 |
| 16 | 3 | 0.00 | 8 | 2 | 24.0 | 1.3226 | 0.0000 |
| 16 | 3 | 0.00 | 9 | 2 | 24.0 | 1.3226 | 0.0000 |
| 16 | 4 | 0.00 | 8 | 2 | 24.0 | 1.3226 | 0.0000 |
| 12 | 4 | 0.00 | 6 | 3 | 24.0 | 1.3210 | 0.0000 |
| 16 | 4 | 0.00 | 5 | 2 | 24.0 | 1.2903 | 0.0000 |
| 16 | 4 | 0.00 | 11 | 2 | 24.0 | 1.2903 | 0.0000 |

## Best Found Instance

- `n = 10`, `B = 3`, `eta = 0.00`
- hot block: start `5`, width `2`, hot weight `24.0`
- greedy absolute objective gap: `1.642857`
- beam absolute objective gap: `0.000000`
- greedy relative objective gap: `71.88%`
- beam relative objective gap: `0.00%`
- exact tree: `{'type': 'split', 'interval': [1, 10], 'threshold': 5, 'left': {'type': 'split', 'interval': [1, 5], 'threshold': 4, 'left': {'type': 'leaf', 'interval': [1, 4]}, 'right': {'type': 'leaf', 'interval': [5, 5]}}, 'right': {'type': 'split', 'interval': [6, 10], 'threshold': 6, 'left': {'type': 'leaf', 'interval': [6, 6]}, 'right': {'type': 'leaf', 'interval': [7, 10]}}}`
- greedy tree: `{'type': 'split', 'interval': [1, 10], 'threshold': 2, 'left': {'type': 'leaf', 'interval': [1, 2]}, 'right': {'type': 'leaf', 'interval': [3, 10]}}`
- beam tree: `{'type': 'split', 'interval': [1, 10], 'threshold': 5, 'left': {'type': 'split', 'interval': [1, 5], 'threshold': 4, 'left': {'type': 'leaf', 'interval': [1, 4]}, 'right': {'type': 'leaf', 'interval': [5, 5]}}, 'right': {'type': 'split', 'interval': [6, 10], 'threshold': 6, 'left': {'type': 'leaf', 'interval': [6, 6]}, 'right': {'type': 'leaf', 'interval': [7, 10]}}}`

# CertiGap Technical Note

## Formal Model

Let the sorted keys be `x_1 < x_2 < ... < x_n`.
A valid CertiGap tree consists of:

- internal split nodes of the form `x <= x_k?`;
- interval leaves `[l, r]`, each representing an unresolved contiguous rank interval.

If key `x_i` lands in interval leaf `I = [l, r]` at depth `d`, then

`C_T(i) = d + ceil(log2(|I|))`.

For a predicted query distribution `p_hat` and distrust parameter `eta`, the robust objective is

`J_eta(T) = (1 - eta) * sum_i p_hat_i C_T(i) + eta * max_i C_T(i)`.

The budget constraint is

`|T| <= B`,

where `|T|` is the number of split nodes.

## Frontier DP State

For interval `[l, r]` and split budget `b`, define the Pareto frontier

`F(l, r, b)`

as the set of nondominated pairs `(A, M)` where:

- `A` is achievable average cost contribution on `[l, r]`;
- `M` is achievable worst-case cost contribution on `[l, r]`.

A pair `(A1, M1)` dominates `(A2, M2)` if:

- `A1 <= A2`,
- `M1 <= M2`,
- and at least one inequality is strict.

Only nondominated states need to be kept, because for every `eta in [0,1]`,

`(1 - eta) * A1 + eta * M1 <= (1 - eta) * A2 + eta * M2`.

## DP Recurrence

Every valid solution is either:

1. a stop state:
   - one leaf `[l, r]`;
2. or a split at `k` with budgets `b_L + b_R = b - 1`.

Therefore:

- stop state contributes
  `A = P(l, r) * ceil(log2(r - l + 1))`,
  `M = ceil(log2(r - l + 1))`;
- split state contributes
  `A = P(l, r) + A_L + A_R`,
  `M = 1 + max(M_L, M_R)`.

This is exactly the recurrence implemented in the prototype.

## Independent Cost-Cap DP

The second exact solver stores `A[l, r, b, h]`: the minimum average-cost contribution for interval `[l, r]`, budget `b`, and relative maximum-cost cap `h`. For a split, both children receive cap `h - 1`; no Cartesian product of Pareto states is required. Minimizing across feasible caps recovers the robust objective.

## Proof-Carrying Branch And Bound

For proof-sized instances, `branch_and_bound_exact` returns an exhaustive trace. Every state either terminates one open leaf, branches on every legal threshold of that leaf, or is pruned only when its local depth-based lower bound is no better than the submitted incumbent. `verify_branch_and_bound_certificate` reconstructs all legal branches and validates every pruning inequality without importing a search solver.

## Why Greedy Fails

A one-step greedy policy asks whether a split is immediately beneficial.
But CertiGap has complementarities:

- a first split can look weak or neutral by itself;
- after that split, a second split may isolate a hot interval and become highly profitable.

Therefore local gain is not sufficient to recover the global optimum.

The automatically generated counterexample search in `generate_counterexamples.py` is intended to turn this into a formal proposition family.

## Lower Bounds

The prototype currently combines:

1. an entropy-style lower bound for the average-cost component;
2. a Lagrangian lower bound obtained from unconstrained optima across budgets.

For small instances, the report generator also computes the exact optimum. This is a diagnostic comparison, not an independent certificate check. The standalone verifier only checks a submitted tree and certificate arithmetic; it does not run a search solver.

## Current Mathematical Status

- exact solver: implemented, checked against brute force on a systematic small-instance random family, and cross-checked against the C++ exact solver on reference cases;
- robustness identity: proof draft included in `FORMAL_RESULTS.md`;
- greedy counterexample family: Theorem C proves an unbounded absolute-gap family for the implemented one-step rule;
- Theorems A and B: proof drafts are included, but they are not machine-verified or externally peer-reviewed.

# Scalable Anytime TV-DRO Search

## Purpose

`anytime_tv_branch_and_bound` extends direct TV-DRO optimization beyond the
proof-sized exhaustive regime. It always returns:

- a feasible incumbent with objective `U`;
- an admissible global lower bound `L`;
- absolute and relative optimality gaps;
- a deterministic replay certificate.

The result is globally exact only when the reported gap is zero. Otherwise the
interval is the claim.

## Search State

A state contains a partial ordered tree, its split count, and a canonical
ordered set of unresolved leaves. Expanding the first unresolved leaf
enumerates closing it with the fallback and every legal threshold split if
budget remains. These alternatives are exhaustive and disjoint.

## Admissible Lower Bounds

Three independently valid bounds are combined by taking their maximum.

### Componentwise TV Bound

For a key in an unresolved leaf, its optimistic cost includes routing
comparisons already incurred and zero future fallback cost. This is no larger
than its cost in any completion. Componentwise monotonicity therefore gives

`sup_q E_q[c_optimistic] <= sup_q E_q[c_completion]`

over the same TV ball. Already materialized memory and build costs are added.

### Information-Theoretic Bound

Every successful binary search code has nominal expected comparison count at
least `H(p)` and maximum depth at least `ceil(log2(n))`. Multiplication by the
smaller calibrated comparison cost preserves a valid execution-cost bound.

### Conditional-Entropy Bound

Closed leaves contribute their exact nominal execution cost. An unresolved
interval with mass `m`, current depth `d`, and conditional distribution `p_I`
contributes at least

`m * d * routing_cost + m * H(p_I) * min_comparison_cost`.

This state-dependent bound distinguishes weak partial trees and tightens during
best-first search.

## Theorem H: Certified Anytime Interval

Let `U` be the score of the best feasible incumbent and let `L_s` be the
combined admissible lower bound of every state remaining in the frontier.
Then

`min(U, min_s L_s) <= OPT <= U`.

The upper inequality follows from feasibility. The lower inequality follows
because the frontier partitions every unexplored completion and each `L_s` is
admissible. Pruned states cannot beat the final incumbent. `QED`

## Replay Verification

The certificate records the initial incumbent, deterministic best-first event
sequence, final incumbent, structural frontier digest, and stopping condition.
The independent verifier reconstructs every state, bound, transition,
incumbent, frontier, gap, and stopping reason.

Floating-point bounds are verified numerically but excluded from the SHA-256
digest. The digest binds structural state identities, avoiding false failures
across supported Python versions.

## Online Corollary

For distributions `p` and `q`, `delta = TV(p,q)`, and any bounded cost vector,

`|E_p[c] - E_q[c]| <= delta * (max(c) - min(c))`.

If a reference solution is within `g` of its optimum and every feasible policy
has cost range at most `R`, its current-distribution regret is at most

`g + 2 * delta * R`.

`online_regret_certificate` implements this mean-execution-cost guarantee. It
does not certify mutation latency or the full TV-DRO plus memory objective.

## Evidence

`results/anytime_validation.csv` contains 12 complete-tree-space oracle
comparisons and 36 trajectories over `n = 16, 32, 64`. Every row is replay
verified. The current matrix reports all 12 oracle matches and monotone
certified intervals. Nonzero gaps remain nonzero claims.

# Dynamic CertiRange

Dynamic CertiRange extends the static budgeted lookup model into a complete
ordered range index.

It supports:

- point lookup;
- point update;
- inclusive range `sum`, `min`, and `max`;
- immutable snapshots through persistent path copying;
- workload-shaped routing;
- drift-triggered rebuilding;
- deterministic depth caps;
- independently replayed structural and optimizer artifacts.

## Python API

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
    aggregate="sum",
    max_depth=10,
    routing="range_aware",
)

print(index.get(1))
print(index.range_query(1, 10))

snapshot = index.snapshot()
index.point_update(2, 1000)
assert snapshot.get(2) != index.get(2)

certificate = index.export_certificate()
```

Keys and ranges are one-based and ranges are inclusive.

## Structure

The routing solver emits a partial alphabetic tree. Every unresolved interval
is deterministically completed by a midpoint tree. If a proposed routing split
cannot fit inside `max_depth`, that interval is replaced by its balanced
completion.

The resulting full tree has exactly one leaf per key. Every internal node
stores the aggregate of its contiguous interval.

## Guarantees

For `n` keys and completed-tree height `h`:

- point lookup takes at most `h` routing steps;
- persistent point update copies `O(h)` nodes;
- range aggregate visits `O(h)` boundary nodes;
- the implementation exports the conservative executable bound `4h + 1`;
- memory is `O(n)` for the current root plus `O(h)` per retained update;
- `h <= max_depth`;
- snapshots acquired before an update remain unchanged.

The structural verifier reconstructs the deterministic completion, checks
every interval and split, recomputes all per-key depths and aggregates, and
validates canonical SHA-256 digests.

## Range-Aware Search

The former endpoint proxy converts range boundaries into point frequencies.
This is cheap but does not optimize actual range traversal.

`range_aware_beam_search` instead evaluates each candidate by replaying the
declared point, update, and range workload on its completed topology. Its
objective is

```text
(1 - eta) * mean_node_visits + eta * (max_point_depth + 1)
```

The balanced completion is always retained as an incumbent. Therefore the
returned bounded-search candidate is never worse than that included candidate
under the exact training-trace evaluator.

This is not a global guarantee for large instances. The repository validates
the implementation against complete routing-tree enumeration on small cases.

## C++ Core

`cpp/certigap_range.hpp` provides a contiguous-node sum implementation. The
C++ benchmark compares identical mixed traces against:

- a direct array;
- Fenwick tree;
- iterative segment tree;
- contiguous Dynamic CertiRange.

The current benchmark rejects a blanket speed claim: Fenwick and segment trees
win raw sum throughput. CertiRange's distinct features are workload-shaped
point paths, generic Python aggregates, persistent snapshots, drift control,
and replayable certificates.

## Scope

Dynamic CertiRange is currently an ordered fixed-key-universe index. It does
not yet support insertion or deletion, lazy range updates, disk pages,
concurrent writers, or an official storage-engine integration.

# Certified AutoIndex

`compile_autoindex` turns an ordered workload trace and explicit constraints
into an executable index. It evaluates a fixed, deterministic portfolio:

1. contiguous sorted array;
2. Fenwick tree;
3. iterative segment tree;
4. point-proxy CertiRange;
5. range-aware CertiRange.

Every candidate remains in the exported artifact, including infeasible ones
and their rejection reasons. The independent verifier reconstructs all five
candidates, recomputes resources and scores, and rejects omitted candidates,
changed winners, changed holdout results, or a modified digest.

```python
from certigap import AutoIndexConstraints, WorkloadTrace, compile_autoindex

trace = WorkloadTrace(32)
for _ in range(100):
    trace.add_range(3, 30)

index = compile_autoindex(
    range(32),
    trace,
    constraints=AutoIndexConstraints(aggregate="sum", budget=4),
)
print(index.summary())
print(index.range_query(3, 30))
```

## Selection Contract

The objective is

`(1-eta) * mean_visits + eta * max_visits + memory_weight * slots + build_weight * build_units`.

The compiler selects the feasible minimum on the training trace. Ties are
resolved by memory and then the published portfolio order. A chronological
holdout may be attached, but it is evaluation-only and cannot affect the
winner.

By default the unit is one declared structural primitive visit. It makes the
selection replayable, but it is not a nanosecond model. Production selection
can set `array_unit_cost`, `fenwick_unit_cost`,
`segment_tree_unit_cost`, and `certirange_unit_cost` from target-system
measurements. The verifier includes these coefficients in regeneration.

## Constraints And Capabilities

- `aggregate`: `sum`, `min`, or `max`; Fenwick is infeasible outside `sum`.
- `memory_limit_slots`: excludes structures exceeding the declared model.
- `max_depth`: bounds candidate height.
- `require_persistent_snapshots`: restricts selection to CertiRange.
- `budget`: controls the adaptive CertiRange routing prefix.
- `*_unit_cost`: calibrates one structural visit for each backend family.

The current universe is static and rank-addressed. Insert/delete, disk-page
layouts, concurrency, and storage-engine latency remain outside the verified
scope.

## Roadmap

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
