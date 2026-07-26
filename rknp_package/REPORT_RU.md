# Отчёт РКНП

## 1. Тема проекта

**CertiGap-AutoDRO: автоматический выбор робастной частичной поисковой структуры**

## 2. Актуальность

Большинство классических поисковых структур предполагают, что весь порядок данных должен быть полностью материализован. Однако в условиях ограниченного бюджета сравнений это не всегда рационально. Если часть элементов запрашивается редко, возможно выгоднее не тратить структурный бюджет на их полное разделение, а оставить их внутри интервалов и уточнять только при фактическом запросе.

Дополнительная проблема состоит в том, что прогноз будущих запросов может быть неверным. Поэтому требуется структура, которая одновременно:

- использует прогноз, если он полезен;
- не деградирует слишком сильно, если прогноз ошибочен;
- позволяет независимо проверить качество найденного решения.

## 3. Цель работы

Разработать и исследовать алгоритм построения частичного поискового дерева, который при ограниченном числе разделений минимизирует робастную стоимость реального fallback-поиска и возвращает независимо проверяемые структуру, стоимость и границы.

## 4. Основная идея

CertiGap не строит полное поисковое дерево на всех ключах. Вместо этого он выбирает, какие пороговые сравнения материализовать заранее, а какие диапазоны оставить неразрешёнными interval-leaf узлами. Стоимость поиска в таком листе равна глубине листа плюс стоимость резервного бинарного поиска внутри интервала.

Оптимизируется робастная целевая функция:

- средняя стоимость при прогнозном распределении;
- худшая стоимость при ошибке прогноза;
- параметр недоверия `eta`, задающий силу робастности.

## 5. Научная новизна

- рассматривается не полное упорядочивание, а **частичная материализация порядка** при явном бюджете разделений;
- используется робастная contamination-модель для учёта недоверия к прогнозу;
- вместе со структурой возвращаются проверяемая стоимость, entropy-нижняя граница и, на малых задачах, exhaustive proof trace;
- exact DP обобщён на реальные per-key стоимости midpoint binary search и пользовательские fallback-профили;
- AutoDRO автоматически выбирает структуру по query counts, memory limit и измеряемой cost model;
- проект сочетает точный алгоритм, эвристику и независимую проверку результата.

## 6. Методы

- frontier dynamic programming;
- beam-search heuristic;
- brute-force oracle для малых экземпляров;
- entropy lower bound;
- Lagrangian lower bound;
- независимый structural checker.

## 7. Текущие результаты

- Rows analyzed: `240`
- Mean greedy absolute objective gap vs exact: `0.0986`
- Mean beam absolute objective gap vs exact: `0.0006`
- Mean greedy relative objective gap vs exact: `2.80%`
- Mean beam relative objective gap vs exact: `0.02%`
- Beam strictly improves on greedy in `104` rows
- Beam matches exact in `237` rows

Дополнительно в текущем прототипе найдены примеры, где:

- beam-search строго улучшает greedy baseline;
- во многих случаях beam совпадает с exact optimum;
- на proof-sized случаях branch-and-bound trace независимо подтверждает оптимальность.

## 8. Примеры сертификатов

# CertiGap Certificate Examples

## zipf, n=8, B=2, eta=0.15

- Upper bound: `2.879325`
- Lower bound: `2.526758`
- Reported entropy-bound gap: `0.139534`
- Reported exact diagnostic gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 8], 'threshold': 2}, {'interval': [3, 8], 'threshold': 4}]`

## hot_middle, n=12, B=3, eta=0.15

- Upper bound: `3.291667`
- Lower bound: `2.694186`
- Reported entropy-bound gap: `0.221767`
- Reported exact diagnostic gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 12], 'threshold': 6}, {'interval': [7, 12], 'threshold': 8}, {'interval': [1, 6], 'threshold': 4}]`

## hot_tail, n=16, B=4, eta=0.30

- Upper bound: `3.854545`
- Lower bound: `2.894329`
- Reported entropy-bound gap: `0.331758`
- Reported exact diagnostic gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 16], 'threshold': 13}, {'interval': [14, 16], 'threshold': 14}, {'interval': [1, 13], 'threshold': 8}, {'interval': [9, 13], 'threshold': 12}]`

# CertiGap Speed and Quality Summary

## Small Cases With Exact Reference

- Exact mean time: `2.537 ms`
- Beam mean time: `4.670 ms`
- Greedy mean time: `0.224 ms`
- Balanced mean time: `0.013 ms`
- Weighted mean time: `0.017 ms`
- Beam mean absolute objective gap vs exact: `0.000979`
- Greedy mean absolute objective gap vs exact: `0.114157`
- Balanced mean absolute objective gap vs exact: `0.447373`
- Weighted mean absolute objective gap vs exact: `0.198609`
- Beam mean relative objective gap vs exact: `0.03%`
- Greedy mean relative objective gap vs exact: `3.48%`

## Large Cases Without Exact Reference

- Beam mean time: `53.103 ms`
- Greedy mean time: `1.448 ms`
- Balanced mean time: `0.024 ms`
- Weighted mean time: `0.039 ms`

## Solver Tradeoff

- `exact` is the reference solver for the measured small instances.
- `beam` is near-exact on the measured small cases, but is not faster than exact there; this benchmark does not establish a crossover point.
- `greedy` is usually faster but can be substantially worse on structured skewed tasks.
- `balanced` and `weighted` are cheap baselines, but quality is systematically weaker on skewed workloads.

# Greedy Counterexample Family

## Proven Infinite Family

For every `m >= 3`, set:

- `n = 2^m`;
- split budget `B = 3`;
- `eta = 0`;
- hot block `[n/2, n/2 + 1]` with each hot key weight `W = n*m`;
- all other keys weight `1`.

The one-step greedy implementation makes no split: the central split is neutral and every off-centre split makes the two hot keys one comparison more expensive. A three-split witness isolates both hot keys at depth two.

The resulting greedy-to-optimum absolute objective gap is at least

`[2W(m - 2) - (n - 2)] / [2W + n - 2]`,

which is positive for every `m >= 3` and grows asymptotically as `m - 2`.

The executable construction is `power_of_two_greedy_family(m)`; generated rows for `m=3..10` are in `results/power_of_two_greedy_family.csv`.

## Historical Empirical Family

The most important discovered family has the following structure:

- the key set is contiguous and sorted;
- a short hot block of width `2` sits near the center;
- all surrounding keys are cold;
- the split budget is at least `3`.

Empirically, a one-step greedy rule often spends its first split too far away from the hot block, because that split gives the largest immediate reduction on a large cold region. Once that happens, the remaining budget is insufficient to isolate both hot keys efficiently.

By contrast, the global optimum first places a preparatory split near the hot block, then spends the remaining splits to isolate the two hot keys.

## Canonical Prototype Instance

As of **July 25, 2026**, the strongest automatically discovered fast-mode instance is:

- `n = 10`
- `B = 3`
- `eta = 0.00`
- hot block start `5`
- hot block width `2`
- hot weight `24.0`

Observed gaps:

- greedy gap vs exact: `1.642857`
- beam gap vs exact: `0.000000`

## Candidate Formal Proposition

There exists an infinite family of hot-block instances for which:

1. one-step greedy chooses a first split outside the eventual optimal refinement zone;
2. the exact optimum uses a sequence of preparatory splits adjacent to the hot block;
3. the objective gap between greedy and optimum stays bounded away from zero and can be scaled upward with the hot-to-cold weight ratio.

## What Still Needs To Be Proved

- a closed-form description of the family as a function of `m`;
- an argument that greedy's locally best first split is uniquely outside the optimal refinement zone;
- a lower bound on the resulting objective gap.

## Why This Matters

This family is the cleanest route to a real negative result in the project:

- it explains why CertiGap is not solved by a trivial local rule;
- it justifies the need for exact DP or stronger search;
- it strengthens the project beyond “we tried a few heuristics”.

## 9. Доказательная часть

# Formal Results

## Definitions

Let `T` be a valid CertiGap tree on ranks `1..n`.

- Every internal node is a threshold comparison `x <= x_k?`.
- Every leaf is a contiguous unresolved interval `[l, r]`.
- The depth of the root is `0`.
- If key `i` reaches interval leaf `I = [l, r]` at depth `d`, then
  `C_T(i) = d + ceil(log2(|I|))`.

For a probability vector `p = (p_1, ..., p_n)`:

- `Avg_p(T) = sum_i p_i C_T(i)`
- `Max(T) = max_i C_T(i)`

For distrust parameter `eta in [0,1]`:

- `J_eta(T) = (1 - eta) Avg_p_hat(T) + eta Max(T)`

The split budget of `T` is the number of internal nodes and must satisfy `|T| <= B`.

## Lemma 1: Structural Decomposition

Every valid CertiGap tree on interval `[l, r]` with budget `b` is exactly one of:

1. a single interval leaf `[l, r]`, or
2. a root split at some `k` with `l <= k < r`, whose left subtree is valid on `[l, k]`,
   whose right subtree is valid on `[k+1, r]`, and whose subtree budgets sum to `b - 1`.

### Proof

If the root is a leaf, we are in case 1.
Otherwise the root is a threshold comparison and so must split the contiguous interval `[l, r]`
into two contiguous subintervals `[l, k]` and `[k+1, r]` for some `k`.
Because CertiGap trees preserve contiguity, the left and right subtrees are valid subtrees on those intervals.
The root itself consumes one split, so the remaining budgets must sum to `b - 1`.
No other form is possible. `QED`

## Lemma 2: Additive Average-Cost Recurrence

Suppose tree `T` on `[l, r]` has root split at `k`, left subtree `T_L`, right subtree `T_R`, and let

- `P(l, r) = sum_{i=l}^r p_hat_i`.

Then

`Avg_p_hat(T) = P(l, r) + Avg_p_hat(T_L) + Avg_p_hat(T_R)`.

### Proof

Every key in `[l, r]` pays one comparison at the root, contributing total mass `P(l, r)`.
After the root, keys routed left incur exactly the cost of `T_L`, and keys routed right incur exactly the cost of `T_R`.
Therefore the expectation decomposes additively. `QED`

## Lemma 3: Worst-Case Recurrence

Under the same assumptions,

`Max(T) = 1 + max(Max(T_L), Max(T_R))`.

### Proof

Every root-to-leaf path in `T` contains the root comparison plus a path entirely inside either `T_L` or `T_R`.
So the largest key cost is exactly one plus the larger subtree maximum. `QED`

## Lemma 4: Dominance Elimination Is Safe

Let states `S1 = (A1, M1)` and `S2 = (A2, M2)` satisfy

- `A1 <= A2`
- `M1 <= M2`
- and at least one inequality is strict.

Then for every `eta in [0,1]`,

`(1 - eta) A1 + eta M1 <= (1 - eta) A2 + eta M2`,

with strict inequality whenever `eta` gives positive weight to a strict component.

### Proof

Both coefficients `(1 - eta)` and `eta` are nonnegative on `[0,1]`.
Multiplying coordinatewise inequalities by nonnegative coefficients and summing preserves the inequality. `QED`

## Theorem A: Exact Optimality of the Frontier Dynamic Program

For every interval `[l, r]`, budget `b`, and distrust parameter `eta in [0,1]`,
the frontier DP returns a tree minimizing

`(1 - eta) Avg_p_hat(T) + eta Max(T)`

among all valid trees on `[l, r]` with at most `b` splits.

### Proof

We proceed by induction on the pair `(r - l, b)` ordered lexicographically.

### Base Cases

If `l = r`, there is only one key. The only valid tree is the leaf `[l, l]`, so the DP is exact.

If `b = 0`, no split is allowed. The only valid tree is the leaf `[l, r]`, so the DP is exact.

### Inductive Step

Assume the theorem holds for all smaller subproblems.
Consider a target subproblem `[l, r]` with budget `b`.

By Lemma 1, every valid tree is either:

1. the stop state `[l, r]`, or
2. a root split at some `k` with a budget partition `b_L + b_R = b - 1`.

For case 1, the DP explicitly includes the corresponding leaf state.

For case 2, by the induction hypothesis the left and right frontiers produced by the DP contain exactly the nondominated achievable states for `[l, k]` and `[k+1, r]`.
Combining any such pair with root split `k` yields a valid achievable state on `[l, r]`.
By Lemma 2 and Lemma 3, its average and maximum components are exactly those used by the recurrence implemented in the DP.

Therefore before compression, the DP enumerates every achievable state of every valid tree on `[l, r]`.

The compression step removes only dominated states.
By Lemma 4, a dominated state can never beat its dominator for any `eta in [0,1]`.
Hence compression preserves the entire set of potentially optimal states.

Finally, the DP selects the state minimizing

`(1 - eta) A + eta M`

over the preserved frontier.
Since every valid tree corresponds to some enumerated state and no potentially optimal state was removed,
the selected tree is globally optimal. `QED`

## Theorem B: Contamination Robustness Identity

Let the true query distribution be

`p = (1 - eta) p_hat + eta q`,

where `q` is any probability distribution over the keys.
Then for every tree `T`,

`max_q Avg_p(T) = (1 - eta) Avg_p_hat(T) + eta Max(T)`.

### Proof

By linearity of expectation,

`Avg_p(T) = (1 - eta) Avg_p_hat(T) + eta Avg_q(T)`.

The first term is independent of `q`.
So maximizing over `q` reduces to maximizing `Avg_q(T)`.

Because `q` ranges over all probability distributions on a finite set, its expectation of `C_T(i)` is maximized by placing all mass on a maximizer of `C_T(i)`.
Hence

`max_q Avg_q(T) = max_i C_T(i) = Max(T)`.

Substituting yields

`max_q Avg_p(T) = (1 - eta) Avg_p_hat(T) + eta Max(T)`.

This is exactly the CertiGap robust objective. `QED`

## Current Formal Status

Theorems A and B are proof-complete at the mathematical level used by the prototype.
Theorem C below gives a concrete asymptotic negative result for the implemented one-step greedy rule.
The remaining open work is stronger approximation/structural results and external or machine-assisted formal review.

## Theorem C: An Infinite Family Where One-Step Greedy Is Arbitrarily Suboptimal

For every integer `m >= 3`, let `n = 2^m`, let `B = 3`, let `eta = 0`, and assign weight
`W = n*m` to keys `n/2` and `n/2 + 1` and weight `1` to every other key.
Then the implemented one-step greedy algorithm makes no split, while a valid three-split tree has objective at least

`[2W(m - 2) - (n - 2)] / [2W + n - 2]`

smaller than greedy. Consequently the greedy absolute objective gap grows without bound as `m` grows.

### Proof

The unsplit leaf has cost `m` for every key because `n = 2^m`.
Consider any first split at threshold `k`.

If `k = n/2`, both children have size `n/2`, so every key still has cost `1 + log2(n/2) = m`; this split has zero gain.

If `k < n/2`, both hot keys lie in the larger right child and their cost rises to `m + 1`.
Let `c = 1 + ceil(log2(k))` be the left-child cost. The unnormalized change in average cost is

`k(c - m) + (n - k - 2) + 2W`.

Since `c >= 1` and `k <= n/2 - 1`, this is at least

`2W - (n/2 - 1)(m - 2) > 0`

for `W = n*m`. The case `k > n/2` is symmetric. Thus no first split strictly improves the objective, and the greedy rule stops at the unsplit leaf.

Now use the explicit tree with root split at `n/2`, a left split at `n/2 - 1`, and a right split at `n/2 + 1`.
Both hot keys have cost `2`; each cold key has cost `m + 1`.
Its objective is therefore

`[4W + (n - 2)(m + 1)] / [2W + n - 2]`.

Subtracting this from greedy's cost `m` gives exactly

`[2W(m - 2) - (n - 2)] / [2W + n - 2]`.

This is positive for every `m >= 3` and is asymptotic to `m - 2`, so the gap is unbounded. Since the optimum is no worse than this explicit tree, the same expression is a valid lower bound on greedy's gap to optimum. `QED`

## Proposition D: Cost-Cap DP Exactness

For a fixed cap `h`, the cost-cap recurrence stores the minimum average cost over all valid trees whose relative maximum cost is at most `h`.
The leaf case is feasible exactly when `ceil(log2(|I|)) <= h`; every split decreases the remaining cap by one for both children.
Induction on interval length and budget proves the recurrence. Minimizing the resulting candidates over `h` recovers the optimum of `J_eta`, because every tree appears at its own maximum cost cap.

The repository cross-validates this recurrence against both the Pareto-frontier DP and brute force on the generated small-instance suite.

## Theorem E: Exact Optimality With Executable Fallback Profiles

Let `F(l,r,i)` be any deterministic non-negative per-key comparison cost for
resolving key `i` inside interval `[l,r]`. Replacing the fixed leaf cost with

- `A_F(l,r) = sum_i p_hat_i F(l,r,i)`;
- `M_F(l,r) = max_i F(l,r,i)`

preserves the split recurrences in Lemmas 2 and 3. The structural induction and
dominance argument of Theorem A therefore apply unchanged. The generalized
frontier DP is exact for every fixed fallback profile.

The full statement, relation to height-limited alphabetic trees, implementation,
and scope are given in `GENERALIZED_FALLBACK.md`.

## Theorem F: Exact Worst-Case Expectation in a Finite TV Ball

Let `p` be a nominal distribution, `c_i` finite per-key execution costs, and
`rho` a total-variation radius. The sorted mass-transfer algorithm implemented
by `worst_case_tv_expectation` returns

`max_q sum_i q_i c_i`

over all distributions satisfying `TV(q,p) <= rho`.

Every feasible probability change decomposes into equal donor-to-receiver mass
transfers. If a solution removes mass from a more expensive donor while a
cheaper donor still has removable mass, exchanging the donors cannot decrease
the objective. The symmetric exchange applies to receivers. Thus an optimum
exists that transfers mass in ascending donor-cost and descending receiver-cost
order. The algorithm performs exactly these transfers until the TV budget or
all profitable capacity is exhausted. `QED`

This theorem certifies the robust score of a fixed candidate. AutoDRO selection
is globally exact only over the submitted candidate portfolio.

# Generalized Executable Fallback Model

## Motivation

The original CertiGap model assigns every key in an unresolved interval
`[l,r]` the conservative fixed-round cost `ceil(log2(r-l+1))`. Real fallback
implementations may have different per-key costs. For example, midpoint
lower-bound search on three keys has costs `(2,2,1)`.

The generalized model closes that model/runtime gap without changing the
materialized-prefix interpretation.

## Definition

Let `F(l,r,i)` be the non-negative integer comparison cost of a deterministic
fallback policy for key `i` in interval `[l,r]`. If key `i` reaches that leaf
at materialized depth `d`, define

`C_T^F(i) = d + F(l,r,i)`.

The robust objective remains

`J_eta^F(T) = (1-eta) sum_i p_hat_i C_T^F(i) + eta max_i C_T^F(i)`.

`fixed_rounds` and the exact comparison profile of executable midpoint binary
search are included. A user may also supply a deterministic custom profile.

## Theorem E: Exactness For Any Fixed Fallback

For every deterministic fallback profile `F`, the generalized frontier dynamic
program returns a tree with at most `B` materialized splits minimizing
`J_eta^F`.

### Proof

For a leaf `[l,r]`, its achievable state is exactly

- `A_F(l,r) = sum_{i=l}^r p_hat_i F(l,r,i)`;
- `M_F(l,r) = max_{i=l}^r F(l,r,i)`.

For a materialized split at `k`, every key pays one new comparison. Therefore
the recurrence remains

- `A = P(l,r) + A_left + A_right`;
- `M = 1 + max(M_left,M_right)`.

The structural decomposition of every valid partial tree is unchanged. By
induction on interval length and budget, the recurrence enumerates every
achievable `(A,M)` pair. Pareto dominance is safe because both coefficients in
`(1-eta)A + eta M` are non-negative. Selecting the minimum retained state is
therefore globally optimal. `QED`

## Relation To Classical Alphabetic Trees

Expanding every unresolved interval leaf with its deterministic fallback tree
maps a CertiGap solution to a full alphabetic decision tree. CertiGap optimizes
over the restricted class in which:

1. at most `B` prefix comparisons are freely materialized;
2. every remaining subtree must equal the selected fallback completion.

This differs from a height-limited alphabetic tree, where all internal nodes
are optimized and the constraint is maximum depth rather than the number of
freely materialized prefix nodes.

## Implementation And Verification

- `generalized_frontier_dp_best` implements Theorem E.
- `midpoint_binary_profile` reproduces per-key comparison counts of midpoint
  lower-bound search.
- `verify_serialized_tree_exact` independently recomputes fixed-round tree
  objectives from integer counts and rational `eta`, without floating-point
  dominance or `EPS`.

The rational verifier proves submitted-tree arithmetic, not global optimality.
Global exactness is established by the DP proof and small-instance independent
cross-validation.

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

# CertiGap-AutoDRO Distribution-Shift Benchmark

Selection uses only the training counts and a fixed TV radius of `0.2`. The test distribution is used only after selection.

| Scenario | n | Method | Selected solver | Fallback | Splits | Bytes | Test mean | Test max |
|---|---:|---|---|---|---:|---:|---:|---:|
| hot_reversal | 32 | autodro | beam | midpoint_binary | 2 | 368 | 6.63636 | 7.00000 |
| hot_reversal | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 6.82955 | 7.00000 |
| hot_reversal | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 5.00000 | 5.00000 |
| hot_reversal | 64 | autodro | beam | midpoint_binary | 2 | 496 | 7.67614 | 8.00000 |
| hot_reversal | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 7.82955 | 8.00000 |
| hot_reversal | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 6.00000 | 6.00000 |
| partial_hot_drift | 32 | autodro | beam | midpoint_binary | 2 | 368 | 4.39836 | 7.00000 |
| partial_hot_drift | 32 | fixed_beam | beam | fixed_rounds | 2 | 368 | 4.48236 | 7.00000 |
| partial_hot_drift | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 5.00000 | 5.00000 |
| partial_hot_drift | 64 | autodro | beam | midpoint_binary | 2 | 496 | 5.41228 | 8.00000 |
| partial_hot_drift | 64 | fixed_beam | beam | fixed_rounds | 2 | 496 | 5.48236 | 8.00000 |
| partial_hot_drift | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 6.00000 | 6.00000 |
| stationary_zipf | 32 | autodro | beam | fixed_rounds | 3 | 464 | 4.30368 | 6.00000 |
| stationary_zipf | 32 | fixed_beam | beam | fixed_rounds | 4 | 560 | 4.24755 | 6.00000 |
| stationary_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 5.00000 | 5.00000 |
| stationary_zipf | 64 | autodro | beam | midpoint_binary | 4 | 688 | 4.99841 | 7.00000 |
| stationary_zipf | 64 | fixed_beam | beam | fixed_rounds | 4 | 688 | 5.01343 | 7.00000 |
| stationary_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 6.00000 | 6.00000 |
| uniform_to_zipf | 32 | autodro | beam | fixed_rounds | 0 | 176 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_beam | beam | fixed_rounds | 0 | 176 | 5.00000 | 5.00000 |
| uniform_to_zipf | 32 | fixed_balanced | balanced | fixed_rounds | 4 | 560 | 5.00000 | 5.00000 |
| uniform_to_zipf | 64 | autodro | beam | fixed_rounds | 0 | 304 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_beam | beam | fixed_rounds | 0 | 304 | 6.00000 | 6.00000 |
| uniform_to_zipf | 64 | fixed_balanced | balanced | fixed_rounds | 4 | 688 | 6.00000 | 6.00000 |

## Aggregate

- AutoDRO beats fixed beam on shifted/stationary test mean in `5/8` cases.
- AutoDRO beats fixed balanced on shifted/stationary test mean in `4/8` cases.

## Scope

This is a deterministic comparison-cost experiment, not a hardware-latency claim. It tests selection under distribution shift; an external trace replay remains required.

# C++ Post-Build Lookup Microbenchmark

This measures only rank lookup after each structure is built. Times are local-machine measurements, not cross-machine or production claims.

- Queries are sampled from each workload distribution with a deterministic PRNG.
- CertiGap uses the candidate-pruned C++ beam (`B=min(6,n-1)`, `eta=0.15`, width 32, candidate limit 16).
- CertiGap and budgeted trees use at most `B=min(6,n-1)` materialized splits and fixed-round interval fallback.
- `balanced_full_reference` and `std_lower_bound` are explicitly unconstrained references, not equal-budget competitors.
- Reported p95 is across repeated batch means; it is not single-query tail latency.
- Total index bytes include the shared integer key array; auxiliary bytes exclude allocator overhead.

| Workload | Solver | n | B | Median batch ns/query | p95 batch ns/query | Nodes | Auxiliary bytes | Total bytes |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| uniform | certigap_pruned | 1000 | 6 | 16.574 | 16.909 | 1 | 48 | 4048 |
| uniform | balanced_budgeted | 1000 | 6 | 18.637 | 19.711 | 13 | 624 | 4624 |
| uniform | weighted_budgeted | 1000 | 6 | 18.592 | 19.480 | 13 | 624 | 4624 |
| uniform | balanced_full_reference | 1000 | 999 | 16.546 | 18.773 | 1999 | 95952 | 99952 |
| uniform | std_lower_bound | 1000 | 0 | 15.670 | 15.947 | 0 | 0 | 4000 |
| zipf | certigap_pruned | 1000 | 6 | 26.138 | 27.782 | 11 | 528 | 4528 |
| zipf | balanced_budgeted | 1000 | 6 | 15.908 | 16.136 | 13 | 624 | 4624 |
| zipf | weighted_budgeted | 1000 | 6 | 25.656 | 27.144 | 13 | 624 | 4624 |
| zipf | balanced_full_reference | 1000 | 999 | 15.514 | 15.666 | 1999 | 95952 | 99952 |
| zipf | std_lower_bound | 1000 | 0 | 15.312 | 17.053 | 0 | 0 | 4000 |
| hot_tail | certigap_pruned | 1000 | 6 | 22.645 | 31.178 | 13 | 624 | 4624 |
| hot_tail | balanced_budgeted | 1000 | 6 | 15.471 | 15.593 | 13 | 624 | 4624 |
| hot_tail | weighted_budgeted | 1000 | 6 | 24.494 | 24.996 | 13 | 624 | 4624 |
| hot_tail | balanced_full_reference | 1000 | 999 | 16.198 | 16.809 | 1999 | 95952 | 99952 |
| hot_tail | std_lower_bound | 1000 | 0 | 15.600 | 16.460 | 0 | 0 | 4000 |
| uniform | certigap_pruned | 10000 | 6 | 28.711 | 41.829 | 5 | 240 | 40240 |
| uniform | balanced_budgeted | 10000 | 6 | 27.275 | 29.340 | 13 | 624 | 40624 |
| uniform | weighted_budgeted | 10000 | 6 | 27.286 | 31.902 | 13 | 624 | 40624 |
| uniform | balanced_full_reference | 10000 | 9999 | 55.459 | 58.687 | 19999 | 959952 | 999952 |
| uniform | std_lower_bound | 10000 | 0 | 38.827 | 40.326 | 0 | 0 | 40000 |
| zipf | certigap_pruned | 10000 | 6 | 27.978 | 28.682 | 13 | 624 | 40624 |
| zipf | balanced_budgeted | 10000 | 6 | 23.843 | 24.185 | 13 | 624 | 40624 |
| zipf | weighted_budgeted | 10000 | 6 | 28.185 | 29.325 | 13 | 624 | 40624 |
| zipf | balanced_full_reference | 10000 | 9999 | 51.785 | 52.753 | 19999 | 959952 | 999952 |
| zipf | std_lower_bound | 10000 | 0 | 44.082 | 46.504 | 0 | 0 | 40000 |
| hot_tail | certigap_pruned | 10000 | 6 | 23.108 | 24.370 | 13 | 624 | 40624 |
| hot_tail | balanced_budgeted | 10000 | 6 | 25.067 | 27.748 | 13 | 624 | 40624 |
| hot_tail | weighted_budgeted | 10000 | 6 | 26.932 | 27.520 | 13 | 624 | 40624 |
| hot_tail | balanced_full_reference | 10000 | 9999 | 49.320 | 51.558 | 19999 | 959952 | 999952 |
| hot_tail | std_lower_bound | 10000 | 0 | 38.837 | 47.130 | 0 | 0 | 40000 |

## Matched-Budget Interpretation

- CertiGap has lower median batch lookup time than `balanced_budgeted` in `2/6` measured workload-size cases.
- CertiGap has lower median batch lookup time than `weighted_budgeted` in `4/6` measured workload-size cases.

## Limits

This is not a hardware-routing, cache-miss, or external-library benchmark. It is reproducible CPU-level evidence that the exported CertiGap decision tree executes real lookups with an explicit storage footprint. Production claims require a target key encoding, allocator, CPU, and independent external baselines.

## 10. Вывод

На текущем этапе CertiGap оформлен как воспроизводимый research-прототип: есть generalized exact solver, две независимые exact-рекуррентности, rational checker, proof trace, C++ heuristic и matched-budget benchmark. Теоремы ещё не проходили внешнюю или машинную формальную проверку. Главный оставшийся теоретический шаг — получить нетривиальную approximation guarantee для candidate-pruned solver; главный внешний шаг — независимое воспроизведение и production pilot.
