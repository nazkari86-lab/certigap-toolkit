from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from certigap import (
    DSLVerificationError,
    ProofCarryingSpec,
    WorkloadTrace,
    compile_proof_carrying_index,
    verify_dsl_certificate,
)
from certigap.dsl_compiler import CompileInputError, compile_dsl_spec


ROOT = Path(__file__).resolve().parents[1]


def _digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("utf-8")
    ).hexdigest()


def raw_spec(algebra: str = "sum") -> dict:
    return {
        "schema": "certigap-dsl-input-v1",
        "values": list(range(16)),
        "train_trace": {
            "n": 16,
            "operations": [
                {"kind": "range", "left": 2, "right": 15}
                for _ in range(32)
            ],
        },
        "holdout_trace": {
            "n": 16,
            "operations": [{"kind": "range", "left": 1, "right": 16}],
        },
        "spec": {"operations": ["range"], "algebra": algebra},
    }


class ProofCarryingDSLTests(unittest.TestCase):
    def test_builtin_algebras_generate_complete_typed_grammar(self) -> None:
        for algebra in ("sum", "min", "max"):
            with self.subTest(algebra=algebra):
                raw = raw_spec(algebra)
                artifact, _ = compile_dsl_spec(raw)
                verified = verify_dsl_certificate(artifact)
                self.assertTrue(verified["typed_capabilities_verified"])
                self.assertTrue(verified["grammar_completeness_verified"])
                self.assertEqual(verified["design_count"], 8)
                designs = {
                    row["backend"]: row for row in artifact["grammar"]["designs"]
                }
                self.assertEqual(
                    designs["fenwick"]["algebra_eligible"], algebra == "sum"
                )
                self.assertEqual(
                    designs["sparse_table"]["algebra_eligible"],
                    algebra in {"min", "max"},
                )

    def test_runtime_matches_oracle_after_updates(self) -> None:
        for algebra in ("sum", "min", "max"):
            trace = WorkloadTrace(32)
            for left in range(1, 17):
                trace.add_range(left, 33 - left).add_update(left, left * 2.0)
            model = compile_proof_carrying_index(
                range(32), trace, ProofCarryingSpec(algebra=algebra)
            )
            oracle = [float(value) for value in range(32)]
            for key in range(1, 17):
                value = float(key * 3 - 7)
                model.point_update(key, value)
                oracle[key - 1] = value
                selected = oracle[key - 1 : 32 - key + 1]
                expected = (
                    sum(selected)
                    if algebra == "sum"
                    else min(selected) if algebra == "min" else max(selected)
                )
                self.assertEqual(model.range_query(key, 32 - key + 1), expected)

    def test_undeclared_operations_and_unknown_algebras_fail_closed(self) -> None:
        trace = WorkloadTrace(8).add_range(1, 8).add_update(1, 2.0)
        with self.assertRaisesRegex(ValueError, "undeclared operations"):
            compile_proof_carrying_index(
                range(8), trace, ProofCarryingSpec(operations=("range",))
            )
        invalid = raw_spec()
        invalid["spec"]["algebra"] = "median"
        with self.assertRaisesRegex(CompileInputError, "algebra"):
            compile_dsl_spec(invalid)

        range_only = WorkloadTrace(8).add_range(1, 8)
        model = compile_proof_carrying_index(
            range(8), range_only, ProofCarryingSpec(operations=("range",))
        )
        with self.assertRaisesRegex(RuntimeError, "not declared"):
            model.get(1)
        with self.assertRaisesRegex(RuntimeError, "not declared"):
            model.point_update(1, 2.0)

    def test_independent_verifier_rejects_rehashed_grammar_omission(self) -> None:
        artifact, _ = compile_dsl_spec(raw_spec())
        tampered = copy.deepcopy(artifact)
        tampered["grammar"]["designs"].pop()
        grammar_unsigned = dict(tampered["grammar"])
        grammar_unsigned.pop("sha256")
        tampered["grammar"]["sha256"] = _digest(grammar_unsigned)
        outer_unsigned = dict(tampered)
        outer_unsigned.pop("sha256")
        tampered["sha256"] = _digest(outer_unsigned)
        with self.assertRaisesRegex(DSLVerificationError, "incomplete"):
            verify_dsl_certificate(tampered)

    def test_independent_verifier_rejects_rehashed_law_change(self) -> None:
        artifact, _ = compile_dsl_spec(raw_spec("min"))
        tampered = copy.deepcopy(artifact)
        tampered["algebra"]["laws"]["has_inverse"] = True
        outer_unsigned = dict(tampered)
        outer_unsigned.pop("sha256")
        tampered["sha256"] = _digest(outer_unsigned)
        with self.assertRaisesRegex(DSLVerificationError, "laws"):
            verify_dsl_certificate(tampered)

    def test_cli_and_unified_verifier_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "dsl.json"
            artifact = root / "certificate.json"
            header = root / "generated.hpp"
            cli_input = raw_spec()
            cli_input["spec"]["operations"] = ["get", "range", "update"]
            source.write_text(json.dumps(cli_input), encoding="utf-8")
            compiled = subprocess.run(
                [
                    sys.executable, "-m", "certigap.dsl_compiler", "compile",
                    str(source), "--artifact", str(artifact), "--header",
                    str(header), "--namespace", "dsl_generated",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(compiled.returncode, 0, compiled.stderr)
            self.assertTrue(json.loads(compiled.stdout)["verified"])
            unified = subprocess.run(
                [sys.executable, "-m", "certigap.cli", "verify", str(artifact)],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(unified.returncode, 0, unified.stderr)
            self.assertEqual(
                json.loads(unified.stdout)["artifact_type"],
                "certigap-proof-carrying-dsl-v1",
            )

            source_cpp = root / "main.cpp"
            source_cpp.write_text(
                """
#include "generated.hpp"

int main() {
    dsl_generated::Index index({0, 1, 2, 3, 4, 5, 6, 7,
                                8, 9, 10, 11, 12, 13, 14, 15});
    if (index.range_query(2, 15) != 105.0) return 1;
    index.point_update(2, 20.0);
    return index.range_query(1, 3) == 22.0 ? 0 : 2;
}
""",
                encoding="utf-8",
            )
            executable = root / "dsl_consumer"
            built = subprocess.run(
                [
                    "c++", "-std=c++17", "-Wall", "-Wextra", "-Wpedantic",
                    "-Werror", "-I", str(root), "-I", str(ROOT / "cpp"),
                    str(source_cpp), "-o", str(executable),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(built.returncode, 0, built.stderr)
            subprocess.run([str(executable)], check=True)

    def test_generated_cpp_omits_undeclared_operations(self) -> None:
        raw = raw_spec()
        _, header = compile_dsl_spec(raw, namespace="range_contract")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "generated.hpp").write_text(header, encoding="utf-8")
            (root / "main.cpp").write_text(
                """
#include "generated.hpp"
int main() {
    range_contract::Index index({0, 1, 2, 3, 4, 5, 6, 7,
                                 8, 9, 10, 11, 12, 13, 14, 15});
    index.point_update(1, 4.0);
}
""",
                encoding="utf-8",
            )
            compiled = subprocess.run(
                [
                    "c++", "-std=c++17", "-I", str(root), "-I",
                    str(ROOT / "cpp"), str(root / "main.cpp"), "-o",
                    str(root / "should_not_build"),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertNotEqual(compiled.returncode, 0)
            self.assertIn("point_update", compiled.stderr)


if __name__ == "__main__":
    unittest.main()
