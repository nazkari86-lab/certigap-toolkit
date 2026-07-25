# CertiGap Final Package Index

## Core Code

- [core.py](certigap/core.py)
- [__init__.py](certigap/__init__.py)

## Generators

- [generate_results.py](generate_results.py)
- [analyze_experiments.py](analyze_experiments.py)
- [generate_speed_quality.py](generate_speed_quality.py)
- [generate_counterexamples.py](generate_counterexamples.py)
- [build_report.py](build_report.py)
- [build_rknp_package.py](build_rknp_package.py)
- [generate_proof_artifacts.py](generate_proof_artifacts.py)
- [generate_scaling_benchmark.py](generate_scaling_benchmark.py)
- [build_all.py](build_all.py)

## Main Results

- [summary.md](results/summary.md)
- [speed_quality_summary.md](results/speed_quality_summary.md)
- [counterexamples.md](results/counterexamples.md)
- [certificate_examples.md](results/certificate_examples.md)
- [scientific_validation.md](results/scientific_validation.md)
- [branch_and_bound_certificate.json](results/branch_and_bound_certificate.json)
- [power_of_two_greedy_family.csv](results/power_of_two_greedy_family.csv)
- [scaling_benchmark.md](results/scaling_benchmark.md)

## English Package

- [ABSTRACT.md](report/ABSTRACT.md)
- [REPORT.md](report/REPORT.md)
- [APPENDIX.md](report/APPENDIX.md)
- [POSTER_OUTLINE.md](report/POSTER_OUTLINE.md)

## Russian RKNP Package

- [ABSTRACT_RU.md](rknp_package/ABSTRACT_RU.md)
- [REPORT_RU.md](rknp_package/REPORT_RU.md)
- [THESES_RU.md](rknp_package/THESES_RU.md)
- [SLIDES_RU.md](rknp_package/SLIDES_RU.md)

## Theory Notes

- [FORMAL_RESULTS.md](docs/FORMAL_RESULTS.md)
- [PROOF_SKETCHES.md](docs/PROOF_SKETCHES.md)
- [TECHNICAL_NOTE.md](docs/TECHNICAL_NOTE.md)
- [GREEDY_COUNTEREXAMPLE_FAMILY.md](docs/GREEDY_COUNTEREXAMPLE_FAMILY.md)
- [THEME.md](docs/THEME.md)
- [THEOREM_GOALS.md](docs/THEOREM_GOALS.md)
- [EXPERIMENT_PLAN.md](docs/EXPERIMENT_PLAN.md)
- [RKNP_ISEF_POSITIONING.md](docs/RKNP_ISEF_POSITIONING.md)

## Status

The package is a reproducible research prototype. Its claims are limited to the documented synthetic benchmark range and its checked small-instance validation suite.

Open research work:

- a fully formal asymptotic greedy-counterexample family;
- any stronger approximation or structural theorem beyond the current prototype.
- large-scale runtime and memory evidence beyond the current benchmark range.
