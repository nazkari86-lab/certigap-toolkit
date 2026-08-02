# Proof-Carrying Data-Structure DSL

`ProofCarryingSpec` binds operation semantics, one canonical aggregate algebra,
resource constraints, a complete typed design grammar, deterministic selection,
and generated C++ into one digest-protected certificate.

```python
from certigap import (
    ProofCarryingSpec,
    WorkloadTrace,
    compile_proof_carrying_index,
    verify_dsl_certificate,
)

trace = WorkloadTrace(32)
for _ in range(100):
    trace.add_range(3, 29)

model = compile_proof_carrying_index(
    range(32),
    trace,
    ProofCarryingSpec(
        operations=("range",),
        algebra="sum",
        memory_limit_slots=96,
    ),
)
certificate = model.export_certificate()
print(verify_dsl_certificate(certificate))
header = model.render_cpp_header("my_index")
```

## Typed Grammar

The compiler enumerates exactly eight declarations:

| Design | Backend | Required laws |
|---|---|---|
| `flat_fold` | sorted array | monoid |
| `prefix_group` | prefix sum | commutative group |
| `fenwick_group` | Fenwick tree | commutative group |
| `sqrt_monoid` | square-root decomposition | monoid |
| `segment_monoid` | segment tree | monoid |
| `sparse_semilattice` | sparse table | idempotent semilattice |
| `certirange_point_monoid` | point-trained CertiRange | monoid |
| `certirange_range_monoid` | range-trained CertiRange | monoid |

The canonical `sum` model supplies a commutative group. Canonical `min` and
`max` supply idempotent commutative monoids. The artifact records both algebraic
eligibility and all ordinary memory, depth, and snapshot constraints. A design
is not silently removed when it is ineligible.

The Python wrapper rejects undeclared operations at runtime. Generated C++ uses
a contract-specific wrapper and does not expose undeclared methods, so an
attempted call fails at C++ compilation rather than silently leaving the
certified interface.

## Independent Verification

`verify_dsl_certificate()` does not trust the compiler summary. It:

1. checks the outer and grammar SHA-256 digests;
2. reconstructs the canonical algebra declaration;
3. independently regenerates all eight typed design rows;
4. verifies operation-contract conformance;
5. invokes the separate AutoIndex replay verifier for candidate costs,
   resources, routing trees, tie-breaking, and winner selection;
6. confirms that the selected DSL design maps to the verified backend.

Removing an infeasible design, changing a law, substituting a trace, or changing
the selected backend fails verification even if the attacker recomputes the
outer digest.

## One-Command Compilation

```bash
certigap-dsl compile input.json \
  --artifact certificate.json \
  --header generated.hpp \
  --namespace my_index

certigap-dsl verify certificate.json
certigap verify certificate.json
certigap explain certificate.json
```

The input schema is
`schemas/certigap_dsl_input_v1.schema.json`. Package consumers include the
generated header and link the ordinary `CertiGap::certigap` CMake target.
A ready input is available at `examples/proof_carrying_dsl.json`; the equivalent
Python API flow is `examples/proof_carrying_dsl.py`. Install the package first
with `python3 -m pip install -e .` when running examples from a source checkout.

## Evidence And Boundaries

The committed 36-case matrix covers all three built-in algebras, four operation
contracts, and default, tight-memory, and persistent-snapshot regimes. Every
case verifies grammar completeness and replays 160 runtime operations against a
list oracle.

The algebra declaration is a capability contract, not a machine proof of a
user-supplied function. In particular, `sum` uses mathematical real-addition
laws for structural reasoning, while the runtime uses `double`; IEEE-754
addition is not associative and can vary with evaluation order. DSL v1 does not
support arbitrary operators, insert/erase, lazy range updates, unbounded design
discovery, or portable wall-clock optimality.
