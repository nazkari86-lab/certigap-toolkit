# План слайдов

## Слайд 1. Название

CertiGap: робастные частичные поисковые деревья с ограниченным бюджетом разделений и сертифицируемой близостью к оптимуму

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
- exact gap на малых случаях.

## Слайд 7. Вывод

- идея научно сильная;
- результаты воспроизводимы;
- проект готов к дальнейшему формальному усилению.
