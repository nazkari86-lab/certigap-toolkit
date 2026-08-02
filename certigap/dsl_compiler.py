from __future__ import annotations

import argparse
import json
import sys
from dataclasses import fields
from pathlib import Path
from typing import Sequence

from .compiler import (
    CompileInputError,
    _finite_values,
    _read_json,
    _trace,
    _write_json,
    _write_text,
)
from .dsl import (
    ProofCarryingSpec,
    compile_proof_carrying_index,
)
from .dsl_verifier import verify_dsl_certificate


INPUT_SCHEMA = "certigap-dsl-input-v1"


def load_dsl_spec(raw: object):
    if not isinstance(raw, dict):
        raise CompileInputError("DSL input must be a JSON object")
    allowed = {"schema", "values", "train_trace", "holdout_trace", "spec"}
    unknown = set(raw) - allowed
    if unknown:
        raise CompileInputError(
            "unknown top-level fields: " + ", ".join(sorted(unknown))
        )
    if raw.get("schema") != INPUT_SCHEMA:
        raise CompileInputError(f"schema must be {INPUT_SCHEMA}")
    values = _finite_values(raw.get("values"))
    train = _trace(raw.get("train_trace"), len(values), "train_trace")
    holdout_raw = raw.get("holdout_trace")
    holdout = (
        None
        if holdout_raw is None
        else _trace(holdout_raw, len(values), "holdout_trace")
    )
    spec_raw = raw.get("spec", {})
    if not isinstance(spec_raw, dict):
        raise CompileInputError("spec must be an object")
    allowed_spec = {field.name for field in fields(ProofCarryingSpec)}
    unknown_spec = set(spec_raw) - allowed_spec
    if unknown_spec:
        raise CompileInputError(
            "unknown spec fields: " + ", ".join(sorted(unknown_spec))
        )
    arguments = dict(spec_raw)
    operations = arguments.get("operations")
    if operations is not None:
        if not isinstance(operations, list):
            raise CompileInputError("spec.operations must be an array")
        arguments["operations"] = tuple(operations)
    try:
        spec = ProofCarryingSpec(**arguments)
        spec.validate(len(values))
    except (TypeError, ValueError) as exc:
        raise CompileInputError(f"spec does not validate: {exc}") from exc
    return values, train, holdout, spec


def compile_dsl_spec(raw: object, *, namespace: str = "certigap_generated"):
    values, train, holdout, spec = load_dsl_spec(raw)
    model = compile_proof_carrying_index(
        values, train, spec, holdout_trace=holdout
    )
    artifact = model.export_certificate()
    header = model.render_cpp_header(namespace)
    return artifact, header


def _compile_command(args: argparse.Namespace) -> int:
    source = Path(args.input).resolve()
    artifact_path = Path(args.artifact).resolve()
    header_path = Path(args.header).resolve()
    if len({source, artifact_path, header_path}) != 3:
        raise CompileInputError(
            "input, artifact, and header paths must be distinct"
        )
    artifact, header = compile_dsl_spec(
        _read_json(source), namespace=args.namespace
    )
    _write_json(artifact_path, artifact)
    _write_text(header_path, header)
    summary = verify_dsl_certificate(artifact)
    print(
        json.dumps(
            {
                **summary,
                "artifact": str(artifact_path),
                "header": str(header_path),
            },
            sort_keys=True,
        )
    )
    return 0


def _verify_command(args: argparse.Namespace) -> int:
    artifact = _read_json(Path(args.artifact).resolve())
    if not isinstance(artifact, dict):
        raise CompileInputError("artifact must be a JSON object")
    print(json.dumps(verify_dsl_certificate(artifact), sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="certigap-dsl",
        description="Compile typed proof-carrying data-structure contracts.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    compile_parser = commands.add_parser(
        "compile", help="compile DSL JSON into a certificate and C++ header"
    )
    compile_parser.add_argument("input")
    compile_parser.add_argument("--artifact", required=True)
    compile_parser.add_argument("--header", required=True)
    compile_parser.add_argument("--namespace", default="certigap_generated")
    compile_parser.set_defaults(handler=_compile_command)
    verify_parser = commands.add_parser(
        "verify", help="independently verify a DSL certificate"
    )
    verify_parser.add_argument("artifact")
    verify_parser.set_defaults(handler=_verify_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (CompileInputError, OSError, TypeError, ValueError) as exc:
        print(f"certigap-dsl: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
