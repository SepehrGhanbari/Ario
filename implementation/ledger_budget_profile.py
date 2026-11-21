"""Privacy-conscious, read-only profiler for Ario's existing JSONL ledger.

Research-only. No ledger writes, no raw field values or identifiers in output.
A temporary SQLite database contains *ephemeral keyed hashes* of task IDs,
never raw identifiers, and is deleted at process exit. Measures observations;
it does not establish ledger provenance or a production safety budget.

Usage from implementation/: python ledger_budget_profile.py --ledger PATH
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
from pathlib import Path

from bounded_json import loads_bounded
from ledger_streaming import (
    MAX_LEDGER_LINE_CHARS,
    LedgerLineLimitExceeded,
    iter_bounded_ledger_lines,
)

# Raw-byte measurement does not allocate full lines even if larger than the
# currently proposed text-character limit.
RAW_CHUNK_BYTES = 64 * 1024


def _raw_line_metrics(path: Path) -> tuple[int, int]:
    """Return exact source byte count and longest LF-delimited physical record."""
    total = 0
    current = 0
    largest = 0
    with path.open("rb") as stream:
        while True:
            chunk = stream.readline(RAW_CHUNK_BYTES)
            if not chunk:
                break
            total += len(chunk)
            current += len(chunk)
            if chunk.endswith(b"\n"):
                largest = max(largest, current)
                current = 0
    return total, max(largest, current)


def profile_ledger(path: str | Path) -> dict:
    """Numeric aggregate only; never print or persist a raw task_id/event."""
    target = Path(path)
    result = {
        "status": "UNKNOWN",
        "basis": "OBSERVATION_ONLY_NOT_AUTHENTICATED",
        "source_content_exported": False,
        "history_modified": False,
        "raw_task_ids_exported": False,
        "candidate_line_limit_chars": MAX_LEDGER_LINE_CHARS,
        "candidate_history_event_limit": 128,
        "lines_seen": 0,
        "events_seen": 0,
        "blank_lines": 0,
        "max_logical_line_chars": 0,
        "max_physical_line_bytes": None,
        "source_total_bytes": None,
        "unique_task_ids": None,
        "max_matching_task_events": None,
        "tasks_over_18_events": None,
        "tasks_over_128_events": None,
        "note": "No complete real-history evidence until status is OBSERVED.",
    }
    # Refuse symlinks and special files: this task is for a selected local
    # regular ledger only, never a device, pipe, directory or arbitrary target.
    try:
        if target.is_symlink() or not target.is_file():
            result["error_class"] = "NOT_REGULAR_FILE"
            return result
        before = target.stat()
        with tempfile.TemporaryDirectory(prefix="ario-ledger-budget-") as scratch:
            db = sqlite3.connect(str(Path(scratch) / "counts.sqlite"))
            try:
                db.execute("CREATE TABLE task_counts (key BLOB PRIMARY KEY, n INTEGER NOT NULL)")
                key = os.urandom(32)
                for line_number, raw in iter_bounded_ledger_lines(target):
                    result["lines_seen"] = line_number
                    result["max_logical_line_chars"] = max(
                        result["max_logical_line_chars"], len(raw)
                    )
                    if not raw.strip():
                        result["blank_lines"] += 1
                        continue
                    event = loads_bounded(raw)
                    if not isinstance(event, dict):
                        result["error_class"] = "INVALID_EVENT_SHAPE"
                        return result
                    result["events_seen"] += 1
                    task_id = event.get("task_id")
                    if task_id is not None:
                        if not isinstance(task_id, str):
                            result["error_class"] = "INVALID_TASK_ID_TYPE"
                            return result
                        # Private one-run keyed hash, never returned or logged.
                        opaque = hashlib.blake2b(
                            task_id.encode("utf-8"), key=key, digest_size=20
                        ).digest()
                        db.execute(
                            "INSERT INTO task_counts (key,n) VALUES (?,1) "
                            "ON CONFLICT(key) DO UPDATE SET n=n+1",
                            (opaque,),
                        )
                db.commit()
                row = db.execute(
                    "SELECT COUNT(*), COALESCE(MAX(n),0), "
                    "COALESCE(SUM(CASE WHEN n>18 THEN 1 ELSE 0 END),0), "
                    "COALESCE(SUM(CASE WHEN n>128 THEN 1 ELSE 0 END),0) "
                    "FROM task_counts"
                ).fetchone()
                result["unique_task_ids"] = row[0]
                result["max_matching_task_events"] = row[1]
                result["tasks_over_18_events"] = row[2]
                result["tasks_over_128_events"] = row[3]
            finally:
                db.close()
        result["source_total_bytes"], result["max_physical_line_bytes"] = (
            _raw_line_metrics(target)
        )
        after = target.stat()
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (
            after.st_size, after.st_mtime_ns, after.st_ino
        ):
            result["error_class"] = "SOURCE_CHANGED_DURING_SCAN"
            return result
        result["status"] = "OBSERVED"
        result["note"] = (
            "Numeric aggregates of one stable-looking scan only. "
            "No provenance guarantee; no concurrent-writer snapshot guarantee."
        )
    except LedgerLineLimitExceeded:
        result["error_class"] = "LINE_LIMIT_EXCEEDED"
    except (UnicodeError, json.JSONDecodeError, ValueError):
        result["error_class"] = "DECODING_OR_JSON_REJECTED"
    except (OSError, sqlite3.Error):
        result["error_class"] = "IO_OR_TEMP_DB_FAILURE"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only numeric profile; no event content is printed"
    )
    parser.add_argument("--ledger", required=True, help="Existing JSONL file")
    args = parser.parse_args()
    result = profile_ledger(args.ledger)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "OBSERVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
