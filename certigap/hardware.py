from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from .synthesis import HardwareProfile


def calibration_source_path() -> Path:
    checkout = Path(__file__).resolve().parents[1] / "cpp" / "hardware_calibration.cpp"
    installed = (
        Path(sys.prefix)
        / "share"
        / "certigap"
        / "tools"
        / "hardware_calibration.cpp"
    )
    for candidate in (checkout, installed):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("CertiGap hardware calibration source is missing")


def calibrate_hardware(compiler: str = "c++") -> HardwareProfile:
    source = calibration_source_path()
    with tempfile.TemporaryDirectory() as directory:
        executable = Path(directory) / "certigap-hardware-calibration"
        subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-O3",
                "-DNDEBUG",
                str(source),
                "-o",
                str(executable),
            ],
            check=True,
        )
        completed = subprocess.run(
            [str(executable)],
            check=True,
            text=True,
            capture_output=True,
        )
    profile = HardwareProfile(**json.loads(completed.stdout))
    profile.validate()
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure CertiGap-X primitive costs on this machine."
    )
    parser.add_argument(
        "--output", type=Path, default=Path("hardware_profile.json")
    )
    parser.add_argument("--compiler", default="c++")
    args = parser.parse_args()
    manifest = calibrate_hardware(args.compiler).manifest()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output} ({manifest['sha256']})")
