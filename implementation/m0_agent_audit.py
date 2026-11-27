"""Bounded read-only M0 consumer for the workspace agent; no evidence admission."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from ario_cli import execute_request
from bounded_json import loads_bounded
from core.audit_engine import parse_evidence_ancestry_findings


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def _finite_float(value):
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("nonfinite JSON number")
    return number


def _reject_constant(value):
    raise ValueError("nonfinite JSON constant")


def audit_request_file(path: Path, expected_sha256: str, *, max_bytes: int) -> dict:
    observation = {
        "ok": False, "verdict": "UNKNOWN", "input_sha256": None,
        "report_sha256": None, "violations": [], "ancestry": "UNKNOWN",
        "claim_truth": "UNKNOWN", "source_authentication": "UNKNOWN",
        "independent_admission_authority": "NONE",
        "scope": "SUPPLIED_SNAPSHOT_STRUCTURAL_AUDIT_ONLY",
    }
    if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
            or any(ch not in "0123456789abcdefABCDEF" for ch in expected_sha256)):
        return {**observation, "reason": "INVALID_INPUT_PIN"}
    if not path.is_file() or path.is_symlink():
        return {**observation, "reason": "NOT_REGULAR_FILE"}
    try:
        with path.open("rb") as stream:
            raw = stream.read(max_bytes + 1)
        if len(raw) > max_bytes:
            return {**observation, "reason": "INPUT_BYTE_LIMIT"}
        observation["input_sha256"] = hashlib.sha256(raw).hexdigest()
        if observation["input_sha256"] != expected_sha256.lower():
            return {**observation, "reason": "INPUT_PIN_MISMATCH"}
        payload = loads_bounded(raw.decode("utf-8-sig"), object_pairs_hook=_unique_pairs,
                                parse_float=_finite_float, parse_constant=_reject_constant)
        report = execute_request(payload)
        findings = parse_evidence_ancestry_findings(report["verdict_basis"])
        canonical = json.dumps(report, sort_keys=True, ensure_ascii=True,
                               separators=(",", ":"), allow_nan=False).encode("ascii")
        verdict = report["verdict"]
        if verdict not in ("PASS", "FAIL", "UNKNOWN"):
            return {**observation, "reason": "INVALID_AUDIT_VERDICT"}
        return {**observation, "ok": verdict == "PASS", "verdict": verdict,
                "report_sha256": hashlib.sha256(canonical).hexdigest(),
                "violations": sorted(set(report["violations"])),
                "ancestry": findings["candidate_ancestry"],
                "reason": "STRUCTURAL_RESULT_ONLY"}
    except (OSError, ValueError, TypeError, UnicodeError, OverflowError, RecursionError):
        return {**observation, "reason": "AUDIT_INPUT_OR_EXECUTION_FAILED"}
