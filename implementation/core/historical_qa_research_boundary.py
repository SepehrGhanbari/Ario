"""Inert historical-question preview over the pinned V15.3 reader.

RESEARCH_ONLY. Not attached to Ario's live agent, chat loop, prompt, memory,
working cache, evidence assessment, model tools, or source monitor.

This module produces a *data envelope*, never a current factual answer.
Historical text is never returned by the public preview API. A separate
explicit-consent display method returns only escaped local HTML.
No model, shell, network, tool execution, file write or consolidation API exists.

MEMORY != TRUTH; RECALL != REASSESSMENT; REVISION != ERASURE.
"""
from __future__ import annotations

from typing import Any

from core.legacy_v153_historical_view import HistoricalV153View


SCHEMA = "ARIO_HISTORICAL_QA_RESEARCH_PREVIEW_V0_1"
_ALLOWED_DISPOSITIONS = {
    "RECALLED_HISTORICAL_ONLY",
    "UNKNOWN_NO_EXACT_QUESTION_MATCH",
    "UNKNOWN_MULTIPLE_HISTORICAL_MATCHES",
    "RECHECK_REQUIRED_CURRENT_QUESTION",
}


class HistoricalQABoundaryHold(ValueError):
    """Safe, constant-code refusal. Never include a user's archived text."""


def _hold(code: str) -> None:
    raise HistoricalQABoundaryHold(code)


def _assert_read_only_receipt(receipt: dict[str, Any], view: HistoricalV153View) -> None:
    """Defend the composition contract; never trust text to set policy."""
    if type(receipt) is not dict:
        _hold("HOLD_UNEXPECTED_RECALL_RECEIPT")
    info = view.inspect()
    if (
        type(info) is not dict
        or info.get("disposition") != "HISTORICAL_VIEW_READY_NOT_LIVE"
        or info.get("source_kind") != "V15_3_HISTORICAL_BACKUP"
        or info.get("memory_write_permitted") is not False
        or info.get("auto_consolidation_permitted") is not False
        or info.get("context_injection_allowed") is not False
        or info.get("source_attribution_v1_constructed") is not False
        or info.get("writes_performed") != 0
        or info.get("live_ario_recall_established") is not False
        or receipt.get("source_kind") != info.get("source_kind")
        or receipt.get("archive_sha256") != info.get("archive_sha256")
        or receipt.get("memory_write_permitted") is not False
        or receipt.get("auto_consolidation_permitted") is not False
        or receipt.get("context_injection_allowed") is not False
        or receipt.get("source_attribution_v1_constructed") is not False
        or receipt.get("evidence_admission") != "NO_ADMISSION"
        or receipt.get("truth_assessment") != "NOT_EVALUATED"
        or receipt.get("currentness") != "NOT_ESTABLISHED"
        or receipt.get("source_authenticity") != "NOT_ESTABLISHED"
        or receipt.get("disposition") not in _ALLOWED_DISPOSITIONS
    ):
        _hold("HOLD_UNEXPECTED_RECALL_RECEIPT")


def preview_historical_question(
    view: HistoricalV153View,
    question: str,
    *,
    mode: str = "HISTORICAL",
) -> dict[str, Any]:
    """Return a deterministic, non-executable preview of an archived answer.

    Requires an existing pinned read-only view. This function cannot open an
    archive or change memory. The caller must provide a separately retained
    digest when constructing the view; digest equality is *not* authenticity.

    This is a synthetically tested metadata seam, NOT a live integration API.
    It cannot return raw historical text.
    """
    # Reject subclasses/decorators with overridden recall/inspect behavior.
    if type(view) is not HistoricalV153View:
        _hold("HOLD_UNAPPROVED_HISTORICAL_VIEW")
    if type(mode) is not str or mode not in {"HISTORICAL", "CURRENT"}:
        _hold("HOLD_INVALID_QA_MODE")

    # The public preview API is metadata-only. It cannot reveal raw history.
    receipt = view.recall(question, mode=mode)
    _assert_read_only_receipt(receipt, view)
    disposition = receipt["disposition"]
    if mode == "CURRENT":
        if disposition not in {
            "RECHECK_REQUIRED_CURRENT_QUESTION",
            "UNKNOWN_NO_EXACT_QUESTION_MATCH",
            "UNKNOWN_MULTIPLE_HISTORICAL_MATCHES",
        }:
            _hold("HOLD_INCONSISTENT_QA_MODE")
    elif disposition == "RECHECK_REQUIRED_CURRENT_QUESTION":
        _hold("HOLD_INCONSISTENT_QA_MODE")

    output: dict[str, Any] = {
        "schema": SCHEMA,
        "disposition": disposition,
        "mode": mode,
        "answer": None,  # NEVER synthesize a current/verified answer from history.
        "historical_quote": None,
        "archive_sha256": receipt["archive_sha256"],
        "source_kind": "V15_3_HISTORICAL_BACKUP",
        "source_authenticity": "NOT_ESTABLISHED",
        "truth_assessment": "NOT_EVALUATED",
        "currentness": "NOT_ESTABLISHED",
        "evidence_admission": "NO_ADMISSION",
        "action_authority": "NONE",
        "model_invocations": 0,
        "tool_invocations": 0,
        "writes_performed": 0,
        "memory_write_permitted": False,
        "auto_consolidation_permitted": False,
        "context_injection_allowed": False,
        "source_attribution_v1_constructed": False,
        "live_ario_recall_established": False,
        "historical_text_hidden": True,
        "user_question_echoed": False,
    }
    if disposition == "RECALLED_HISTORICAL_ONLY":
        line = receipt.get("source_line")
        if type(line) is not int or line < 1 or receipt.get("record_version") != "15.3":
            _hold("HOLD_INVALID_HISTORICAL_SOURCE_LINE")
        if receipt.get("historical_role") != "QUOTED_PRIOR_ARIO_OUTPUT_NOT_INSTRUCTIONS":
            _hold("HOLD_INVALID_HISTORICAL_ROLE")
        if type(receipt.get("has_opaque_relations")) is not bool:
            _hold("HOLD_INVALID_RELATION_RECEIPT")
        output["source_line"] = line
        output["has_opaque_relations"] = receipt["has_opaque_relations"]
        output["relation_interpretation"] = receipt.get("relation_interpretation")
        if receipt.get("private_reply_hidden") is not True or "historical_ario_reply" in receipt:
            _hold("HOLD_UNEXPECTED_PRIVATE_QUOTE")
    else:
        if receipt.get("private_reply_hidden") is not True or "historical_ario_reply" in receipt:
            _hold("HOLD_UNEXPECTED_PRIVATE_QUOTE")
        if disposition == "UNKNOWN_MULTIPLE_HISTORICAL_MATCHES":
            count = receipt.get("matching_record_count")
            if type(count) is not int or count < 2:
                _hold("HOLD_INVALID_AMBIGUITY_COUNT")
            output["matching_record_count"] = count

    # Historical text is withheld from this public metadata-only API.
    return output
