from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


def extension_source_path() -> Path:
    checkout = Path(__file__).resolve().parents[1] / "cpp" / "certigap_sqlite.cpp"
    installed = (
        Path(sys.prefix)
        / "share"
        / "certigap"
        / "tools"
        / "certigap_sqlite.cpp"
    )
    for candidate in (checkout, installed):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("CertiGap SQLite extension source is missing")


def virtual_table_source_path() -> Path:
    checkout = Path(__file__).resolve().parents[1] / "cpp" / "certigap_sqlite_vtab.cpp"
    installed = (
        Path(sys.prefix)
        / "share"
        / "certigap"
        / "tools"
        / "certigap_sqlite_vtab.cpp"
    )
    for candidate in (checkout, installed):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("CertiGap SQLite virtual-table source is missing")


def certigap_include_dir() -> Path:
    checkout = Path(__file__).resolve().parents[1] / "cpp"
    installed = Path(sys.prefix) / "include" / "certigap"
    for candidate in (checkout, installed):
        if (candidate / "certigap.hpp").is_file():
            return candidate
    raise FileNotFoundError("CertiGap C++ headers are missing")


def sqlite_include_dir() -> Path:
    candidates = []
    configured = os.environ.get("SQLITE_INCLUDE_DIR")
    if configured:
        candidates.append(Path(configured))
    candidates.extend(
        Path(path)
        for path in (
            "/opt/homebrew/include",
            "/usr/local/include",
            "/usr/include",
        )
    )
    homebrew = Path("/opt/homebrew/Cellar/sqlite")
    if homebrew.is_dir():
        candidates.extend(
            path / "include" for path in sorted(homebrew.iterdir(), reverse=True)
        )
    for candidate in candidates:
        if (candidate / "sqlite3ext.h").is_file():
            return candidate
    raise FileNotFoundError("sqlite3ext.h was not found; set SQLITE_INCLUDE_DIR")


def build_sqlite_extension(
    output: Path,
    *,
    compiler: str = "c++",
) -> Path:
    resolved_compiler = shutil.which(compiler)
    if resolved_compiler is None:
        raise FileNotFoundError(f"compiler not found: {compiler}")
    target = output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            resolved_compiler,
            "-std=c++17",
            "-O3",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-fPIC",
            "-shared",
            "-I",
            str(certigap_include_dir()),
            "-I",
            str(sqlite_include_dir()),
            str(extension_source_path()),
            str(virtual_table_source_path()),
            "-o",
            str(target),
        ],
        check=True,
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the CertiGap SQLite loadable extension."
    )
    suffix = ".dylib" if sys.platform == "darwin" else ".so"
    parser.add_argument("--output", type=Path, default=Path(f"certigap{suffix}"))
    parser.add_argument("--compiler", default=os.environ.get("CXX", "c++"))
    args = parser.parse_args()
    print(build_sqlite_extension(args.output, compiler=args.compiler))


if __name__ == "__main__":
    main()
