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
- Exact gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 8], 'threshold': 2}, {'interval': [3, 8], 'threshold': 4}]`

## hot_middle, n=12, B=3, eta=0.15

- Upper bound: `3.291667`
- Lower bound: `2.694186`
- Reported entropy-bound gap: `0.221767`
- Exact gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 12], 'threshold': 6}, {'interval': [7, 12], 'threshold': 8}, {'interval': [1, 6], 'threshold': 4}]`

## hot_tail, n=16, B=4, eta=0.30

- Upper bound: `3.854545`
- Lower bound: `2.894329`
- Reported entropy-bound gap: `0.331758`
- Exact gap: `0.000000`
- Bound source: `entropy_only`
- Splits: `[{'interval': [1, 16], 'threshold': 13}, {'interval': [14, 16], 'threshold': 14}, {'interval': [1, 13], 'threshold': 8}, {'interval': [9, 13], 'threshold': 12}]`

# CertiGap Speed and Quality Summary

## Small Cases With Exact Reference

- Exact mean time: `3.028 ms`
- Beam mean time: `5.181 ms`
- Greedy mean time: `0.242 ms`
- Balanced mean time: `0.014 ms`
- Weighted mean time: `0.019 ms`
- Beam mean absolute objective gap vs exact: `0.000979`
- Greedy mean absolute objective gap vs exact: `0.114157`
- Balanced mean absolute objective gap vs exact: `0.447373`
- Weighted mean absolute objective gap vs exact: `0.198609`
- Beam mean relative objective gap vs exact: `0.03%`
- Greedy mean relative objective gap vs exact: `3.48%`

## Large Cases Without Exact Reference

- Beam mean time: `53.550 ms`
- Greedy mean time: `1.452 ms`
- Balanced mean time: `0.024 ms`
- Weighted mean time: `0.040 ms`

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

## 10. Вывод

На текущем этапе CertiGap оформлен как воспроизводимый research-прототип: есть точный solver, усиленная эвристика, benchmark, checker, lower bounds и автоматическая генерация отчётных артефактов. Доказательства Theorem A и Theorem B представлены как proof drafts; они ещё не проходили внешнюю или машинную формальную проверку. Следующий главный научный шаг — завершить строгую бесконечную отрицательную конструкцию для greedy baseline и расширить масштаб экспериментов.
