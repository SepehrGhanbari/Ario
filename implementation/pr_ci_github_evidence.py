"""Validation shared by the read-only GitHub evidence probes."""


def matches_id(value: object, expected: int) -> bool:
    """Match a JSON identifier against an already validated positive integer."""
    return type(value) is int and value > 0 and value == expected
