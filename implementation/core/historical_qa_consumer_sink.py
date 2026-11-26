"""RESEARCH_ONLY historical-quote consumer sink, never a live Ario bridge.

A V15.3 archived response is UNTRUSTED data. This sink has exactly two
research outputs: receipt metadata, or a locally displayable escaped HTML
fragment after explicit opt-in. It refuses prompts, model/tool channels,
working-memory sinks and evidence admission by design.

Nothing here imports a chat loop, model API, tool executor, cache, signer,
or memory writer. Escaping protects this specific HTML fragment only;
downstream bypasses remain out of scope and must be independently reviewed.
"""
from __future__ import annotations

from typing import Any

from core.historical_qa_research_boundary import (
    HistoricalQABoundaryHold,
    preview_historical_question,
)
from core.legacy_v153_historical_view import (
    HistoricalV153View, _make_controls_visible,
)


SCHEMA = "ARIO_HISTORICAL_CONSUMER_SINK_R0"
TARGET_METADATA = "METADATA_ONLY"
TARGET_LOCAL_HTML = "LOCAL_HTML_DISPLAY_ONLY"
_FORBIDDEN = frozenset({
    "MODEL", "MODEL_PROMPT", "SYSTEM_PROMPT", "TOOL",
    "TOOL_ARGUMENT", "WORKING_MEMORY", "EVIDENCE_ADMISSION",
    "AUTO_CONSOLIDATION", "LIVE_CHAT_LOOP",
})
_DISPLAY_KIND = "UNTRUSTED_HISTORICAL_QUOTE_NOT_INSTRUCTIONS"


class HistoricalConsumerHold(ValueError):
    """Stable refusal code; never include the private historical payload."""


def _fail(code: str) -> None:
    raise HistoricalConsumerHold(code)


def route_historical_consumer(
    view: HistoricalV153View,
    question: str,
    *,
    target: str = TARGET_METADATA,
    mode: str = "HISTORICAL",
    local_display_consent: bool = False,
) -> dict[str, Any]:
    """Inert sink routing over the real pinned read-only V15.3 preview.

    This function NEVER supplies a model prompt, tool call, new answer,
    working-memory entry or admitted evidence. Only the LOCAL_HTML_DISPLAY_ONLY
    destination may receive escaped historical characters. It is still
    *untrusted text* and must never be fed back into prompt/tool sinks.

    This is an experimental local renderer, not live runtime authorization.
    """
    if type(target) is not str:
        _fail("HOLD_INVALID_CONSUMER_SINK")
    if target in _FORBIDDEN:
        _fail("HOLD_HISTORY_TO_ACTIVE_SINK")
    if target not in (TARGET_METADATA, TARGET_LOCAL_HTML):
        _fail("HOLD_UNKNOWN_CONSUMER_SINK")
    if type(local_display_consent) is not bool:
        _fail("HOLD_INVALID_DISPLAY_CONSENT")
    if target == TARGET_METADATA and local_display_consent:
        _fail("HOLD_CONSENT_REQUIRES_LOCAL_DISPLAY")
    if target == TARGET_LOCAL_HTML and mode != "HISTORICAL":
        _fail("HOLD_LOCAL_DISPLAY_REQUIRES_HISTORICAL_MODE")

    # Call the *existing* real V15.3 research preview. It enforces the exact
    # view type, pinned archive, receipt invariants and historical/current mode.
    expose = target == TARGET_LOCAL_HTML and local_display_consent
    preview = preview_historical_question(view, question, mode=mode)
    if (
        preview.get("answer") is not None
        or preview.get("evidence_admission") != "NO_ADMISSION"
        or preview.get("truth_assessment") != "NOT_EVALUATED"
        or preview.get("source_authenticity") != "NOT_ESTABLISHED"
        or preview.get("action_authority") != "NONE"
        or preview.get("model_invocations") != 0
        or preview.get("tool_invocations") != 0
        or preview.get("writes_performed") != 0
        or preview.get("memory_write_permitted") is not False
        or preview.get("context_injection_allowed") is not False
    ):
        _fail("HOLD_UNEXPECTED_PREVIEW_AUTHORITY")

    output: dict[str, Any] = {
        "schema": SCHEMA,
        "target": target,
        "mode": mode,
        "disposition": preview["disposition"],
        "source_kind": "V15_3_HISTORICAL_BACKUP",
        "archive_sha256": preview["archive_sha256"],
        "source_authenticity": "NOT_ESTABLISHED",
        "truth_assessment": "NOT_EVALUATED",
        "evidence_admission": "NO_ADMISSION",
        "answer": None,
        "model_prompt": None,
        "tool_request": None,
        "memory_entry": None,
        "rendered_html": None,
        "quote_is_raw": False,
        "html_rendering_only": True,
        "model_dispatch_permitted": False,
        "tool_dispatch_permitted": False,
        "memory_write_permitted": False,
        "context_injection_allowed": False,
        "live_ario_recall_established": False,
        "writes_performed": 0,
    }
    if preview["disposition"] == "RECALLED_HISTORICAL_ONLY":
        line = preview.get("source_line")
        if type(line) is not int or line < 1:
            _fail("HOLD_MISSING_HISTORICAL_SOURCE")
        output["source_line"] = line
        if expose:
            display = view.render_local_quote_html(question, consent=True)
            if (
                type(display) is not dict
                or display.get("disposition") != preview["disposition"]
                or display.get("archive_sha256") != preview["archive_sha256"]
                or display.get("source_line") != line
                or display.get("quote_is_raw") is not False
                or display.get("source_authenticity") != "NOT_ESTABLISHED"
                or display.get("truth_assessment") != "NOT_EVALUATED"
                or display.get("evidence_admission") != "NO_ADMISSION"
                or type(display.get("rendered_html")) is not str
            ):
                _fail("HOLD_UNTRUSTED_QUOTE_CONTRACT")
            output["rendered_html"] = display["rendered_html"]
    elif preview.get("historical_quote") is not None:
        _fail("HOLD_UNEXPECTED_UNKNOWN_QUOTE")
    # Never return preview, raw quote, question text, or model/tool callables.
    return output
