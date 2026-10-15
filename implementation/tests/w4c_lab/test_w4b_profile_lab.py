"""W4-B negative/adversarial offline cryptographic test profile.

ALL signing uses publicly documented RFC8032 **test-only private seed**.
This test key MUST NOT be enrolled, reused or treated as a production credential.
"""
from __future__ import annotations

import copy
import json
from dataclasses import replace
from hashlib import sha256

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

import w4b_profile_lab as lab

RFC8032_TEST_ONLY_SEED = bytes.fromhex(
    "9d61b19deffd5a60ba844af492ec2cc4"
    "4449c5697b326919703bac031cae7f60"
)
RFC8032_EXPECTED_PUBLIC = bytes.fromhex(
    "d75a980182b10ab7d54bfed3c964073a"
    "0ee172f3daa62325af021a68f707511a"
)
RFC8032_EMPTY_SIGNATURE = bytes.fromhex(
    "e5564300c360ac729086e2cc806e828a"
    "84877f1eb8e5d974d873e06522490155"
    "5fb8821590a33bacc61e39701cf9b46b"
    "d25bf5f0595bbe24655141438e7a100b"
)
TEST_PAYLOAD = b"{\"event\":\"TASK_FINISHED\",\"result\":\"COMPLETED\"}\n"


def private_test_key():
    return Ed25519PrivateKey.from_private_bytes(RFC8032_TEST_ONLY_SEED)


def public_test_bytes():
    return private_test_key().public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def attestation(**overrides):
    values = dict(
        profile=lab.PROFILE,
        payload_sha256=sha256(TEST_PAYLOAD).hexdigest(),
        payload_byte_length=len(TEST_PAYLOAD),
        event_namespace="ario.synthetic.lab",
        event_id="TASK-A",
        event_type="TASK_FINISHED",
        event_epoch="SYNTHETIC-01",
        claim_id="CLAIM-A",
        claim_scope="task.record.presence",
        requested_use="RECORD_DESCRIPTION",
        audience="ario.offline.test",
        request_id="NONCE-001",
        witness_key_id=lab.public_key_id(public_test_bytes()),
        source_id="SOURCE-A",
        custodian_id="LAB-CUSTODIAN-A",
        control_group_id="LAB-CONTROL-A",
        parent_refs=["EVENT-ROOT-A"],
    )
    values.update(overrides)
    return values


def context(a):
    return lab.Context(**{k:a[k] for k in lab.Context.__dataclass_fields__})


def sign_wire(a):
    return lab.encode_wire(a, private_test_key().sign(lab.bytes_to_sign(a)))


def synthetic_registry():
    return {lab.public_key_id(public_test_bytes()): public_test_bytes()}


def inspect(a=None, *, wire=None, expected=None, payload_reader=None, keys=None):
    a = attestation() if a is None else a
    wire = sign_wire(a) if wire is None else wire
    expected = context(a) if expected is None else expected
    payload_reader = (lambda: TEST_PAYLOAD) if payload_reader is None else payload_reader
    keys = synthetic_registry() if keys is None else keys
    return lab.inspect(wire, payload_reader, keys, expected)


def assert_fails_closed(out):
    assert out.status in ("UNKNOWN", "REJECTED")
    assert out.source_authentication == "UNKNOWN"
    assert out.source_independence == "UNKNOWN"
    assert out.reviewer_authorization == "UNKNOWN"
    assert out.admission_decision == "NOT_EVALUATED"
    assert out.claim_truth == "UNKNOWN"


def test_rfc8032_test_vector_interoperability():
    # A standard, published Ed25519 interoperability vector (empty message).
    assert public_test_bytes() == RFC8032_EXPECTED_PUBLIC
    assert private_test_key().sign(b"") == RFC8032_EMPTY_SIGNATURE
    Ed25519PublicKey.from_public_bytes(RFC8032_EXPECTED_PUBLIC).verify(RFC8032_EMPTY_SIGNATURE, b"")


def test_exact_unsigned_status_even_when_test_signature_checks():
    result = inspect()
    assert result.status == "UNKNOWN"
    assert result.reason == "W4B-SYNTHETIC_CRYPTO_ONLY_NO_INDEPENDENT_AUTHENTICATION"
    assert result.byte_integrity_check == "MATCHED"
    assert result.test_signature_check == "VALID_UNDER_INJECTED_TEST_KEY"
    assert_fails_closed(result)


def test_deterministic_signed_bytes_and_wire_are_byte_identical():
    a = attestation()
    assert lab.bytes_to_sign(a) == lab.bytes_to_sign(dict(reversed(list(a.items()))))
    assert lab.encode_wire(a, private_test_key().sign(lab.bytes_to_sign(a))) == sign_wire(a)
    assert lab.bytes_to_sign(a).startswith(lab.DOMAIN)


@pytest.mark.parametrize("field", sorted(lab.Context.__dataclass_fields__))
def test_signed_scope_cannot_migrate_to_a_different_verifier_request(field):
    a = attestation()
    c = replace(context(a), **{field: "ATTACK-DIFFERENT"})
    result = inspect(a, expected=c)
    assert result.status == "REJECTED"
    assert result.reason == "W4B-CONTEXT_MISMATCH:" + field
    assert_fails_closed(result)


@pytest.mark.parametrize("mutated", [
    b"{\"event\":\"TASK_FINISHED\",\"result\":\"COMPLETEd\"}\n",
    TEST_PAYLOAD.replace(b"COMPLETED", b"FAILED___"),
    TEST_PAYLOAD + b"x",
    TEST_PAYLOAD[:-1],
])
def test_payload_must_match_computed_digest_and_length(mutated):
    result = inspect(payload_reader=lambda: mutated)
    assert result.status == "REJECTED"
    assert result.reason == "W4B-PAYLOAD_DIGEST_OR_LENGTH_MISMATCH"
    assert_fails_closed(result)


def test_payload_snapshot_is_read_once_only():
    calls = []
    def unstable():
        calls.append(1)
        return TEST_PAYLOAD if len(calls) == 1 else b"MALICIOUS-SECOND-READ"
    result = inspect(payload_reader=unstable)
    assert len(calls) == 1
    assert result.test_signature_check == "VALID_UNDER_INJECTED_TEST_KEY"
    assert_fails_closed(result)


def test_unavailable_reader_preserves_unknown():
    def fail():
        raise OSError("unavailable")
    result = inspect(payload_reader=fail)
    assert result.status == "UNKNOWN" and result.reason == "W4B-PAYLOAD_UNAVAILABLE"
    assert_fails_closed(result)


@pytest.mark.parametrize("bad_data", [b"", b"x"*65537, "not bytes", bytearray(TEST_PAYLOAD)])
def test_missing_or_invalid_payload_is_unknown(bad_data):
    r = inspect(payload_reader=lambda: bad_data)
    assert r.status == "UNKNOWN" and r.reason == "W4B-PAYLOAD_MISSING_OR_OVERSIZED"
    assert_fails_closed(r)


def test_valid_signature_with_no_enrolled_external_test_root_cannot_authenticate():
    result = inspect(keys={})
    assert result.status == "UNKNOWN" and result.reason == "W4B-NO_ENROLLED_TEST_KEY"
    assert_fails_closed(result)


def test_mismatched_key_substitution_is_detected():
    wrong_key = Ed25519PrivateKey.from_private_bytes(b"\x02"*32).public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    result = inspect(keys={lab.public_key_id(public_test_bytes()): wrong_key})
    assert result.status == "REJECTED" and result.reason == "W4B-MISMATCHED_TEST_KEY"
    assert_fails_closed(result)


def test_wrong_signature_bit_is_detected():
    a = attestation()
    signature = bytearray(private_test_key().sign(lab.bytes_to_sign(a)))
    signature[0] ^= 1
    result = inspect(a, wire=lab.encode_wire(a, bytes(signature)))
    assert result.status == "REJECTED" and result.reason == "W4B-INVALID_TEST_SIGNATURE"
    assert_fails_closed(result)


def test_wire_cannot_self_enroll_a_key():
    a = attestation()
    raw = sign_wire(a)
    altered = raw[:-1] + b',"public_key":"' + public_test_bytes().hex().encode("ascii") + b'"}'
    result = inspect(a, wire=altered)
    assert result.status == "REJECTED"
    assert_fails_closed(result)


@pytest.mark.parametrize("invalid_wire", [
    b"\xef\xbb\xbf"+sign_wire(attestation()),
    sign_wire(attestation()) + b" ",
    sign_wire(attestation()) + b"\n",
    sign_wire(attestation()).replace(b'"signature_hex":', b'"signature_hex":"f", "signature_hex":'),
    b"[]",
    b"{" + b"x"*8192 + b"}",
    b"{\"attestation\":null,\"signature_hex\":null}",
    b"{\"attestation\": NaN, \"signature_hex\":\"bad\"}",
    sign_wire(attestation()).replace(b'"payload_byte_length":', b'"payload_byte_length":1.0, "ignored":'),
])
def test_noncanonical_ambiguous_or_malformed_wire_is_rejected(invalid_wire):
    result = inspect(wire=invalid_wire)
    assert result.status == "REJECTED"
    assert_fails_closed(result)


@pytest.mark.parametrize("change", [
    {"profile":"ARIO-FAKE-VERSION"},
    {"parent_refs":["B", "A"]},
    {"parent_refs":["A", "A"]},
    {"parent_refs":["A"]*17},
    {"parent_refs":"A"},
    {"payload_byte_length":0},
    {"payload_byte_length":True},
    {"payload_byte_length":1.5},
    {"payload_sha256":"z"*64},
    {"event_id":"TASK-\u2603"},
    {"claim_id":"CLAIM\x00A"},
    {"requested_use":"ADMIT_EVIDENCE"},
    {"audience":"*"},
    {"witness_key_id":"sha256:" + "z"*64},
    {"source_id":"x"*129},
])
def test_unsupported_ambiguous_records_cannot_be_signed_under_fixed_profile(change):
    with pytest.raises(ValueError):
        lab.canonical_attestation(attestation(**change))


def test_status_object_itself_cannot_be_promoted():
    with pytest.raises(ValueError):
        lab.Outcome("ACCEPTED", "WRONG")
    with pytest.raises(ValueError):
        lab.Outcome("UNKNOWN", "WRONG", admission_decision="ADMITTED")
    with pytest.raises(ValueError):
        lab.Outcome("UNKNOWN", "WRONG", source_authentication="VERIFIED")


def test_context_mismatch_detected_before_payload_read():
    calls=[]
    def reader():
        calls.append(1)
        return TEST_PAYLOAD
    out = inspect(expected=replace(context(attestation()), event_id="OTHER"),payload_reader=reader)
    assert calls == []
    assert out.status == "REJECTED"


def test_replay_in_same_context_remains_unresolved_without_external_nonce_history():
    # Do not misreport same exact signed bytes as 'replay-resistant'; absent a
    # trusted monotonic nonce registry, this lab cannot know if it was replayed.
    a=attestation()
    wire=sign_wire(a)
    x=inspect(a,wire=wire)
    y=inspect(a,wire=wire)
    assert x==y
    assert x.status=="UNKNOWN"
    assert x.test_signature_check=="VALID_UNDER_INJECTED_TEST_KEY"
    assert_fails_closed(x)


def test_cryptographic_byte_binding_does_not_prove_custody_or_independence():
    a=attestation(custodian_id="UNKNOWN",control_group_id="UNKNOWN",source_id="UNKNOWN",parent_refs=[])
    r=inspect(a)
    assert r.test_signature_check=="VALID_UNDER_INJECTED_TEST_KEY"
    assert_fails_closed(r)


def test_mock_two_signers_are_not_two_independent_witnesses():
    # Even when two different real Ed25519 test signatures verify, metadata has
    # no independent custodian attestation, so no corroboration may be inferred.
    a=attestation()
    other=Ed25519PrivateKey.from_private_bytes(b"\x03"*32)
    key=other.public_key().public_bytes(encoding=serialization.Encoding.Raw,format=serialization.PublicFormat.Raw)
    b=attestation(witness_key_id=lab.public_key_id(key),source_id="SOURCE-B",custodian_id="LAB-CUSTODIAN-A",control_group_id="LAB-CONTROL-A")
    wire=lab.encode_wire(b,other.sign(lab.bytes_to_sign(b)))
    result=lab.inspect(wire,lambda:TEST_PAYLOAD,{lab.public_key_id(key):key},context(b))
    assert result.test_signature_check=="VALID_UNDER_INJECTED_TEST_KEY"
    assert_fails_closed(result)


def test_signature_invalid_under_swapped_domain_separator():
    a=attestation()
    signature=private_test_key().sign(b"ARIO-UNRELATED-TEST\x00" + lab.canonical_attestation(a))
    r=inspect(a,wire=lab.encode_wire(a,signature))
    assert r.status=="REJECTED" and r.reason=="W4B-INVALID_TEST_SIGNATURE"


def test_canonical_encoding_byte_vector_is_ASCII_and_ordered():
    a=attestation()
    c=lab.canonical_attestation(a)
    assert all(v<128 for v in c)
    assert c[0:15]==b'{"audience":"ar'
    assert c.find(b'"audience"') < c.find(b'"claim_id"') < c.find(b'"event_id"')
    assert b'\n' not in c


def test_frozen_cross_platform_vector_reproduces_every_byte():
    from pathlib import Path
    doc=json.loads(Path(__file__).with_name("W4B_TEST_VECTORS.json").read_text(encoding="utf-8"))
    assert doc["test_private_seed_hex_PUBLISHED_NOT_SECRET"] == RFC8032_TEST_ONLY_SEED.hex()
    assert bytes.fromhex(doc["test_public_key_hex"]) == public_test_bytes()
    assert bytes.fromhex(doc["signed_message_hex"]) == lab.bytes_to_sign(attestation())
    assert bytes.fromhex(doc["wire_message_utf8_hex"]) == sign_wire(attestation())
    assert bytes.fromhex(doc["canonical_attestation_utf8_hex"]) == lab.canonical_attestation(attestation())
    assert bytes.fromhex(doc["test_signature_hex"]) == private_test_key().sign(lab.bytes_to_sign(attestation()))
    assert doc["expected_outcome"] == inspect().__dict__


def test_frozen_vector_different_request_nonce_fails_closed():
    from pathlib import Path
    doc=json.loads(Path(__file__).with_name("W4B_TEST_VECTORS.json").read_text(encoding="utf-8"))
    existing=attestation()
    rejected=inspect(existing,wire=bytes.fromhex(doc["wire_message_utf8_hex"]),
                     expected=replace(context(existing),request_id="NONCE-REPLAY-002"))
    assert rejected.status == "REJECTED"
    assert rejected.reason == "W4B-CONTEXT_MISMATCH:request_id"
    assert_fails_closed(rejected)
