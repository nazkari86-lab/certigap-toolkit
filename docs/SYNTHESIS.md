# CertiGap-X Certified Structure Synthesis

CertiGap-X extends fixed-portfolio selection with a synthesized
`VariableBlockIndex`. It partitions ordered keys into unequal contiguous
blocks. A range query reads one precomputed aggregate for each fully covered
block and scans only partially covered block fragments.

```python
from certigap import SynthesisConstraints, WorkloadTrace
from certigap import compile_synthesized_index, verify_synthesis_certificate

trace = WorkloadTrace(32)
for _ in range(100):
    trace.add_range(2, 11)

model = compile_synthesized_index(
    range(32),
    trace,
    constraints=SynthesisConstraints(max_blocks=12, max_block_width=16),
)
print(model.selected_boundaries)
print(verify_synthesis_certificate(model.export_certificate()))
```

## Exact Grammar

For every block count up to `max_blocks`, the compiler considers every
contiguous partition whose blocks do not exceed `max_block_width`. Dynamic
programming returns the exact minimum for each block count. The final winner
is the feasible minimum across that complete frontier.

For operation `o` and block `B`, let `c(o,B)` be the declared calibrated
primitive cost contributed by that block. Whole-operation cost is
`C(o,P)=sum_B c(o,B)`. Therefore:

`mean_o C(o,P) = sum_B mean_o c(o,B)`

and

`max_o C(o,P) <= sum_B max_o c(o,B)`.

The optimized additive objective is consequently a certified upper bound on
the requested mean/tail objective. It is intentionally conservative: the
partition minimizing this upper bound need not minimize measured `p99`.

## Hardware Calibration

```bash
python3 calibrate_hardware.py --output hardware_profile.json
```

The C++17 calibrator records median primitive costs. A certificate is
conditional on these supplied measurements. The verifier checks their digest
and recomputes the complete frontier, but cannot prove that another machine
has the same latency.

## C++ Export

`model.render_cpp_header("my_index")` emits a deterministic configuration that
uses `cpp/certigap_synth.hpp`. Python and generated C++ share inclusive
1-based point/range/update semantics. Memory accounting is `2n+2b` scalar
slots: values, key-to-block mapping, boundaries, and block aggregates.

## Safe Migration

`migration_decision` permits rebuilding only when projected horizon savings
strictly exceed rebuild cost plus an explicit confidence margin. This is an
amortization rule, not a workload forecast or statistical confidence
estimator.

## Native Holdout Result And Successor

The structural theorem does not imply wall-clock speed. The matched native
benchmark selects partitions from `800` train operations and measures five C++
implementations on `6000` separately seeded holdout operations. It covers four
stationary synthetic cases, one temporal shift, and three public
frequency-derived cases.

The original committed audit found that CertiGap-X did not beat Fenwick. That
negative result motivated CertiGap-H, which replaces the covered-block loop
with local and top-level prefix arrays and changes the exact objective to
model range-boundary separation and update suffix writes.

The practical policy remains fail-safe: AutoIndex chooses between global
prefix, Fenwick, and the synthesized hybrid from train measurements. See
[`results/synthesis_native_latency.md`](../results/synthesis_native_latency.md)
and [`HYBRID.md`](HYBRID.md).

## Claim Boundary

The current grammar synthesizes in-memory rank-addressed block indexes. It
does not yet include PGM/ALEX, concurrency, inserts/deletes, disk pages, SIMD
layouts, or a storage-engine integration. Committed validation uses portable
unit primitive costs; target-specific nanoseconds must be measured locally.
