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
- [generate_cpp_scaling.py](generate_cpp_scaling.py)
- [generate_lookup_benchmark.py](generate_lookup_benchmark.py)
- [verify_artifacts.py](verify_artifacts.py)
- [generate_pruning_validation.py](generate_pruning_validation.py)
- [generate_temporal_holdout.py](generate_temporal_holdout.py)
- [benchmark_datasets.py](certigap/benchmark_datasets.py)
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
- [benchmark_provenance.json](results/benchmark_provenance.json)
- [cpp_pruned_scaling.md](results/cpp_pruned_scaling.md)
- [cpp_lookup_latency.md](results/cpp_lookup_latency.md)
- [C++ lookup environment metadata](results/cpp_lookup_metadata.json)
- [Generalized executable fallback theorem](docs/GENERALIZED_FALLBACK.md)
- [LaTeX paper](paper/main.tex)
- [pruning_validation.md](results/pruning_validation.md)
- [temporal_holdout.md](results/temporal_holdout.md)

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
- [BENCHMARK_PROTOCOL.md](docs/BENCHMARK_PROTOCOL.md)
- [SCIENTIFIC_CLOSURE.md](docs/SCIENTIFIC_CLOSURE.md)
- [COMPLEXITY.md](docs/COMPLEXITY.md)
- [RELATED_WORK.md](docs/RELATED_WORK.md)
- [RKNP_ISEF_POSITIONING.md](docs/RKNP_ISEF_POSITIONING.md)

## Status

The package is a reproducible research prototype. Its claims are limited to the documented benchmark protocol, real-workload key ordering, and checked small-instance validation suite.

Open research work:

- a fully formal asymptotic greedy-counterexample family;
- any stronger approximation or structural theorem beyond the current prototype.
- independent replication of the runtime and memory benchmark on other machines.
