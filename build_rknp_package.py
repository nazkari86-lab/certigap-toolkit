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

**Тема:** CertiGap-AutoDRO — автоматический выбор робастной частичной поисковой структуры по статистике запросов.

В работе исследуется статическая задача поиска в отсортированном наборе ключей при двух ограничениях: число заранее материализованных пороговых сравнений ограничено бюджетом, а прогноз распределения запросов может быть неверным. В отличие от полностью упорядоченных поисковых структур, CertiGap оптимизирует не форму полного дерева, а то, **какую часть порядка вообще стоит материализовать заранее**, а какую оставить в виде неразрешённых интервалов с резервным поиском.

Предлагаемый проект включает:

1. точный generalized frontier DP для произвольного детерминированного interval fallback;
2. масштабируемую C++ эвристику и доказанное семейство неограниченной ошибки one-step greedy;
3. независимые floating-point, proof-trace и rational-arithmetic проверки;
4. direct TV-DRO перебор с доказанной полнотой на малых экземплярах;
5. проверяемый AutoDRO-выбор бюджета, solver и fallback с защитой от удаления кандидатов;
6. масштабируемый anytime TV-DRO Branch-and-Bound с проверяемым интервалом оптимальности;
7. формальную границу regret `g + 2 delta R` при изменении распределения;
8. синтетические, публичные, temporal и matched-budget C++ эксперименты.
9. точный синтез неравномерных блоков CertiGap-X и отдельный native holdout,
   проверяющий перенос структурной модели в реальную задержку.
10. CertiGap-H с `O(1)` range-sum, representation-aware exact DP и
    независимо воспроизводимым сертификатом полного пространства разбиений.
11. Sequential SafeAutoIndex с alpha-spending confidence sequence и
    проверяемой первой точкой optional stopping.
12. Martingale SafeAutoIndex с e-process deployment, автоматическим
    revocation при доказанном вреде и bounded adapted-data гарантией.
13. настоящий SQLite loadable extension, выполняющий C++ CertiGap lifecycle
    непосредственно из SQL без Python runtime.
14. planner-native SQLite virtual table с `xBestIndex`, durable shadow storage,
    транзакционным rollback и проверкой двух WAL writers.
15. zero-based `adaptive_array<T>` с автоматическим профилированием,
    переносом workload-профиля между запусками и fail-closed score gate.

Текущее состояние прототипа подтверждается следующими результатами:

{metric_lines}

Полученные результаты поддерживают основную гипотезу работы: оптимизация степени материализации порядка является нетривиальной алгоритмической задачей и даёт измеримое преимущество над простыми greedy и balanced baseline на скошенных распределениях запросов.
Первоначальный native benchmark не подтвердил ускорение CertiGap-X и этот
отрицательный результат сохранён. Разработанный после него CertiGap-H устранил
последовательный обход блоков: в текущей 11-сценарной матрице он быстрее
Fenwick в 9 случаях, но проигрывает при 30% и 50% обновлений. Поэтому
train-only AutoIndex сохраняет global-prefix и Fenwick как обязательные
кандидаты, а temporal shift остаётся явным failure case.
"""


def build_report_ru(summary_text: str, cert_text: str, proof_text: str) -> str:
    metrics = parse_global_summary(summary_text)
    metric_lines = "\n".join(f"- {line}" for line in metrics)
    return f"""# Отчёт РКНП

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
- direct TV-DRO solver глобально оптимален на полном малом пространстве деревьев;
- anytime TV-DRO solver возвращает replay-verified нижнюю границу и gap;
- conditional-entropy bound усиливает поиск на больших пространствах;
- online certificate ограничивает regret величиной `g + 2 delta R`;
- verifier версии 2 повторно генерирует портфель и обнаруживает удаление кандидатов;
- проект сочетает точный алгоритм, эвристику и независимую проверку результата.

## 6. Методы

- frontier dynamic programming;
- beam-search heuristic;
- brute-force oracle для малых экземпляров;
- entropy lower bound;
- Lagrangian lower bound;
- независимый structural checker.
- independently replayed anytime frontier certificate;
- TV-drift mean-cost regret bound.

## 7. Текущие результаты

{metric_lines}

Дополнительно в текущем прототипе найдены примеры, где:

- beam-search строго улучшает greedy baseline;
- во многих случаях beam совпадает с exact optimum;
- на proof-sized случаях branch-and-bound trace независимо подтверждает оптимальность.
- anytime solver совпадает с complete-tree-space oracle в 12 из 12 случаев;
- 36 scalable trajectories имеют независимо проверенные монотонные интервалы.
- sequential no-regression gate прошёл 4 из 4 replay-сценариев; в
  mean-zero диагностике корректная граница дала 0 из 5000 ложных одобрений,
  тогда как повторное использование fixed-time интервала дало 576 из 5000.
- martingale lifecycle прошёл 4 из 4 сценариев: стабильный поток развёрнут,
  а update-heavy shift вернул классический baseline; adapted-null диагностика
  дала 101 ложное решение из 5000 при номинальном alpha 0.05.
- SQLite ABI integration загружается командой `.load`; virtual table передаёт
  equality/range constraints через `xBestIndex`, сохраняет данные между
  подключениями и прошёл 6 из 6 planner/durability сценариев.
- `adaptive_array<T>` прошёл 6 из 6 native-сценариев: automatic warmup,
  отказ слабой миграции, explicit maintenance и восстановление профиля.

## 8. Примеры сертификатов

{cert_text}

## 9. Доказательная часть

{proof_text}

## 10. Вывод

На текущем этапе CertiGap оформлен как воспроизводимый research-прототип: есть generalized exact solver, две независимые exact-рекуррентности, rational checker, proof trace, scalable anytime TV-DRO interval, C++ heuristic и matched-budget benchmark. Теоремы ещё не проходили внешнюю или машинную формальную проверку. Главный оставшийся теоретический шаг — получить более тесные large-instance bounds или approximation guarantee; главный внешний шаг — официальный YCSB/storage-engine эксперимент, независимое воспроизведение и production pilot.
"""


def build_theses_ru() -> str:
    return """# Тезисы для защиты

1. CertiGap решает не задачу построения полного дерева, а задачу выбора того, какую часть порядка вообще стоит материализовать.
2. В модели явно учитывается недоверие к прогнозу запросов через параметр `eta`.
3. Для малых и средних случаев построен точный алгоритм frontier DP.
4. Для более крупных случаев реализована beam-search эвристика, существенно лучше greedy baseline.
5. Стоимость решения независимо проверяется, а exact proof trace доступен на малых экземплярах.
6. Эксперименты показывают, что на скошенных распределениях beam почти всегда совпадает с exact optimum, а greedy заметно хуже.
7. Anytime solver возвращает проверяемый интервал оптимальности на пространствах, где полный перебор недоступен.
8. При TV-сдвиге online certificate ограничивает mean-cost regret через `g + 2 delta R`.
9. Sequential SafeAutoIndex допускает остановку на первом доказанном
   validation-префиксе без увеличения общего риска выше `alpha`.
10. Martingale SafeAutoIndex допускает зависимые bounded observations при
    явно сформулированных conditional-mean null hypotheses.
11. SQLite extension показывает прямую интеграцию C++ алгоритма в реальную
    систему управления данными без Python-посредника.
12. Planner-native virtual table проверяет equality/range pushdown,
    транзакции, durable reconnect и сериализацию двух WAL writers.
13. `adaptive_array<T>` автоматически собирает workload-профиль и сохраняет
    прежний backend, если модельный выигрыш ниже заданного порога.
14. Проект хорошо подходит для РКНП как теоретико-алгоритмическая работа с воспроизводимым результатом.
"""


def build_slides_ru(summary_text: str) -> str:
    metrics = parse_global_summary(summary_text)
    metric_lines = "\n".join(f"- {line}" for line in metrics)
    return f"""# План слайдов

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

{metric_lines}

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
"""


def main() -> None:
    RKNP_DIR.mkdir(exist_ok=True)
    summary_text = read(RESULTS_DIR / "summary.md")
    cert_text = read(RESULTS_DIR / "certificate_examples.md")
    proof_text = read(DOCS_DIR / "FORMAL_RESULTS.md")
    generalized_text = read(DOCS_DIR / "GENERALIZED_FALLBACK.md")
    lookup_text = read(RESULTS_DIR / "cpp_lookup_latency.md")
    autodro_text = "\n\n".join(
        read(path)
        for path in (
            RESULTS_DIR / "autodro_shift.md",
            RESULTS_DIR / "direct_tv_validation.md",
            RESULTS_DIR / "temporal_holdout.md",
            RESULTS_DIR / "uncertainty_validation.md",
            RESULTS_DIR / "online_adaptation.md",
            RESULTS_DIR / "anytime_validation.md",
        )
    )
    autodro_theory_text = read(DOCS_DIR / "AUTODRO.md")
    anytime_theory_text = read(DOCS_DIR / "ANYTIME_TV.md")
    dynamic_range_text = "\n\n".join(
        read(path)
        for path in (
            DOCS_DIR / "DYNAMIC_RANGE.md",
            RESULTS_DIR / "range_optimizer_validation.md",
            RESULTS_DIR / "cpp_dynamic_range.md",
        )
    )
    autoindex_text = "\n\n".join(
        read(path)
        for path in (
            DOCS_DIR / "AUTOINDEX.md",
            RESULTS_DIR / "autoindex_validation.md",
            DOCS_DIR / "COMPILER_INTEGRATION.md",
            RESULTS_DIR / "compiler_integration_validation.md",
            DOCS_DIR / "ADAPTIVE_CPP.md",
            RESULTS_DIR / "adaptive_header_validation.md",
            DOCS_DIR / "SYNTHESIS.md",
            RESULTS_DIR / "synthesis_validation.md",
            DOCS_DIR / "HYBRID.md",
            RESULTS_DIR / "hybrid_validation.md",
            RESULTS_DIR / "synthesis_native_latency.md",
        )
    )
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
            proof_text
            + "\n\n"
            + generalized_text
            + "\n\n"
            + autodro_theory_text
            + "\n\n"
            + anytime_theory_text
            + "\n\n"
            + autodro_text
            + "\n\n"
            + lookup_text
            + "\n\n"
            + dynamic_range_text
            + "\n\n"
            + autoindex_text,
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
