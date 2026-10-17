"""W5 experimental byte-binding probe. NOT an Ario M0 trust/admission adapter.

Boundary: check a caller-declared W1 report digest against separately supplied raw
bytes. The supplier is synthetic/untrusted here; equality establishes only that
these two supplied values match, not who authored or controlled the bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import re
from typing import Callable

# W1 provenance refs were generated as W1-SHA256-<lowerhex> or
# W1-<caller_label>-SHA256-<lowerhex>. The label is NEVER a principal identity.
_W1_REF = re.compile(r"\AW1-(?:[A-Z0-9][A-Z0-9_-]{0,31}-)?SHA256-([0-9a-f]{64})\Z", re.ASCII)
REFERENCE_TYPE = "UNTRUSTED_LAB_REPORT_DIGEST"
MAX_PAYLOAD_BYTES = 262_144


@dataclass(frozen=True)
class BindingResult:
    status: str
    reason: str
    observed_sha256: str | None = None
    # Intentionally fixed. Neither a digest match nor the caller label has authority.
    source_authentication: str = "UNKNOWN"
    independent_custody: str = "UNKNOWN"
    reviewer_authorization: str = "NOT_EVALUATED"
    evidence_admission: str = "NOT_EVALUATED"
    claim_truth: str = "UNKNOWN"


def check_supplied_payload(
    reference_id: str,
    reference_type: str,
    byte_supplier: Callable[[], bytes],
    *,
    max_payload_bytes: int = MAX_PAYLOAD_BYTES,
) -> BindingResult:
    """Check exact bytes only. Never issue an independent evidence decision.

    The function must not fetch a network URL, use a key, modify a ledger or
    infer that `byte_supplier` is an authenticated independent custody source.
    """
    if (type(reference_id) is not str or type(reference_type) is not str
            or reference_type != REFERENCE_TYPE or len(reference_id) > 128):
        return BindingResult("MALFORMED", "UNTRUSTED_REFERENCE_FORMAT")
    match = _W1_REF.fullmatch(reference_id)
    if match is None:
        return BindingResult("MALFORMED", "UNTRUSTED_REFERENCE_FORMAT")
    if type(max_payload_bytes) is not int or not (1 <= max_payload_bytes <= MAX_PAYLOAD_BYTES):
        return BindingResult("MALFORMED", "INVALID_BOUND")
    if not callable(byte_supplier):
        return BindingResult("UNAVAILABLE", "BYTE_SUPPLIER_MISSING")
    try:
        payload = byte_supplier()
    except (OSError, RuntimeError, ValueError, TypeError, LookupError):
        # Expected user-provided byte supplier/read/decoding failures are not
        # a digest mismatch and must not raise an unaudited success/failure.
        # Do not mask process signals (KeyboardInterrupt/SystemExit) or
        # programmer assertions as ordinary source-unavailability events.
        return BindingResult("UNAVAILABLE", "BYTE_SUPPLIER_UNAVAILABLE")
    if type(payload) is not bytes:
        return BindingResult("UNAVAILABLE", "BYTE_SUPPLIER_DID_NOT_RETURN_BYTES")
    if len(payload) > max_payload_bytes:
        return BindingResult("BOUNDED", "PAYLOAD_TOO_LARGE")
    actual = hashlib.sha256(payload).hexdigest()
    if not hmac.compare_digest(actual, match.group(1)):
        return BindingResult("MISMATCH", "CLAIMED_DIGEST_DIFFERS_FROM_SUPPLIED_BYTES", actual)
    return BindingResult("MATCHED_BYTES_ONLY", "UNAUTHENTICATED_BYTE_EQUALITY_ONLY", actual)
