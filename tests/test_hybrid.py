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
    HybridConstraints,
    HybridVerificationError,
    PrefixBlockIndex,
    WorkloadTrace,
    compile_hybrid_index,
    synthesize_hybrid_partitions,
    verify_hybrid_certificate,
)
from certigap.hybrid import _interval_score


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


class HybridIndexTests(unittest.TestCase):
    def test_prefix_runtime_matches_random_array_oracle(self) -> None:
        rng = random.Random(190)
        for boundaries in ((31,), (3, 11, 19, 31), (8, 16, 24, 31)):
            index = PrefixBlockIndex(range(31), boundaries)
            oracle = [float(value) for value in range(31)]
            for _ in range(500):
                selector = rng.random()
                if selector < 0.30:
                    key = rng.randint(1, 31)
                    value = float(rng.randint(-500, 500))
                    index.point_update(key, value)
                    oracle[key - 1] = value
                elif selector < 0.40:
                    key = rng.randint(1, 31)
                    self.assertEqual(index.get(key), oracle[key - 1])
                else:
                    left = rng.randint(1, 31)
                    right = rng.randint(left, 31)
                    self.assertAlmostEqual(
                        index.range_query(left, right),
                        sum(oracle[left - 1 : right]),
                    )

    def test_exact_dp_matches_exhaustive_hybrid_grammar(self) -> None:
        trace = WorkloadTrace(8)
        for left, right in ((1, 3), (2, 7), (5, 8), (2, 2)):
            trace.add_range(left, right)
        trace.add_update(3, 10.0).add_update(7, 5.0).add_get(2)
        constraints = HybridConstraints(
            max_blocks=5,
            max_block_width=8,
            tail_weight=0.25,
            memory_weight_ns=0.01,
        )
        profile = HardwareProfile(
            value_read_ns=1.1,
            aggregate_read_ns=0.7,
            combine_ns=0.4,
            value_write_ns=1.3,
            aggregate_write_ns=0.8,
        )
        for row in synthesize_hybrid_partitions(
            trace, constraints, profile
        ):
            blocks = row["blocks"]
            scored = []
            for path in partitions(trace.n, blocks):
                starts = (1, *(cut + 1 for cut in path[:-1]))
                if max(
                    right - left + 1
                    for left, right in zip(starts, path)
                ) > constraints.max_block_width:
                    continue
                score = 0.0
                for block_index, (left, right) in enumerate(
                    zip(starts, path), start=1
                ):
                    score = round(
                        score
                        + round(
                            _interval_score(
                                trace,
                                left,
                                right,
                                block_index,
                                blocks,
                                constraints,
                                profile,
                            )[0],
                            12,
                        ),
                        12,
                    )
                scored.append((score, path))
            expected = min(scored, key=lambda item: (item[0], item[1]))
            self.assertAlmostEqual(row["score"], expected[0])
            self.assertEqual(tuple(row["boundaries"]), expected[1])

    def test_certificate_replays_and_rejects_omission(self) -> None:
        trace = WorkloadTrace(12)
        for index in range(50):
            trace.add_range(2, 10)
            if index % 5 == 0:
                trace.add_update(3, float(index))
        artifact = compile_hybrid_index(
            range(12),
            trace,
            constraints=HybridConstraints(
                max_blocks=6, max_block_width=6
            ),
        ).export_certificate()
        self.assertTrue(verify_hybrid_certificate(artifact)["verified"])
        omitted = copy.deepcopy(artifact)
        omitted["candidates"].pop()
        redigest(omitted)
        with self.assertRaises(HybridVerificationError):
            verify_hybrid_certificate(omitted)

    def test_generated_cpp_header_executes_hybrid_partition(self) -> None:
        trace = WorkloadTrace(16)
        for index in range(80):
            trace.add_range(2, 10)
            if index % 8 == 0:
                trace.add_update(3, float(index))
        model = compile_hybrid_index(
            range(16),
            trace,
            constraints=HybridConstraints(
                max_blocks=8, max_block_width=8
            ),
        )
        header = model.render_cpp_header("hybrid_generated")
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
    auto structure = hybrid_generated::make_index(values);
    if (std::abs(structure.range_query(2, 10) - 45.0) > 1e-12) return 2;
    structure.point_update(3, 100.0);
    if (std::abs(structure.range_query(2, 10) - 143.0) > 1e-12) return 3;
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
