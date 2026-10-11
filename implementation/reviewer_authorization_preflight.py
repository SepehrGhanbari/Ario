"""RAC-0.1 non-authorizing, read-only reviewer authorization preflight.

No trust anchor, issuer verifier, trusted clock, revocation authority, or
canonical dossier digest is supplied by RAC-0.1. This module MUST NOT grant
review authority or evidence admission. It only checks proposed envelope
structure and detects some explicit contradictions.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

CONTRACT_VERSION = "RAC-0.1"
MAX_JSON_BYTES = 1024 * 1024
MAX_TEXT = 512
MAX_BINDING = 2048
FIELDS = frozenset({
    "authorization_contract_version", "grant_id", "issuer_id", "issuer_trust_basis",
    "principal_id", "identity_binding_method", "permitted_action", "policy_version",
    "claim_scope", "candidate_binding", "validity_start", "validity_end",
    "verification_time_basis", "revocation_reference", "revocation_check",
    "separation_of_duties", "signature_or_attestation", "verification_result",
    "grant_limitations", "rule_version",
})
# Untrusted, self-declared fields are always treated as declarations, not facts.
FORBIDDEN_ACTIONS = frozenset({"ADMIT_EVIDENCE", "ADMITTED", "ACCEPTED_AS_EVIDENCE", "M0_PASS", "ASSERT_TRUTH"})
REVIEW_ACTION = "REVIEW_CANDIDATE"
LIMIT = (
    "Structural preflight only. No issuer trust anchor, authenticated principal, "
    "verified scope/time/revocation, review authority, Evidence admission, "
    "M0 verdict, or truth established."
)


def _result(status: str, rule_id: str, reason: str) -> dict[str, str]:
    return {
        "status": status,
        "contract_version": CONTRACT_VERSION,
        "rule_id": rule_id,
        "reason": reason,
        "authorization_decision": "NOT_CHECKED",
        "admission_decision": "NOT_EVALUATED",
        "epistemic_limit": LIMIT,
    }


def _text(value: Any, bound: int = MAX_TEXT) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= bound


def preflight_authorization(record: Any) -> dict[str, str]:
    """Never return an affirmative authorization outcome, even for well-formed inputs."""
    if not isinstance(record, dict) or set(record) != FIELDS:
        return _result("REJECTED", "RAC-12", "authorization record must have exact RAC-0.1 fields")
    if record["authorization_contract_version"] != CONTRACT_VERSION or record["rule_version"] != CONTRACT_VERSION:
        return _result("REJECTED", "RAC-12", "unsupported or inconsistent contract/rule version")
    for key in (
        "grant_id", "issuer_id", "principal_id", "policy_version", "claim_scope",
        "permitted_action", "grant_limitations",
    ):
        if not _text(record[key]):
            return _result("REJECTED", "RAC-12", f"invalid bounded {key}")
    if record["policy_version"] != "ARP-0.1":
        return _result("REJECTED", "RAC-04", "policy version outside RAC-0.1 review scope")
    action = record["permitted_action"]
    if action in FORBIDDEN_ACTIONS or action != REVIEW_ACTION:
        return _result("REJECTED", "RAC-05", "only candidate review may be requested; no evidence admission")

    # These are *declarations* and may be unknown; no untrusted value can prove itself.
    for key in (
        "issuer_trust_basis", "identity_binding_method", "candidate_binding",
        "validity_start", "validity_end", "verification_time_basis",
        "revocation_reference", "revocation_check", "separation_of_duties",
        "signature_or_attestation", "verification_result",
    ):
        if record[key] is not None and not _text(record[key], MAX_BINDING):
            return _result("REJECTED", "RAC-12", f"invalid bounded {key}")

    # An explicit identity collision is a conflict, not a grant. Unverified
    # distinct names are equally insufficient to establish independence.
    relation = record["separation_of_duties"]
    if isinstance(relation, str) and relation.upper() in {"SAME_PROPOSER_AND_REVIEWER", "SELF_REVIEW"}:
        return _result("REJECTED", "RAC-10", "explicit separation-of-duties conflict")
    # A declared revocation is not authenticated; nevertheless, a known adverse
    # declaration must never be ignored as if active.
    revocation = record["revocation_check"]
    if isinstance(revocation, str) and revocation.upper() == "REVOKED":
        return _result("REJECTED", "RAC-08", "record declares its authorization revoked")
    # Absence of independently approved trust anchor, verified clock and
    # authoritative revocation check forces UNKNOWN in *all* other cases.
    return _result("UNKNOWN", "RAC-02", "no independently trusted issuer, reviewer binding or authorization verifier configured")


def _read_bounded_json(path: Path) -> Any:
    if path.is_symlink():
        raise ValueError("symlink input refused")
    with path.open("rb") as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("input byte limit exceeded")
    return json.loads(raw.decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAC-0.1 reviewer grant preflight (never authorizes)")
    parser.add_argument("authorization_record", help="JSON file with proposed RAC-0.1 authorization record")
    args = parser.parse_args(argv)
    try:
        outcome = preflight_authorization(_read_bounded_json(Path(args.authorization_record)))
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        outcome = _result("UNKNOWN", "RAC-14", f"bounded input unavailable: {type(exc).__name__}")
    print(json.dumps(outcome, ensure_ascii=False, sort_keys=True))
    return 0 if outcome["status"] == "UNKNOWN" else 2


if __name__ == "__main__":
    raise SystemExit(main())
