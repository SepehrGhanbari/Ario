"""Read-only verification of an Ario ledger observation manifest.

This bridge compares a manifest to a fresh bounded read of the nominated ledger.
It produces neither M0 Evidence nor Assessment nor an audit verdict. A match
only establishes consistency with bytes available during the fresh read.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ledger_observation_adapter import observe_ledger

MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MANIFEST_KEYS = frozenset({
    "status", "source", "sha256", "bytes_read", "event_count",
    "observations", "epistemic_limit",
})
LIMIT = "Matching a current ledger read does not authenticate historical events, establish truth, or create admissible Evidence, Assessment, or M0 PASS."


def verify_observation_manifest(manifest: Any, ledger_path: str | Path) -> dict:
    """Compare a supplied observation manifest against a fresh ledger snapshot."""
    def result(status: str, reason: str, **extras: Any) -> dict:
        return {"status": status, "reason": reason, "epistemic_limit": LIMIT, **extras}

    if not isinstance(manifest, dict):
        return result("REJECTED", "manifest must be a JSON object")
    if manifest.get("status") == "UNKNOWN":
        return result("UNKNOWN", "upstream observation is UNKNOWN; no evidence inferred")
    if set(manifest) != MANIFEST_KEYS or manifest.get("status") != "OBSERVED":
        return result("REJECTED", "manifest schema or status is invalid")
    if (not isinstance(manifest.get("source"), str)
            or not isinstance(manifest.get("sha256"), str)
            or not isinstance(manifest.get("bytes_read"), int)
            or isinstance(manifest.get("bytes_read"), bool)
            or not isinstance(manifest.get("event_count"), int)
            or isinstance(manifest.get("event_count"), bool)
            or not isinstance(manifest.get("observations"), list)
            or not isinstance(manifest.get("epistemic_limit"), str)):
        return result("REJECTED", "manifest field types invalid")

    target = Path(ledger_path)
    # Never trust a manifest to redirect us to a different source.
    if manifest["source"] != str(target.absolute()):
        return result("REJECTED", "manifest source does not match nominated ledger")

    current = observe_ledger(target)
    if current["status"] != "OBSERVED":
        return result("UNKNOWN", "fresh ledger observation unavailable", source=current.get("source"), error=current.get("error"))
    # Strict equality also detects forged observation metadata, duplicate lines,
    # altered statuses, missing lines, and modified epistemic-limit wording.
    if manifest != current:
        return result("REJECTED", "manifest differs from fresh ledger observation")
    return result(
        "OBSERVED", "manifest matches a fresh bounded ledger observation",
        source=current["source"], ledger_sha256=current["sha256"],
        event_count=current["event_count"], bytes_read=current["bytes_read"],
    )


def verify_manifest_file(manifest_path: str | Path, ledger_path: str | Path) -> dict:
    """Read at most MAX_MANIFEST_BYTES; never create or modify files."""
    target = Path(manifest_path)
    if target.is_symlink():
        return {"status": "UNKNOWN", "reason": "symlink manifest refused", "epistemic_limit": LIMIT}
    try:
        with target.open("rb") as stream:
            raw = stream.read(MAX_MANIFEST_BYTES + 1)
    except OSError as exc:
        return {"status": "UNKNOWN", "reason": f"manifest unreadable: {type(exc).__name__}", "epistemic_limit": LIMIT}
    if len(raw) > MAX_MANIFEST_BYTES:
        return {"status": "UNKNOWN", "reason": "manifest byte limit exceeded", "epistemic_limit": LIMIT}
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"status": "REJECTED", "reason": "manifest is not valid UTF-8 JSON", "epistemic_limit": LIMIT}
    return verify_observation_manifest(manifest, ledger_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify observation consistency only; no M0 verdict")
    parser.add_argument("manifest", help="Previously saved observation manifest JSON")
    parser.add_argument("ledger", help="Ledger to compare with a fresh bounded read")
    args = parser.parse_args(argv)
    result = verify_manifest_file(args.manifest, args.ledger)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "OBSERVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
