"""ARP-0.1 conservative, read-only admission review screening.

No identity/authorization verifier is present in ARP-0.1. Therefore this
checker cannot issue REVIEWABLE or a review recommendation as an authorized
reviewer, and it never grants evidence admission.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from candidate_dossier_builder import build_candidate_dossier

POLICY_VERSION = "ARP-0.1"
MAX_JSON_BYTES = 4 * 1024 * 1024
LIMIT = (
    "Review screening only: no authenticated review authority, independent "
    "corroboration, evidence admission, M0 verdict, or truth established."
)
REQUEST_FIELDS = frozenset({
    "policy_version", "candidate", "candidate_digest", "reviewer_id",
    "reviewer_role", "authorization_reference", "requested_claim_id",
    "requested_claim_scope", "requested_support_relation", "corroboration_refs",
    "review_rule_ids", "limitations", "recorded_at", "decision",
})
FORBIDDEN = frozenset({"ADMITTED", "ACCEPTED_AS_EVIDENCE", "M0_PASS"})
ALLOWED = frozenset({
    "NOT_EVALUATED", "UNKNOWN", "REJECTED", "NEEDS_CORROBORATION",
    "REVIEWABLE", "RECOMMENDED_FOR_FUTURE_REVIEW",
})


def _result(status: str, reason: str) -> dict[str, str]:
    return {"status": status, "reason": reason, "policy_version": POLICY_VERSION,
            "admission_decision": "NOT_EVALUATED", "epistemic_limit": LIMIT}


def _text(value: Any, max_length: int = 600) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= max_length


def evaluate_review_request(request: Any, manifest: Any, ledger_path: str | Path) -> dict[str, str]:
    """Screen a declared request, but never authenticate a reviewer or admit evidence."""
    if not isinstance(request, dict):
        return _result("REJECTED", "review request must be a JSON object")
    if set(request) != REQUEST_FIELDS:
        return _result("REJECTED", "review request fields do not match ARP-0.1 envelope")
    if request["policy_version"] != POLICY_VERSION:
        return _result("REJECTED", "unsupported policy version")
    decision = request["decision"]
    if not isinstance(decision, str) or decision in FORBIDDEN or decision not in ALLOWED:
        return _result("REJECTED", "requested outcome is not authorized by ARP-0.1")
    candidate = request["candidate"]
    if not isinstance(candidate, dict):
        return _result("REJECTED", "candidate must be a JSON object")
    if candidate.get("status") != "CANDIDATE" or candidate.get("contract_version") != "EA-0.1" or candidate.get("admission_decision") != "NOT_EVALUATED":
        return _result("REJECTED", "candidate is not a non-admitted EA-0.1 dossier")
    if not isinstance(request["corroboration_refs"], list) or len(request["corroboration_refs"]) > 100:
        return _result("REJECTED", "corroboration_refs must be a bounded list")
    if not isinstance(request["review_rule_ids"], list) or len(request["review_rule_ids"]) > 100 or not all(_text(x, 160) for x in request["review_rule_ids"]):
        return _result("REJECTED", "review_rule_ids must be bounded strings")
    for key in ("reviewer_id", "reviewer_role", "requested_claim_id", "requested_claim_scope", "requested_support_relation", "limitations", "recorded_at"):
        if not _text(request[key]):
            return _result("REJECTED", f"invalid {key}")
    if not (_text(request["authorization_reference"]) or request["authorization_reference"] is None):
        return _result("REJECTED", "invalid authorization reference")
    if request["candidate_digest"] != "UNKNOWN":
        return _result("UNKNOWN", "canonical candidate digest verification is unspecified in ARP-0.1")
    if any(not isinstance(ref, dict) for ref in request["corroboration_refs"]):
        return _result("REJECTED", "corroboration references must be objects")
    if (request["requested_claim_id"] != candidate.get("claim_id")
            or request["requested_claim_scope"] != candidate.get("claim_scope")
            or request["requested_support_relation"] != candidate.get("proposed_support_relation")):
        return _result("REJECTED", "requested claim or support relation differs from candidate")
    loc = candidate.get("observation_locator")
    if not isinstance(loc, dict) or not isinstance(loc.get("line"), int) or isinstance(loc.get("line"), bool):
        return _result("REJECTED", "candidate locator missing or invalid")
    # The dossier must exactly match a newly reconstructed, bounded candidate.
    rebuilt = build_candidate_dossier(
        manifest, ledger_path, line=loc["line"],
        claim_id=request["requested_claim_id"],
        claim_scope=request["requested_claim_scope"],
        proposed_support_relation=request["requested_support_relation"],
    )
    if rebuilt["status"] == "UNKNOWN":
        return _result("UNKNOWN", "fresh ledger verification is unavailable")
    if rebuilt["status"] != "CANDIDATE" or candidate != rebuilt:
        return _result("REJECTED", "candidate does not match fresh bounded observation")
    # No verifier of reviewer identity, provenance or independent corroboration
    # is defined in the current policy. Declared references never suffice.
    return _result("UNKNOWN", "reviewer authorization and source independence cannot be authenticated by ARP-0.1")


def _read_json(path: Path) -> Any:
    if path.is_symlink():
        raise ValueError("symlink refused")
    with path.open("rb") as stream:
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ValueError("input byte limit exceeded")
    return json.loads(raw.decode("utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Screen ARP-0.1 review request without evidence admission")
    parser.add_argument("request", help="Review request JSON")
    parser.add_argument("manifest", help="Existing observation manifest JSON")
    parser.add_argument("ledger", help="Nominated ledger JSONL")
    args = parser.parse_args(argv)
    try:
        outcome = evaluate_review_request(_read_json(Path(args.request)), _read_json(Path(args.manifest)), args.ledger)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        outcome = _result("UNKNOWN", f"cannot load bounded input: {type(exc).__name__}")
    print(json.dumps(outcome, sort_keys=True, ensure_ascii=False))
    return 0 if outcome["status"] in ("UNKNOWN", "REVIEWABLE", "NEEDS_CORROBORATION") else 2


if __name__ == "__main__":
    raise SystemExit(main())
