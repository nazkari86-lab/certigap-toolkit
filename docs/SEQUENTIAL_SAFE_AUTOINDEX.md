# Sequential Safe AutoIndex

`compile_sequential_safe_autoindex` permits inspection after every validation
operation without reusing a fixed-time confidence interval. It selects from
the complete eight-candidate AutoIndex portfolio, chooses a conventional safe
baseline from training data, and evaluates paired candidate-minus-baseline
structural costs in chronological order.

```python
from certigap import (
    SequentialSafeSelectionPolicy,
    WorkloadTrace,
    compile_sequential_safe_autoindex,
)

train = WorkloadTrace(8)
validation = WorkloadTrace(8)
for _ in range(100):
    train.add_range(2, 7)
for _ in range(2_000):
    validation.add_range(2, 7)

index = compile_sequential_safe_autoindex(
    range(8),
    train,
    validation,
    policy=SequentialSafeSelectionPolicy(
        confidence_alpha=0.05,
        minimum_observations=100,
        horizon_operations=1_000_000,
    ),
)
print(index.summary())
```

The deployment compiler is:

```bash
certigap sequential-safe-compile input.json \
  --artifact build/sequential-selection.json \
  --header build/sequential-index.hpp

certigap verify build/sequential-selection.json
certigap explain build/sequential-selection.json
```

The input is validated against
[`certigap_sequential_safe_compile_input_v1.schema.json`](../schemas/certigap_sequential_safe_compile_input_v1.schema.json).
The generated C++17 header embeds the outer sequential-certificate digest and
materializes the actually deployed candidate.

## Confidence Sequence

For operation `t`, let `X_t` be candidate work minus baseline work and let all
differences lie in an interval of width `B`. The compiler allocates

`alpha_t = alpha / (t(t+1))`.

At every eligible prefix it computes

`U_t = mean(X_1,...,X_t) + B sqrt(log(1/alpha_t)/(2t)) + transition/horizon`.

The candidate is deployed at the first prefix for which

`U_t < -minimum_improvement`.

Because `sum_t alpha_t = alpha`, fixed-time Hoeffding bounds and a union bound
give simultaneous coverage for every finite prefix. Therefore inspecting the
sequence continuously or stopping at its first crossing does not increase the
declared type-I error above `alpha`.

The certificate records the first eligible crossing, alpha allocated at that
operation, cumulative alpha spent, the final full-stream audit, and the number
of post-stop operations. The verifier reconstructs the complete first-crossing
decision. Editing only the stopping operation and recomputing the outer digest
is rejected.

## Exact Boundary

The theorem assumes independent identically distributed bounded validation
operations and a fixed candidate selected only from training data. It certifies
optional stopping during validation. It does not certify:

- arbitrary future workload drift;
- dependent or adversarial validation operations;
- measured nanosecond latency from structural work;
- correctness of manually calibrated unit costs;
- global optimality beyond the declared candidate portfolio.

The post-stop reversal experiment is intentionally an audit witness: it shows
that later observations cannot retroactively alter the recorded decision. It
does not claim that an old deployment remains safe after distribution shift.
