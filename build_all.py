from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    python = sys.executable
    run([python, "build_cpp_core.py"])
    run([python, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run([python, "generate_results.py"])
    run([python, "analyze_experiments.py"])
    run([python, "generate_speed_quality.py", "--mode", "fast"])
    run([python, "generate_counterexamples.py", "--mode", "fast"])
    run([python, "generate_proof_artifacts.py"])
    run([python, "generate_scaling_benchmark.py", "--mode", "quick", "--datasets", "all"])
    run([python, "generate_figures.py"])
    run([python, "build_report.py"])
    run([python, "build_rknp_package.py"])
    print("Full CertiGap package rebuilt successfully.")


if __name__ == "__main__":
    main()
