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
    tracking_lines = (
        CPP / "certigap_tracking.hpp"
    ).read_text(encoding="utf-8").splitlines()
    tracking = "\n".join(
        line
        for line in tracking_lines
        if line != "#pragma once"
        and line != '#include "certigap_adaptive.hpp"'
    ).lstrip()
    concurrent_lines = (
        CPP / "certigap_concurrent.hpp"
    ).read_text(encoding="utf-8").splitlines()
    concurrent = "\n".join(
        line
        for line in concurrent_lines
        if line != "#pragma once"
        and line != '#include "certigap_tracking.hpp"'
    ).lstrip()
    return (
        "// CertiGap single-header distribution. Generated; do not edit.\n"
        + core
        + "\n"
        + adaptive
        + "\n"
        + tracking
        + "\n"
        + concurrent
        + "\n"
    )


def main() -> None:
    OUTPUT.write_text(generated_text(), encoding="utf-8")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
