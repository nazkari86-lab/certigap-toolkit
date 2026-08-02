from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Callable, Sequence

from .anytime_verifier import verify_anytime_tv_certificate
from .adaptive_profile import parse_adaptive_profile
from .autodro import verify_autodro_selection_artifact
from .autoindex_verifier import verify_autoindex_artifact
from .compiler import (
    CompileInputError,
    _read_json,
    _write_json,
    _write_text,
    compile_spec,
    cpp_include_dir,
    generate_cpp_header,
)
from .dynamic_range_verifier import verify_dynamic_range_certificate
from .hardware import calibrate_hardware
from .hybrid_verifier import verify_hybrid_certificate
from .martingale_safe_autoindex_verifier import (
    verify_martingale_safe_autoindex_certificate,
)
from .martingale_safe_compiler import (
    compile_martingale_safe_spec,
    generate_martingale_safe_cpp_header,
)
from .measured_deployment_verifier import verify_measured_deployment_artifact
from .pruned_verifier import verify_pruned_beam_certificate
from .range_optimizer_verifier import verify_range_optimizer_artifact
from .safe_autoindex_verifier import verify_safe_autoindex_certificate
from .safe_compiler import compile_safe_spec, generate_safe_cpp_header
from .sequential_safe_autoindex_verifier import (
    verify_sequential_safe_autoindex_certificate,
)
from .sequential_safe_compiler import (
    compile_sequential_safe_spec,
    generate_sequential_safe_cpp_header,
)
from .synthesis_verifier import verify_synthesis_certificate
from .tracking_autoindex_verifier import verify_tracking_autoindex_certificate


Verifier = Callable[[dict], dict]

_SCHEMA_VERIFIERS: dict[str, Verifier] = {
    "certigap-autoindex-v2": verify_autoindex_artifact,
    "certigap-dynamic-range-v1": verify_dynamic_range_certificate,
    "certigap-hybrid-v1": verify_hybrid_certificate,
    "certigap-martingale-safe-autoindex-v1": (
        verify_martingale_safe_autoindex_certificate
    ),
    "certigap-measured-deployment-v1": verify_measured_deployment_artifact,
    "certigap-range-optimizer-v1": verify_range_optimizer_artifact,
    "certigap-safe-autoindex-v1": verify_safe_autoindex_certificate,
    "certigap-sequential-safe-autoindex-v1": (
        verify_sequential_safe_autoindex_certificate
    ),
    "certigap-synthesis-v1": verify_synthesis_certificate,
    "certigap-tracking-autoindex-v1": verify_tracking_autoindex_certificate,
}


def _package_version() -> str:
    try:
        return version("certigap-toolkit")
    except PackageNotFoundError:
        return "1.10.1"


def verify_artifact(artifact: dict) -> tuple[str, dict]:
    """Verify a self-describing CertiGap artifact without trusting its summary."""
    if not isinstance(artifact, dict):
        raise ValueError("artifact must be a JSON object")
    schema = artifact.get("schema")
    if isinstance(schema, str) and schema in _SCHEMA_VERIFIERS:
        return schema, _SCHEMA_VERIFIERS[schema](artifact)
    if artifact.get("model") == "CertiGap-AutoDRO-v2":
        return "CertiGap-AutoDRO-v2", verify_autodro_selection_artifact(
            artifact
        )
    if artifact.get("schema") == "certigap-pruned-beam-v1":
        embedded_weights = artifact.get("weights")
        if not isinstance(embedded_weights, list):
            raise ValueError(
                "pruned-beam verification requires embedded weights"
            )
        return "certigap-pruned-beam-v1", verify_pruned_beam_certificate(
            embedded_weights, artifact
        )
    anytime_fields = {
        "version",
        "events",
        "final_incumbent",
        "frontier_sha256",
        "global_lower_bound",
        "stop_reason",
    }
    if anytime_fields.issubset(artifact):
        return "certigap-anytime-tv-v1", verify_anytime_tv_certificate(artifact)
    supported = ", ".join(sorted(_SCHEMA_VERIFIERS))
    raise ValueError(
        f"unsupported artifact type; known schemas: {supported}, "
        "CertiGap-AutoDRO-v2, and anytime-TV certificates"
    )


def explain_artifact(kind: str, artifact: dict, verification: dict) -> dict:
    explanation: dict[str, object] = {
        "artifact_type": kind,
        "verified": bool(verification.get("verified", True)),
        "claim_boundary": (
            "Verification covers the declared model, constraints, candidate "
            "space, and artifact arithmetic. It does not certify portable "
            "wall-clock latency or global optimality outside that space."
        ),
    }
    if kind == "certigap-autoindex-v2":
        selected = artifact["selected"]
        row = next(
            candidate
            for candidate in artifact["candidates"]
            if candidate["name"] == selected
        )
        explanation.update(
            {
                "selected": selected,
                "candidate_count": len(artifact["candidates"]),
                "selection_reason": (
                    "lowest training score among all feasible declared "
                    "portfolio candidates"
                ),
                "selected_score": row["train"]["score"],
                "selected_resources": row["resources"],
                "scope": artifact.get("scope"),
                "leaderboard": [
                    {
                        "name": candidate["name"],
                        "feasible": candidate["feasible"],
                        "reason": candidate["reason"],
                        "train_score": candidate["train"]["score"],
                    }
                    for candidate in sorted(
                        artifact["candidates"],
                        key=lambda candidate: (
                            not candidate["feasible"],
                            candidate["train"]["score"],
                            candidate["name"],
                        ),
                    )
                ],
            }
        )
    elif kind == "certigap-tracking-autoindex-v1":
        explanation.update(
            {
                "selected": artifact["steps"][-1]["selected"],
                "operations": len(artifact["steps"]),
                "switches": sum(step["switched"] for step in artifact["steps"]),
                "actual_structural_cost": artifact["actual_cost"],
                "comparator_switch_limit": artifact["policy"][
                    "max_comparator_switches"
                ],
                "constrained_oracle": artifact["constrained_oracle"],
                "dynamic_regret": artifact["dynamic_regret"],
                "wfa_competitive_factor": artifact[
                    "wfa_competitive_factor"
                ],
                "observed_factor_bound_holds": artifact[
                    "observed_factor_bound_holds"
                ],
                "scope": artifact["scope"],
                "theorem_scope": artifact["theorem_scope"],
            }
        )
    elif kind == "certigap-safe-autoindex-v1":
        decision = artifact["decision"]
        explanation.update(
            {
                "selected": decision["deployed"],
                "train_candidate": decision["train_candidate"],
                "safe_baseline": decision["safe_baseline"],
                "candidate_approved": decision["candidate_approved"],
                "selection_reason": decision["reason"],
                "validation_upper_difference": decision["validation"][
                    "upper_difference"
                ],
                "confidence_alpha": artifact["policy"]["confidence_alpha"],
                "scope": artifact["scope"],
            }
        )
    elif kind == "certigap-measured-deployment-v1":
        decision = artifact["decision"]
        explanation.update(
            {
                "selected": artifact["selected"],
                "candidate": artifact["candidate"],
                "baseline": artifact["baseline"],
                "candidate_deployed": decision["candidate_deployed"],
                "selection_reason": decision["reason"],
                "sample_count": decision["sample_count"],
                "mean_normalized_harm": decision["mean_normalized_harm"],
                "upper_normalized_harm": decision["upper_normalized_harm"],
                "confidence_alpha": artifact["policy"]["alpha"],
                "environment": artifact["environment"],
                "scope": artifact["claim_boundary"],
            }
        )
    elif kind == "certigap-sequential-safe-autoindex-v1":
        decision = artifact["decision"]
        checkpoint = (
            decision["selection_checkpoint"] or decision["final_audit"]
        )
        explanation.update(
            {
                "selected": decision["deployed"],
                "train_candidate": decision["train_candidate"],
                "safe_baseline": decision["safe_baseline"],
                "candidate_approved": decision["candidate_approved"],
                "selection_reason": decision["reason"],
                "stopping_operation": decision["stopping_operation"],
                "upper_difference": (
                    None
                    if checkpoint is None
                    else checkpoint["upper_difference"]
                ),
                "confidence_alpha": artifact["policy"][
                    "confidence_alpha"
                ],
                "monitoring": decision["monitoring"],
                "scope": artifact["scope"],
            }
        )
    elif kind == "certigap-martingale-safe-autoindex-v1":
        decision = artifact["decision"]
        explanation.update(
            {
                "selected": decision["deployed"],
                "train_candidate": decision["train_candidate"],
                "safe_baseline": decision["safe_baseline"],
                "candidate_approved": decision["candidate_approved"],
                "candidate_revoked": decision["candidate_revoked"],
                "selection_reason": decision["reason"],
                "deployment_operation": (
                    None
                    if decision["deployment_event"] is None
                    else decision["deployment_event"]["stream_operation"]
                ),
                "revocation_operation": (
                    None
                    if decision["revocation_event"] is None
                    else decision["revocation_event"]["stream_operation"]
                ),
                "scope": artifact["scope"],
            }
        )
    elif kind in {"certigap-hybrid-v1", "certigap-synthesis-v1"}:
        selected = artifact["selected"]
        selected_row = next(
            row
            for row in artifact["candidates"]
            if row["boundaries"] == selected["boundaries"]
        )
        alternatives = sorted(
            (
                row
                for row in artifact["candidates"]
                if row["feasible"]
                and row["boundaries"] != selected["boundaries"]
            ),
            key=lambda row: (
                row.get("score", row.get("certified_score")),
                row["memory_slots"],
                row["boundaries"],
            ),
        )
        selected_score = selected_row.get(
            "score", selected_row.get("certified_score")
        )
        alternative = alternatives[0] if alternatives else None
        trace = artifact.get("trace", {})
        operation_counts: dict[str, int] = {}
        for operation in trace.get("operations", []):
            operation_counts[operation["kind"]] = (
                operation_counts.get(operation["kind"], 0) + 1
            )
        previous = 0
        widths = []
        for boundary in selected["boundaries"]:
            widths.append(boundary - previous)
            previous = boundary
        explanation.update(
            {
                "selected": selected,
                "candidate_count": len(artifact["candidates"]),
                "selection_reason": (
                    "minimum certified structural score among all feasible "
                    "partitions in the declared contiguous-block grammar"
                ),
                "selected_score": selected_score,
                "selected_memory_slots": selected_row["memory_slots"],
                "block_widths": widths,
                "operation_counts": operation_counts,
                "nearest_alternative": (
                    None
                    if alternative is None
                    else {
                        "boundaries": alternative["boundaries"],
                        "score": alternative.get(
                            "score", alternative.get("certified_score")
                        ),
                        "memory_slots": alternative["memory_slots"],
                        "selected_score_improvement_percent": (
                            0.0
                            if alternative.get(
                                "score",
                                alternative.get("certified_score"),
                            )
                            == 0.0
                            else 100.0
                            * (
                                alternative.get(
                                    "score",
                                    alternative.get("certified_score"),
                                )
                                - selected_score
                            )
                            / alternative.get(
                                "score",
                                alternative.get("certified_score"),
                            )
                        ),
                    }
                ),
                "scope": artifact.get("scope"),
            }
        )
    elif kind == "CertiGap-AutoDRO-v2":
        explanation.update(
            {
                "selected": artifact["selected"],
                "candidate_count": len(artifact["leaderboard"]),
                "selection_reason": (
                    "minimum robust score in the omission-checked declared "
                    "portfolio"
                ),
                "scope": artifact.get("scope"),
            }
        )
    elif kind == "certigap-anytime-tv-v1":
        explanation.update(
            {
                "exact": artifact["exact"],
                "upper_bound": artifact["final_incumbent"]["score"],
                "lower_bound": artifact["global_lower_bound"],
                "relative_gap": artifact["relative_gap"],
                "stop_reason": artifact["stop_reason"],
                "selection_reason": (
                    "best feasible incumbent found before the certified "
                    "stopping condition"
                ),
            }
        )
    else:
        explanation["selection_reason"] = (
            "artifact-specific replay checks completed successfully"
        )
        for key in ("selected", "score", "objective", "scope"):
            if key in artifact:
                explanation[key] = artifact[key]
    return explanation


def _compile(args: argparse.Namespace) -> int:
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
    kind, verification = verify_artifact(artifact)
    print(
        json.dumps(
            {
                "artifact_type": kind,
                "selected": verification["selected"],
                "artifact": str(artifact_path),
                "header": str(header_path),
                "sha256": artifact["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


def _safe_compile(args: argparse.Namespace) -> int:
    source = Path(args.input).resolve()
    artifact_path = Path(args.artifact).resolve()
    header_path = Path(args.header).resolve()
    if len({source, artifact_path, header_path}) != 3:
        raise CompileInputError(
            "input, artifact, and header paths must be distinct"
        )
    certificate = compile_safe_spec(_read_json(source))
    header = generate_safe_cpp_header(
        certificate, namespace=args.namespace
    )
    _write_json(artifact_path, certificate)
    _write_text(header_path, header)
    verification = verify_safe_autoindex_certificate(certificate)
    print(
        json.dumps(
            {
                "artifact_type": certificate["schema"],
                "selected": verification["selected"],
                "candidate_approved": verification["candidate_approved"],
                "artifact": str(artifact_path),
                "header": str(header_path),
                "sha256": certificate["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


def _sequential_safe_compile(args: argparse.Namespace) -> int:
    source = Path(args.input).resolve()
    artifact_path = Path(args.artifact).resolve()
    header_path = Path(args.header).resolve()
    if len({source, artifact_path, header_path}) != 3:
        raise CompileInputError(
            "input, artifact, and header paths must be distinct"
        )
    certificate = compile_sequential_safe_spec(_read_json(source))
    header = generate_sequential_safe_cpp_header(
        certificate, namespace=args.namespace
    )
    _write_json(artifact_path, certificate)
    _write_text(header_path, header)
    verification = verify_sequential_safe_autoindex_certificate(certificate)
    print(
        json.dumps(
            {
                "artifact_type": certificate["schema"],
                "selected": verification["selected"],
                "candidate_approved": verification[
                    "candidate_approved"
                ],
                "stopping_operation": verification["stopping_operation"],
                "artifact": str(artifact_path),
                "header": str(header_path),
                "sha256": certificate["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


def _martingale_safe_compile(args: argparse.Namespace) -> int:
    source = Path(args.input).resolve()
    artifact_path = Path(args.artifact).resolve()
    header_path = Path(args.header).resolve()
    if len({source, artifact_path, header_path}) != 3:
        raise CompileInputError(
            "input, artifact, and header paths must be distinct"
        )
    certificate = compile_martingale_safe_spec(_read_json(source))
    header = generate_martingale_safe_cpp_header(
        certificate, namespace=args.namespace
    )
    _write_json(artifact_path, certificate)
    _write_text(header_path, header)
    verification = verify_martingale_safe_autoindex_certificate(certificate)
    print(
        json.dumps(
            {
                "artifact_type": certificate["schema"],
                "selected": verification["selected"],
                "candidate_approved": verification["candidate_approved"],
                "candidate_revoked": verification["candidate_revoked"],
                "deployment_operation": verification[
                    "deployment_operation"
                ],
                "revocation_operation": verification[
                    "revocation_operation"
                ],
                "artifact": str(artifact_path),
                "header": str(header_path),
                "sha256": certificate["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


def _verify(args: argparse.Namespace) -> int:
    artifact = _read_json(Path(args.artifact).resolve())
    kind, verification = verify_artifact(artifact)
    print(
        json.dumps(
            {"artifact_type": kind, "verification": verification},
            indent=2 if args.pretty else None,
            sort_keys=True,
        )
    )
    return 0


def _explain(args: argparse.Namespace) -> int:
    artifact = _read_json(Path(args.artifact).resolve())
    kind, verification = verify_artifact(artifact)
    print(
        json.dumps(
            explain_artifact(kind, artifact, verification),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


def _calibrate(args: argparse.Namespace) -> int:
    output = Path(args.output).resolve()
    manifest = calibrate_hardware(args.compiler).manifest()
    _write_json(output, manifest)
    print(
        json.dumps(
            {"output": str(output), "sha256": manifest["sha256"]},
            sort_keys=True,
        )
    )
    return 0


def _include_dir(args: argparse.Namespace) -> int:
    del args
    print(cpp_include_dir())
    return 0


def _profile_explain(args: argparse.Namespace) -> int:
    summary = parse_adaptive_profile(Path(args.profile).resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def _checkout_root() -> Path:
    candidates: list[Path] = []
    configured = os.environ.get("CERTIGAP_SOURCE_ROOT")
    if configured:
        candidates.append(Path(configured).expanduser())
    for start in (Path.cwd(), Path(__file__).resolve().parents[1]):
        candidates.extend((start, *start.parents))
    visited: set[Path] = set()
    for candidate in candidates:
        root = candidate.resolve()
        if root in visited:
            continue
        visited.add(root)
        if (
            (root / "verify_artifacts.py").is_file()
            and (root / "pyproject.toml").is_file()
        ):
            return root
    raise ValueError(
        "reproduction requires a CertiGap source checkout; run from the "
        "checkout or set CERTIGAP_SOURCE_ROOT"
    )


def _reproduce(args: argparse.Namespace) -> int:
    root = _checkout_root()
    python = sys.executable
    if args.mode == "tests":
        command = [python, "-m", "unittest", "discover", "-s", "tests", "-v"]
    elif args.mode == "artifacts":
        command = [python, "verify_artifacts.py"]
    else:
        command = [
            python,
            "build_all.py",
            "--benchmark-mode",
            args.benchmark_mode,
        ]
    subprocess.run(command, cwd=root, check=True)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="certigap",
        description=(
            "Compile, verify, explain, calibrate, and reproduce CertiGap "
            "artifacts."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"certigap-toolkit {_package_version()}",
    )
    commands = parser.add_subparsers(dest="command", required=True)

    compile_parser = commands.add_parser(
        "compile", help="compile a workload spec into a C++ configuration"
    )
    compile_parser.add_argument("input")
    compile_parser.add_argument("--artifact", required=True)
    compile_parser.add_argument("--header", required=True)
    compile_parser.add_argument(
        "--namespace", default="certigap_generated"
    )
    compile_parser.set_defaults(handler=_compile)

    safe_compile_parser = commands.add_parser(
        "safe-compile",
        help="compile train/validation/test traces with a no-regression gate",
    )
    safe_compile_parser.add_argument("input")
    safe_compile_parser.add_argument("--artifact", required=True)
    safe_compile_parser.add_argument("--header", required=True)
    safe_compile_parser.add_argument(
        "--namespace", default="certigap_generated"
    )
    safe_compile_parser.set_defaults(handler=_safe_compile)

    sequential_parser = commands.add_parser(
        "sequential-safe-compile",
        help=(
            "compile with an optional-stopping-safe sequential validation gate"
        ),
    )
    sequential_parser.add_argument("input")
    sequential_parser.add_argument("--artifact", required=True)
    sequential_parser.add_argument("--header", required=True)
    sequential_parser.add_argument(
        "--namespace", default="certigap_generated"
    )
    sequential_parser.set_defaults(handler=_sequential_safe_compile)

    martingale_parser = commands.add_parser(
        "martingale-safe-compile",
        help="compile with adapted-data e-process deploy/revoke gates",
    )
    martingale_parser.add_argument("input")
    martingale_parser.add_argument("--artifact", required=True)
    martingale_parser.add_argument("--header", required=True)
    martingale_parser.add_argument(
        "--namespace", default="certigap_generated"
    )
    martingale_parser.set_defaults(handler=_martingale_safe_compile)

    verify_parser = commands.add_parser(
        "verify", help="auto-detect and independently replay an artifact"
    )
    verify_parser.add_argument("artifact")
    verify_parser.add_argument("--pretty", action="store_true")
    verify_parser.set_defaults(handler=_verify)

    explain_parser = commands.add_parser(
        "explain", help="verify an artifact and explain its selection boundary"
    )
    explain_parser.add_argument("artifact")
    explain_parser.set_defaults(handler=_explain)

    calibrate_parser = commands.add_parser(
        "calibrate", help="measure primitive operation costs on this machine"
    )
    calibrate_parser.add_argument(
        "--output", default="hardware_profile.json"
    )
    calibrate_parser.add_argument("--compiler", default="c++")
    calibrate_parser.set_defaults(handler=_calibrate)

    include_parser = commands.add_parser(
        "include-dir", help="print the installed C++ header directory"
    )
    include_parser.set_defaults(handler=_include_dir)

    profile_parser = commands.add_parser(
        "profile-explain",
        help="strictly inspect an adaptive_array workload profile",
    )
    profile_parser.add_argument("profile")
    profile_parser.set_defaults(handler=_profile_explain)

    reproduce_parser = commands.add_parser(
        "reproduce", help="run tests, verify artifacts, or rebuild the package"
    )
    reproduce_parser.add_argument(
        "--mode",
        choices=("tests", "artifacts", "full"),
        default="tests",
    )
    reproduce_parser.add_argument(
        "--benchmark-mode",
        choices=("quick", "full", "max"),
        default="quick",
    )
    reproduce_parser.set_defaults(handler=_reproduce)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except (
        CompileInputError,
        OSError,
        subprocess.CalledProcessError,
        TypeError,
        ValueError,
    ) as exc:
        print(f"certigap: error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
