"""Explicit synthetic RERE-01 revision inspection; never an evidence admission API."""
from __future__ import annotations

from pathlib import Path

from research.rere01.assessment_history_v1 import MAX_BYTES, append_history, restore_history
from research.rere01.revision_comparator_v0_2 import LabContractError
from research.w38_receipt_fd_guard import read_bounded_regular


def inspect_revision(prior_path: Path, prior_pin: str, current_path: Path, current_pin: str) -> dict:
    observation = {
        "ok": False, "revision_status": "UNKNOWN",
        "scope": "RERE01_SYNTHETIC_LAB_E101_ONLY",
        "prior_sha256": None, "current_sha256": None,
        "prior_event_outcome": "UNKNOWN", "event_outcome": "UNKNOWN",
        "prior_record_count": None, "current_record_count": None,
        "appended_record_count": None, "withdrawn_assessment_count": None,
        "claim_truth": "UNKNOWN", "freshness": "UNKNOWN",
        "source_authentication": "UNKNOWN", "evidence_authorized_for_real_memory": False,
    }
    for pin in (prior_pin, current_pin):
        if not isinstance(pin, str) or len(pin) != 64 or any(c not in "0123456789abcdefABCDEF" for c in pin):
            return {**observation, "reason": "INVALID_INPUT_PIN"}
    try:
        prior_raw = read_bounded_regular(prior_path, MAX_BYTES)
        current_raw = read_bounded_regular(current_path, MAX_BYTES)
        before = restore_history(prior_raw, expected_sha256=prior_pin.lower())
        after = restore_history(current_raw, expected_sha256=current_pin.lower())
        observation.update(prior_sha256=before.sha256, current_sha256=after.sha256)
        if (before.policy != after.policy
                or after.records[:len(before.records)] != before.records):
            return {**observation, "reason": "PRIOR_PREFIX_OR_POLICY_MISMATCH"}
        additions = after.records[len(before.records):]
        if append_history(prior_raw, expected_sha256=before.sha256, additions=additions) != current_raw:
            return {**observation, "reason": "APPEND_RECONSTRUCTION_MISMATCH"}
        previous = dict(before.projection.assessment_reliability)
        current = dict(after.projection.assessment_reliability)
        withdrawn = sum(
            value == "CONDITIONALLY_WARRANTED_IN_LAB"
            and current.get(key) == "CHALLENGED_BY_LATER_CALIBRATION"
            for key, value in previous.items()
        )
        return {**observation, "ok": True,
                "revision_status": "VERIFIED_EXTENSION" if additions else "EXACT_REPLAY",
                "prior_event_outcome": before.projection.event_outcome,
                "event_outcome": after.projection.event_outcome,
                "prior_record_count": len(before.records),
                "current_record_count": len(after.records),
                "appended_record_count": len(additions),
                "withdrawn_assessment_count": withdrawn,
                "reason": "SYNTHETIC_HISTORY_COMPARISON_ONLY"}
    except (OSError, ValueError, LabContractError):
        return {**observation, "reason": "HISTORY_READ_OR_VALIDATION_FAILED"}
