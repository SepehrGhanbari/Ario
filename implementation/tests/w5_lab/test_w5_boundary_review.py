"""W5 R01 supplier exception regressions and explicit untrusted-boundary probes.

No source authenticity, independent custody or Evidence admission is granted.
"""
from hashlib import sha256
from threading import Event, Thread
import json

import pytest
from w5_payload_binding_lab import (
    REFERENCE_TYPE, MAX_PAYLOAD_BYTES, check_supplied_payload,
)


def ref(payload, label=None):
    suffix = sha256(payload).hexdigest()
    return f"W1-{label + '-' if label else ''}SHA256-{suffix}"


def bounded_no_authority(result):
    assert result.source_authentication == result.independent_custody == result.claim_truth == "UNKNOWN"
    assert result.reviewer_authorization == result.evidence_admission == "NOT_EVALUATED"


@pytest.mark.parametrize("error", [EOFError("truncated stream"), StopIteration("exhausted byte stream")], ids=["EOFError", "StopIteration"])
def test_stream_supplier_failure_should_be_unavailable(error):
    def supplier():
        raise error
    result = check_supplied_payload(ref(b"x"), REFERENCE_TYPE, supplier)
    assert (result.status, result.reason) == ("UNAVAILABLE", "BYTE_SUPPLIER_UNAVAILABLE")
    bounded_no_authority(result)


def test_supplier_ordinary_side_effects_are_not_contained(tmp_path):
    marker = tmp_path / "side-effect-marker.txt"
    data = b"LOCAL-ONLY"
    def supplier():
        marker.write_text("THIS IS A TEST FIXTURE, NOT A NETWORK OR LEDGER WRITE")
        return data
    result = check_supplied_payload(ref(data), REFERENCE_TYPE, supplier)
    assert result.status == "MATCHED_BYTES_ONLY"
    assert marker.is_file()   # Calls arbitrary code; DOES NOT sandbox supplier.
    bounded_no_authority(result)


def test_oversize_is_detected_only_after_payload_is_returned():
    events = []
    data = b"x" * (MAX_PAYLOAD_BYTES + 1)
    def supplier():
        events.append(len(data))
        return data
    result = check_supplied_payload(ref(data), REFERENCE_TYPE, supplier)
    assert events == [MAX_PAYLOAD_BYTES + 1]
    assert result.status == "BOUNDED"
    bounded_no_authority(result)


def test_no_internal_deadline_for_blocked_callback():
    entered, release, completed = Event(), Event(), Event()
    results = []
    def supplier():
        entered.set()
        if not release.wait(1.5):
            raise RuntimeError("test fixture timed out")
        return b"alive"
    def worker():
        try:
            results.append(check_supplied_payload(ref(b"alive"), REFERENCE_TYPE, supplier))
        finally:
            completed.set()
    thread = Thread(target=worker, daemon=True)
    thread.start()
    try:
        assert entered.wait(1.0)
        assert not completed.is_set() # Cannot finish until callback unblocks.
    finally:
        release.set()
        thread.join(timeout=1.0)
    assert completed.is_set()
    assert results[0].status == "MATCHED_BYTES_ONLY"
    bounded_no_authority(results[0])


@pytest.mark.parametrize("attacker_metadata", [
    {"source_authenticated": True, "independent": True, "admitted": True},
    {"reviewer_grant": "VERIFIED", "revocation": "CURRENT", "truth": "PROVEN"},
    {"signature": "VALID", "issuer": "TRUSTED", "source": "INDEPENDENT"},
])
def test_attacker_written_authority_strings_stay_untrusted(attacker_metadata):
    data = json.dumps(attacker_metadata, sort_keys=True).encode()
    result = check_supplied_payload(ref(data), REFERENCE_TYPE, lambda: data)
    assert result.status == "MATCHED_BYTES_ONLY"
    bounded_no_authority(result)


def test_two_attacker_labels_same_bytes_remain_one_unverified_payload():
    data = b"repeated evidence"
    a = check_supplied_payload(ref(data, "FAKE-A"), REFERENCE_TYPE, lambda: data)
    b = check_supplied_payload(ref(data, "FAKE-B"), REFERENCE_TYPE, lambda: data)
    assert a == b
    bounded_no_authority(a)
