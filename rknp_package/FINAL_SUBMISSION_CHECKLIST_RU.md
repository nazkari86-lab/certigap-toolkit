# CertiGap: финальный чек-лист РКНП

Этот чек-лист разделяет то, что можно завершить перед защитой, от внешних
научных этапов, которые нельзя честно заменить локальным запуском кода.

## Перед отправкой работы

- [ ] Указать автора, класс, школу, город и научного руководителя на
  титульной странице отчёта, презентации и стенда.
- [ ] Везде использовать единое название: `CertiGap — сертифицируемый
  компилятор адаптивных структур данных`.
- [ ] Проверить, что в аннотации, отчёте и слайдах нет слов «первый в мире»,
  «всегда быстрее» и «заменяет Fenwick».
- [ ] Приложить ссылку на конкретный commit GitHub и на release `v1.16.0`.
- [ ] Приложить `outputs/CertiGap_RKNP_2026_RU.pdf` и PPTX как материалы
  защиты.
- [ ] Отрепетировать доклад в лимит времени этапа; резервный слайд с
  источниками не включать в основное время.

## Что демонстрировать жюри

1. Простое дерево: горячие числа получают короткий путь, холодные интервалы
   используют обычный поиск.
2. Exact DP служит oracle, Beam даёт масштабируемое решение, а verifier
   проверяет результат независимо.
3. AutoIndex не навязывает CertiGap: при другой нагрузке он оставляет Fenwick,
   prefix sum или segment tree.
4. Главный quality-result: Beam совпал с exact в 237 из 240 committed cases.
5. Главная честная граница: latency измерена на записанной машине и workload,
   а не доказана для любого компьютера.

## Локальная проверка перед показом

```bash
python3 build_cpp_core.py
PYTHONPATH=. python3 -m unittest discover -s tests -q
PYTHONPATH=. python3 verify_artifacts.py
cmake -S examples/cmake_autoindex -B /tmp/certigap-cmake
cmake --build /tmp/certigap-cmake --parallel 2
/tmp/certigap-cmake/certigap_autoindex_example
```

## Внешние этапы после РКНП

Эти пункты не закрываются написанием новых локальных файлов и не должны
выдаваться за выполненные:

- независимый повтор эксперимента на другой машине и другим исследователем;
- официальный YCSB/RocksDB run с полезным CertiGap integration;
- matched-resource сравнение с внешними learned-index и robust-BST системами;
- внешний review доказательств;
- approximation guarantee или tighter certified gap для scalable C++ beam.

Подробный протокол для независимого повтора находится в
`docs/REPRODUCIBILITY.md`; шаблон манифеста добавлен в
`reproduction/independent_run_manifest.template.json`.
