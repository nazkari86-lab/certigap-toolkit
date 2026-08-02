"""Fetch and validate every external CertiGap benchmark dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from certigap.benchmark_datasets import (
    MANIFEST_PATH,
    SOSD_SOURCES,
    SOURCES,
    download_sosd_dataset,
    load_real_workload,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def write_inventory() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    inventory = {
        "schema": "certigap-external-datasets-v1",
        "dataset_count": len(manifest),
        "total_compressed_bytes": sum(item["bytes"] for item in manifest.values()),
        "datasets": manifest,
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "external_dataset_inventory.json").write_text(
        json.dumps(inventory, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    class_counts: dict[str, int] = {}
    for item in manifest.values():
        dataset_class = item.get("dataset_class", "observed_frequency")
        class_counts[dataset_class] = class_counts.get(dataset_class, 0) + 1
    lines = [
        "# External Dataset Inventory",
        "",
        f"- Validated datasets: `{len(manifest)}`.",
        f"- Cached compressed bytes: `{inventory['total_compressed_bytes']}`.",
        "- Raw files are ignored by Git; provenance and digests are committed.",
        "",
        "## Classes",
        "",
    ]
    lines.extend(f"- `{name}`: `{count}`" for name, count in sorted(class_counts.items()))
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "Observed-frequency workloads and sorted-key distributions are distinct.",
            "SOSD files are not claimed to contain observed query frequencies.",
        ]
    )
    (RESULTS / "external_dataset_inventory.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--class",
        dest="dataset_class",
        choices=("all", "frequency", "sosd"),
        default="all",
    )
    args = parser.parse_args()

    results: list[dict] = []
    if args.dataset_class in {"all", "frequency"}:
        for name in SOURCES:
            weights, record = load_real_workload(name)
            results.append(
                {
                    "name": name,
                    "class": "observed_frequency",
                    "keys": len(weights),
                    "bytes": record["bytes"],
                    "sha256": record["sha256"],
                }
            )
            print(f"validated {name}: {len(weights)} keys")

    if args.dataset_class in {"all", "sosd"}:
        for name in SOSD_SOURCES:
            _, record = download_sosd_dataset(name)
            results.append(
                {
                    "name": name,
                    "class": "sorted_key_distribution",
                    "keys": record["elements"],
                    "bytes": record["bytes"],
                    "sha256": record["sha256"],
                }
            )
            print(f"validated {name}: {record['elements']} keys")

    write_inventory()
    print(json.dumps(results, indent=2, sort_keys=True))
    print(f"manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
