from __future__ import annotations

import csv
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def main() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        executable = root / "adaptive_array_validation"
        profile = root / "workload.profile"
        subprocess.run(
            [
                "c++",
                "-std=c++17",
                "-O2",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-pedantic",
                "-I",
                str(ROOT / "cpp"),
                str(ROOT / "cpp" / "adaptive_array_validation.cpp"),
                "-o",
                str(executable),
            ],
            check=True,
        )
        completed = subprocess.run(
            [str(executable), str(profile)],
            text=True,
            capture_output=True,
            check=True,
        )
    rows = list(csv.DictReader(completed.stdout.splitlines()))
    if len(rows) != 6 or any(row["passed"] != "true" for row in rows):
        raise RuntimeError("adaptive_array native validation failed")
    RESULTS.mkdir(parents=True, exist_ok=True)
    output = RESULTS / "adaptive_array_validation.csv"
    output.write_text(completed.stdout, encoding="utf-8")
    (RESULTS / "adaptive_array_validation.md").write_text(
        "\n".join(
            [
                "# Adaptive Array Validation",
                "",
                "- Native scenarios: `6`",
                "- Passed: `6/6`",
                "- Covers: automatic warmup, point/range selection, deployment "
                "threshold, explicit maintenance, and cross-instance profile "
                "persistence.",
                "- Boundary: model-score deployment gate; not a statistical "
                "no-regression or portable latency guarantee.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"Wrote {output} (6/6 passed)")


if __name__ == "__main__":
    main()
