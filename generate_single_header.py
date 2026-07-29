from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
CPP = ROOT / "cpp"
OUTPUT = CPP / "certigap.hpp"


def generated_text() -> str:
    core = (CPP / "certigap_autoindex.hpp").read_text(encoding="utf-8")
    adaptive_lines = (
        CPP / "certigap_adaptive.hpp"
    ).read_text(encoding="utf-8").splitlines()
    adaptive = "\n".join(
        line
        for line in adaptive_lines
        if line != "#pragma once"
        and line != '#include "certigap_autoindex.hpp"'
    ).lstrip()
    return (
        "// CertiGap single-header distribution. Generated; do not edit.\n"
        + core
        + "\n"
        + adaptive
        + "\n"
    )


def main() -> None:
    OUTPUT.write_text(generated_text(), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
