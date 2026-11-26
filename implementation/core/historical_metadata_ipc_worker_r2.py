"""RIO-01 R2.2: one-shot metadata-only subprocess research boundary.

No archive reply, HTML, question or path returned. No live integration.
Same-OS-account file access and debugging remain outside the guarantee.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.historical_qa_research_boundary import (  # noqa: E402
    HistoricalQABoundaryHold, preview_historical_question,
)
from core.legacy_v153_historical_view import (  # noqa: E402
    HistoricalV153View, HistoricalViewHold,
)

SCHEMA = "ARIO_RIO01_METADATA_IPC_R2_2"
MAX_REQUEST_BYTES = 8192
OP = "METADATA_LOOKUP_ONLY"
_FIELDS = frozenset({"op", "archive_path", "expected_sha256", "question", "mode"})


class WorkerHold(ValueError):
    """Constant-code refusal only."""


def _hold(code: str) -> None:
    raise WorkerHold(code) from None


def _pairs_unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    obj: dict[str, object] = {}
    for key, value in pairs:
        if key in obj:
            _hold("HOLD_DUPLICATE_IPC_KEY")
        obj[key] = value
    return obj


def _request_from_bytes(data: bytes) -> dict[str, str]:
    if type(data) is not bytes or len(data) > MAX_REQUEST_BYTES or not data:
        _hold("HOLD_IPC_REQUEST_SIZE")
    try:
        request = json.loads(data.decode("utf-8"), object_pairs_hook=_pairs_unique)
    except WorkerHold:
        raise
    except (UnicodeError, ValueError, TypeError, RecursionError):
        _hold("HOLD_INVALID_IPC_JSON")
    if type(request) is not dict or set(request) != _FIELDS:
        _hold("HOLD_UNEXPECTED_IPC_SCHEMA")
    if any(type(request[k]) is not str for k in _FIELDS):
        _hold("HOLD_UNEXPECTED_IPC_SCHEMA")
    if request["op"] != OP or request["mode"] not in ("HISTORICAL", "CURRENT"):
        _hold("HOLD_UNSUPPORTED_IPC_OPERATION")
    if (not request["question"].strip() or len(request["question"]) > 2048
            or not request["archive_path"] or len(request["archive_path"]) > 4096):
        _hold("HOLD_INVALID_IPC_FIELD")
    # Filename convention reduces accidental real-file use but cannot
    # authenticate the data or defend against an intentionally renamed file.
    if not Path(request["archive_path"]).name.startswith("RIO01_SYNTHETIC_"):
        _hold("HOLD_SYNTHETIC_ONLY_SOURCE_REQUIRED")
    return request


def metadata_only(request: dict[str, str]) -> dict[str, object]:
    view = HistoricalV153View(
        request["archive_path"], expected_sha256=request["expected_sha256"]
    )
    result = preview_historical_question(view, request["question"], mode=request["mode"])
    if (result.get("historical_quote") is not None or result.get("answer") is not None
            or result.get("context_injection_allowed") is not False
            or result.get("evidence_admission") != "NO_ADMISSION"
            or result.get("writes_performed") != 0):
        _hold("HOLD_IPC_UNEXPECTED_AUTHORITY")
    receipt: dict[str, object] = {
        "schema": SCHEMA,
        "status": "METADATA_ONLY_NOT_AUTHENTICATED",
        "disposition": result["disposition"],
        "archive_sha256": result["archive_sha256"],
        "source_authenticity": "NOT_ESTABLISHED",
        "truth_assessment": "NOT_EVALUATED",
        "evidence_admission": "NO_ADMISSION",
        "model_dispatch_permitted": False,
        "memory_write_permitted": False,
        "context_injection_allowed": False,
        "live_ario_recall_established": False,
        "independent_custody_established": False,
        "real_os_sandbox_established": False,
        "writes_performed": 0,
    }
    if result["disposition"] == "RECALLED_HISTORICAL_ONLY":
        receipt["source_line"] = result["source_line"]
    return receipt


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args != ["--research-synthetic-only"]:
        print(json.dumps({"schema": SCHEMA, "status": "HOLD_EXPLICIT_SYNTHETIC_OPT_IN_REQUIRED"}))
        return 2
    try:
        data = sys.stdin.buffer.read(MAX_REQUEST_BYTES + 1)
        receipt = metadata_only(_request_from_bytes(data))
        print(json.dumps(receipt, sort_keys=True))
        return 0
    except (WorkerHold, HistoricalQABoundaryHold, HistoricalViewHold) as exc:
        status = str(exc)
    except (OSError, ValueError, RecursionError, TypeError, KeyError, IndexError):
        status = "HOLD_WORKER_UNEXPECTED_ERROR"
    print(json.dumps({"schema": SCHEMA, "status": status}, sort_keys=True))
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
