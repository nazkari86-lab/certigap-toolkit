from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Sequence

from .autoindex import (
    AutoIndexConstraints,
    TraceOperation,
    WorkloadTrace,
    compile_autoindex,
)
from .autoindex_verifier import verify_autoindex_artifact
from .dynamic_range import _complete_topology


INPUT_SCHEMA = "certigap-compile-input-v1"
_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_BACKEND_ENUM = {
    "sorted_array": "SortedArray",
    "fenwick": "Fenwick",
    "segment_tree": "SegmentTree",
    "certirange_point": "CertiRangePoint",
    "certirange_range": "CertiRangeRange",
}
_AGGREGATE_ENUM = {"sum": "Sum", "min": "Min", "max": "Max"}


class CompileInputError(ValueError):
    pass


def _read_json(path: Path) -> object:
    def unique_object(pairs: list[tuple[str, object]]) -> dict:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise CompileInputError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=unique_object,
        )
    except OSError as exc:
        raise CompileInputError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise CompileInputError(
            f"{path}:{exc.lineno}:{exc.colno}: invalid JSON"
        ) from exc


def _finite_values(raw: object) -> list[float]:
    if not isinstance(raw, list) or not raw:
        raise CompileInputError("values must be a non-empty JSON array")
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in raw
    ):
        raise CompileInputError("values must be numeric and not boolean")
    try:
        values = [float(value) for value in raw]
    except (TypeError, ValueError) as exc:
        raise CompileInputError("values must be numeric") from exc
    if any(not math.isfinite(value) for value in values):
        raise CompileInputError("values must be finite")
    return values


def _trace(raw: object, n: int, label: str) -> WorkloadTrace:
    if not isinstance(raw, dict) or set(raw) != {"n", "operations"}:
        raise CompileInputError(
            f"{label} must contain exactly n and operations"
        )
    if raw["n"] != n or isinstance(raw["n"], bool):
        raise CompileInputError(f"{label}.n must equal len(values)")
    operations = raw["operations"]
    if not isinstance(operations, list):
        raise CompileInputError(f"{label}.operations must be an array")
    parsed: list[TraceOperation] = []
    try:
        for index, operation in enumerate(operations):
            if not isinstance(operation, dict):
                raise CompileInputError(
                    f"{label}.operations[{index}] must be an object"
                )
            unknown = set(operation) - {"kind", "left", "right", "value"}
            if unknown:
                raise CompileInputError(
                    f"{label}.operations[{index}] has unknown fields: "
                    + ", ".join(sorted(unknown))
                )
            if not {"kind", "left"}.issubset(operation):
                raise CompileInputError(
                    f"{label}.operations[{index}] lacks kind or left"
                )
            left = operation["left"]
            right = operation.get("right", left)
            value = operation.get("value", 0.0)
            if operation["kind"] not in {"get", "range", "update"}:
                raise CompileInputError(
                    f"{label}.operations[{index}] has invalid kind"
                )
            if (
                not isinstance(left, int)
                or isinstance(left, bool)
                or not isinstance(right, int)
                or isinstance(right, bool)
            ):
                raise CompileInputError(
                    f"{label}.operations[{index}] ranks must be integers"
                )
            if isinstance(value, bool) or not isinstance(
                value, (int, float)
            ):
                raise CompileInputError(
                    f"{label}.operations[{index}] value must be numeric"
                )
            parsed.append(
                TraceOperation(
                    kind=operation["kind"],
                    left=left,
                    right=right,
                    value=float(value),
                )
            )
        return WorkloadTrace(n, parsed)
    except CompileInputError:
        raise
    except (TypeError, ValueError) as exc:
        raise CompileInputError(f"{label} does not validate: {exc}") from exc


def load_compile_spec(
    raw: object,
) -> tuple[
    list[float],
    WorkloadTrace,
    WorkloadTrace | None,
    AutoIndexConstraints,
]:
    if not isinstance(raw, dict):
        raise CompileInputError("compile input must be a JSON object")
    allowed = {
        "schema",
        "values",
        "train_trace",
        "holdout_trace",
        "constraints",
    }
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
    constraints_raw = raw.get("constraints", {})
    if not isinstance(constraints_raw, dict):
        raise CompileInputError("constraints must be an object")
    try:
        constraints = AutoIndexConstraints(**constraints_raw)
        constraints.validate(len(values))
    except (TypeError, ValueError) as exc:
        raise CompileInputError(f"constraints do not validate: {exc}") from exc
    return values, train, holdout, constraints


def compile_spec(raw: object) -> dict:
    values, train, holdout, constraints = load_compile_spec(raw)
    model = compile_autoindex(
        values,
        train,
        constraints=constraints,
        holdout_trace=holdout,
    )
    return model.export_selection_artifact()


def _namespace_parts(namespace: str) -> list[str]:
    parts = namespace.split("::")
    if not parts or any(not _IDENTIFIER.fullmatch(part) for part in parts):
        raise CompileInputError(
            "namespace must be C++ identifiers separated by ::"
        )
    return parts


def _topology_rows(topology: dict) -> list[tuple[int, int, int, int, int]]:
    rows: list[list[int]] = []

    def visit(node: dict) -> int:
        index = len(rows)
        left, right = node["interval"]
        threshold = left if node["type"] == "leaf" else node["threshold"]
        rows.append([left, right, threshold, -1, -1])
        if node["type"] != "leaf":
            rows[index][3] = visit(node["left"])
            rows[index][4] = visit(node["right"])
        return index

    visit(topology)
    return [tuple(row) for row in rows]


def _selected_topology(artifact: dict) -> list[tuple[int, int, int, int, int]]:
    selected = next(
        row for row in artifact["candidates"]
        if row["name"] == artifact["selected"]
    )
    if not artifact["selected"].startswith("certirange"):
        return []
    minimum = 0 if artifact["n"] <= 1 else math.ceil(math.log2(artifact["n"]))
    max_depth = artifact["constraints"]["max_depth"] or 2 * minimum + 1
    topology = _complete_topology(
        selected["routing_tree"], 1, artifact["n"], max_depth
    )
    return _topology_rows(topology)


def generate_cpp_header(
    artifact: dict,
    *,
    namespace: str = "certigap_generated",
) -> str:
    verification = verify_autoindex_artifact(artifact)
    parts = _namespace_parts(namespace)
    rows = _selected_topology(artifact)
    selected = artifact["selected"]
    aggregate = artifact["constraints"]["aggregate"]
    lines = [
        "// Generated by certigap-compile. Do not edit.",
        "#pragma once",
        "",
        "#include <array>",
        '#include "certigap_autoindex.hpp"',
        "",
    ]
    lines.extend(f"namespace {part} {{" for part in parts)
    lines.extend(
        [
            "",
            "struct Config {",
            f"    static constexpr std::size_t kN = {artifact['n']};",
            (
                "    static constexpr certigap::Backend kBackend = "
                f"certigap::Backend::{_BACKEND_ENUM[selected]};"
            ),
            (
                "    static constexpr certigap::Aggregate kAggregate = "
                f"certigap::Aggregate::{_AGGREGATE_ENUM[aggregate]};"
            ),
            (
                "    static constexpr const char* kArtifactSha256 = "
                f'"{artifact["sha256"]}";'
            ),
            (
                "    static constexpr const char* kSelectionScope = "
                '"complete deterministic five-candidate training portfolio";'
            ),
            (
                "    inline static constexpr "
                f"std::array<certigap::TopologyNode, {len(rows)}> "
                "kTopology = {"
            ),
        ]
    )
    for left, right, threshold, left_child, right_child in rows:
        lines.append(
            "        certigap::TopologyNode{"
            f"{left}, {right}, {threshold}, {left_child}, {right_child}"
            "},"
        )
    lines.extend(
        [
            "    };",
            "};",
            "",
            "using Index = certigap::AutoIndex<Config>;",
            f"inline constexpr const char* kSelectedName = \"{selected}\";",
            (
                "inline constexpr double kVerifiedTrainScore = "
                f"{verification['train_score']:.17g};"
            ),
            "",
        ]
    )
    lines.extend(f"}}  // namespace {part}" for part in reversed(parts))
    return "\n".join(lines) + "\n"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _write_json(path: Path, value: object) -> None:
    _write_text(
        path,
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
    )


def _compile_command(args: argparse.Namespace) -> int:
    source = Path(args.input).resolve()
    artifact_path = Path(args.artifact).resolve()
    header_path = Path(args.header).resolve()
    if len({source, artifact_path, header_path}) != 3:
        raise CompileInputError(
            "input, artifact, and header paths must be distinct"
        )
    artifact = compile_spec(_read_json(source))
    header = generate_cpp_header(artifact, namespace=args.namespace)
    _write_json(artifact_path, artifact)
    _write_text(header_path, header)
    summary = verify_autoindex_artifact(artifact)
    print(
        json.dumps(
            {
                "selected": summary["selected"],
                "train_score": summary["train_score"],
                "candidate_count": summary["candidate_count"],
                "artifact": str(artifact_path),
                "header": str(header_path),
                "sha256": artifact["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


def _verify_command(args: argparse.Namespace) -> int:
    artifact = _read_json(Path(args.artifact).resolve())
    if not isinstance(artifact, dict):
        raise CompileInputError("artifact must be a JSON object")
    print(json.dumps(verify_autoindex_artifact(artifact), sort_keys=True))
    return 0


def cpp_include_dir() -> Path:
    installed = Path(sys.prefix) / "include" / "certigap"
    source = Path(__file__).resolve().parents[1] / "cpp"
    for candidate in (installed, source):
        if (candidate / "certigap_autoindex.hpp").is_file():
            return candidate
    raise CompileInputError(
        "certigap_autoindex.hpp is missing; reinstall certigap-toolkit"
    )


def _include_dir_command(args: argparse.Namespace) -> int:
    del args
    print(cpp_include_dir())
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="certigap-compile",
        description="Compile and verify Certified AutoIndex configurations.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    compile_parser = subparsers.add_parser(
        "compile", help="compile JSON workload into artifact and C++ header"
    )
    compile_parser.add_argument("input")
    compile_parser.add_argument("--artifact", required=True)
    compile_parser.add_argument("--header", required=True)
    compile_parser.add_argument(
        "--namespace", default="certigap_generated"
    )
    compile_parser.set_defaults(handler=_compile_command)
    verify_parser = subparsers.add_parser(
        "verify", help="independently verify a selection artifact"
    )
    verify_parser.add_argument("artifact")
    verify_parser.set_defaults(handler=_verify_command)
    include_parser = subparsers.add_parser(
        "include-dir", help="print the installed C++ header directory"
    )
    include_parser.set_defaults(handler=_include_dir_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (CompileInputError, OSError, ValueError, TypeError) as exc:
        print(f"certigap-compile: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
