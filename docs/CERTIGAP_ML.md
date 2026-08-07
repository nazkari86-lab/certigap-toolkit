# CertiGap-ML: Certified Finite-Portfolio Model Elimination

CertiGap-ML is a separate research extension of CertiGap, not a rename of the
ordered-index project. It selects among a **predeclared finite portfolio** of
binary online-logistic training programs under a fixed checkpoint schedule.

## What It Does

At every checkpoint, each still-active candidate trains only on the training
split and emits predictions on a validation split. Let `C` be the original
number of candidates, `T` the number of checkpoints, `m` validation examples,
and `alpha` the requested error probability. The common two-sided radius is

`eps = sqrt(log(2CT/alpha)/(2m))`.

For candidate `c` at checkpoint `t`, CertiGap-ML exports

`LCB(c,t) = max(0, accuracy_hat(c,t) - eps)`

`UCB(c,t) = min(1, accuracy_hat(c,t) + eps)`.

It prunes a nonleader only if

`UCB(c,t) < LCB(leader,t) - pruning_margin`.

The chosen model is the best final survivor by validation accuracy. The test
split is evaluated only after this selection and never enters pruning.

## Theorem S: Finite Checkpoint Coverage

The canonical statement and proof are in `FORMAL_RESULTS.md`; this section
summarizes its operational interpretation.

Assume validation examples are IID and the complete candidate training paths
are fixed without using validation labels. For every predeclared candidate and
checkpoint program, Hoeffding's inequality bounds failure of its interval by
`alpha/(CT)`. A union bound gives simultaneous coverage of all `C*T` programs
with probability at least `1-alpha`, including any subset examined adaptively
by the pruning policy.

On that event, if `s` is the selected final survivor and `R` is the set of all
checkpoint models actually evaluated, then

`max_{r in R} accuracy(r) - accuracy(s) <= max_{r in R} UCB(r) - LCB(s)`.

The exported `selection_regret_upper_bound` is exactly the nonnegative right
side. The standalone verifier recomputes all prediction accuracies, confidence
intervals, pruning decisions, final selection, and test accuracy.

## Critical Boundary

This theorem does **not** say that a candidate pruned at epoch 2 could not
have beaten the selected model at epoch 100. Generic learning algorithms have
no valid universal upper bound on future improvement. CertiGap-ML certifies
only the finite, observed checkpoint portfolio. Any stronger early-stopping
claim needs a separately proved optimization or learning-curve envelope.

The verifier checks statistical logic for submitted prediction vectors; it does
not independently replay floating-point training. The current model family is
intentionally small and dependency-free to make this boundary visible.

## Minimal Usage

```python
from certigap import CertiGapML, LogisticConfig

selector = CertiGapML(
    [
        LogisticConfig("fast", learning_rate=0.15),
        LogisticConfig("regularized", learning_rate=0.05, l2=0.03),
    ],
    checkpoints=[1, 2, 4, 8],
    alpha=0.05,
)
result = selector.fit(train_x, train_y, validation_x, validation_y, test_x, test_y)
print(result["selected"], result["selection_regret_upper_bound"])
```

## Required Next Research

The committed synthetic diagnostic validates only implementation. A contest or
paper claim requires preregistered public tabular datasets, repeated seeds,
fixed compute/RAM accounting, and comparisons with full portfolio training,
Successive Halving, Hyperband, Random Search, and Optuna. Claims must retain
both failures and cases where pruning does not save work.
