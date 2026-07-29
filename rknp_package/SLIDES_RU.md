# План слайдов

## Слайд 1. Название

CertiGap: робастный префиксный поиск с исполняемыми interval fallback

## Слайд 2. Проблема

- полное дерево тратит бюджет на холодные данные;
- прогноз запросов может быть ошибочным;
- нужна независимо проверяемая оценка качества.

## Слайд 3. Идея

- материализуем только часть порядка;
- остальное оставляем interval-leaf интервалами;
- используем робастную целевую функцию.

## Слайд 4. Алгоритмы

- exact frontier DP;
- greedy baseline;
- beam-search heuristic;
- anytime TV-DRO Branch-and-Bound;
- checker + lower bounds.

## Слайд 5. Результаты

- Rows analyzed: `240`
- Mean greedy absolute objective gap vs exact: `0.0986`
- Mean beam absolute objective gap vs exact: `0.0006`
- Mean greedy relative objective gap vs exact: `2.80%`
- Mean beam relative objective gap vs exact: `0.02%`
- Beam strictly improves on greedy in `104` rows
- Beam matches exact in `237` rows

## Слайд 6. Сертификаты

- upper bound;
- lower bound;
- independently recomputed entropy bound;
- rational arithmetic для integer counts;
- exhaustive proof trace на малых случаях.
- replay-verified anytime frontier и optimality gap.

## Слайд 7. Вывод

- идея научно сильная;
- результаты воспроизводимы;
- проект готов к дальнейшему формальному усилению.
- nonzero anytime gap честно остаётся незакрытым интервалом.
