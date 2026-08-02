from __future__ import annotations

import copy
import csv
import hashlib
import json
from pathlib import Path

from certigap import (
    DeltaSpec,
    DeltaVerificationError,
    compile_proof_carrying_delta_index,
    verify_delta_certificate,
)


ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"


def rehash(artifact: dict) -> None:
    unsigned = dict(artifact)
    unsigned.pop("sha256", None)
    artifact["sha256"] = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def main() -> None:
    rows = []
    example = None
    for algebra in ("sum", "min", "max"):
        for threshold in (1, 4, 16, 64):
            index = compile_proof_carrying_delta_index(
                ((key, float(key)) for key in range(0, 128, 2)),
                DeltaSpec(algebra=algebra, rebuild_threshold=threshold),
            )
            for key in range(1, 64, 2):
                index.insert(key, float(-key))
                if key % 5 == 1:
                    index.update(key - 1, float(key * 10))
                if key % 7 == 1:
                    index.erase(key + 63)
                index.range_query(max(0, key - 8), key + 8)
            certificate = index.export_certificate()
            summary = verify_delta_certificate(certificate)
            forged = copy.deepcopy(certificate)
            mutation = next(
                event for event in forged["events"]
                if event["operation"] in {"insert", "update"}
            )
            mutation["value"] += 1.0
            rehash(forged)
            tamper_rejected = False
            try:
                verify_delta_certificate(forged)
            except DeltaVerificationError:
                tamper_rejected = True
            rows.append({
                "algebra": algebra,
                "rebuild_threshold": threshold,
                "events": summary["event_count"],
                "rebuilds": summary["rebuild_count"],
                "final_entries": summary["final_entry_count"],
                "verified": summary["verified"],
                "rehashed_tamper_rejected": tamper_rejected,
                "certificate_sha256": summary["sha256"],
            })
            if algebra == "sum" and threshold == 16:
                example = certificate
    RESULTS.mkdir(exist_ok=True)
    with (RESULTS / "delta_validation.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    assert example is not None
    (RESULTS / "delta_certificate_example.json").write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"wrote {len(rows)} delta validation rows")


if __name__ == "__main__":
    main()
