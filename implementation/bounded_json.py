"""Interpreter-independent bounded JSON parsing for Ario CLI inputs.

Whether deeply nested JSON raises ``RecursionError`` depends on the CPython
version (3.12/3.13 raise it; 3.14 parses the same text). Unhandled, that
turns a structured fail-closed result into a traceback on one runtime and
an ordinary rejection on another. ``loads_bounded`` applies an explicit,
string-aware depth bound before parsing, so the outcome depends on the
input text alone.

``JSONDepthExceeded`` subclasses ``json.JSONDecodeError``. Existing
``except json.JSONDecodeError`` clauses therefore keep their current
fail-closed mapping without changes to their result vocabulary.

A depth check is structural only. It does not validate, authenticate, or
assess the content.
"""
from __future__ import annotations

import json
from typing import Any

MAX_JSON_DEPTH = 64
# Below CPython's default decimal-int conversion limit (4300 digits).
# Applied through parse_int so custom hooks cannot bypass the input bound.
MAX_JSON_INTEGER_DIGITS = 4096


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
    """``json.loads`` with an explicit nesting bound and no RecursionError escape."""
    position = nesting_exceeds(text, max_depth)
    if position is not None:
        raise JSONDepthExceeded(
            f"JSON nesting-depth limit {max_depth} exceeded", text, position
        )
    # CPython 3.11+ can raise ValueError (rather than JSONDecodeError)
    # on an integer exceeding its decimal-digit limit. Enforce a stable
    # input bound even when interpreter digit limits differ or are disabled.
    parse_int = kwargs.get("parse_int", int)
    if callable(parse_int):
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
