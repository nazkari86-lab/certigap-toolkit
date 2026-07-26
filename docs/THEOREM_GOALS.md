# Theorem Goals

## Best Main Theorem

**Theorem A: Exact optimality of the frontier dynamic program**

For the static budgeted partial-search model, the frontier DP returns a tree minimizing

`(1 - eta) * average_cost + eta * max_cost`

among all valid trees with at most `B` splits.

Why this is the best first theorem:

- it is clean;
- it is central, not peripheral;
- it matches the code directly;
- it is easy for judges to understand.

## Best Secondary Theorem

**Theorem B: Robustness under contamination**

If the true distribution is

`p = (1 - eta) * p_hat + eta * q`,

then the CertiGap objective exactly matches worst-case expected cost under that contamination model.

Why it matters:

- it justifies the robustness parameter mathematically;
- it turns `eta` from a tuning knob into a formal model parameter.

## Proven Negative Result

**Theorem C: The implemented one-step greedy baseline can be arbitrarily suboptimal**

The proved family uses `n=2^m`, two central hot keys of weight `n*m`, `B=3`, and `eta=0`. Greedy rejects every first split, while an explicit three-split tree has an absolute gap lower bound asymptotic to `m-2`.

Why it matters:

- it proves the problem is not solved by local improvement;
- it makes the project look like research, not engineering.

## Strong Optional Result

**Theorem D: Exact optimality on a restricted distribution family**

Identify a clean family, such as single hot interval or symmetric bimodal mass, where a specific constructive policy is provably optimal.

This is strong, but optional. It should not delay Theorems A and B.

## Generalized Positive Result

**Theorem E: exact optimality for any deterministic executable interval fallback**

The leaf base case may use a full per-key cost profile rather than a uniform
`ceil(log2 |I|)` bound. The materialized split recurrence and Pareto-dominance
proof remain exact. This closes the mathematical/runtime gap and makes the
fixed-round formulation a special case.

## Fixed-Candidate DRO Result

**Theorem F: exact worst-case expectation in a finite total-variation ball**

Sorted probability-mass transfer computes the exact maximum expected
per-key execution cost over the TV ambiguity set. The implementation is
cross-checked against exhaustive probability grids.

This certifies each generated candidate's robust score. It does not prove that
a heuristic portfolio contains the globally optimal tree.

## Highest-Value Open Theorem

Prove an additive approximation guarantee for mass-quantile candidate pruning
with mandatory size-boundary thresholds. This is intentionally still marked
open; empirical 0.04% mean relative gap is not a theorem.
