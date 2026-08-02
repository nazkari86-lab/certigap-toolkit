# Python AdaptiveArray

`AdaptiveArray` is the lowest-friction Python interface to the complete
eight-candidate AutoIndex portfolio. It observes normal operations, selects a
feasible backend after warmup, and preserves ordinary zero-based Python
indexing with half-open ranges.

```python
from pathlib import Path

from certigap import AdaptiveArray, AdaptiveArrayPolicy

policy = AdaptiveArrayPolicy(profile_path=Path("catalog.profile"))
with AdaptiveArray(range(1_000), policy=policy) as data:
    total = data.range_sum(10, 40)
    data.update(12, 100.0)
    print(total, data.get(12), data.explain())
```

The portfolio contains sorted array, prefix sum, Fenwick, segment tree,
square-root decomposition, sparse table, and two CertiRange variants.
Unsupported candidates are filtered by aggregate and memory constraints.

## Deployment Policy

```python
policy = AdaptiveArrayPolicy(
    warmup_operations=256,
    check_interval=10_000,
    minimum_tv_drift=0.10,
    minimum_relative_improvement=0.05,
    max_profile_operations=100_000,
)
```

The bounded profile decays before exceeding its configured capacity. The
modeled winner replaces the current backend only when it clears the relative
improvement threshold. `automatic_maintenance=False` moves compilation to an
explicit `data.maintenance()` call. Public operations and lifecycle methods
are serialized by a reentrant lock; this is correctness-oriented thread
safety, not a parallel-throughput claim.

## Persistent Warm Start

When `profile_path` is configured, construction reads the same strict
`CERTIGAP_PROFILE_V1` format used by the C++ container. `close()` or a context
manager writes it atomically using a temporary file and `os.replace`. The
profile stores operation counts, never array values.

The deployment threshold compares declared structural scores. It is neither a
wall-clock guarantee nor a statistical no-regression certificate. Use the Safe
or Martingale SafeAutoIndex APIs when those assumptions and guarantees match
the deployment.

Reproduce the seven Python lifecycle scenarios with:

```bash
python3 generate_python_adaptive_array_validation.py
```

The committed output is
[`results/python_adaptive_array_validation.csv`](../results/python_adaptive_array_validation.csv).
