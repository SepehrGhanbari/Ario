"""Streaming UTF-8-SIG JSONL record boundaries for research-only ledger reads.

No global ledger size or event-count cap: long historical ledgers remain
readable without allocating the entire file. A very large individual record
is explicitly rejected instead of silently truncated or partially parsed.

Using universal newline translation plus splitlines() on each physical line
preserves the older Path.read_text(...).splitlines() behavior for standard
LF/CRLF/CR, blank lines, and Unicode splitline separators. The caller owns
JSON schema checks and fail-closed outcome vocabulary.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterator

# Candidate safety budget, not inherited from the 64-KiB observer policy.
# Includes the terminating newline when one exists. No total-ledger ceiling.
MAX_LEDGER_LINE_CHARS = 16 * 1024 * 1024


class LedgerLineLimitExceeded(ValueError):
    """A JSONL logical line exceeded the bounded streaming read ceiling."""


def iter_bounded_ledger_lines(path: str | Path) -> Iterator[tuple[int, str]]:
    """Yield original 1-based splitlines() numbers with bounded memory.

    Explicitly reject a long physical line BEFORE handing a truncated chunk
    to any JSON parser. No state is written, and no history is rewritten.
    """
    line_number = 0
    with Path(path).open("r", encoding="utf-8-sig", newline=None) as stream:
        while True:
            piece = stream.readline(MAX_LEDGER_LINE_CHARS + 1)
            if piece == "":
                break
            if len(piece) > MAX_LEDGER_LINE_CHARS:
                raise LedgerLineLimitExceeded(
                    f"ledger JSONL line {line_number + 1} exceeds "
                    f"{MAX_LEDGER_LINE_CHARS} characters"
                )
            # splitlines() is intentionally applied even to each physical
            # record: old whole-file readers also split on U+2028, NEL, etc.
            for segment in piece.splitlines():
                line_number += 1
                yield line_number, segment
