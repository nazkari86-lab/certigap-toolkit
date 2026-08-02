# Martingale Safe AutoIndex

Martingale Safe AutoIndex extends sequential deployment from IID validation to
bounded adapted observations under explicit conditional-mean null hypotheses.
It has two independently budgeted lifecycle gates:

- deployment rejects the null that specialization has no conditional expected
  advantage after required improvement and amortized transition cost;
- revocation rejects the null that the deployed candidate remains no worse
  than a declared tolerance.

If deployment evidence is insufficient, the conventional baseline remains
active. If post-deployment harm evidence crosses its threshold, the emitted
configuration returns to that baseline.

```python
from certigap import (
    MartingaleSafeSelectionPolicy,
    WorkloadTrace,
    compile_martingale_safe_autoindex,
)

train = WorkloadTrace(8)
monitoring = WorkloadTrace(8)
for _ in range(100):
    train.add_range(2, 7)
for _ in range(1_000):
    monitoring.add_range(2, 7)
for index in range(3_000):
    monitoring.add_update(1 + index % 8, float(index))

index = compile_martingale_safe_autoindex(
    range(8),
    train,
    monitoring,
    policy=MartingaleSafeSelectionPolicy(minimum_observations=50),
)
print(index.summary())
```

The example first deploys the training winner and later revokes it after an
update-heavy workload shift. Compilation to a verified C++17 configuration is:

```bash
certigap martingale-safe-compile input.json \
  --artifact build/martingale-selection.json \
  --header build/martingale-index.hpp
```

## E-process

Let `Y_t` be adapted to filtration `F_t`, have conditional mean at most zero,
and lie in an interval of width `B`. For fixed positive `lambda`, Hoeffding's
lemma makes

`E_t(lambda) = exp(lambda sum_{i<=t} Y_i - lambda^2 B^2 t / 8)`

a non-negative supermartingale. The implementation uses an equal-weight
mixture over declared dimensionless betting fractions `c_j`, with
`lambda_j = c_j/B`. A fixed mixture of supermartingales is again a
supermartingale. Ville's inequality therefore gives

`Pr(sup_t E_t >= 1/alpha) <= alpha`.

For deployment, `Y_t = -(D_t + A + m)`, where `D_t` is candidate work minus
baseline work, `A` is amortized transition cost, and `m` is required
improvement. For revocation, `Y_t = D_t - r`, where `r` is the allowed harm
tolerance. Deployment and revocation have separate alpha budgets and separate
e-processes.

## Certificate

The artifact contains the complete policy, first deployment crossing, first
revocation crossing, final audits, monitoring trace, selected baseline, final
backend, and outer digest. The replay verifier reconstructs both lifecycle
crossings and rejects edited decisions even if the outer digest is recomputed.

## Claim Boundary

The result permits adapted, non-IID bounded observations only under the stated
conditional-mean null. It does not prove:

- that arbitrary adversarial drift is harmless;
- that the candidate remains safe before harm is detected;
- correctness under unbounded or incorrectly bounded costs;
- wall-clock performance from structural work;
- global optimality outside the eight-backend portfolio.

Revocation controls false alarms under its null. It cannot eliminate detection
delay or losses accumulated before crossing.
