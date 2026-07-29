from __future__ import annotations

import copy
import hashlib
import itertools
import json
import random
import subprocess
import tempfile
import unittest
from pathlib import Path

from certigap import (
    HardwareProfile,
    SynthesisConstraints,
    SynthesisVerificationError,
    WorkloadTrace,
    compile_synthesized_index,
    migration_decision,
    synthesize_partitions,
    verify_synthesis_certificate,
)
from certigap.synthesis import _interval_score


ROOT = Path(__file__).resolve().parents[1]


def redigest(artifact: dict) -> None:
    unsigned = copy.deepcopy(artifact)
    unsigned.pop("sha256", None)
    artifact["sha256"] = hashlib.sha256(
        json.dumps(
            unsigned,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def partitions(n: int, blocks: int):
    for cuts in itertools.combinations(range(1, n), blocks - 1):
        yield (*cuts, n)


class SynthesisTests(unittest.TestCase):
    def test_dp_matches_exhaustive_partition_oracle(self) -> None:
        trace = WorkloadTrace(8)
        for left, right in ((1, 3), (2, 7), (5, 8), (2, 2)):
            trace.add_range(left, right)
        trace.add_update(3, 10.0)
        constraints = SynthesisConstraints(
            max_blocks=5,
            max_block_width=8,
            tail_weight=0.25,
            memory_weight_ns=0.01,
            build_weight_ns=0.02,
        )
        profile = HardwareProfile(
            value_read_ns=1.1,
            aggregate_read_ns=0.7,
            combine_ns=0.4,
            value_write_ns=1.3,
            aggregate_write_ns=0.8,
        )
        rows = synthesize_partitions(trace, constraints, profile)
        for row in rows:
            blocks = row["blocks"]
            scored = []
            for path in partitions(trace.n, blocks):
                starts = (1, *(cut + 1 for cut in path[:-1]))
                if max(
                    right - left + 1
                    for left, right in zip(starts, path)
                ) > constraints.max_block_width:
                    continue
                score = sum(
                    _interval_score(
                        trace, left, right, constraints, profile
                    )[0]
                    for left, right in zip(starts, path)
                )
                scored.append((score, path))
            expected = min(scored, key=lambda item: (item[0], item[1]))
            self.assertAlmostEqual(
                row["train"]["certified_robust_upper_ns"], expected[0]
            )
            self.assertEqual(tuple(row["boundaries"]), expected[1])

    def test_runtime_matches_random_oracle_for_all_aggregates(self) -> None:
        rng = random.Random(160)
        for aggregate in ("sum", "min", "max"):
            trace = WorkloadTrace(31)
            for _ in range(80):
                left = rng.randint(1, 31)
                trace.add_range(left, rng.randint(left, 31))
            model = compile_synthesized_index(
                range(31),
                trace,
                constraints=SynthesisConstraints(
                    aggregate=aggregate,
                    max_blocks=10,
                    max_block_width=8,
                ),
            )
            oracle = [float(value) for value in range(31)]
            for _ in range(200):
                if rng.random() < 0.35:
                    key = rng.randint(1, 31)
                    value = float(rng.randint(-100, 100))
                    oracle[key - 1] = value
                    model.point_update(key, value)
                else:
                    left = rng.randint(1, 31)
                    right = rng.randint(left, 31)
                    expected = {
                        "sum": sum,
                        "min": min,
                        "max": max,
                    }[aggregate](oracle[left - 1 : right])
                    self.assertAlmostEqual(
                        model.range_query(left, right), expected
                    )

    def test_verifier_rejects_omission_and_rewritten_winner(self) -> None:
        trace = WorkloadTrace(12)
        for _ in range(30):
            trace.add_range(2, 10)
        artifact = compile_synthesized_index(
            range(12),
            trace,
            constraints=SynthesisConstraints(
                max_blocks=6, max_block_width=6
            ),
        ).export_certificate()
        self.assertTrue(verify_synthesis_certificate(artifact)["verified"])

        omitted = copy.deepcopy(artifact)
        omitted["candidates"].pop()
        redigest(omitted)
        with self.assertRaises(SynthesisVerificationError):
            verify_synthesis_certificate(omitted)

        changed = copy.deepcopy(artifact)
        changed["selected"] = changed["candidates"][0]["boundaries"]
        redigest(changed)
        with self.assertRaises(SynthesisVerificationError):
            verify_synthesis_certificate(changed)

        grammar = copy.deepcopy(artifact)
        grammar["grammar"]["partition_space"] = "selected partitions only"
        redigest(grammar)
        with self.assertRaises(SynthesisVerificationError):
            verify_synthesis_certificate(grammar)

    def test_migration_requires_amortized_confident_benefit(self) -> None:
        accepted = migration_decision(
            current_ns_per_operation=20.0,
            proposed_ns_per_operation=10.0,
            rebuild_ns=1_000.0,
            confidence_margin_ns=500.0,
            horizon_operations=1_000,
        )
        rejected = migration_decision(
            current_ns_per_operation=20.0,
            proposed_ns_per_operation=19.0,
            rebuild_ns=1_000.0,
            confidence_margin_ns=500.0,
            horizon_operations=1_000,
        )
        self.assertTrue(accepted["migrate"])
        self.assertFalse(rejected["migrate"])

    def test_native_hardware_calibrator_emits_valid_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / "calibrate"
            subprocess.run(
                [
                    "c++",
                    "-std=c++17",
                    "-O2",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-pedantic",
                    str(ROOT / "cpp" / "hardware_calibration.cpp"),
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            output = subprocess.run(
                [str(executable)],
                check=True,
                text=True,
                capture_output=True,
            )
            profile = HardwareProfile(**json.loads(output.stdout))
            profile.validate()
            self.assertEqual(profile.sample_count, 9)

    def test_generated_cpp_header_executes_selected_partition(self) -> None:
        trace = WorkloadTrace(16)
        for _ in range(50):
            trace.add_range(2, 10)
        model = compile_synthesized_index(
            range(16),
            trace,
            constraints=SynthesisConstraints(
                max_blocks=8, max_block_width=8
            ),
        )
        header = model.render_cpp_header("experiment_index")
        self.assertEqual(header, model.render_cpp_header("experiment_index"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "generated.hpp").write_text(header, encoding="utf-8")
            (root / "main.cpp").write_text(
                """
#include <cmath>
#include <vector>
#include "generated.hpp"

int main() {
    std::vector<double> values(16);
    for (int index = 0; index < 16; ++index) values[index] = index;
    auto structure = experiment_index::make_index(values);
    if (std::abs(structure.range_query(2, 10) - 45.0) > 1e-12) return 2;
    structure.point_update(3, 100.0);
    if (std::abs(structure.range_query(2, 10) - 143.0) > 1e-12) return 3;
    if (structure.memory_slots() != 2 * values.size()
        + 2 * structure.boundaries().size()) return 4;
    return 0;
}
""",
                encoding="utf-8",
            )
            executable = root / "generated"
            subprocess.run(
                [
                    "c++",
                    "-std=c++17",
                    "-O2",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-pedantic",
                    "-I",
                    str(ROOT / "cpp"),
                    "-I",
                    str(root),
                    str(root / "main.cpp"),
                    "-o",
                    str(executable),
                ],
                check=True,
            )
            subprocess.run([str(executable)], check=True)


if __name__ == "__main__":
    unittest.main()
