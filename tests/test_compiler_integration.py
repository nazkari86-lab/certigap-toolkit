from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from certigap.compiler import (
    CompileInputError,
    compile_spec,
    generate_cpp_header,
    load_compile_spec,
)


ROOT = Path(__file__).resolve().parents[1]


def spec(
    *,
    aggregate: str = "sum",
    constraints: dict | None = None,
    operations: list[dict] | None = None,
) -> dict:
    configured = {"aggregate": aggregate, "budget": 3}
    configured.update(constraints or {})
    return {
        "schema": "certigap-compile-input-v1",
        "values": list(range(8)),
        "train_trace": {
            "n": 8,
            "operations": operations
            or [{"kind": "range", "left": 2, "right": 8}] * 20,
        },
        "holdout_trace": {
            "n": 8,
            "operations": [{"kind": "get", "left": 8}],
        },
        "constraints": configured,
    }


class CompilerIntegrationTests(unittest.TestCase):
    def test_json_schema_is_strict_and_shorthand_is_canonicalized(self) -> None:
        raw = spec(operations=[{"kind": "get", "left": 2}])
        values, train, holdout, constraints = load_compile_spec(raw)
        self.assertEqual(values[2], 2.0)
        self.assertEqual(train.operations[0].right, 2)
        self.assertEqual(holdout.operations[0].left, 8)
        self.assertEqual(constraints.aggregate, "sum")

        invalid = copy.deepcopy(raw)
        invalid["unexpected"] = True
        with self.assertRaisesRegex(CompileInputError, "unknown top-level"):
            load_compile_spec(invalid)
        boolean_rank = spec(
            operations=[{"kind": "get", "left": True}]
        )
        with self.assertRaisesRegex(CompileInputError, "ranks"):
            load_compile_spec(boolean_rank)
        boolean_value = spec()
        boolean_value["values"][0] = False
        with self.assertRaisesRegex(CompileInputError, "not boolean"):
            load_compile_spec(boolean_value)

    def test_header_is_deterministic_and_namespace_is_validated(self) -> None:
        artifact = compile_spec(spec())
        left = generate_cpp_header(artifact, namespace="demo::generated")
        right = generate_cpp_header(artifact, namespace="demo::generated")
        self.assertEqual(left, right)
        self.assertIn(artifact["sha256"], left)
        with self.assertRaisesRegex(CompileInputError, "namespace"):
            generate_cpp_header(artifact, namespace="bad-name")

    def test_cli_compiles_verifies_and_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            artifact = root / "selection.json"
            header = root / "generated.hpp"
            source.write_text(json.dumps(spec()), encoding="utf-8")
            command = [
                sys.executable,
                "-m",
                "certigap.compiler",
                "compile",
                str(source),
                "--artifact",
                str(artifact),
                "--header",
                str(header),
            ]
            result = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(artifact.is_file())
            self.assertTrue(header.is_file())
            verification = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "certigap.compiler",
                    "verify",
                    str(artifact),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(verification.returncode, 0, verification.stderr)
            self.assertTrue(json.loads(verification.stdout)["verified"])

            broken = json.loads(artifact.read_text(encoding="utf-8"))
            broken["selected"] = "sorted_array"
            artifact.write_text(json.dumps(broken), encoding="utf-8")
            rejected = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "certigap.compiler",
                    "verify",
                    str(artifact),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("digest mismatch", rejected.stderr)

    def test_cli_does_not_write_partial_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            artifact = root / "selection.json"
            header = root / "generated.hpp"
            source.write_text(json.dumps(spec()), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "certigap.compiler",
                    "compile",
                    str(source),
                    "--artifact",
                    str(artifact),
                    "--header",
                    str(header),
                    "--namespace",
                    "invalid-name",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertFalse(artifact.exists())
            self.assertFalse(header.exists())

    def test_cli_rejects_duplicate_json_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "input.json"
            source.write_text(
                '{"schema":"certigap-compile-input-v1",'
                '"schema":"certigap-compile-input-v1",'
                '"values":[0],"train_trace":{"n":1,"operations":[]}}',
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "certigap.compiler",
                    "compile",
                    str(source),
                    "--artifact",
                    str(root / "selection.json"),
                    "--header",
                    str(root / "generated.hpp"),
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("duplicate JSON key", result.stderr)

    def test_generated_cpp_backends_match_oracles(self) -> None:
        cases = {
            "array_sum": spec(
                constraints={"memory_limit_slots": 8},
                operations=[{"kind": "range", "left": 1, "right": 8}] * 20,
            ),
            "fenwick_sum": spec(),
            "segment_sum": spec(
                constraints={"segment_tree_unit_cost": 0.1},
            ),
            "certirange_sum": spec(
                constraints={"require_persistent_snapshots": True},
            ),
            "segment_min": spec(
                aggregate="min",
                constraints={"segment_tree_unit_cost": 0.1},
            ),
            "segment_max": spec(
                aggregate="max",
                constraints={"segment_tree_unit_cost": 0.1},
            ),
        }
        expected = {
            "array_sum": "sorted_array",
            "fenwick_sum": "fenwick",
            "segment_sum": "segment_tree",
            "segment_min": "segment_tree",
            "segment_max": "segment_tree",
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, raw in cases.items():
                artifact = compile_spec(raw)
                if name in expected:
                    self.assertEqual(artifact["selected"], expected[name])
                else:
                    self.assertTrue(artifact["selected"].startswith("certirange"))
                (root / f"{name}.hpp").write_text(
                    generate_cpp_header(
                        artifact, namespace=f"generated_{name}"
                    ),
                    encoding="utf-8",
                )
            source = root / "main.cpp"
            source.write_text(
                """
#include <cmath>
#include <vector>
#include "array_sum.hpp"
#include "fenwick_sum.hpp"
#include "segment_sum.hpp"
#include "certirange_sum.hpp"
#include "segment_min.hpp"
#include "segment_max.hpp"

template <class Index>
bool check_sum() {
    Index index({0, 1, 2, 3, 4, 5, 6, 7});
    auto snapshot = index.snapshot();
    if (std::abs(index.range_query(2, 8) - 28.0) > 1e-12) return false;
    index.point_update(2, 100.0);
    return std::abs(index.range_query(1, 3) - 102.0) <= 1e-12
        && std::abs(snapshot.get(2) - 1.0) <= 1e-12;
}

int main() {
    if (!check_sum<generated_array_sum::Index>()) return 2;
    if (!check_sum<generated_fenwick_sum::Index>()) return 3;
    if (!check_sum<generated_segment_sum::Index>()) return 4;
    if (!check_sum<generated_certirange_sum::Index>()) return 5;
    generated_segment_min::Index minimum({7, 6, 5, 4, 3, 2, 1, 0});
    generated_segment_max::Index maximum({0, 1, 2, 3, 4, 5, 6, 7});
    if (minimum.range_query(2, 7) != 1.0) return 6;
    if (maximum.range_query(2, 7) != 6.0) return 7;
    minimum.point_update(7, 9.0);
    maximum.point_update(7, -9.0);
    if (minimum.range_query(2, 7) != 2.0) return 8;
    if (maximum.range_query(2, 7) != 5.0) return 9;
    return 0;
}
""",
                encoding="utf-8",
            )
            executable = root / "autoindex_test"
            compile_result = subprocess.run(
                [
                    "c++",
                    "-std=c++17",
                    "-Wall",
                    "-Wextra",
                    "-pedantic",
                    "-I",
                    str(root),
                    "-I",
                    str(ROOT / "cpp"),
                    str(source),
                    "-o",
                    str(executable),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(
                compile_result.returncode, 0, compile_result.stderr
            )
            run_result = subprocess.run(
                [str(executable)], check=False
            )
            self.assertEqual(run_result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
