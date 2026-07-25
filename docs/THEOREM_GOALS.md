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

## Best Negative Result

**Theorem C or Proposition C: A natural greedy baseline can be arbitrarily suboptimal**

Construct an instance family where a simple prediction-only or balanced-splitting strategy wastes the split budget and incurs asymptotically worse cost than the CertiGap optimum.

Why it matters:

- it proves the problem is not trivial;
- it makes the project look like research, not engineering.

## Strong Optional Result

**Theorem D: Exact optimality on a restricted distribution family**

Identify a clean family, such as single hot interval or symmetric bimodal mass, where a specific constructive policy is provably optimal.

This is strong, but optional. It should not delay Theorems A and B.
