"""R63 V10 RESEARCH-ONLY candidate for a guest-only pre-sign spend gate.

Read-only. No signer, CNG, keys, ACLs, network or Windows service API.
This reduces V9's V1-disk blind spot but does NOT provide atomic snapshots,
external custody, crash recovery or anti-rollback. The caller MUST hold its
witness RPC server lock; that is not a cross-process filesystem lock.
"""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Callable
import spend_chain_v2 as v2

CAP = 2 * 1024 * 1024
MAX_ROWS = 100000
MAX_LINE = 8192

class GateHold(ValueError):
    """Ambiguous, missing, malformed, or divergent state: no further signing."""


def bounded_bytes(path: Path) -> bytes:
    """Require a present file even when the legitimate journal is empty."""
    try:
        with Path(path).open('rb') as f:
            data = f.read(CAP + 1)
    except OSError as e:
        raise GateHold('spend journal missing or unreadable') from e
    if len(data) > CAP:
        raise GateHold('spend journal exceeds byte cap')
    return data


def v1_pairs(raw: bytes) -> list[list[str]]:
    if type(raw) is not bytes or (raw and not raw.endswith(b'\n')):
        raise GateHold('V1 invalid bytes or incomplete final line')
    lines = raw[:-1].split(b'\n') if raw else []
    if len(lines) > MAX_ROWS:
        raise GateHold('V1 record limit exceeded')
    out: list[list[str]] = []
    seen_nonces: set[str] = set()
    seen_ids: set[str] = set()
    for line in lines:
        if not line or len(line) > MAX_LINE:
            raise GateHold('V1 empty or oversized record')
        try:
            item = json.loads(line.decode('ascii'))
            if (type(item) is not list or len(item) != 2 or
                not all(v2.ishash(v) for v in item) or
                v2.canonical(item) != line):
                raise GateHold('V1 noncanonical or invalid reservation')
        except (ValueError, UnicodeError, TypeError, RecursionError) as e:
            raise GateHold('V1 malformed entry') from e
        nonce, ident = item
        if nonce in seen_nonces or ident in seen_ids:
            raise GateHold('V1 duplicate nonce or id')
        seen_nonces.add(nonce)
        seen_ids.add(ident)
        out.append(item)
    return out


def check_spend_gate(v1_path: Path, v2_path: Path,
                     memory_spends: Any, expected_r60_digest: str,
                     *, expected_prior_v2: bytes | None = None,
                     between_reads_hook: Callable[[], None] | None = None):
    """Strict comparison to current bytes; final reread is only drift detection.

    No independent witness or cross-process locking is established here.
    Optional hook exists ONLY for deterministic synthetic mutation tests.
    """
    raw_v1 = bounded_bytes(v1_path)
    raw_v2 = bounded_bytes(v2_path)
    if between_reads_hook is not None:
        between_reads_hook()
    try:
        left = v1_pairs(raw_v1)
        right = v2.review(raw_v2)
        if (type(memory_spends) is not list or
            any(type(x) is not list or len(x) != 2 for x in memory_spends)):
            raise GateHold('RPC spend memory not a list of pairs')
        memory = [list(item) for item in memory_spends]
        if left != [list(p) for p in right.pairs] or left != memory:
            raise GateHold('V1/V2/memory append-order disagreement')
        if (not v2.ishash(expected_r60_digest) or
            v2.snapshot(right.pairs) != expected_r60_digest):
            raise GateHold('R60 content commitment mismatch')
        if expected_prior_v2 is not None and raw_v2 != expected_prior_v2:
            raise GateHold('V2 bytes changed after prior read')
    except (v2.Hold, ValueError, RecursionError, OverflowError) as e:
        raise GateHold('spend state not safe to use') from e
    if bounded_bytes(v1_path) != raw_v1 or bounded_bytes(v2_path) != raw_v2:
        raise GateHold('journal changed during review')
    return right
