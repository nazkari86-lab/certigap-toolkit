from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import shutil
import struct
import subprocess
import tempfile
from pathlib import Path

from certigap.benchmark_datasets import CACHE_DIR, SOSD_SOURCES


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "cpp" / "sosd_streaming_benchmark.cpp"
RESULTS = ROOT / "results"
SOSD_COMMIT = "f52f4cba01dfcd37f1574551fccef00198863b88"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_sample(source: Path, value_type: str, count: int, target: Path) -> None:
    width = 4 if value_type == "uint32" else 8
    unpack = struct.Struct("<I" if width == 4 else "<Q")
    process = subprocess.Popen(["zstd", "-dc", str(source)], stdout=subprocess.PIPE)
    assert process.stdout is not None
    header = process.stdout.read(8)
    if len(header) != 8:
        raise RuntimeError(f"truncated SOSD header: {source}")
    total = struct.unpack("<Q", header)[0]
    if total != 200_000_000:
        raise RuntimeError(f"unexpected SOSD element count: {total}")
    count = min(count, total)
    targets = [index * (total - 1) // max(1, count - 1) for index in range(count)]
    selected: list[int] = []
    next_target = 0
    buffer = b""
    position = 0
    while position < total:
        block = process.stdout.read(1024 * 1024)
        if not block:
            break
        buffer += block
        values_in_block = len(buffer) // width
        usable = values_in_block * width
        while next_target < count and targets[next_target] < position + values_in_block:
            offset = (targets[next_target] - position) * width
            selected.append(unpack.unpack_from(buffer, offset)[0])
            next_target += 1
        position += values_in_block
        buffer = buffer[usable:]
    if process.wait() != 0 or position != total or len(selected) != count:
        raise RuntimeError(f"SOSD streaming validation failed for {source.name}")
    with target.open("wb") as output:
        output.write(struct.pack("<Q", len(selected)))
        output.write(struct.pack(f"<{len(selected)}Q", *selected))


def ensure_sosd_checkout(path: Path) -> bool:
    if not (path / ".git").exists():
        subprocess.run(
            ["git", "clone", "--depth", "1", "--recurse-submodules", "--shallow-submodules",
             "https://github.com/learnedsystems/SOSD.git", str(path)],
            check=True,
        )
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
    return commit == SOSD_COMMIT and (path / "competitors/rs/include/rs/builder.h").exists()


def main() -> None:
    parser = argparse.ArgumentParser(description="Streaming SOSD-derived native benchmark")
    parser.add_argument("--sample-keys", type=int, default=200_000)
    parser.add_argument("--queries", type=int, default=200_000)
    parser.add_argument("--repeats", type=int, default=9)
    parser.add_argument("--budget", type=int, default=32)
    parser.add_argument("--datasets", nargs="+", default=list(SOSD_SOURCES))
    parser.add_argument("--sosd-checkout", type=Path, default=Path("/tmp/certigap-sosd-official"))
    args = parser.parse_args()
    if min(args.sample_keys, args.queries, args.repeats, args.budget) < 1:
        raise SystemExit("sample, queries, repeats, and budget must be positive")
    if shutil.which("zstd") is None:
        raise SystemExit("zstd executable is required")
    official_rs = ensure_sosd_checkout(args.sosd_checkout)
    binary = ROOT / "build" / "certigap_sosd_streaming"
    binary.parent.mkdir(exist_ok=True)
    command = ["c++", "-std=c++17", "-O3", "-DNDEBUG", str(SOURCE), "-o", str(binary)]
    if official_rs:
        command.extend([
            "-DCERTIGAP_HAVE_RADIX_SPLINE=1",
            "-I", str(args.sosd_checkout / "competitors/rs/include"),
        ])
    subprocess.run(command, cwd=ROOT, check=True)
    all_rows: list[dict[str, str]] = []
    with tempfile.TemporaryDirectory(prefix="certigap-sosd-") as temporary:
        for name in args.datasets:
            if name not in SOSD_SOURCES:
                raise SystemExit(f"unknown SOSD dataset: {name}")
            source = SOSD_SOURCES[name]
            compressed = CACHE_DIR / source["filename"]
            if not compressed.exists():
                raise SystemExit(f"missing dataset; run download_sosd_dataset('{name}'): {compressed}")
            sample = Path(temporary) / f"{name}.uint64"
            make_sample(compressed, source["value_type"], args.sample_keys, sample)
            output = subprocess.check_output(
                [str(binary), str(sample), name, str(args.queries), str(args.repeats), str(args.budget)],
                cwd=ROOT, text=True,
            )
            all_rows.extend(csv.DictReader(output.splitlines()))
    RESULTS.mkdir(exist_ok=True)
    csv_path = RESULTS / "sosd_streaming.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(all_rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(all_rows)
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in all_rows:
        groups.setdefault((row["dataset"], row["workload"]), []).append(row)
    fastest: dict[str, int] = {}
    certigap_vs_std = 0
    for group in groups.values():
        winner = min(group, key=lambda row: float(row["median_ns_per_query"]))
        fastest[winner["method"]] = fastest.get(winner["method"], 0) + 1
        by_method = {row["method"]: row for row in group}
        certigap_vs_std += (
            float(by_method["certigap_partial"]["median_ns_per_query"])
            < float(by_method["std_lower_bound"]["median_ns_per_query"])
        )
    lines = [
        "# SOSD-Derived Streaming Results", "",
        f"- Full compressed distributions validated: `{len(set(row['dataset'] for row in all_rows))}`.",
        f"- Dataset/workload cases: `{len(groups)}`.",
        f"- CertiGap partial routing beats `std::lower_bound` in `{certigap_vs_std}/{len(groups)}` cases.",
        "- Fastest-method counts: " + ", ".join(
            f"`{method}` {count}" for method, count in sorted(fastest.items())
        ) + ".", "",
        "These are local-machine measurements on deterministic rank samples. "
        "They are not the official SOSD harness, and all four query workloads are synthetic. "
        "The CSV retains every loss and includes build time and index size.",
    ]
    (RESULTS / "sosd_streaming.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    metadata = {
        "schema": "certigap-sosd-streaming-v1",
        "methodology": "full zstd stream validation plus deterministic even-rank sample",
        "official_sosd_harness": False,
        "official_sosd_dataset_values": True,
        "additional_workloads_are_synthetic": True,
        "sosd_commit": SOSD_COMMIT,
        "official_radix_spline_enabled": official_rs,
        "sample_keys": args.sample_keys,
        "queries_per_workload": args.queries,
        "repeats": args.repeats,
        "budget": args.budget,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "compiler": subprocess.check_output(["c++", "--version"], text=True).splitlines()[0],
        "source_sha256": sha256(SOURCE),
        "csv_sha256": sha256(csv_path),
    }
    (RESULTS / "sosd_streaming.metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(all_rows)} rows to {csv_path}")


if __name__ == "__main__":
    main()
