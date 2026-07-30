# Safe AutoIndex

`compile_safe_autoindex` adds a fail-closed deployment gate to the complete
AutoIndex portfolio. It separates data chronologically or experimentally into:

- `train`: constructs candidates and selects the minimum modeled score;
- `validation`: decides whether specialization has enough evidence;
- `test`: reports final behavior and never changes deployment.

The safe baseline is chosen on training data from a declared ordered set whose
default is array, Fenwick, and segment tree. If no baseline satisfies the
constraints, compilation fails instead of silently weakening the policy.

```python
from certigap import (
    SafeSelectionPolicy,
    WorkloadTrace,
    compile_safe_autoindex,
)

train = WorkloadTrace(32)
validation = WorkloadTrace(32)
test = WorkloadTrace(32)
for _ in range(200):
    train.add_range(3, 30)
for _ in range(50_000):
    validation.add_range(3, 30)
for _ in range(1_000):
    test.add_range(4, 29)

index = compile_safe_autoindex(
    range(32),
    train,
    validation,
    test_trace=test,
    policy=SafeSelectionPolicy(
        confidence_alpha=0.05,
        horizon_operations=1_000_000,
        migration_cost_units=500.0,
    ),
)
print(index.summary())
print(index.export_certificate())
```

The same workflow can emit a deployment-specific C++17 header without a
Python runtime:

```bash
certigap safe-compile safe_trace.json \
  --artifact build/safe-selection.json \
  --header build/safe-index.hpp

certigap verify build/safe-selection.json
certigap explain build/safe-selection.json
```

The strict input schema is
[`certigap_safe_compile_input_v1.schema.json`](../schemas/certigap_safe_compile_input_v1.schema.json).
The emitted backend is the validation-approved candidate or the actual safe
fallback, not necessarily the raw training winner. Its C++ configuration
embeds the outer safe-certificate digest.

## Decision Rule

For paired candidate-minus-baseline validation cost with sample mean
`mean_difference`, declared range width `B`, validation size `m`, and
one-sided error probability `alpha`, the certificate computes

`radius = B * sqrt(log(1/alpha) / (2m))`.

It deploys the candidate only when

`mean_difference + radius + (build + migration) / horizon < -minimum_improvement`.

Otherwise the conventional baseline remains deployed. The range bound is
deliberately conservative and covers every supported operation in the current
eight-backend grammar. The verifier independently recomputes the baseline,
bound, confidence radius, transition amortization, decision, test evaluation,
and both artifact digests.

## Claim Boundary

This is a Hoeffding guarantee conditional on independent IID bounded validation
operations and the declared structural-cost model. It does not prove:

- generalization under arbitrary temporal drift;
- portable wall-clock latency;
- correctness of manually supplied hardware coefficients;
- optimality outside the declared eight-candidate portfolio.

Temporal dependence needs a block-bootstrap, martingale, or mixing-process
certificate in a future schema. Until then, the IID condition must remain
visible in every scientific claim.
