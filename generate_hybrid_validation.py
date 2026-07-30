from __future__ import annotations

import csv
import json
from pathlib import Path

from certigap import (
    HardwareProfile,
    HybridConstraints,
    WorkloadTrace,
    compile_hybrid_index,
    verify_hybrid_certificate,
)
from certigap.hybrid import _interval_score


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "results" / "hybrid_validation.csv"
MD_PATH = ROOT / "results" / "hybrid_validation.md"
ARTIFACT_PATH = ROOT / "results" / "hybrid_certificate_example.json"


def make_trace(n: int, scenario: str) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for index in range(200):
        if scenario == "left_hot":
            trace.add_range(1 + index % 3, n // 3 + index % 4)
        elif scenario == "two_hot":
            trace.add_range(
                2 if index % 2 else 3 * n // 4,
                n // 4 if index % 2 else n - 1,
            )
        elif scenario == "mixed":
            if index % 5 == 0:
                trace.add_update(1 + index % n, float(index))
            elif index % 3 == 0:
                trace.add_get(1 + index % n)
            else:
                trace.add_range(1 + index % (n // 4), n - index % 5)
        elif scenario == "uniform":
            left = 1 + index % n
            trace.add_range(
                left, min(n, left + index % max(2, n // 4))
            )
        elif scenario == "point_hot":
            trace.add_get(1 + index % max(2, n // 8))
        elif scenario == "update_hot":
            if index % 2:
                trace.add_update(1 + index % max(2, n // 8), float(index))
            else:
                trace.add_range(1, n - index % 3)
        else:
            raise ValueError(scenario)
    return trace


def uniform_boundaries(n: int, width: int) -> tuple[int, ...]:
    return tuple([*range(width, n, width), n])


def score_path(
    trace: WorkloadTrace,
    path: tuple[int, ...],
    constraints: HybridConstraints,
    hardware: HardwareProfile,
) -> float:
    starts = (1, *(boundary + 1 for boundary in path[:-1]))
    blocks = len(path)
    return sum(
        _interval_score(
            trace,
            left,
            right,
            block_index,
            blocks,
            constraints,
            hardware,
        )[0]
        for block_index, (left, right) in enumerate(
            zip(starts, path), start=1
        )
    )


def main() -> None:
    profile = HardwareProfile()
    rows: list[dict[str, object]] = []
    gains: list[float] = []
    nonuniform = 0
    example: dict | None = None
    scenarios = (
        "left_hot",
        "two_hot",
        "mixed",
        "uniform",
        "point_hot",
        "update_hot",
    )
    for n in (16, 32, 64, 128):
        for scenario in scenarios:
            trace = make_trace(n, scenario)
            constraints = HybridConstraints(
                max_blocks=12,
                max_block_width=max(8, n // 2),
                tail_weight=0.15,
            )
            model = compile_hybrid_index(
                range(n),
                trace,
                constraints=constraints,
                hardware=profile,
            )
            artifact = model.export_certificate()
            verified = verify_hybrid_certificate(artifact)
            selected = next(
                row
                for row in artifact["candidates"]
                if row["blocks"] == artifact["selected"]["blocks"]
                and row["boundaries"] == artifact["selected"]["boundaries"]
            )
            uniform = [
                (
                    score_path(
                        trace,
                        uniform_boundaries(n, width),
                        constraints,
                        profile,
                    ),
                    uniform_boundaries(n, width),
                )
                for width in range(1, constraints.max_block_width + 1)
                if len(uniform_boundaries(n, width))
                <= constraints.max_blocks
            ]
            uniform_score, uniform_path = min(
                uniform, key=lambda item: (item[0], item[1])
            )
            gain = (uniform_score - float(selected["score"])) / max(
                uniform_score, 1e-12
            )
            gains.append(gain)
            widths = [
                right - left + 1
                for left, right in zip(
                    (
                        1,
                        *(
                            boundary + 1
                            for boundary in model.selected_boundaries[:-1]
                        ),
                    ),
                    model.selected_boundaries,
                )
            ]
            is_nonuniform = len(set(widths)) > 1
            nonuniform += int(is_nonuniform)
            if model.range_query(1, n) != sum(range(n)):
                raise RuntimeError("hybrid runtime failed array oracle")
            rows.append(
                {
                    "n": n,
                    "scenario": scenario,
                    "candidate_count": verified["candidate_count"],
                    "selected_blocks": verified["selected_blocks"],
                    "selected_boundaries": ";".join(
                        map(str, model.selected_boundaries)
                    ),
                    "nonuniform": str(is_nonuniform).lower(),
                    "selected_score": f"{float(selected['score']):.12f}",
                    "best_uniform_score": f"{uniform_score:.12f}",
                    "best_uniform_boundaries": ";".join(
                        map(str, uniform_path)
                    ),
                    "relative_gain": f"{gain:.12f}",
                    "certificate_verified": "true",
                    "runtime_correct": "true",
                }
            )
            if n == 32 and scenario == "mixed":
                example = artifact
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    if example is None:
        raise RuntimeError("hybrid example was not generated")
    ARTIFACT_PATH.write_text(
        json.dumps(example, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    MD_PATH.write_text(
        "\n".join(
            [
                "# CertiGap-H exact validation",
                "",
                f"- Independently replayed frontiers: `{len(rows)}/{len(rows)}`.",
                f"- Runtime oracle passes: `{len(rows)}/{len(rows)}`.",
                f"- Nonuniform selected designs: `{nonuniform}/{len(rows)}`.",
                f"- Mean certified gain over best uniform-prefix partition: "
                f"`{sum(gains) / len(gains):.2%}`.",
                f"- Maximum certified gain: `{max(gains):.2%}`.",
                f"- Minimum certified gain: `{min(gains):.2%}`.",
                "",
                "Scores use deterministic unit primitive costs. Native latency "
                "is evaluated separately on train/holdout traces.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} hybrid validation rows")


if __name__ == "__main__":
    main()
