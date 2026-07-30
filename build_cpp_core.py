from __future__ import annotations

import platform
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CPP_DIR = ROOT / "cpp"
BUILD_DIR = ROOT / "build"
SOURCE = CPP_DIR / "certigap_core.cpp"


def output_name() -> str:
    system = platform.system().lower()
    if system == "darwin":
        return "libcertigap_core.dylib"
    if system == "windows":
        return "certigap_core.dll"
    return "libcertigap_core.so"


def compile_args() -> list[str]:
    out = str(BUILD_DIR / output_name())
    system = platform.system().lower()
    if system == "darwin":
        return ["c++", "-std=c++17", "-O3", "-dynamiclib", str(SOURCE), "-o", out]
    if system == "windows":
        return ["c++", "-std=c++17", "-O3", "-shared", str(SOURCE), "-o", out]
    return ["c++", "-std=c++17", "-O3", "-shared", "-fPIC", str(SOURCE), "-o", out]


def main() -> None:
    BUILD_DIR.mkdir(exist_ok=True)
    cmd = compile_args()
    subprocess.run(cmd, cwd=ROOT, check=True)
    print(f"Built {BUILD_DIR / output_name()}")


if __name__ == "__main__":
    main()
