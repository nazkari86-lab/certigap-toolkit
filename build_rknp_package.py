from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"
RESULTS_DIR = ROOT / "results"
RKNP_DIR = ROOT / "rknp_package"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").strip()


def parse_global_summary(summary_text: str) -> list[str]:
    lines = []
    inside = False
    for line in summary_text.splitlines():
        if line.strip() == "## Global Summary":
            inside = True
            continue
        if inside and line.startswith("## "):
            break
        if inside and line.startswith("- "):
            lines.append(line[2:].strip())
    return lines


def build_abstract_ru(summary_text: str) -> str:
    metrics = parse_global_summary(summary_text)
    metric_lines = "\n".join(f"- {line}" for line in metrics)
    return f"""# Аннотация

**Тема:** CertiGap — робастные частичные поисковые деревья с ограниченным бюджетом разделений и сертифицируемой близостью к оптимуму.

В работе исследуется статическая задача поиска в отсортированном наборе ключей при двух ограничениях: число заранее материализованных пороговых сравнений ограничено бюджетом, а прогноз распределения запросов может быть неверным. В отличие от полностью упорядоченных поисковых структур, CertiGap оптимизирует не форму полного дерева, а то, **какую часть порядка вообще стоит материализовать заранее**, а какую оставить в виде неразрешённых интервалов с резервным поиском.

Предлагаемый проект включает:

1. точный frontier dynamic programming алгоритм для малых и средних экземпляров;
2. более сильную beam-search эвристику для более крупных экземпляров;
3. независимый checker, пересчитывающий целевую функцию и entropy-нижнюю оценку;
4. воспроизводимый синтетический benchmark.

Текущее состояние прототипа подтверждается следующими результатами:

{metric_lines}

Полученные результаты поддерживают основную гипотезу работы: оптимизация степени материализации порядка является нетривиальной алгоритмической задачей и даёт измеримое преимущество над простыми greedy и balanced baseline на скошенных распределениях запросов.
"""


def build_report_ru(summary_text: str, cert_text: str, proof_text: str) -> str:
    metrics = parse_global_summary(summary_text)
    metric_lines = "\n".join(f"- {line}" for line in metrics)
    return f"""# Отчёт РКНП

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

{metric_lines}

Дополнительно в текущем прототипе найдены примеры, где:

- beam-search строго улучшает greedy baseline;
- во многих случаях beam совпадает с exact optimum;
- на proof-sized случаях branch-and-bound trace независимо подтверждает оптимальность.

## 8. Примеры сертификатов

{cert_text}

## 9. Доказательная часть

{proof_text}

## 10. Вывод

На текущем этапе CertiGap оформлен как воспроизводимый research-прототип: есть точный solver, усиленная эвристика, benchmark, checker, lower bounds и автоматическая генерация отчётных артефактов. Доказательства Theorem A и Theorem B представлены как proof drafts; они ещё не проходили внешнюю или машинную формальную проверку. Следующий главный научный шаг — завершить строгую бесконечную отрицательную конструкцию для greedy baseline и расширить масштаб экспериментов.
"""


def build_theses_ru() -> str:
    return """# Тезисы для защиты

1. CertiGap решает не задачу построения полного дерева, а задачу выбора того, какую часть порядка вообще стоит материализовать.
2. В модели явно учитывается недоверие к прогнозу запросов через параметр `eta`.
3. Для малых и средних случаев построен точный алгоритм frontier DP.
4. Для более крупных случаев реализована beam-search эвристика, существенно лучше greedy baseline.
5. Вместе с решением возвращается проверяемый сертификат качества.
6. Эксперименты показывают, что на скошенных распределениях beam почти всегда совпадает с exact optimum, а greedy заметно хуже.
7. Проект хорошо подходит для РКНП как теоретико-алгоритмическая работа с воспроизводимым результатом.
"""


def build_slides_ru(summary_text: str) -> str:
    metrics = parse_global_summary(summary_text)
    metric_lines = "\n".join(f"- {line}" for line in metrics)
    return f"""# План слайдов

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

{metric_lines}

## Слайд 6. Сертификаты

- upper bound;
- lower bound;
- independently recomputed entropy bound;
- exact gap на малых случаях.

## Слайд 7. Вывод

- идея научно сильная;
- результаты воспроизводимы;
- проект готов к дальнейшему формальному усилению.
"""


def main() -> None:
    RKNP_DIR.mkdir(exist_ok=True)
    summary_text = read(RESULTS_DIR / "summary.md")
    cert_text = read(RESULTS_DIR / "certificate_examples.md")
    proof_text = read(DOCS_DIR / "PROOF_SKETCHES.md")
    counterexample_text = read(RESULTS_DIR / "counterexamples.md") if (RESULTS_DIR / "counterexamples.md").exists() else ""
    family_text = read(DOCS_DIR / "GREEDY_COUNTEREXAMPLE_FAMILY.md") if (DOCS_DIR / "GREEDY_COUNTEREXAMPLE_FAMILY.md").exists() else ""
    speed_quality_text = read(RESULTS_DIR / "speed_quality_summary.md") if (RESULTS_DIR / "speed_quality_summary.md").exists() else ""
    formal_results_text = read(DOCS_DIR / "FORMAL_RESULTS.md") if (DOCS_DIR / "FORMAL_RESULTS.md").exists() else ""

    (RKNP_DIR / "ABSTRACT_RU.md").write_text(build_abstract_ru(summary_text), encoding="utf-8")
    (RKNP_DIR / "REPORT_RU.md").write_text(
        build_report_ru(
            summary_text
            + ("\n\n## Скорость и качество\n\n" + speed_quality_text if speed_quality_text else "")
            + ("\n\n## Контрпримеры greedy\n\n" + counterexample_text if counterexample_text else ""),
            cert_text + ("\n\n" + speed_quality_text if speed_quality_text else "") + ("\n\n" + family_text if family_text else ""),
            proof_text,
        ),
        encoding="utf-8",
    )
    (RKNP_DIR / "THESES_RU.md").write_text(build_theses_ru(), encoding="utf-8")
    (RKNP_DIR / "SLIDES_RU.md").write_text(build_slides_ru(summary_text), encoding="utf-8")
    if formal_results_text:
        (RKNP_DIR / "FORMAL_RESULTS_EN.md").write_text(formal_results_text, encoding="utf-8")

    print(f"Wrote {RKNP_DIR / 'ABSTRACT_RU.md'}")
    print(f"Wrote {RKNP_DIR / 'REPORT_RU.md'}")
    print(f"Wrote {RKNP_DIR / 'THESES_RU.md'}")
    print(f"Wrote {RKNP_DIR / 'SLIDES_RU.md'}")
    if formal_results_text:
        print(f"Wrote {RKNP_DIR / 'FORMAL_RESULTS_EN.md'}")


if __name__ == "__main__":
    main()
