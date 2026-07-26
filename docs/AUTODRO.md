# CertiGap-AutoDRO

## Purpose

AutoDRO chooses a concrete search structure instead of requiring a user to
manually select `B`, solver, robustness parameter, and interval fallback.
Selection is constrained by an optional memory limit and evaluated with an
explicit execution-cost model.

## Statistical Uncertainty

For integer query counts with total sample size `N`, AutoDRO constructs an
empirical distribution and applies additive pseudocount smoothing. The sampling
radius uses the finite-alphabet multinomial inequality

`P(||p_hat - p||_1 >= epsilon) <= 2^n exp(-N epsilon^2 / 2)`.

This is the conservative finite-alphabet form of the L1 deviation bound from
Weissman et al., *Inequalities for the L1 Deviation of the Empirical
Distribution* (2003).

The reported total-variation radius is half the resulting L1 radius plus the
exact TV distance introduced by smoothing. The sum follows from the triangle
inequality and is capped at one. A user may instead supply a radius directly;
this is required for fractional frequency weights that are not observation
counts.

## Exact Fixed-Candidate DRO Evaluation

For a candidate with per-key execution costs `c_i`, AutoDRO computes

`max_q sum_i q_i c_i`

subject to `TV(q, p_nominal) <= rho`.

The evaluator transfers probability mass from the currently cheapest keys to
the currently most expensive keys until the TV budget or profitable transfer
capacity is exhausted.

**Theorem F.** The transfer algorithm returns the exact worst-case expectation
for a finite total-variation ball.

**Proof.** A feasible change can be decomposed into transfers of equal mass from
donor coordinates to receiver coordinates. An exchange that removes mass from
a donor with larger cost while a cheaper donor has removable mass cannot be
optimal. Likewise, adding mass to a cheaper receiver while a more expensive
receiver has capacity cannot be optimal. Repeatedly exchanging such pairs gives
the sorted transfer rule without decreasing the objective. The algorithm stops
only when the TV budget is exhausted or no positive-cost transfer remains.
Therefore no feasible transfer can further increase the expectation. `QED`

## Portfolio Selection

For every requested budget and training robustness value, AutoDRO constructs
trees with the configured solver portfolio and evaluates both fixed-round and
midpoint-binary executable fallbacks. Duplicate tree/fallback pairs are removed.
Candidates that exceed the memory limit are rejected.

The selected score is

`DROMean + tail_weight * MaxCost + memory_weight * Bytes + build_weight * Splits`.

Exact DP candidates are included by default only when `n <= exact_limit`.

## Guarantee Boundary

- Worst-case expectation is exact for each generated candidate.
- Selection is exact over the enumerated, deduplicated portfolio.
- The result is not claimed globally optimal over every possible tree unless
  the portfolio itself exhausts the feasible tree family.
- Default costs are comparison-equivalent units, not nanoseconds.
- Nanosecond claims require calibration samples from the deployment target.
- Re-fitting after additional integer counts is supported through
  `update_counts`; low-latency in-place tree mutation is not yet implemented.
