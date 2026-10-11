"""Ario EA-0.1: prepare a non-admitted candidate dossier from a verified ledger observation.

No M0 Evidence, Assessment, Claim, or AuditResult is constructed here.
A dossier only describes what current ledger bytes report. It is not admissible evidence.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from ledger_audit_bridge import verify_observation_manifest

CONTRACT_VERSION = "EA-0.1"
MAX_CLAIM_CHARS = 400
MAX_SCOPE_CHARS = 400
MAX_RELATION_CHARS = 600
MAX_ID_CHARS = 160
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_LIMIT = (
    "Candidate only. Current ledger consistency is not historical authentication, "
    "independent corroboration, admissible Evidence, Assessment, M0 PASS, or truth."
)


def _unknown(reason: str) -> dict:
    return {
        "status": "UNKNOWN", "reason": reason,
        "admission_decision": "NOT_EVALUATED", "epistemic_limit": _LIMIT,
    }


def _rejected(reason: str) -> dict:
    return {
        "status": "REJECTED", "reason": reason,
        "admission_decision": "NOT_EVALUATED", "epistemic_limit": _LIMIT,
    }


def _valid_text(value: Any, limit: int) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= limit


def build_candidate_dossier(
    manifest: Any,
    ledger_path: str | Path,
    *,
    line: int,
    claim_id: str,
    claim_scope: str,
    proposed_support_relation: str,
) -> dict:
    """Produce a candidate for exactly one *currently matching* manifest record.

    User-supplied claim text is a declaration, never an automatically accepted claim.
    """
    if not isinstance(line, int) or isinstance(line, bool) or line <= 0:
        return _rejected("line must be a positive integer")
    for field, value, limit in (
        ("claim_id", claim_id, MAX_ID_CHARS),
        ("claim_scope", claim_scope, MAX_SCOPE_CHARS),
        ("proposed_support_relation", proposed_support_relation, MAX_RELATION_CHARS),
    ):
        if not _valid_text(value, limit):
            return _rejected(f"{field} must be non-empty bounded text")

    if not isinstance(manifest, dict):
        return _rejected("manifest must be an object")
    # A valid upstream UNKNOWN is preserved, not recast into evidence.
    if manifest.get("status") == "UNKNOWN":
        return _unknown("upstream manifest is UNKNOWN")

    # The bridge re-reads the nominated ledger and checks the complete manifest.
    verification = verify_observation_manifest(manifest, ledger_path)
    if verification["status"] == "UNKNOWN":
        return _unknown("bridge cannot establish a fresh matching observation")
    if verification["status"] != "OBSERVED":
        return _rejected("manifest failed fresh ledger verification")

    matches = [o for o in manifest["observations"] if o.get("line") == line]
    if len(matches) != 1:
        return _rejected("locator must resolve to exactly one observation")
    observation = matches[0]
    record_digest = observation["record_sha256"]
    ledger_digest = manifest["sha256"]
    if (not isinstance(record_digest, str) or not _SHA256.fullmatch(record_digest)
            or not isinstance(ledger_digest, str) or not _SHA256.fullmatch(ledger_digest)):
        return _rejected("unusable SHA-256 digest")

    # Status labels from the ledger remain *reported* statuses, not acceptance decisions.
    return {
        "status": "CANDIDATE",
        "contract_version": CONTRACT_VERSION,
        "admission_decision": "NOT_EVALUATED",
        "source_ledger": {
            "path": manifest["source"],
            "sha256": ledger_digest,
        },
        "observation_locator": {
            "line": line,
            "record_sha256": record_digest,
            "event": observation["event"],
            "reported_task_id": observation["task_id"],
            "reported_workflow_id": observation["workflow_id"],
            "reported_status": observation["reported_status"],
        },
        "bridge_verification": {
            "status": "OBSERVED",
            "implementation": "ledger_audit_bridge.verify_observation_manifest",
            "contract_version": "ledger-audit-bridge-v0.1",
            "ledger_sha256": verification["ledger_sha256"],
        },
        "claim_id": claim_id.strip(),
        "claim_scope": claim_scope.strip(),
        "proposed_support_relation": proposed_support_relation.strip(),
        "provenance_limitations": (
            "Ledger origin and historical event authenticity are not independently authenticated; "
            "reported timestamps and statuses are declarations in local bytes."
        ),
        "independence_declaration": "UNKNOWN",
        "temporal_scope": (
            "This dossier is scoped to the currently verified ledger bytes. "
            "Event timestamp, if any, is not independently authenticated."
        ),
        "epistemic_limit": _LIMIT,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a non-admitted EA-0.1 candidate dossier")
    parser.add_argument("manifest", help="Previously generated observation manifest JSON")
    parser.add_argument("ledger", help="Nominated current ledger JSONL")
    parser.add_argument("--line", type=int, required=True, help="1-based ledger line")
    parser.add_argument("--claim-id", required=True, help="Caller-declared claim identifier")
    parser.add_argument("--claim-scope", required=True, help="Explicitly bounded claim scope")
    parser.add_argument("--support-relation", required=True, help="Declared support relationship")
    args = parser.parse_args(argv)
    target = Path(args.manifest)
    if target.is_symlink():
        outcome = _unknown("symlink manifest refused")
    else:
        try:
            # Same 4MB bound as the bridge; parse only after bounded read.
            with target.open("rb") as stream:
                raw = stream.read(4 * 1024 * 1024 + 1)
            if len(raw) > 4 * 1024 * 1024:
                outcome = _unknown("manifest byte limit exceeded")
            else:
                try:
                    manifest = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    outcome = _rejected("invalid manifest JSON/UTF-8")
                else:
                    outcome = build_candidate_dossier(
                        manifest, args.ledger, line=args.line,
                        claim_id=args.claim_id, claim_scope=args.claim_scope,
                        proposed_support_relation=args.support_relation,
                    )
        except OSError as exc:
            outcome = _unknown(f"manifest unreadable: {type(exc).__name__}")
    print(json.dumps(outcome, sort_keys=True, ensure_ascii=False))
    return 0 if outcome["status"] == "CANDIDATE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
