from __future__ import annotations

import json
from pathlib import Path

from certigap import (
    CppCertiGap,
    make_distribution,
    verify_pruned_beam_certificate,
)


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "results" / "pruned_beam_certificate_example.json"


def main() -> None:
    weights = make_distribution("hot_middle", 4096)
    artifact = CppCertiGap().pruned_beam(
        weights,
        budget=6,
        eta=0.15,
        beam_width=16,
        candidate_limit=32,
    )
    verification = verify_pruned_beam_certificate(weights, artifact)
    if not verification["verified"]:
        raise RuntimeError("generated pruned-beam certificate did not replay")
    OUTPUT.write_text(
        json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
