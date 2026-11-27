"""Compare a previous execution ledger against a caller-pinned observation manifest."""
from __future__ import annotations

import hashlib
from pathlib import Path

from bounded_json import loads_bounded
from ledger_audit_bridge import MAX_MANIFEST_BYTES, verify_observation_manifest
from research.w38_receipt_fd_guard import read_bounded_regular


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def verify_pinned_manifest(manifest_path: Path, expected_sha256: str, ledger_path: Path) -> dict:
    observation = {
        "ok": False, "ledger_status": "UNKNOWN",
        "scope": "CALLER_PINNED_LOCAL_LEDGER_OBSERVATION_ONLY",
        "manifest_sha256": None, "ledger_sha256": None,
        "event_count": None, "bytes_read": None,
        "claim_truth": "UNKNOWN", "source_authentication": "UNKNOWN",
        "freshness": "UNKNOWN", "independent_admission_authority": "NONE",
    }
    if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
            or any(c not in "0123456789abcdefABCDEF" for c in expected_sha256)):
        return {**observation, "reason": "INVALID_MANIFEST_PIN"}
    try:
        raw = read_bounded_regular(manifest_path, MAX_MANIFEST_BYTES)
        observation["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        if observation["manifest_sha256"] != expected_sha256.lower():
            return {**observation, "ledger_status": "REJECTED", "reason": "MANIFEST_PIN_MISMATCH"}
        manifest = loads_bounded(raw.decode("utf-8"), object_pairs_hook=_unique_pairs)
        result = verify_observation_manifest(manifest, ledger_path)
        status = result["status"]
        if status != "OBSERVED":
            return {**observation, "ledger_status": status,
                    "reason": "LEDGER_COMPARISON_" + status}
        return {**observation, "ok": True, "ledger_status": "OBSERVED",
                "ledger_sha256": result["ledger_sha256"], "event_count": result["event_count"],
                "bytes_read": result["bytes_read"], "reason": "LOCAL_MANIFEST_MATCH"}
    except (OSError, ValueError, UnicodeError, TypeError, RecursionError):
        return {**observation, "reason": "MANIFEST_READ_OR_VALIDATION_FAILED"}
