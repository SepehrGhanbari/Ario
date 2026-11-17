"""All keys are ephemeral synthetic test fixtures; no production key or signer."""
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from receipt_verifier_readonly_lab import (
    ENVELOPE_VERSION, PAYLOAD_VERSION, POLICY_VERSION, SIGNATURE_DOMAIN, inspect_receipt,
)

def enc(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")

def _case(*, priv=None):
    priv = priv or Ed25519PrivateKey.generate()
    pub = priv.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    policy = {
        "version": POLICY_VERSION, "key_id": "lab-executor-1", "public_key_hex": pub.hex(),
        "not_before_epoch": 1000, "not_after_epoch": 2000,
        "revoked": False, "purpose": "SYNTHETIC_RESEARCH_ONLY",
    }
    payload = {
        "version": PAYLOAD_VERSION, "key_id": "lab-executor-1", "execution_id": "synthetic-execution-1",
        "nonce": "synthetic-nonce-123", "tool": "file_fingerprint",
        "request_sha256": "a" * 64, "result_sha256": "b" * 64,
        "exit_code": 0, "observed_epoch": 1400,
    }
    signature = priv.sign(SIGNATURE_DOMAIN + enc(payload))
    envelope = {"version": ENVELOPE_VERSION, "payload": payload, "signature_hex": signature.hex()}
    raw_policy = enc(policy)
    args = dict(envelope_bytes=enc(envelope), policy_bytes=raw_policy,
                expected_policy_sha256=hashlib.sha256(raw_policy).hexdigest(),
                expected_request_sha256="a" * 64, expected_result_sha256="b" * 64,
                spent_nonces=frozenset(), now_epoch=1420)
    return priv, policy, payload, envelope, args

def _update_policy(args, policy):
    raw = enc(policy)
    return dict(args, policy_bytes=raw, expected_policy_sha256=hashlib.sha256(raw).hexdigest())

def _resign(args, priv, envelope):
    e = dict(envelope)
    e["signature_hex"] = priv.sign(SIGNATURE_DOMAIN + enc(e["payload"])).hex()
    return dict(args, envelope_bytes=enc(e))

def _check_no_authority(r):
    assert r["custody_independence"] == "NOT_ESTABLISHED"
    assert r["executor_authorization"] == "NOT_ESTABLISHED"
    assert r["execution_reality"] == "NOT_ESTABLISHED"
    assert r["claim_truth"] == "UNKNOWN"
    for k in ("evidence_admission_allowed", "memory_write_allowed", "tool_execution_allowed",
              "signing_allowed", "trust_activation_allowed"):
        assert r[k] is False

def test_positive_synthetic_signature_only_all_authority_denied():
    _, _, _, _, args = _case()
    original = dict(args)
    r = inspect_receipt(**args)
    assert r["inspection"] == "REVIEWABLE_ONLY"
    assert r["reason_code"] == "SIGNED_METADATA_CHECKS_PASSED"
    assert r["signature_valid"] is True and r["policy_pin_matches"] is True
    _check_no_authority(r)
    assert args == original

def test_same_actor_can_forge_policy_pin_and_sign_without_independent_custody():
    _, _, _, _, a = _case()
    _, _, _, _, b = _case()
    for args in (a, b):
        r = inspect_receipt(**args)
        assert r["signature_valid"] is True
        _check_no_authority(r)

def test_policy_pin_mismatch_rejected():
    _, _, _, _, args = _case()
    r = inspect_receipt(**dict(args, expected_policy_sha256="0" * 64))
    assert r["reason_code"] == "EXTERNAL_POLICY_PIN_MISMATCH"
    _check_no_authority(r)

def test_revoked_policy_rejected_even_valid_signature():
    _, p, _, _, args = _case()
    p["revoked"] = True
    r = inspect_receipt(**_update_policy(args, p))
    assert r["reason_code"] == "DECLARED_KEY_REVOKED"
    assert r["signature_valid"] is False
    _check_no_authority(r)

@pytest.mark.parametrize("clock", [999, 2001, True, None, "1420"])
def test_out_of_range_or_wrong_clock_fails_closed(clock):
    _, _, _, _, args = _case()
    r = inspect_receipt(**dict(args, now_epoch=clock))
    assert r["inspection"] == "UNKNOWN"
    _check_no_authority(r)

def test_previously_spent_nonce_is_rejected_without_mutating_registry():
    _, _, _, _, args = _case()
    seen = frozenset({"synthetic-nonce-123"})
    r = inspect_receipt(**dict(args, spent_nonces=seen))
    assert r["reason_code"] == "REPLAYED_NONCE_DECLARED"
    assert r["replay_seen"] is True
    assert seen == frozenset({"synthetic-nonce-123"})
    _check_no_authority(r)

def test_signature_bit_flip_rejected():
    _, _, _, e, args = _case()
    e["signature_hex"] = ("0" if e["signature_hex"][0] != "0" else "1") + e["signature_hex"][1:]
    r = inspect_receipt(**dict(args, envelope_bytes=enc(e)))
    assert r["reason_code"] == "INVALID_SIGNATURE"
    _check_no_authority(r)

def test_signed_content_mismatch_rejected_even_with_valid_crypto():
    _, _, _, _, args = _case()
    r = inspect_receipt(**dict(args, expected_result_sha256="0" * 64))
    assert r["signature_valid"] is True
    assert r["reason_code"] == "EXTERNAL_CONTENT_BINDING_MISMATCH"
    _check_no_authority(r)

def test_modified_payload_without_resign_rejected():
    _, _, _, e, args = _case()
    e["payload"]["result_sha256"] = "0" * 64
    r = inspect_receipt(**dict(args, envelope_bytes=enc(e)))
    assert r["reason_code"] == "INVALID_SIGNATURE"
    _check_no_authority(r)

def test_key_substitution_rejected_if_independent_pin_unchanged():
    _, _, _, _, a = _case()
    _, _, _, _, b = _case()
    r = inspect_receipt(**dict(b, policy_bytes=a["policy_bytes"], expected_policy_sha256=a["expected_policy_sha256"]))
    assert r["reason_code"] == "INVALID_SIGNATURE"
    _check_no_authority(r)

def test_key_id_substitution_signed_but_policy_disagrees():
    key, _, _, e, args = _case()
    e["payload"]["key_id"] = "other-id"
    r = inspect_receipt(**_resign(args, key, e))
    assert r["reason_code"] == "KEY_ID_MISMATCH"
    _check_no_authority(r)

@pytest.mark.parametrize("raw", [
    b'{"version":"ARIO-EXECUTION-ENVELOPE-0.1","version":"ARIO-EXECUTION-ENVELOPE-0.1"}',
    b'{"x":1.5}', b'{"x":NaN}', b'\xff', b' ' * 5000, b'[]', b'{} ', b'',
])
def test_malformed_noncanonical_or_oversized_envelope_fails_closed(raw):
    _, _, _, _, args = _case()
    r = inspect_receipt(**dict(args, envelope_bytes=raw))
    assert r["inspection"] == "UNKNOWN"
    _check_no_authority(r)

def test_extra_envelope_field_rejected_even_with_valid_signature():
    _, _, _, e, args = _case()
    e["accepted"] = True
    r = inspect_receipt(**dict(args, envelope_bytes=enc(e)))
    assert r["reason_code"] == "INVALID_ENVELOPE_CONTRACT"
    _check_no_authority(r)

@pytest.mark.parametrize("bad_exit", [True, False, 0.0, "0", None, -1, 256])
def test_bad_exit_code_not_accepted_as_integer(bad_exit):
    key, _, _, e, args = _case()
    e["payload"]["exit_code"] = bad_exit
    if type(bad_exit) is float:
        r = inspect_receipt(**dict(args, envelope_bytes=enc(e)))
    else:
        r = inspect_receipt(**_resign(args, key, e))
    assert r["inspection"] == "UNKNOWN"
    _check_no_authority(r)

def test_expired_signed_event_rejected():
    key, _, _, e, args = _case()
    e["payload"]["observed_epoch"] = 1001
    r = inspect_receipt(**_resign(args, key, e))
    assert r["reason_code"] == "EVENT_TIME_NOT_CURRENT"
    _check_no_authority(r)

def test_invalid_external_bindings_default_fail_closed():
    _, _, _, _, args = _case()
    for changed in ({"spent_nonces": set()}, {"spent_nonces": frozenset({123})},
                    {"expected_policy_sha256": None}, {"expected_result_sha256": "A" * 64}):
        r = inspect_receipt(**dict(args, **changed))
        assert r["reason_code"] == "INVALID_EXTERNAL_BINDINGS"
        _check_no_authority(r)

def test_policy_with_unrecognized_authority_field_is_refused():
    _, p, _, _, args = _case()
    p["trust_activation_allowed"] = True
    r = inspect_receipt(**_update_policy(args, p))
    assert r["reason_code"] == "INVALID_POLICY_CONTRACT"
    _check_no_authority(r)


def test_missing_external_nonce_history_cannot_establish_replay_safety():
    _, _, _, _, args = _case()
    # Two inspections with an unchanging caller-controlled empty snapshot
    # both appear reviewable; NO durable replay defense is established.
    first, second = inspect_receipt(**args), inspect_receipt(**args)
    assert first["signature_valid"] is True
    assert second["signature_valid"] is True
    assert second["replay_seen"] is False
    _check_no_authority(second)

def test_declared_revocation_can_be_unilaterally_reversed_by_policy_supplier():
    _, p, _, _, args = _case()
    revoked = dict(p, revoked=True)
    assert inspect_receipt(**_update_policy(args, revoked))["reason_code"] == "DECLARED_KEY_REVOKED"
    # Whoever supplies policy AND pin can reverse revocation without a custodian.
    r = inspect_receipt(**_update_policy(args, dict(revoked, revoked=False)))
    assert r["inspection"] == "REVIEWABLE_ONLY"
    _check_no_authority(r)

def test_caller_supplied_clock_does_not_prove_real_time():
    _, _, _, _, args = _case()
    early = inspect_receipt(**dict(args, now_epoch=1420))
    late = inspect_receipt(**dict(args, now_epoch=2001))
    assert early["signature_valid"] is True
    assert late["reason_code"] == "POLICY_NOT_CURRENT"
    _check_no_authority(early)
    _check_no_authority(late)


def test_seeded_single_byte_mutations_never_crash_or_authorize():
    import random
    _, _, _, _, args = _case()
    rng = random.Random(20261117)
    for which in ("envelope_bytes", "policy_bytes"):
        for _ in range(128):
            raw = bytearray(args[which])
            at = rng.randrange(len(raw))
            raw[at] = rng.randrange(256)
            result = inspect_receipt(**dict(args, **{which: bytes(raw)}))
            _check_no_authority(result)
