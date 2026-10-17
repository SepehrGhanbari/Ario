"""Offline contract probes, entirely separate from the Ario source tree."""
from dataclasses import replace
from hashlib import sha256
import json

import pytest

from w5_payload_binding_lab import (
    MAX_PAYLOAD_BYTES, REFERENCE_TYPE, check_supplied_payload,
)


def canonical(obj):
    """Mirror W1's json/ascii hash domain for synthetic serializable dicts."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def ref(payload, label=""):
    caller_label = f"{label}-" if label else ""
    return f"W1-{caller_label}SHA256-{sha256(payload).hexdigest()}"


def assert_not_authority(result):
    assert result.source_authentication == "UNKNOWN"
    assert result.independent_custody == "UNKNOWN"
    assert result.reviewer_authorization == "NOT_EVALUATED"
    assert result.evidence_admission == "NOT_EVALUATED"
    assert result.claim_truth == "UNKNOWN"


def test_w5_01_actual_byte_match_still_has_no_authority():
    payload = canonical({"status": "CONDITIONAL_CORRESPONDENCE", "source": "LAB"})
    out = check_supplied_payload(ref(payload), REFERENCE_TYPE, lambda: payload)
    assert out.status == "MATCHED_BYTES_ONLY"
    assert out.observed_sha256 == sha256(payload).hexdigest()
    assert_not_authority(out)


def test_w5_02_stale_digest_rejected_with_changed_bytes():
    original = canonical({"status": "UNKNOWN"})
    rewritten = canonical({"status": "VERIFIED"})
    assert original != rewritten
    out = check_supplied_payload(ref(original), REFERENCE_TYPE, lambda: rewritten)
    assert (out.status, out.reason) == (
        "MISMATCH", "CLAIMED_DIGEST_DIFFERS_FROM_SUPPLIED_BYTES")
    assert out.observed_sha256 == sha256(rewritten).hexdigest()
    assert_not_authority(out)


def test_w5_03_two_names_one_identical_payload_not_independent():
    payload = canonical({"event": "SAME-SYNTHETIC-EVENT"})
    results = [check_supplied_payload(ref(payload, label), REFERENCE_TYPE, lambda: payload)
               for label in ("FAKE-WITNESS-A", "FAKE-WITNESS-B")]
    assert all(r.status == "MATCHED_BYTES_ONLY" for r in results)
    assert results[0] == results[1]
    assert all(r.independent_custody == "UNKNOWN" for r in results)
    assert all(r.evidence_admission == "NOT_EVALUATED" for r in results)


def test_w5_04_distinct_bytes_are_not_independent_custody_proof():
    payloads = [canonical({"event": 1}), canonical({"event": 2})]
    results = [check_supplied_payload(ref(p), REFERENCE_TYPE, lambda p=p: p)
               for p in payloads]
    assert all(r.status == "MATCHED_BYTES_ONLY" for r in results)
    assert results[0].observed_sha256 != results[1].observed_sha256
    assert all(r.independent_custody == "UNKNOWN" for r in results)


@pytest.mark.parametrize("reference_id", [
    "W1-SHA256-", "W1-SHA256-" + "Z" * 64,
    "W1-SHA256-" + "a" * 63, "W1-SHA256-" + "a" * 65,
    "W1-SHA256-" + "A" * 64, "W1-VERY-LONG-ATTACKER-CHOSEN-WITNESS-NAME-OVER-LIMIT-SHA256-" + "a" * 64,
    "W1-SHA256-" + "a" * 64 + "\n", "W2-SHA256-" + "a" * 64,
])
def test_w5_05_malformed_reference_rejected_before_read(reference_id):
    calls = []
    def supplier():
        calls.append(1)
        return b"anything"
    out = check_supplied_payload(reference_id, REFERENCE_TYPE, supplier)
    assert out.status == "MALFORMED"
    assert calls == []
    assert_not_authority(out)


def test_w5_06_bad_reference_type_cannot_relabel_digest_as_authenticated():
    calls = []
    out = check_supplied_payload(ref(b"test"), "AUTHENTICATED_WITNESS", lambda: calls.append(1))
    assert out.status == "MALFORMED"
    assert calls == []
    assert_not_authority(out)


@pytest.mark.parametrize("payload", [bytearray(b"a"), None, "a", memoryview(b"a")])
def test_w5_07_invalid_supplier_result_fails_closed(payload):
    out = check_supplied_payload(ref(b"a"), REFERENCE_TYPE, lambda: payload)
    assert out.status == "UNAVAILABLE"
    assert_not_authority(out)


@pytest.mark.parametrize("exception", [OSError(), TimeoutError(), RuntimeError()])
def test_w5_08_unavailable_source_is_not_a_mismatch_or_match(exception):
    def unavailable():
        raise exception
    out = check_supplied_payload(ref(b"a"), REFERENCE_TYPE, unavailable)
    assert out.status == "UNAVAILABLE"
    assert out.observed_sha256 is None
    assert_not_authority(out)


def test_w5_09_oversized_report_is_bounded_and_not_hashed():
    payload = b"A" * (MAX_PAYLOAD_BYTES + 1)
    out = check_supplied_payload(ref(payload), REFERENCE_TYPE, lambda: payload)
    assert out.status == "BOUNDED"
    assert out.observed_sha256 is None
    assert_not_authority(out)


@pytest.mark.parametrize("bound", [-1, 0, 1.5, True, MAX_PAYLOAD_BYTES + 1])
def test_w5_10_invalid_bounds_rejected_before_read(bound):
    called = []
    out = check_supplied_payload(ref(b"a"), REFERENCE_TYPE,
                                 lambda: called.append(1), max_payload_bytes=bound)
    assert out.status == "MALFORMED"
    assert called == []
    assert_not_authority(out)


def test_w5_11_empty_report_binds_bytes_but_grants_nothing():
    out = check_supplied_payload(ref(b""), REFERENCE_TYPE, lambda: b"")
    assert out.status == "MATCHED_BYTES_ONLY"
    assert_not_authority(out)


def test_w5_12_same_data_different_json_serialization_must_not_match():
    data = {"a": 1, "z": 2}
    canonical_payload = canonical(data)
    other_bytes = b'{"z": 2, "a": 1}'
    assert json.loads(canonical_payload) == json.loads(other_bytes)
    out = check_supplied_payload(ref(canonical_payload), REFERENCE_TYPE, lambda: other_bytes)
    assert out.status == "MISMATCH"
    assert_not_authority(out)


def test_w5_13_single_changed_byte_fails_claimed_binding():
    original = b"A" * 100
    for change in (0, 49, 99):
        mutated = bytearray(original)
        mutated[change] = ord("B")
        out = check_supplied_payload(ref(original), REFERENCE_TYPE, lambda: bytes(mutated))
        assert out.status == "MISMATCH"
        assert_not_authority(out)


def test_w5_14_no_mutation_or_hidden_state_across_repeated_calls():
    blob = canonical({"version": 1})
    before = bytes(blob)
    outputs = [check_supplied_payload(ref(blob), REFERENCE_TYPE, lambda: blob) for _ in range(3)]
    assert blob == before
    assert outputs[0] == outputs[1] == outputs[2]
    assert_not_authority(outputs[0])
