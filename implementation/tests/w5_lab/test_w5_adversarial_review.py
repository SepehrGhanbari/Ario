"""W5 v0.2 independent hostile-input review; not a production bridge.

All tests are deterministic and offline. Fail-closed means returning a
non-authorizing diagnostic for expected supplier failures, not trusting input.
"""
from hashlib import sha256
import pytest

from w5_payload_binding_lab import (
    MAX_PAYLOAD_BYTES, REFERENCE_TYPE, check_supplied_payload,
)


def ref(payload=b"SYNTHETIC"):
    return "W1-SHA256-" + sha256(payload).hexdigest()


def no_authority(r):
    assert r.source_authentication == r.independent_custody == r.claim_truth == "UNKNOWN"
    assert r.reviewer_authorization == r.evidence_admission == "NOT_EVALUATED"


@pytest.mark.parametrize("exception", [
    ValueError("damaged record"),
    KeyError("payload"),
    TypeError("malformed loader object"),
    IndexError("missing index"),
    UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid"),
])
def test_expected_supplier_failures_return_unavailable_not_raise(exception):
    calls=[]
    def broken():
        calls.append(True)
        raise exception
    result=check_supplied_payload(ref(), REFERENCE_TYPE, broken)
    assert calls==[True]
    assert (result.status,result.reason)==("UNAVAILABLE","BYTE_SUPPLIER_UNAVAILABLE")
    assert result.observed_sha256 is None
    no_authority(result)


@pytest.mark.parametrize("exception", [KeyboardInterrupt(), SystemExit(3), GeneratorExit()])
def test_process_control_exceptions_are_not_silently_swallowed(exception):
    def supplier():
        raise exception
    with pytest.raises(type(exception)):
        check_supplied_payload(ref(), REFERENCE_TYPE, supplier)


def test_fully_attacker_controlled_bytes_and_digest_still_do_not_prove_origin():
    # A matching digest is not a second-party corroboration or source authenticator.
    forged=b'{"independent":"TRUE", "fake-source":"X"}'
    result=check_supplied_payload(ref(forged),REFERENCE_TYPE,lambda:forged)
    assert result.status == "MATCHED_BYTES_ONLY"
    no_authority(result)


def test_replayed_payload_verifies_bytes_but_never_freshness_or_revocation():
    earlier=b'{"event":"OLD"}'
    outputs=[check_supplied_payload(ref(earlier),REFERENCE_TYPE,lambda:earlier) for _ in range(3)]
    assert all(r.status=="MATCHED_BYTES_ONLY" for r in outputs)
    assert outputs[0]==outputs[1]==outputs[2]
    for result in outputs:
        no_authority(result)


def test_payload_exact_limit_is_byte_equality_not_authority():
    payload=b"B"*MAX_PAYLOAD_BYTES
    result=check_supplied_payload(ref(payload), REFERENCE_TYPE,lambda:payload)
    assert result.status=="MATCHED_BYTES_ONLY"
    no_authority(result)


def test_supplier_not_called_when_invalid_bound_or_reference():
    calls=[]
    def read():
        calls.append(1)
        return b"x"
    for kwargs in ({"max_payload_bytes":True}, {"max_payload_bytes":0}):
        assert check_supplied_payload(ref(),REFERENCE_TYPE,read,**kwargs).status=="MALFORMED"
    assert check_supplied_payload(ref(),"AUTHENTICATED",read).status=="MALFORMED"
    assert calls==[]


def test_non_operational_callback_errors_are_exposed_as_coding_faults():
    # Do not hide assertion failures in an 'unavailable source' classification.
    def broken():
        raise AssertionError("coding invariant failed")
    with pytest.raises(AssertionError):
        check_supplied_payload(ref(),REFERENCE_TYPE,broken)
