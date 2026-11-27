from __future__ import annotations

import argparse
import json
import sys
import types
from dataclasses import fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Union, get_args, get_origin, get_type_hints

from bounded_json import load_json_file_bounded
from core.audit_engine import AuditEngine, AuditInput, parse_evidence_ancestry_findings
from core.schema import Timestamp


def decode_value(annotation: Any, value: Any, path: str = "$") -> Any:
    """Decode JSON into the typed M0 input schema; reject unknown/malformed data."""
    if isinstance(annotation, str):
        # CPython 3.10 get_type_hints() leaves a nested quoted forward reference
        # as a bare name (tuple['LineageCompatibilityAuthorization', ...]).
        # Falling through used to return the raw dict, and AuditEngine then
        # crashed with AttributeError instead of a typed verdict.
        from core import schema as m0_schema

        resolved = getattr(m0_schema, annotation, None)
        if not isinstance(resolved, type):
            raise ValueError(f"{path}: unresolved schema type")
        annotation = resolved

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin in (Union, types.UnionType):
        if value is None and type(None) in args:
            return None
        for option in args:
            if option is type(None):
                continue
            try:
                return decode_value(option, value, path)
            except (TypeError, ValueError):
                pass
        raise ValueError(f"{path}: value does not match any permitted type")

    if origin is tuple:
        if not isinstance(value, list):
            raise TypeError(f"{path}: expected JSON array")
        if len(args) == 2 and args[1] is Ellipsis:
            return tuple(decode_value(args[0], item, f"{path}[{i}]") for i, item in enumerate(value))
        if args and len(args) != len(value):
            raise ValueError(f"{path}: expected {len(args)} items")
        return tuple(decode_value(t, item, f"{path}[{i}]") for i, (t, item) in enumerate(zip(args, value)))

    if origin is list:
        if not isinstance(value, list):
            raise TypeError(f"{path}: expected JSON array")
        item_type = args[0] if args else Any
        return [decode_value(item_type, item, f"{path}[{i}]") for i, item in enumerate(value)]

    if annotation is Any:
        return value

    if isinstance(annotation, type) and issubclass(annotation, Enum):
        try:
            return annotation(value)
        except (ValueError, TypeError) as exc:
            allowed = ", ".join(str(member.value) for member in annotation)
            raise ValueError(f"{path}: unsupported enum value; expected one of: {allowed}") from exc

    if annotation is Timestamp and isinstance(value, str):
        return Timestamp(value)

    if isinstance(annotation, type) and is_dataclass(annotation):
        if not isinstance(value, dict):
            raise TypeError(f"{path}: expected JSON object")
        hints = get_type_hints(annotation)
        allowed = {field.name for field in fields(annotation) if field.init}
        unknown = set(value) - allowed
        if unknown:
            raise ValueError(f"{path}: unknown field(s): {', '.join(sorted(unknown))}")
        kwargs = {
            name: decode_value(hints[name], item, f"{path}.{name}")
            for name, item in value.items()
        }
        try:
            return annotation(**kwargs)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{path}: {exc}") from exc

    if annotation is str:
        if not isinstance(value, str):
            raise TypeError(f"{path}: expected string")
        return value
    if annotation is bool:
        if not isinstance(value, bool):
            raise TypeError(f"{path}: expected boolean")
        return value
    if annotation is int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{path}: expected integer")
        return value
    if annotation is float:
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise TypeError(f"{path}: expected number")
        return float(value)
    return value


def parse_request(payload: Any):
    if not isinstance(payload, dict):
        raise ValueError("$: top-level JSON value must be an object")
    allowed = {
        "audit_id", "rule_versions", "configuration_id",
        "execution_timestamp", "artifacts",
    }
    unknown = set(payload) - allowed
    if unknown:
        raise ValueError(f"$: unknown field(s): {', '.join(sorted(unknown))}")
    missing = allowed - set(payload)
    if missing:
        raise ValueError(f"$: missing field(s): {', '.join(sorted(missing))}")
    if not isinstance(payload["artifacts"], dict):
        raise TypeError("$.artifacts: expected JSON object")
    artifacts = decode_value(AuditInput, payload["artifacts"], "$.artifacts")
    rule_versions = decode_value(tuple[str, ...], payload["rule_versions"], "$.rule_versions")
    timestamp = decode_value(Timestamp, payload["execution_timestamp"], "$.execution_timestamp")
    audit_id = decode_value(str, payload["audit_id"], "$.audit_id")
    configuration_id = decode_value(str, payload["configuration_id"], "$.configuration_id")
    if not rule_versions:
        raise ValueError("$.rule_versions: must not be empty")
    return artifacts, rule_versions, timestamp, audit_id, configuration_id


def result_to_dict(result):
    return {
        "audit_id": result.audit_id,
        "inspector_id": result.inspector_id,
        "inspector_version": result.inspector_version,
        "execution_timestamp": result.execution_timestamp.value,
        "configuration_id": result.configuration_id,
        "rule_versions": list(result.rule_versions),
        "artifacts_examined": [
            {"reference_id": ref.reference_id, "reference_type": ref.reference_type}
            for ref in result.artifacts_examined
        ],
        "violations": list(result.violations),
        "verdict": result.verdict,
        "verdict_basis": result.verdict_basis,
    }


def execute_request(payload):
    artifacts, rule_versions, timestamp, audit_id, configuration_id = parse_request(payload)
    result = AuditEngine().audit(
        artifacts,
        rule_versions=rule_versions,
        configuration_id=configuration_id,
        execution_timestamp=timestamp,
        audit_id=audit_id,
    )
    # Do not let the CLI serialize an unqualified PASS (or FAIL/UNKNOWN)
    # as if the caller-controlled rule list were the complete policy.
    if (
        result.inspector_version == AuditEngine.INSPECTOR_VERSION
        and AuditEngine.ALWAYS_ON_FIREWALL_VERSION not in result.verdict_basis
    ):
        raise ValueError("M0 security profile missing from verdict_basis")
    if result.inspector_version == AuditEngine.INSPECTOR_VERSION:
        parse_evidence_ancestry_findings(result.verdict_basis)
    return result_to_dict(result)


def execute_review_diagnostic(paths) -> dict:
    """Inspect supplied review captures; never create M0 evidence or approval."""
    import hashlib
    from bounded_json import MAX_JSON_FILE_BYTES
    from research.review_evidence import assess, decode
    from research.w38_receipt_fd_guard import read_bounded_regular

    roles = ("pin", "first", "last")
    hashes = {}
    values = []
    try:
        if len(paths) != len(roles):
            raise ValueError("three review inputs required")
        for role, path in zip(roles, paths):
            raw = read_bounded_regular(Path(path), MAX_JSON_FILE_BYTES)
            hashes[role] = hashlib.sha256(raw).hexdigest()
            values.append(decode(raw.decode("utf-8")))
        result = assess(*values)
    except (OSError, ValueError, UnicodeError, RecursionError, OverflowError):
        result = {"gate": "HOLD", "metadata": "UNKNOWN", "merge_authorized": False,
                  "execution_attestation": "UNKNOWN", "review_states": [],
                  "reason": "unreadable or invalid review input"}
    return {
        "operation": "OFFLINE_REVIEW_EVIDENCE_DIAGNOSTIC",
        "input_sha256": hashes,
        "diagnostic": result,
        "claim_truth": "UNKNOWN",
        "source_authentication": "UNKNOWN",
        "freshness": "UNKNOWN",
        "independent_admission_authority": "NONE",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Run Ario's deterministic M0 audit from a JSON request."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input", help="Path to the JSON M0 audit request")
    mode.add_argument("--review-evidence", nargs=3, metavar=("PIN", "FIRST", "LAST"),
                      help="Offline review metadata diagnostic; no M0 evidence or merge authority")
    parser.add_argument(
        "--ledger",
        help="Optional append-only JSONL output ledger; existing entries are never replaced",
    )
    args = parser.parse_args(argv)
    if args.review_evidence is not None:
        if args.ledger is not None:
            parser.error("--ledger is only available for the M0 audit input")
        report = execute_review_diagnostic(args.review_evidence)
        print(json.dumps(report, ensure_ascii=True, sort_keys=True))
        return 1  # Preserve the original diagnostic's non-passing gate status.

    try:
        payload = load_json_file_bounded(args.input)
        result = execute_request(payload)
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True)
        if args.ledger:
            ledger_path = Path(args.ledger)
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with ledger_path.open("a", encoding="utf-8", newline="\n") as ledger:
                ledger.write(serialized + "\n")
        print(serialized)
        return 0
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({
            "error": "AUDIT_INPUT_OR_EXECUTION_FAILED",
            "detail": str(exc),
            "verdict": "UNKNOWN",
        }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
