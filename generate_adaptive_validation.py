from __future__ import annotations

import csv
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "cpp" / "adaptive_validation.cpp"
EXECUTABLE = ROOT / "build" / "certigap_adaptive_validation"
CSV_PATH = ROOT / "results" / "adaptive_header_validation.csv"
MD_PATH = ROOT / "results" / "adaptive_header_validation.md"


def main() -> None:
    EXECUTABLE.parent.mkdir(exist_ok=True)
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
            str(SOURCE),
            "-o",
            str(EXECUTABLE),
        ],
        cwd=ROOT,
        check=True,
    )
    completed = subprocess.run(
        [str(EXECUTABLE)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    CSV_PATH.write_text(completed.stdout, encoding="utf-8")
    with CSV_PATH.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 24 or any(row["correct"] != "true" for row in rows):
        raise RuntimeError("adaptive C++ validation did not complete")
    selections = Counter(row["selected"] for row in rows)
    MD_PATH.write_text(
        "\n".join(
            [
                "# Adaptive single-header C++ validation",
                "",
                f"- Native C++ rows: `{len(rows)}`.",
                "- Correct point/range/update/snapshot cases: `24/24`.",
                "- Complete candidate reports per case: `5/5`.",
                f"- Selected backend distribution: `{dict(sorted(selections.items()))}`.",
                "- Sizes: `16, 32, 64, 128`.",
                "- Modes: point-hot, range-hot, calibrated segment tree, "
                "required CertiRange, minimum, and maximum.",
                "",
                "This validates deterministic reference behavior and selection "
                "contracts. It is not a production latency benchmark.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} adaptive C++ validation rows")


if __name__ == "__main__":
    main()
