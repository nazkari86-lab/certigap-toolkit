# Measured Safe Deployment

`compile_measured_autoindex` separates three roles:

1. a training trace selects the analytical candidate;
2. an independent validation trace is replayed against the conventional
   baseline and candidate with alternating execution order;
3. a bounded paired-harm gate decides whether to deploy the candidate.

```python
from certigap import (
    AdaptiveSpec,
    MeasuredDeploymentPolicy,
    WorkloadTrace,
    compile_measured_autoindex,
)

train = WorkloadTrace(1_000)
validation = WorkloadTrace(1_000)
for _ in range(200):
    train.add_range(10, 900)
    validation.add_range(20, 850)

index = compile_measured_autoindex(
    range(1_000),
    train,
    validation,
    AdaptiveSpec(operations=("range",), memory_limit_slots=4_000),
    policy=MeasuredDeploymentPolicy(
        alpha=0.05,
        repetitions=64,
        amortization_operations=100_000,
    ),
)
print(index.explain())
```

For each paired batch, normalized harm is

`(candidate_ns - baseline_ns) / max(candidate_ns, baseline_ns)`.

It lies in `[-1,1]`. The candidate is deployed only if a one-sided Hoeffding
upper bound on mean harm clears the configured improvement threshold. Positive
candidate build overhead is amortized over the declared operation horizon.
The artifact stores every pair, policy, trace, environment, structural
selection, decision, and digest. The independent verifier recomputes the bound
and rejects rewritten measurements or decisions.

## Boundary

The statistical interpretation requires representative independent bounded
repetitions. Replays from one process may contain autocorrelation, timer noise,
thermal effects, and scheduler interference. The certificate therefore does
not establish p99 latency, future-drift safety, cross-machine transfer, or a
production service-level objective. It is a fail-closed measured prototype,
not a replacement for a prospective production experiment.

`results/measured_deployment_validation.csv` contains deterministic synthetic
decision-boundary cases. Real timer replay is covered by the runtime test suite
but is deliberately not committed as portable benchmark evidence.
