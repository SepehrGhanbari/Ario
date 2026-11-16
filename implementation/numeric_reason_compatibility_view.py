"""Standalone, read-only compatibility VIEW for Ario numeric reason versions.

NOT a shared parser, a replacement for any existing observer/comparator, a
memory write path, an evidence admission gate, or a source-authenticity test.

Both existing components and the proposed sidecar examine the same immutable
caller-owned bytes; their return contracts remain distinct, not silently
normalized into a single authority.
"""
from __future__ import annotations

from typing import Any

import event_intake_validator_lab
import ledger_observation_adapter
from ario_same_snapshot_comparator import compare_snapshot
from numeric_resource_contract_lab import (
    NumericResourceLimits,
    diagnose_numeric_resource_bytes,
)

VIEW_VERSION = "ario_numeric_reason_compatibility_view_v0_1"
CURRENT_COMPARISON_STATES = frozenset({
    "AGREE_OBSERVED", "AGREE_UNKNOWN", "DISAGREE",
})
CURRENT_PARSER_STATES = frozenset({"OBSERVED", "UNKNOWN"})
DIAGNOSTIC_STATES = frozenset({
    "UNKNOWN", "NO_NUMERIC_RESOURCE_OBSERVED",
})
KNOWN_DIAGNOSTIC_REASONS = frozenset({
    None, "NUMERIC_RESOURCE_LIMIT",
    "OTHER_INVALID_OR_UNSUPPORTED",
    "LEDGER_SIZE_LIMIT", "LINE_SIZE_LIMIT",
    "EVENT_COUNT_LIMIT", "EMPTY_LEDGER",
    "EMPTY_JSONL_RECORD", "INCOMPLETE_JSONL_RECORD",
})
# A non-numeric resource rejection in the original strict parser must
# never be presented as generic successful intake or numeric compatibility.
OTHER_RESOURCE_REASONS = frozenset({
    "LEDGER_SIZE_LIMIT", "LINE_SIZE_LIMIT", "EVENT_COUNT_LIMIT",
})
EARLY_FRAMING_REASONS = frozenset({
    "EMPTY_LEDGER", "INCOMPLETE_JSONL_RECORD", "EMPTY_JSONL_RECORD",
})

KNOWN_CURRENT_REASONS = frozenset({
    None, "INVALID_JSON", "JSON_NONFINITE_CONSTANT",
    "JSON_DUPLICATE_KEY", "INVALID_UTF8",
    "NOT_JSON_OBJECT", "MISSING_EVENT_KIND",
    "UNSUPPORTED_EVENT_KIND", "MISSING_OR_INVALID_TIMESTAMP",
    "MISSING_OR_INVALID_TASK_ID", "MISSING_OR_INVALID_GOAL",
    "MISSING_OR_INVALID_STEP_ID", "MISSING_OR_INVALID_STATUS",
    "MISSING_OR_INVALID_CRITERION_ID",
    "MISSING_OR_INVALID_WORKFLOW_ID",
    "MISSING_OR_INVALID_STAGE_ID",
    "LEDGER_SIZE_LIMIT", "LINE_SIZE_LIMIT", "EVENT_COUNT_LIMIT",
    "EMPTY_LEDGER", "EMPTY_JSONL_RECORD", "INCOMPLETE_JSONL_RECORD",
    "SYMLINK_REFUSED", "NON_REGULAR_SOURCE", "FILE_READ_FAILED",
})


def _new_view(nbytes: int) -> dict[str, Any]:
    return {
        "view_version": VIEW_VERSION,
        "status": "UNKNOWN_COMPARISON",
        "relation": "UNKNOWN",
        "reason_code": None,
        "historical_comparison": None,
        "historical_observer_status": None,
        "existing_strict_lab_status": None,
        "existing_strict_lab_reason": None,
        "proposed_sidecar_status": None,
        "proposed_numeric_reason": None,
        "source_kind": "CALLER_PROVIDED_IMMUTABLE_BYTES",
        "source_authenticity": "UNKNOWN",
        "assessment": "NOT_ASSESSED",
        "memory_mutation": "NONE",
        "history_mutation": "NONE",
        "contract_adoption": "NOT_ADOPTED",
        "raw_bytes": nbytes,
    }


def compare_numeric_reason_views(
    raw: bytes, *,
    limits: NumericResourceLimits = NumericResourceLimits(),
) -> dict[str, Any]:
    """Compare *existing* old-vs-strict agreement to a separate reason view.

    Return a fixed, content-free metadata result. Never add a new reason to the
    old generic comparator, nor treat a diagnostic as evidence/truth.
    """
    if type(raw) is not bytes:
        raise TypeError("raw must be immutable bytes")
    if type(limits) is not NumericResourceLimits:
        raise TypeError("limits must be NumericResourceLimits")

    result = _new_view(len(raw))
    # Avoid triggering *either* parser when the supplied snapshot exceeds the
    # smallest relevant bound. The caller has already allocated these bytes.
    size_limit = min(8 * 1024 * 1024, limits.max_raw_bytes)
    if len(raw) > size_limit:
        result["reason_code"] = "SNAPSHOT_SIZE_LIMIT"
        return result
    if not raw:
        result["reason_code"] = "EMPTY_SNAPSHOT"
        return result

    try:
        # Diagnose caller-selected resource caps FIRST. The sidecar's bounded
        # framing preflight can reject without invoking the original parser.
        proposed = diagnose_numeric_resource_bytes(raw, limits=limits)
        if type(proposed) is not dict:
            result["reason_code"] = "UNRECOGNIZED_REPORT_TYPE"
            return result
        if proposed.get("existing_lab_status") == "NOT_CHECKED":
            # This diagnostic cannot make historical comparator claims about
            # a source it deliberately did not pass through the old parser.
            early_reason = proposed.get("reason_code")
            if (proposed.get("status") != "UNKNOWN"
                    or proposed.get("existing_lab_reason") is not None):
                result["reason_code"] = "VERSION_REPORT_MISMATCH"
            elif type(early_reason) is str and early_reason in OTHER_RESOURCE_REASONS:
                result["reason_code"] = "OTHER_RESOURCE_BOUNDARY"
            elif type(early_reason) is str and early_reason in EARLY_FRAMING_REASONS:
                result["reason_code"] = "NO_NUMERIC_DECISION"
            else:
                result["reason_code"] = "VERSION_REPORT_MISMATCH"
            result["proposed_sidecar_status"] = "UNKNOWN"
            return result

        old = compare_snapshot(
            raw,
            legacy_observer_module=ledger_observation_adapter,
            strict_lab_module=event_intake_validator_lab,
        )
        if type(old) is not dict:
            result["reason_code"] = "UNRECOGNIZED_REPORT_TYPE"
            return result
        if (type(old.get("comparison")) is not str or
                old["comparison"] not in CURRENT_COMPARISON_STATES):
            result["reason_code"] = "UNUSABLE_EXISTING_COMPARISON"
            return result

        observer_status = old.get("legacy_status")
        strict_status = old.get("candidate_status")
        prior_status = proposed.get("existing_lab_status")
        prior_reason = proposed.get("existing_lab_reason")
        proposed_status = proposed.get("status")
        proposed_reason = proposed.get("reason_code")

        if (type(observer_status) is not str or
                observer_status not in CURRENT_PARSER_STATES or
                type(strict_status) is not str or
                strict_status not in CURRENT_PARSER_STATES or
                type(prior_status) is not str or
                prior_status != strict_status or
                type(proposed_status) is not str or
                proposed_status not in DIAGNOSTIC_STATES or
                type(prior_reason) not in (str, type(None)) or
                prior_reason not in KNOWN_CURRENT_REASONS or
                type(proposed_reason) not in (str, type(None)) or
                proposed_reason not in KNOWN_DIAGNOSTIC_REASONS or
                old.get("candidate_reason_code") != prior_reason):
            result["reason_code"] = "VERSION_REPORT_MISMATCH"
            return result

        result["historical_comparison"] = old["comparison"]
        result["historical_observer_status"] = observer_status
        result["existing_strict_lab_status"] = strict_status
        result["existing_strict_lab_reason"] = prior_reason
        result["proposed_sidecar_status"] = proposed_status

        # The existing strict parser's nonnumeric resource refusal takes
        # precedence even if the separate sidecar also found a numeric cap.
        # Never convert two simultaneous UNKNOWN reasons into acceptance.
        if strict_status == "UNKNOWN" and prior_reason in OTHER_RESOURCE_REASONS:
            result["reason_code"] = "OTHER_RESOURCE_BOUNDARY"
            return result

        if proposed_reason == "NUMERIC_RESOURCE_LIMIT":
            if proposed_status != "UNKNOWN" or proposed.get("resource_records", 0) < 1:
                result["reason_code"] = "VERSION_REPORT_MISMATCH"
                return result
            # The original observer/comparator verdict remains a separate
            # historical outcome. This reports *only* a proposed explanation.
            if strict_status == "UNKNOWN" and prior_reason == "INVALID_JSON":
                result["relation"] = "PROPOSED_NUMERIC_RECLASSIFICATION"
            elif strict_status == "OBSERVED" and prior_reason is None:
                result["relation"] = "PROPOSED_LOWER_NUMERIC_LIMIT"
            else:
                result["reason_code"] = "UNRESOLVED_SEMANTIC_DIFFERENCE"
                return result
            result["status"] = "DIAGNOSTIC_ONLY"
            result["proposed_numeric_reason"] = proposed_reason
        elif proposed_reason is None and proposed_status == "NO_NUMERIC_RESOURCE_OBSERVED":
            # "No integer budget exceeded in the sidecar" does NOT imply the
            # existing parser or old comparator accepted this exact snapshot.
            if strict_status != "OBSERVED" or prior_reason is not None:
                result["reason_code"] = "EXISTING_STRUCTURAL_REJECTION"
                return result
            if old["comparison"] != "AGREE_OBSERVED":
                result["reason_code"] = "EXISTING_COMPARISON_UNRESOLVED"
                return result
            result["relation"] = "NO_NUMERIC_LIMIT_OBSERVED"
            result["status"] = "DIAGNOSTIC_ONLY"
        else:
            # Syntax, record-framing, source or other failures do not become
            # a numeric resource explanation merely because a token was long.
            result["reason_code"] = "NO_NUMERIC_DECISION"
        return result
    except Exception:
        # Do not echo exceptions, raw JSON values, paths or user-controlled
        # parser metadata, including in partially constructed reports.
        failed = _new_view(len(raw))
        failed["reason_code"] = "COMPARISON_EXECUTION_ERROR"
        return failed
