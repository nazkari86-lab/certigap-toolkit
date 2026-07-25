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

### What Still Needs To Be Written Formally

- precise induction over interval length and split budget;
- explicit domination lemma for frontier compression;
- tie-handling and boundary cases for singleton intervals.

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

## Proposition C: A Greedy Baseline Can Be Arbitrarily Suboptimal

### Intended Family

Use a family with:

- a medium-sized hot interval;
- a cold surrounding region;
- a split budget large enough that the best solution requires an initially neutral split followed by highly profitable refinement.

### Proof Strategy

1. Construct instances where no single root split improves the objective enough locally.
2. Show that after one specific preparatory split, a second split creates a large gain by isolating the hot region.
3. A one-step greedy algorithm refuses the first split because it evaluates only immediate improvement.
4. The global optimum uses both splits and beats the greedy solution by a gap bounded away from zero.
5. Scale the family so that the absolute or relative gap grows with the instance size.

### Prototype Evidence

The current benchmark already exposes this behavior on `hot_middle` instances:

- many rows where greedy has a substantial gap;
- beam search recovers the exact optimum.

That empirical pattern is the starting point for the formal counterexample family.
