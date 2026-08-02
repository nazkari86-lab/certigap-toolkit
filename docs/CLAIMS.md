# CertiGap Claim Register

This register is the source of truth for statements made in the README, paper,
presentations, and competition material. A result outside the stated scope must
not be used to strengthen the claim.

Status: CertiGap Toolkit `v1.10.1`.

## Central Claim

CertiGap synthesizes or selects workload-adaptive ordered in-memory structures
inside explicitly declared finite design spaces. For exact paths it emits
artifacts whose candidate completeness, structural objective, constraints,
tie-breaking, and selected winner can be replayed independently. Hardware
latency is measured separately and is never certified by a structural score.

## Verified Claims

| Claim | Type | Evidence | Exact boundary |
|---|---|---|---|
| Frontier DP returns an optimum | Mathematical and exhaustive | `docs/FORMAL_RESULTS.md`, brute force and cost-cap cross-validation | Budgeted partial alphabetic trees with the declared executable fallback |
| Cost-cap DP is an independent exact recurrence | Mathematical and differential | `results/exact_cross_validation.csv` | Same grammar and objective as the frontier DP |
| One-step greedy has an unbounded additive gap | Mathematical | Theorem C and generated infinite-family witnesses | The implemented one-step rule; not every possible greedy algorithm |
| The contamination objective equals finite-support worst-case expectation | Mathematical | Theorems A and B | Declared Huber contamination set |
| Direct TV search is globally optimal on proof-sized cases | Exhaustive | 181 complete tree spaces in `results/direct_tv_validation.csv` | Enumerated key sizes, budgets, fallbacks, and TV objective |
| Anytime TV search returns a valid interval | Mathematical and replay-verified | Theorem H and `results/anytime_validation.csv` | Declared lower bound, processed prefix, and remaining frontier |
| Candidate-pruned C++ beam returns a valid interval | Replay-certified | `certigap-pruned-beam-v1` and scaling artifacts | Feasible heuristic upper bound plus entropy/max-cost lower bound; no approximation ratio |
| Online mean-cost regret is at most `g + 2 delta R` | Mathematical | Theorem I and `online_regret_certificate` tests | Mean modeled execution cost; excludes unmodeled DB and migration latency |
| AutoIndex selects the minimum-score feasible candidate | Replay-certified | `results/autoindex_validation.csv` | The complete declared eight-candidate portfolio, not all data structures |
| Safe AutoIndex deploys specialization only below its validation upper bound | Statistical and replay-certified | `results/safe_autoindex_validation.csv` | One-sided Hoeffding bound conditional on independent IID bounded validation operations and declared structural costs |
| Sequential Safe AutoIndex permits optional stopping during validation | Mathematical, statistical, and replay-certified | Corollary L.2, `results/sequential_safe_validation.csv`, and `results/optional_stopping_monte_carlo.csv` | Alpha-spending Hoeffding sequence conditional on independent IID bounded validation operations; not a future-drift guarantee |
| Martingale Safe AutoIndex controls optional-stopping errors for adapted observations | Mathematical, statistical, and replay-certified | Theorem L.3, `results/martingale_safe_validation.csv`, and `results/martingale_null_monte_carlo.csv` | Mixture Hoeffding e-process under the declared bounded conditional-mean deployment/revocation nulls; detection delay and future safety are not guaranteed |
| CertiGap-X selects an exact contiguous partition | Replay-certified | `results/synthesis_validation.csv` | Declared aggregate, constraints, cost profile, and block grammar |
| CertiGap-H selects an exact representation-aware partition | Replay-certified | `results/hybrid_validation.csv` | Declared two-level-prefix representation and additive structural model |
| CertiGap-H DP tie-breaking is platform-stable | Arithmetic and differential | Integer `1e-12` score units in solver and separately implemented verifier | Decimalized declared hardware profile; native timings remain floating-point |
| Fixed-point Pareto dominance is safe | Machine-checked theorem | `formal/CertiGap.lean` | Scalarized non-negative integer coordinates and common additive continuations |
| CertiGap-H improves structural score over uniform prefix | Certified empirical | `6.73%` mean and `33.43%` maximum over 24 deterministic cases | Committed validation matrix only |
| CertiGap-H beats Fenwick in native timing | Empirical | `9/11` holdout scenarios in `results/synthesis_native_latency.csv` | Apple M4, Apple clang, committed workloads and operation mixes |
| CertiGap-H beats uniform prefix in native timing | Empirical | `10/11` holdout scenarios in `results/synthesis_native_latency.csv` | Apple M4, Apple clang, committed workloads and operation mixes |
| CertiGap-H is the fastest tested implementation | Empirical | `4/11` holdout scenarios in `results/synthesis_native_latency.csv` | Tested implementations and committed machine only |
| AutoIndex has low stationary three-backend regret | Empirical | `1.02%` mean, `6.42%` maximum over ten stationary scenarios | Same machine and three-candidate holdout oracle |
| SQLite pilot executes real SQL operations | Empirical systems pilot | 375 raw repetitions, checksums, and bootstrap intervals | In-memory Python application integration with YCSB-compatible mixes; not official YCSB or a SQLite extension |
| SQLite loadable extension executes CertiGap C++ operations from SQL | Cross-language systems integration | `cpp/certigap_sqlite.cpp` and `tests/test_sqlite_extension.py` | Connection-local SQL functions loaded through SQLite extension ABI; not a virtual table, planner integration, durability layer, or performance claim |
| SQLite virtual table exposes planner-visible and durable CertiGap operations | Cross-process systems integration | `cpp/certigap_sqlite_vtab.cpp`, `results/sqlite_vtab_validation.csv`, and real SQLite CLI tests | Equality/bounded-range `xBestIndex`, inclusive range-sum pushdown, shadow durability, basic mutations, rollback/savepoints, and serialized two-process WAL writes; not an official YCSB or performance claim |
| Temporal shift can break train-only selection | Empirical failure case | `219.69%` regret in the declared shift scenario | One deterministic stress case; not a drift frequency estimate |
| Generated C++ implements the selected semantics | Cross-language differential | compiler integration and native runtime oracle tests | Supported get/range/update/snapshot operations and generated backends |
| `adaptive_array` automatically profiles and applies a fail-closed score gate | Native behavioral and persistence validation | `results/adaptive_array_validation.csv` and C++ compile/run tests | Five-candidate structural model, zero-based API, synchronous maintenance, and strict workload-profile persistence; not a statistical or wall-clock no-regression guarantee |
| Python `AdaptiveArray` selects from the complete AutoIndex portfolio | Behavioral, differential, and persistence validation | `results/python_adaptive_array_validation.csv` and Python oracle tests | Eight declared candidates, zero-based API, bounded integer profile, serialized public operations, and atomic persistence; not a latency or parallel-throughput guarantee |

## Statements That Are Not Established

The following statements must not appear as project conclusions:

- CertiGap is the first robust or learned search structure.
- CertiGap is globally optimal outside its declared grammar or portfolio.
- A structural score is nanosecond latency.
- CertiGap-H universally beats Fenwick, segment trees, or global prefix sums.
- Public frequency-derived cases are real database query traces.
- The candidate-pruned C++ beam has an approximation ratio or a tight gap.
- The current replay verifiers are machine-checked formal proofs.
- The current project discovers arbitrary new data structures from operation
  specifications.
- Results from one Apple M4 machine transfer to other processors.
- The toolkit is ready for insert/delete-heavy, concurrent, durable, or
  disk-resident production use.

## Open Evidence Required

1. Independent reproduction on separate Intel, AMD, and ARM Linux machines.
2. External learned-index and robust-BST implementations under matched
   operation semantics, memory budgets, and hardware.
3. Official YCSB or a RocksDB plugin with real operation traces and matched
   native SQLite B-tree measurements.
4. A non-trivial approximation theorem or tighter certified gaps for the
   candidate-pruned scalable path.
5. Exact or machine-assisted checking of proof-critical arithmetic and
   recurrence completeness.
6. A preregistered domain-owner pilot with build, memory, latency, migration,
   and failure metrics.
7. Train/validation/test separation for grammar and hyperparameter decisions,
   repeated native measurements, confidence intervals, and ablations.
8. Mixing-process or block-bootstrap inference for dependent traces that do not
   satisfy the current conditional-mean martingale nulls.

## Language Rules

Use:

> Within the declared grammar and structural model, the replay verifier confirms
> that the selected design has minimum certified score.

Do not use:

> CertiGap proves that this is the fastest possible index.

Use:

> In the committed Apple M4 holdout run, CertiGap-H beat Fenwick in nine of
> eleven scenarios and lost at 30% and 50% update rates.

Do not use:

> CertiGap-H is faster than Fenwick.
