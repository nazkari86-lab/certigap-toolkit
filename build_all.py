from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the complete CertiGap scientific package.")
    parser.add_argument("--benchmark-mode", choices=("quick", "full", "max"), default="max")
    args = parser.parse_args()
    python = sys.executable
    run([python, "generate_single_header.py"])
    run([python, "build_cpp_core.py"])
    run([python, "generate_adaptive_validation.py"])
    run([python, "generate_synthesis_validation.py"])
    run([python, "generate_hybrid_validation.py"])
    run([python, "generate_cpp_scaling.py"])
    run([python, "generate_lookup_benchmark.py"])
    run([python, "generate_cpp_dynamic_range.py"])
    run([python, "generate_dynamic_range_benchmark.py", "--mode", "full"])
    run([python, "generate_range_optimizer_validation.py"])
    run([python, "generate_autoindex_validation.py"])
    run([python, "generate_compiler_integration_validation.py"])
    run([python, "generate_autodro_benchmark.py"])
    run([python, "generate_direct_tv_validation.py"])
    run([python, "generate_anytime_validation.py"])
    run([python, "generate_uncertainty_validation.py"])
    run([python, "generate_online_adaptation.py"])
    run([python, "generate_pruning_validation.py"])
    run([python, "generate_temporal_holdout.py"])
    run([python, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([python, "generate_results.py"])
    run([python, "analyze_experiments.py"])
    run([python, "generate_speed_quality.py", "--mode", "fast"])
    run([python, "generate_counterexamples.py", "--mode", "fast"])
    run([python, "generate_proof_artifacts.py"])
    run([python, "generate_scaling_benchmark.py", "--mode", args.benchmark_mode, "--datasets", "all"])
    run([python, "generate_figures.py"])
    run([python, "build_report.py"])
    run([python, "build_rknp_package.py"])
    verify_command = [python, "verify_artifacts.py"]
    if args.benchmark_mode != "max":
        verify_command.append("--allow-nonmax-scaling")
    run(verify_command)
    print("Full CertiGap package rebuilt successfully.")


if __name__ == "__main__":
    main()
