"""Non-persistent, scope-aware human correction decision helper.

Classifies a supplied correction event for review. It does not authenticate a
person, persist personal data, mutate history, or determine identity. Authority
is an externally supplied assertion and is not verified by this helper.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class CorrectionEvent:
    event_id: str
    target_reference: str
    subject_reference: str
    scope: str
    new_interpretation_reference: str
    authority_status: str


@dataclass(frozen=True)
class CorrectionDecision:
    status: str
    reason: str
    future_use: str
    historical_record_action: str = "NO_MUTATION"
    persistence: str = "NONE"
    identity_verdict: str = "NONE"


def evaluate_correction(
    event: CorrectionEvent,
    *,
    expected_scope: str,
    seen_event_ids: FrozenSet[str] = frozenset(),
) -> CorrectionDecision:
    """Return a review classification; never applies or stores a correction."""
    if not isinstance(event, CorrectionEvent):
        return CorrectionDecision("REJECTED", "INVALID_EVENT_TYPE", "NO_CHANGE")
    required = (
        event.event_id, event.target_reference, event.subject_reference,
        event.scope, event.new_interpretation_reference, expected_scope,
    )
    if any(not isinstance(value, str) or not value.strip() for value in required):
        return CorrectionDecision("UNKNOWN", "REQUIRED_CONTEXT_MISSING", "NO_CHANGE")
    if event.event_id in seen_event_ids:
        return CorrectionDecision("REJECTED", "REPLAYED_EVENT_ID", "NO_CHANGE")
    if event.scope != expected_scope:
        return CorrectionDecision("REJECTED", "SCOPE_MISMATCH", "NO_CHANGE")
    if event.authority_status == "UNKNOWN":
        return CorrectionDecision("UNKNOWN", "AUTHORITY_UNKNOWN", "NO_CHANGE")
    if event.authority_status != "EXTERNALLY_VERIFIED":
        return CorrectionDecision("REJECTED", "AUTHORITY_NOT_VERIFIED", "NO_CHANGE")

    return CorrectionDecision(
        status="ACCEPTABLE_FOR_SCOPED_REVIEW",
        reason="EXTERNAL_AUTHORITY_ASSERTION_ACCEPTED_FOR_REVIEW_ONLY",
        future_use="DO_NOT_USE_SUPERSEDED_INTERPRETATION_IN_THIS_SCOPE",
    )
