"""Validation shared by the read-only GitHub evidence probes."""


def matches_id(value: object, expected: int) -> bool:
    """Match a JSON identifier against an already validated positive integer."""
    return type(value) is int and value > 0 and value == expected


def links_pr(links: object, number: int, pr_id: int, head: str) -> bool:
    """Require an explicit association with the requested PR identity and head."""
    return isinstance(links, list) and any(
        isinstance(link, dict) and matches_id(link.get("number"), number)
        and matches_id(link.get("id"), pr_id) and isinstance(link.get("head"), dict)
        and link["head"].get("sha") == head for link in links
    )


def read_bounded_body(response, cap: int) -> bytes:
    """Read at most cap+1 bytes and check HTTP's declared length when present."""
    data = response.read(cap + 1)
    if len(data) > cap:
        raise ValueError("GitHub response exceeds byte cap")
    lengths = response.headers.get_all("Content-Length", [])
    if lengths:
        if len(lengths) != 1 or response.headers.get("Transfer-Encoding") is not None:
            raise ValueError("ambiguous HTTP response length")
        length = lengths[0].strip()
        if not length.isascii() or not length.isdecimal() or (length.lstrip("0") or "0") != str(len(data)):
            raise ValueError("invalid or incomplete HTTP response length")
    return data
