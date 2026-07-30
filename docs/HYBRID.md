# CertiGap-H: Certified Hybrid Prefix Index

CertiGap-H is the representation-aware successor to the original
variable-block aggregate index. It stores:

- the original values;
- one local prefix array restarted at every synthesized block;
- one prefix array over complete block sums;
- a key-to-block map and block boundaries.

A range sum uses at most two local-prefix differences and one block-prefix
difference. It does not loop over covered blocks.

## Complexity

For `n` values, `b` blocks, and the updated key's remaining block suffix `w`:

| Operation | Time |
|---|---:|
| `get` | `O(1)` |
| `range_query` | `O(1)` |
| `point_update` | `O(w + b)` |
| build | `O(n + b)` |
| memory | `3n + 2b` scalar slots |

This deliberately targets read-heavy mixed workloads. A global prefix array
is simpler and usually faster when updates are absent. Fenwick becomes safer
as update frequency increases.

## Exact Representation-Aware Synthesis

For a candidate block `[l,r]` at position `j` in a `b`-block partition, the
partition-dependent work model charges:

- a range only when its endpoints are separated by the boundary after this
  block;
- an update at key `k` for `r-k+1` local-prefix writes and `b-j+1`
  block-prefix writes;
- declared primitive costs and memory penalties.

Every range-separation charge belongs to exactly the block containing its left
endpoint. Every update belongs to exactly one block. Mean work is therefore
additive. The sum of per-block maxima remains a conservative upper bound on
the whole-operation maximum.

For every legal block count, dynamic programming evaluates all contiguous
partitions respecting `max_block_width`. The independent verifier separately
reconstructs statistics, the complete frontier, tie-breaking, and the winner.

```python
from certigap import (
    HybridConstraints,
    WorkloadTrace,
    compile_hybrid_index,
    verify_hybrid_certificate,
)

trace = WorkloadTrace(256)
for _ in range(900):
    trace.add_range(1, 80)
for key in range(1, 101):
    trace.add_update(key, float(key))

index = compile_hybrid_index(
    range(256),
    trace,
    constraints=HybridConstraints(
        max_blocks=16,
        max_block_width=64,
    ),
)
print(index.selected_boundaries)
print(verify_hybrid_certificate(index.export_certificate()))
```

`render_cpp_header()` emits a C++17 `certigap::PrefixBlockIndex`
configuration.

## Verified Evidence

The deterministic exact matrix contains `24` workloads across four sizes and
six operation families:

- `24/24` independently replayed complete frontiers;
- `24/24` runtime oracle passes;
- `10/24` selected nonuniform designs;
- `6.73%` mean certified score gain over the best uniform-prefix partition;
- `33.43%` maximum certified gain.

The native Apple M4 holdout matrix has `11` scenarios and `110` method rows.
Partitions and AutoIndex backend choices use only `800` train operations;
`6000` independently seeded operations are used for post-build timing.

In the committed run:

- CertiGap-H beats Fenwick in `9/11` scenarios;
- it beats uniform-prefix in `10/11`;
- global prefix is generally best for read-heavy stationary workloads;
- Fenwick wins the `30%` and `50%` update scenarios;
- the nonuniform CertiGap-H layout is the fastest specialized backend on the
  left-hot scenario;
- the declared temporal shift exposes the need for online re-selection.

The train-only three-backend selector has `1.02%` mean and `6.42%` maximum
holdout regret on the ten stationary scenarios. The explicit temporal shift
raises regret to `219.69%`; this is the documented trigger for drift detection
and re-selection, not evidence of a portable guarantee.

## Claim Boundary

The certificate proves optimality only for the declared additive structural
model and partition grammar. It does not prove nanosecond latency. The native
results are single-machine evidence, not a portable speed guarantee.

The current implementation supports sum, point updates, and rank-addressed
in-memory arrays. It does not yet provide inserts/deletes, concurrency,
durability, disk pages, lazy range updates, or an independent external
reproduction.
