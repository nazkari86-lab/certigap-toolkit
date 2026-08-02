# CertiGap Final Package Index

## Core Code

- [core.py](certigap/core.py)
- [AutoDRO core](certigap/autodro.py)
- [Direct TV tree-space enumerator](certigap/direct_tv.py)
- [Anytime TV-DRO solver](certigap/anytime_tv.py)
- [Independent anytime replay verifier](certigap/anytime_verifier.py)
- [Online drift certificates](certigap/online.py)
- [Dynamic CertiRange](certigap/dynamic_range.py)
- [Range-aware optimizer](certigap/range_optimizer.py)
- [Range optimizer verifier](certigap/range_optimizer_verifier.py)
- [Certified AutoIndex](certigap/autoindex.py)
- [Independent AutoIndex verifier](certigap/autoindex_verifier.py)
- [Python AdaptiveArray](certigap/adaptive_array.py)
- [Declarative adaptive specification](certigap/spec.py)
- [Measured deployment gate](certigap/measured_deployment.py)
- [Measured deployment verifier](certigap/measured_deployment_verifier.py)
- [JSON/C++ compiler](certigap/compiler.py)
- [Reusable C++ AutoIndex runtime](cpp/certigap_autoindex.hpp)
- [Adaptive C++ runtime](cpp/certigap_adaptive.hpp)
- [Standalone single header](cpp/certigap.hpp)
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
- [generate_autodro_benchmark.py](generate_autodro_benchmark.py)
- [generate_direct_tv_validation.py](generate_direct_tv_validation.py)
- [generate_uncertainty_validation.py](generate_uncertainty_validation.py)
- [generate_online_adaptation.py](generate_online_adaptation.py)
- [generate_anytime_validation.py](generate_anytime_validation.py)
- [generate_dynamic_range_benchmark.py](generate_dynamic_range_benchmark.py)
- [generate_cpp_dynamic_range.py](generate_cpp_dynamic_range.py)
- [generate_range_optimizer_validation.py](generate_range_optimizer_validation.py)
- [generate_autoindex_validation.py](generate_autoindex_validation.py)
- [generate_compiler_integration_validation.py](generate_compiler_integration_validation.py)
- [generate_adaptive_validation.py](generate_adaptive_validation.py)
- [generate_adaptive_array_validation.py](generate_adaptive_array_validation.py)
- [generate_python_adaptive_array_validation.py](generate_python_adaptive_array_validation.py)
- [generate_measured_deployment_validation.py](generate_measured_deployment_validation.py)
- [verify_artifacts.py](verify_artifacts.py)
- [generate_pruning_validation.py](generate_pruning_validation.py)
- [generate_temporal_holdout.py](generate_temporal_holdout.py)
- [benchmark_datasets.py](certigap/benchmark_datasets.py)
- [build_all.py](build_all.py)
- [AutoDRO catalog example](examples/autodro_catalog.py)
- [Certified AutoIndex example](examples/certified_autoindex.py)
- [Generated CMake example](examples/cmake_autoindex)
- [Online single-file example](examples/online_single_file.cpp)

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
- [AutoDRO distribution-shift benchmark](results/autodro_shift.md)
- [Verified AutoDRO selection example](results/autodro_selection_example.json)
- [Direct TV exact-space validation](results/direct_tv_validation.md)
- [Finite-sample uncertainty validation](results/uncertainty_validation.md)
- [Online adaptation simulation](results/online_adaptation.md)
- [Anytime TV-DRO validation](results/anytime_validation.md)
- [Anytime replay certificate](results/anytime_certificate_example.json)
- [Dynamic range benchmark](results/dynamic_range_benchmark.md)
- [C++ dynamic range benchmark](results/cpp_dynamic_range.md)
- [Range optimizer validation](results/range_optimizer_validation.md)
- [Dynamic range certificate](results/dynamic_range_certificate_example.json)
- [Range optimizer artifact](results/range_optimizer_example.json)
- [AutoIndex validation](results/autoindex_validation.md)
- [Verified AutoIndex selection example](results/autoindex_selection_example.json)
- [TrackingAutoIndex validation](results/tracking_autoindex_validation.md)
- [TrackingAutoIndex replay certificate](results/tracking_autoindex_example.json)
- [TrackingAutoIndex comprehensive comparison](results/tracking_autoindex_comparison.md)
- [TrackingAutoIndex policy matrix](results/tracking_autoindex_comparison.csv)
- [TrackingAutoIndex fixed-candidate matrix](results/tracking_autoindex_candidates.csv)
- [TrackingAutoIndex runtime matrix](results/tracking_autoindex_runtime.csv)
- [TrackingAutoIndex comparison metadata](results/tracking_autoindex_comparison_metadata.json)
- [Compiler integration validation](results/compiler_integration_validation.md)
- [Adaptive header validation](results/adaptive_header_validation.md)
- [Adaptive C++ container validation](results/adaptive_array_validation.md)
- [Adaptive Python container validation](results/python_adaptive_array_validation.md)
- [Measured deployment gate validation](results/measured_deployment_validation.md)
- [AutoDRO theorem and API](docs/AUTODRO.md)
- [Anytime theorem and certificate contract](docs/ANYTIME_TV.md)
- [Dynamic CertiRange theorem and API](docs/DYNAMIC_RANGE.md)
- [Certified AutoIndex theorem and API](docs/AUTOINDEX.md)
- [Compiler and CMake integration](docs/COMPILER_INTEGRATION.md)
- [Adaptive single-header C++](docs/ADAPTIVE_CPP.md)
- [Adaptive C++ container](docs/ADAPTIVE_ARRAY.md)
- [Adaptive Python container](docs/PYTHON_ADAPTIVE_ARRAY.md)
- [Measured safe deployment](docs/MEASURED_DEPLOYMENT.md)
- [Causal representation tracking](docs/TRACKING_AUTOINDEX.md)
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

## CertiGap-X Synthesis

- [synthesis.py](certigap/synthesis.py)
- [synthesis_verifier.py](certigap/synthesis_verifier.py)
- [certigap_synth.hpp](cpp/certigap_synth.hpp)
- [hardware_calibration.cpp](cpp/hardware_calibration.cpp)
- [calibrate_hardware.py](calibrate_hardware.py)
- [generate_synthesis_validation.py](generate_synthesis_validation.py)
- [synthesis_validation.csv](results/synthesis_validation.csv)
- [generate_synthesis_native_benchmark.py](generate_synthesis_native_benchmark.py)
- [synthesis_native_benchmark.cpp](cpp/synthesis_native_benchmark.cpp)
- [synthesis_native_latency.csv](results/synthesis_native_latency.csv)
- [synthesis_native_latency_metadata.json](results/synthesis_native_latency_metadata.json)
- [SYNTHESIS.md](docs/SYNTHESIS.md)

## CertiGap-H Hybrid Prefix Synthesis

- [hybrid.py](certigap/hybrid.py)
- [hybrid_verifier.py](certigap/hybrid_verifier.py)
- [generate_hybrid_validation.py](generate_hybrid_validation.py)
- [hybrid_validation.csv](results/hybrid_validation.csv)
- [hybrid_certificate_example.json](results/hybrid_certificate_example.json)
- [HYBRID.md](docs/HYBRID.md)

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

- tighter scalable TV-DRO bounds and approximation ratios;
- an official YCSB integration with RocksDB or SQLite;
- external robust-BST and learned-index implementations under matched resources;
- independent replication of the runtime and memory benchmark on other machines.
