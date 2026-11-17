"""Non-authoritative consumer-side projection for Ario claim-support research.

This module has no access to the memory store, admission evaluator, signer,
tools or trust controls. It does not enforce a boundary on callers that bypass
it. A REVIEWABLE_ONLY proposal can be displayed for manual review, never
treated as authenticated evidence by this projection.
"""
from __future__ import annotations

from typing import Any

from claim_support_readonly_lab import CONTRACT_VERSION, MAX_RECEIPTS

_EXPECTED_KEYS = frozenset({
    "contract_version", "review_status", "reason_code",
    "claimed_support_count", "unique_receipt_count",
    "independent_support_count", "execution_integrity",
    "source_authenticity", "semantic_support", "claim_assessment",
    "admission_decision", "reviewer_authorization",
    "memory_mutation", "history_mutation", "contract_adoption",
})

_FIXED_NON_AUTHORITY = {
    "source_authenticity": "UNKNOWN",
    "semantic_support": "NOT_ASSESSED",
    "claim_assessment": "NOT_ASSESSED",
    "admission_decision": "NOT_EVALUATED",
    "reviewer_authorization": "NOT_ESTABLISHED",
    "memory_mutation": "NONE",
    "history_mutation": "NONE",
    "contract_adoption": "NOT_ADOPTED",
}


def inspect_consumer_boundary(report: object) -> dict[str, Any]:
    """Project a claimed support report into an INERT manual-review queue.

    Never returns a grant of truth, evidence admission, executable capability,
    signer permission, memory write or trust activation. Even a forged,
    well-shaped report is only an unauthenticated review candidate.

    Caller-supplied Python objects are not process-isolated. This is a pure
    research projection, not an admission authorization implementation.
    """
    result: dict[str, Any] = {
        "boundary_version": "ario_claim_support_consumer_boundary_v0_1",
        "queue_state": "NO_CANDIDATE",
        "reason_code": "INVALID_OR_UNTRUSTED_REPORT",
        "epistemic_verdict": "NOT_ASSESSED",
        "evidence_admission_allowed": False,
        "tool_execution_allowed": False,
        "memory_write_allowed": False,
        "signing_allowed": False,
        "trust_activation_allowed": False,
        "contract_adoption": "NOT_ADOPTED",
    }
    # No duck-typed mappings or unchecked extras; never echo original text.
    if type(report) is not dict or any(type(k) is not str for k in report):
        return result
    if report.keys() != _EXPECTED_KEYS:
        return result
    if report["contract_version"] != CONTRACT_VERSION:
        return result
    if any(report[k] != v for k, v in _FIXED_NON_AUTHORITY.items()):
        return result
    if (type(report["independent_support_count"]) is not int
            or report["independent_support_count"] != 0):
        return result
    claimed = report["claimed_support_count"]
    unique = report["unique_receipt_count"]
    if (type(claimed) is not int or type(unique) is not int
            or not (0 <= claimed <= MAX_RECEIPTS)
            or not (0 <= unique <= MAX_RECEIPTS)):
        return result
    if type(report["reason_code"]) is not str:
        return result
    if report["review_status"] == "UNKNOWN":
        # A rejected/unknown view may contain diagnostics, but never gives
        # downstream evidence/admission permission.
        result["reason_code"] = "SOURCE_VIEW_UNKNOWN"
        return result
    if (
        report["review_status"] == "REVIEWABLE_ONLY"
        and report["reason_code"] == "UNAUTHENTICATED_SUPPORT_PROPOSAL"
        and report["execution_integrity"] == "LEGACY_REPORTED_VERIFIED"
        and 1 <= claimed == unique <= MAX_RECEIPTS
    ):
        result["queue_state"] = "MANUAL_REVIEW_CANDIDATE_ONLY"
        result["reason_code"] = "UNAUTHENTICATED_PROPOSAL"
    return result
