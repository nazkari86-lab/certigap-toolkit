from __future__ import annotations

import csv
from pathlib import Path

from certigap import (
    HardwareProfile,
    SynthesisConstraints,
    WorkloadTrace,
    compile_synthesized_index,
    verify_synthesis_certificate,
)
from certigap.synthesis import _interval_score


ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "results" / "synthesis_validation.csv"
MD_PATH = ROOT / "results" / "synthesis_validation.md"


def make_trace(n: int, scenario: str) -> WorkloadTrace:
    trace = WorkloadTrace(n)
    for index in range(160):
        if scenario == "left_hot":
            trace.add_range(1 + index % 3, n // 3 + index % 4)
        elif scenario == "two_hot":
            if index % 2:
                trace.add_range(2, n // 4)
            else:
                trace.add_range(3 * n // 4, n - 1)
        elif scenario == "mixed":
            if index % 5 == 0:
                trace.add_update(1 + index % n, float(index))
            elif index % 3 == 0:
                trace.add_get(1 + index % n)
            else:
                trace.add_range(1 + index % (n // 4), n - index % 5)
        elif scenario == "minimum":
            if index % 4 == 0:
                trace.add_update(1 + index % n, float(index))
            else:
                trace.add_range(1 + index % 5, n - index % 7)
        elif scenario == "uniform":
            left = 1 + index % n
            trace.add_range(left, min(n, left + index % max(2, n // 4)))
        elif scenario == "point_hot":
            trace.add_get(1 + index % max(2, n // 8))
        else:
            raise ValueError(scenario)
    return trace


def uniform_boundaries(n: int, width: int) -> tuple[int, ...]:
    return tuple([*range(width, n, width), n])


def score_partition(
    trace: WorkloadTrace,
    path: tuple[int, ...],
    constraints: SynthesisConstraints,
    profile: HardwareProfile,
) -> float:
    starts = (1, *(boundary + 1 for boundary in path[:-1]))
    return sum(
        _interval_score(trace, left, right, constraints, profile)[0]
        for left, right in zip(starts, path)
    )


def main() -> None:
    profile = HardwareProfile()
    rows: list[dict[str, object]] = []
    gains: list[float] = []
    nonuniform = 0
    scenarios = (
        "left_hot",
        "two_hot",
        "mixed",
        "minimum",
        "uniform",
        "point_hot",
    )
    for n in (16, 32, 64, 128):
        for scenario in scenarios:
            trace = make_trace(n, scenario)
            constraints = SynthesisConstraints(
                aggregate="min" if scenario == "minimum" else "sum",
                max_blocks=12,
                max_block_width=max(8, n // 2),
                tail_weight=0.15,
            )
            model = compile_synthesized_index(
                range(n), trace, constraints=constraints, hardware=profile
            )
            verified = verify_synthesis_certificate(
                model.export_certificate()
            )
            selected_score = float(
                verified["certified_robust_upper_ns"]
            )
            uniform = [
                (
                    score_partition(
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
            uniform_score, uniform_path = min(uniform)
            gain = (uniform_score - selected_score) / uniform_score
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
            is_nonuniform = len(set(widths[:-1] or widths)) > 1
            nonuniform += int(is_nonuniform)
            expected = (
                min(range(n))
                if scenario == "minimum"
                else sum(range(n))
            )
            if model.range_query(1, n) != expected:
                raise RuntimeError("synthesized runtime failed oracle")
            rows.append(
                {
                    "n": n,
                    "scenario": scenario,
                    "aggregate": constraints.aggregate,
                    "candidate_count": verified["candidate_count"],
                    "selected_blocks": verified["partition_count"],
                    "selected_boundaries": ";".join(
                        map(str, model.selected_boundaries)
                    ),
                    "nonuniform": str(is_nonuniform).lower(),
                    "selected_certified_score": f"{selected_score:.12f}",
                    "best_uniform_score": f"{uniform_score:.12f}",
                    "best_uniform_boundaries": ";".join(map(str, uniform_path)),
                    "relative_gain": f"{gain:.12f}",
                    "certificate_verified": "true",
                    "runtime_correct": "true",
                }
            )
    CSV_PATH.parent.mkdir(exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=list(rows[0]), lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    MD_PATH.write_text(
        "\n".join(
            [
                "# CertiGap-X synthesis validation",
                "",
                f"- Exact independently verified portfolios: `{len(rows)}/{len(rows)}`.",
                f"- Runtime oracle passes: `{len(rows)}/{len(rows)}`.",
                f"- Nonuniform selected designs: `{nonuniform}/{len(rows)}`.",
                f"- Mean certified gain over best uniform blocks: `{sum(gains) / len(gains):.2%}`.",
                f"- Maximum certified gain over best uniform blocks: `{max(gains):.2%}`.",
                f"- Minimum certified gain over best uniform blocks: `{min(gains):.2%}`.",
                "",
                "The committed matrix uses unit primitive costs for deterministic "
                "reproduction. Machine-specific nanosecond profiles are conditional "
                "inputs produced by `calibrate_hardware.py`, not portable facts.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} synthesis validation rows")


if __name__ == "__main__":
    main()
