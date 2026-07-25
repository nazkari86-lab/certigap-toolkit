# Proof Sketches

## Theorem A: Exact Optimality of the Frontier Dynamic Program

### Statement

For the static budgeted partial-search model, the frontier DP returns a tree minimizing

`(1 - eta) * average_cost + eta * max_cost`

among all valid trees with at most `B` splits.

### Proof Sketch

1. Define the subproblem on an interval `[l, r]` with split budget `b`.
2. Any valid tree on `[l, r]` is either:
   - a single interval leaf, or
   - a root split at some threshold `k`, followed by valid left and right subtrees whose budgets sum to `b - 1`.
3. The average-cost contribution of a root split decomposes additively:
   - every key in `[l, r]` pays one extra comparison;
   - the remaining cost is exactly the cost of the left and right subtrees.
4. The worst-case cost also decomposes structurally:
   - after one root split, the resulting worst-case cost is `1 + max(left_max, right_max)`.
5. Therefore each feasible tree induces a pair
   - `(average_cost, max_cost)`
   obtainable from smaller subproblems.
6. The DP enumerates all such decompositions and compresses only dominated states:
   - if state `A` has no larger max-cost and strictly smaller average-cost than state `B`,
     then `B` can never be optimal for any `eta in [0,1]`.
7. Since compression removes only dominated states, the Pareto frontier is preserved exactly.
8. Minimizing `(1 - eta) * average_cost + eta * max_cost` over the preserved frontier yields the true optimum.

### Formal Status

The complete induction, dominance lemma, tie handling, and singleton boundary cases are written in `FORMAL_RESULTS.md`.

## Theorem B: Contamination Robustness

### Statement

If the true query distribution is

`p = (1 - eta) * p_hat + eta * q`,

where `q` is arbitrary, then the worst-case expected cost of tree `T` under this model equals

`(1 - eta) * sum_i p_hat_i * C_T(i) + eta * max_i C_T(i)`.

### Proof Sketch

1. Expand expectation linearly:
   - `E_p[C_T] = (1 - eta) E_p_hat[C_T] + eta E_q[C_T]`.
2. Since `q` is arbitrary over the discrete key set, the adversary can place all mass on the key with largest cost.
3. Therefore
   - `max_q E_q[C_T] = max_i C_T(i)`.
4. Substitute this into the objective to obtain the CertiGap robust objective exactly.

### Why This Matters

- it turns `eta` into a mathematically meaningful distrust parameter;
- it justifies the objective without informal “trade-off” language.

## Theorem C: A Greedy Baseline Can Be Arbitrarily Suboptimal

The proved family uses `n=2^m`, `B=3`, `eta=0`, and two central hot keys of weight `W=n*m`.
Every first split is either neutral or strictly worse, so one-step greedy stops. A fixed three-split witness isolates the two hot keys at depth two and yields an absolute gap lower bound asymptotic to `m-2`.

The full derivation and code generator are in `FORMAL_RESULTS.md` and `power_of_two_greedy_family`.
