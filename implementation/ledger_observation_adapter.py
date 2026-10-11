"""Bounded, read-only observations of Ario execution JSONL.

An observation manifest is not Evidence, Assessment, or a truth verdict.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

MAX_LEDGER_BYTES = 8 * 1024 * 1024
MAX_LINE_BYTES = 64 * 1024
MAX_EVENTS = 5000
KNOWN_EVENTS = frozenset({
    "TASK_STARTED", "STEP_OBSERVED", "GOAL_CRITERION_OBSERVED",
    "FAILURE_DIAGNOSTIC_OBSERVED", "TASK_FINISHED", "WORKFLOW_STARTED",
    "WORKFLOW_STAGE_OBSERVED", "WORKFLOW_FINISHED",
})


def observe_ledger(path: str | Path) -> dict:
    """Read ledger without writing; fail closed on invalid or incomplete content."""
    target = Path(path)
    source = str(target.absolute())

    def unknown(reason: str) -> dict:
        return {"status": "UNKNOWN", "source": source, "error": reason,
                "observations": [], "epistemic_limit": "No evidence or assessment inferred"}

    try:
        if target.is_symlink():
            return unknown("symbolic-link ledger refused")
        digest = hashlib.sha256()
        observations: list[dict] = []
        total_bytes = 0
        with target.open("rb") as stream:
            for line_number, raw_line in enumerate(iter(lambda: stream.readline(MAX_LINE_BYTES + 1), b""), 1):
                if line_number > MAX_EVENTS:
                    return unknown("event-count limit exceeded")
                if len(raw_line) > MAX_LINE_BYTES:
                    return unknown(f"line {line_number}: line-size limit exceeded")
                total_bytes += len(raw_line)
                if total_bytes > MAX_LEDGER_BYTES:
                    return unknown("ledger-size limit exceeded")
                if not raw_line.endswith(b"\n"):
                    return unknown(f"line {line_number}: incomplete JSONL line")
                digest.update(raw_line)
                try:
                    event = json.loads(raw_line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    return unknown(f"line {line_number}: invalid UTF-8 or JSON")
                if (not isinstance(event, dict)
                        or event.get("event") not in KNOWN_EVENTS
                        or not isinstance(event.get("timestamp"), str)
                        or not event["timestamp"].strip()):
                    return unknown(f"line {line_number}: invalid event envelope")
                observations.append({
                    "line": line_number,
                    "event": event["event"],
                    "record_sha256": hashlib.sha256(raw_line).hexdigest(),
                    "task_id": event.get("task_id") if isinstance(event.get("task_id"), str) else None,
                    "workflow_id": event.get("workflow_id") if isinstance(event.get("workflow_id"), str) else None,
                    "reported_status": event.get("status") if isinstance(event.get("status"), str) else None,
                })
    except (OSError, ValueError) as exc:
        return unknown(f"cannot inspect ledger: {type(exc).__name__}")
    if not observations:
        return unknown("empty ledger")
    return {
        "status": "OBSERVED",
        "source": source,
        "sha256": digest.hexdigest(),
        "bytes_read": total_bytes,
        "event_count": len(observations),
        "observations": observations,
        "epistemic_limit": (
            "This manifest describes bytes read from a local ledger. "
            "It neither authenticates history nor establishes truth, "
            "admissible Evidence, or a confirmed Assessment."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only bounded Ario ledger observation")
    parser.add_argument("ledger", help="Existing Ario JSONL ledger")
    args = parser.parse_args()
    result = observe_ledger(args.ledger)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "OBSERVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
