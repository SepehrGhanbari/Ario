"""Ario JSON input limits, version 1: 64 containers, 4096 decimal integer digits.

The scanner counts open arrays and objects before the decoder runs.
The integer converter counts decimal digits before invoking its hook.
Both limits are ceilings. The default integer converter bypasses a stricter interpreter decimal-string
conversion setting while respecting the explicit digit cap. A stricter
interpreter recursion limit may still reject deeply nested input.

``JSONDepthExceeded`` subclasses ``json.JSONDecodeError``. Existing
``except json.JSONDecodeError`` clauses therefore keep their current
fail-closed mapping without changes to their result vocabulary.

A depth check is structural only. It does not validate, authenticate, or
assess the content.
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

MAX_JSON_DEPTH = 64
# Below CPython's default decimal-int conversion limit (4300 digits).
# Applied through parse_int so custom hooks cannot bypass the input bound.
MAX_JSON_INTEGER_DIGITS = 4096

# Research candidate: CLI request file cap, not an event-ledger or Ollama cap.
MAX_JSON_FILE_BYTES = 4 * 1024 * 1024


class JSONDepthExceeded(json.JSONDecodeError):
    """Raised when array/object nesting exceeds the explicit bound."""


class JSONValueLimitExceeded(json.JSONDecodeError):
    """Raised when a JSON integer is oversized or a decoder value is rejected."""


def nesting_exceeds(text: str, limit: int = MAX_JSON_DEPTH) -> int | None:
    """Return the offset where nesting first exceeds ``limit``, else ``None``.

    Brackets inside JSON strings, including escaped quotes, are ignored.
    """
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char in "[{":
            depth += 1
            if depth > limit:
                return index
        elif char in "]}":
            depth -= 1
    return None


def loads_bounded(text: str, *, max_depth: int = MAX_JSON_DEPTH, **kwargs: Any) -> Any:
    """Parse decoded text. Callers own byte limits, encoding and BOM policy."""
    if not isinstance(text, str):
        raise TypeError("loads_bounded requires decoded str input")
    if type(max_depth) is not int or not 0 <= max_depth <= MAX_JSON_DEPTH:
        raise ValueError(f"max_depth must be between 0 and {MAX_JSON_DEPTH}")
    if kwargs.get("cls") not in (None, json.JSONDecoder):
        raise TypeError("loads_bounded requires the standard JSON decoder")
    position = nesting_exceeds(text, max_depth)
    if position is not None:
        raise JSONDepthExceeded(
            f"JSON nesting-depth limit {max_depth} exceeded", text, position
        )
    # CPython 3.11+ can raise ValueError (rather than JSONDecodeError)
    # on an integer exceeding its decimal-digit limit. Enforce a stable
    # input bound even when interpreter digit limits differ or are disabled.
    parse_int = kwargs.get("parse_int")
    if parse_int is None or parse_int is int:
        # CPython's process-global sys.set_int_max_str_digits() can be below
        # our documented 4096-digit input ceiling (e.g. 640). Decimal parses
        # JSON integer tokens exactly, then int(Decimal) avoids the stricter
        # decimal *string* conversion limit. The explicit digit check below
        # still runs BEFORE any conversion. Custom hooks retain ownership of
        # their own narrower numeric policies.
        def parse_default_integer(literal: str) -> int:
            return int(Decimal(literal))
        parse_int = parse_default_integer
    elif not callable(parse_int):
        raise TypeError("parse_int must be callable or None")

    def bounded_parse_int(literal: str) -> Any:
        if len(literal.lstrip("-")) > MAX_JSON_INTEGER_DIGITS:
            raise JSONValueLimitExceeded(
                f"JSON integer digit limit {MAX_JSON_INTEGER_DIGITS} exceeded",
                text, 0,
            )
        return parse_int(literal)

    kwargs["parse_int"] = bounded_parse_int
    try:
        return json.loads(text, **kwargs)
    except json.JSONDecodeError:
        raise  # keep the decoder's exact syntax error and position
    except ValueError as exc:
        # Includes interpreter-configured int limits and custom hook errors.
        raise JSONValueLimitExceeded("JSON value rejected by decoder", text, 0) from exc
    except RecursionError as exc:  # defensive: runtime limit below max_depth
        raise JSONDepthExceeded("JSON recursion limit reached", text, 0) from exc


def load_json_file_bounded(
    path: str | Path, *, max_bytes: int = MAX_JSON_FILE_BYTES
) -> Any:
    """Read one UTF-8(-BOM) JSON request file within the shared byte ceiling.

    The one-byte lookahead rejects oversized files before decoding/parsing.
    This bounds the request buffer, not disk IO or the shared JSON decoder's
    output allocation. It does not change ledger JSONL or Ollama limits.
    """
    if type(max_bytes) is not int or not 1 <= max_bytes <= MAX_JSON_FILE_BYTES:
        raise ValueError(f"max_bytes must be between 1 and {MAX_JSON_FILE_BYTES}")
    with Path(path).open("rb") as stream:
        raw = stream.read(max_bytes + 1)
    if len(raw) > max_bytes:
        # Do not retain or echo caller input in a decode error.
        raise JSONValueLimitExceeded(
            f"JSON input byte limit {max_bytes} exceeded", "", 0
        )
    return loads_bounded(raw.decode("utf-8-sig"))
