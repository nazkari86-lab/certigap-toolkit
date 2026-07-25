# Отчёт РКНП

## 1. Тема проекта

**CertiGap: робастные частичные поисковые деревья с ограниченным бюджетом разделений и сертифицируемой близостью к оптимуму**

## 2. Актуальность

Большинство классических поисковых структур предполагают, что весь порядок данных должен быть полностью материализован. Однако в условиях ограниченного бюджета сравнений это не всегда рационально. Если часть элементов запрашивается редко, возможно выгоднее не тратить структурный бюджет на их полное разделение, а оставить их внутри интервалов и уточнять только при фактическом запросе.

Дополнительная проблема состоит в том, что прогноз будущих запросов может быть неверным. Поэтому требуется структура, которая одновременно:

- использует прогноз, если он полезен;
- не деградирует слишком сильно, если прогноз ошибочен;
- позволяет независимо проверить качество найденного решения.

## 3. Цель работы

Разработать и исследовать алгоритм построения частичного поискового дерева, который при ограниченном числе разделений минимизирует робастную стоимость поиска и возвращает проверяемый сертификат близости к оптимуму.

## 4. Основная идея

CertiGap не строит полное поисковое дерево на всех ключах. Вместо этого он выбирает, какие пороговые сравнения материализовать заранее, а какие диапазоны оставить неразрешёнными interval-leaf узлами. Стоимость поиска в таком листе равна глубине листа плюс стоимость резервного бинарного поиска внутри интервала.

Оптимизируется робастная целевая функция:

- средняя стоимость при прогнозном распределении;
- худшая стоимость при ошибке прогноза;
- параметр недоверия `eta`, задающий силу робастности.

## 5. Научная новизна

- рассматривается не полное упорядочивание, а **частичная материализация порядка** при явном бюджете разделений;
- используется робастная contamination-модель для учёта недоверия к прогнозу;
- вместе со структурой возвращается **сертификат качества**: верхняя оценка, нижняя оценка и разрыв между ними;
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
- Mean greedy gap vs exact: `0.0986`
- Mean beam gap vs exact: `0.0006`
- Beam strictly improves on greedy in `104` rows
- Beam matches exact in `237` rows

Дополнительно в текущем прототипе найдены примеры, где:

- beam-search строго улучшает greedy baseline;
- во многих случаях beam совпадает с exact optimum;
- для нескольких подготовленных случаев сертифицированный разрыв равен нулю.

## 8. Примеры сертификатов

# CertiGap Certificate Examples

## zipf, n=8, B=2, eta=0.15

- Upper bound: `2.879325`
- Lower bound: `2.879325`
- Certified gap: `0.000000`
- Exact gap: `0.000000`
- Bound source: `lagrangian`
- Splits: `[{'interval': [1, 8], 'threshold': 2}, {'interval': [3, 8], 'threshold': 4}]`

## hot_middle, n=12, B=3, eta=0.15

- Upper bound: `3.291667`
- Lower bound: `3.291667`
- Certified gap: `0.000000`
- Exact gap: `0.000000`
- Bound source: `lagrangian`
- Splits: `[{'interval': [1, 12], 'threshold': 6}, {'interval': [1, 6], 'threshold': 4}, {'interval': [7, 12], 'threshold': 8}]`

## hot_tail, n=16, B=4, eta=0.30

- Upper bound: `3.854545`
- Lower bound: `3.854545`
- Certified gap: `0.000000`
- Exact gap: `0.000000`
- Bound source: `lagrangian`
- Splits: `[{'interval': [1, 16], 'threshold': 13}, {'interval': [1, 13], 'threshold': 8}, {'interval': [9, 13], 'threshold': 12}, {'interval': [14, 16], 'threshold': 14}]`

# CertiGap Speed and Quality Summary

## Small Cases With Exact Reference

- Exact mean time: `2.526 ms`
- Beam mean time: `3.889 ms`
- Greedy mean time: `0.166 ms`
- Balanced mean time: `0.009 ms`
- Weighted mean time: `0.013 ms`
- Beam mean gap vs exact: `0.000979`
- Greedy mean gap vs exact: `0.114157`
- Balanced mean gap vs exact: `0.447373`
- Weighted mean gap vs exact: `0.198609`

## Large Cases Without Exact Reference

- Beam mean time: `39.587 ms`
- Greedy mean time: `0.927 ms`
- Balanced mean time: `0.014 ms`
- Weighted mean time: `0.028 ms`

## Solver Tradeoff

- `exact` is the reference solver for small and medium instances, but it is much slower.
- `beam` is the strongest practical heuristic: near-exact quality on small cases with much lower runtime than `exact`.
- `greedy` is usually faster but can be substantially worse on structured skewed tasks.
- `balanced` and `weighted` are cheap baselines, but quality is systematically weaker on skewed workloads.

# Greedy Counterexample Family

## Informal Family

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

## 10. Вывод

На текущем этапе CertiGap уже оформлен как полноценный research-прототип: есть точный solver, усиленная эвристика, benchmark, checker, lower bounds и автоматическая генерация отчётных артефактов. Следующий научный шаг — формально дописать доказательства Theorem A и Theorem B, а также завершить строгую отрицательную конструкцию для greedy baseline.
