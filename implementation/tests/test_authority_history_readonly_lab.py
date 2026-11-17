"""Synthetic history chain tests: metadata integrity != independent custody.

No production key, signing operation, persistence, authority or live M0 effects.
"""
import hashlib
import json
import pytest

from authority_history_readonly_lab import (
    DOMAIN, GENESIS, RECORD_VERSION, _hash, inspect_declared_history,
)

KEY = "lab-executor-1"
POLICY = "a" * 64
NONCE = "nonce-never-spent"


def enc(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("ascii")


def make_history(*, kinds=("KEY_ENROLLED",), policy=POLICY, key=KEY, nonces=()):
    previous, records, digests = GENESIS, [], []
    for number, kind in enumerate(kinds, 1):
        nonce = nonces[number - 1] if number <= len(nonces) else None
        record = dict(version=RECORD_VERSION, sequence=number, previous_sha256=previous,
                      kind=kind, key_id=key, nonce=nonce, policy_sha256=policy)
        raw = enc(record)
        previous = _hash(raw)
        records.append(raw)
        digests.append(previous)
    return records, digests


def args_for(records, digests, *, floor=0, nonce=NONCE):
    return dict(journal_bytes=b"\n".join(records) + b"\n",
                expected_head_sha256=digests[-1],
                floor_sequence=floor,
                floor_sha256=digests[floor - 1] if floor else GENESIS,
                requested_key_id=KEY, expected_policy_sha256=POLICY,
                requested_nonce=nonce)


def deny_all(r):
    assert r["custody_independence"] == "NOT_ESTABLISHED"
    assert r["policy_origin_authenticated"] is False
    assert r["revocation_source_authenticated"] is False
    assert r["nonce_history_durability"] == "NOT_ESTABLISHED"
    for key in ("authority_granted", "memory_write_allowed", "evidence_admission_allowed",
                "signing_allowed", "trust_activation_allowed"):
        assert r[key] is False


def test_synthetic_genesis_is_structurally_reviewable_but_not_authorized():
    records, digests = make_history()
    r = inspect_declared_history(**args_for(records, digests))
    assert r["inspection"] == "REVIEWABLE_ONLY"
    assert r["reason_code"] == "DECLARED_HISTORY_CONSISTENT"
    assert r["record_count"] == 1
    assert r["declared_head_matches"] and r["declared_floor_matches"]
    deny_all(r)


def test_caller_can_rewrite_all_history_and_update_own_head_pin():
    records, digests = make_history()
    a = inspect_declared_history(**args_for(records, digests))
    records2, digests2 = make_history(policy=POLICY, key=KEY, kinds=("KEY_ENROLLED", "NONCE_SPENT"),
                                     nonces=(None, "old-used-nonce"))
    b = inspect_declared_history(**args_for(records2, digests2))
    assert a["inspection"] == b["inspection"] == "REVIEWABLE_ONLY"
    assert digests[-1] != digests2[-1]
    deny_all(a)
    deny_all(b)


def test_revoked_key_never_reviewable_even_with_matching_head():
    records, digests = make_history(kinds=("KEY_ENROLLED", "KEY_REVOKED"))
    r = inspect_declared_history(**args_for(records, digests))
    assert r["reason_code"] == "DECLARED_KEY_REVOKED"
    deny_all(r)


def test_spent_nonce_blocks_replay_in_declared_history():
    records, digests = make_history(kinds=("KEY_ENROLLED", "NONCE_SPENT"),
                                     nonces=(None, NONCE))
    r = inspect_declared_history(**args_for(records, digests))
    assert r["reason_code"] == "DECLARED_NONCE_SPENT"
    assert r["nonce_declared_spent"] is True
    deny_all(r)


def test_same_nonce_twice_invalidates_chain_policy_even_with_matching_head():
    records, digests = make_history(kinds=("KEY_ENROLLED", "NONCE_SPENT", "NONCE_SPENT"),
                                    nonces=(None, NONCE, NONCE))
    r = inspect_declared_history(**args_for(records, digests))
    assert r["reason_code"] == "DUPLICATE_NONCE_SPEND"
    deny_all(r)


def test_reenroll_after_revocation_rejected():
    records, digests = make_history(kinds=("KEY_ENROLLED", "KEY_REVOKED", "KEY_ENROLLED"))
    r = inspect_declared_history(**args_for(records, digests))
    assert r["reason_code"] == "DUPLICATE_OR_REVOKED_ENROLLMENT"
    deny_all(r)


def test_wrong_head_pin_detects_fork_unless_attacker_controls_anchor():
    records, digests = make_history()
    r = inspect_declared_history(**dict(args_for(records, digests), expected_head_sha256="0" * 64))
    assert r["reason_code"] == "EXTERNAL_HEAD_MISMATCH"
    deny_all(r)


def test_truncation_below_externally_declared_floor_detected():
    records, digests = make_history(kinds=("KEY_ENROLLED", "NONCE_SPENT"),
                                    nonces=(None, "some-nonce"))
    args = args_for(records[:1], digests[:1])
    args.update(floor_sequence=2, floor_sha256=digests[1])
    r = inspect_declared_history(**args)
    assert r["reason_code"] == "HISTORY_BELOW_DECLARED_FLOOR"
    deny_all(r)


def test_full_fork_with_recomputed_head_detected_if_floor_pin_is_unchanged():
    before, bdig = make_history(kinds=("KEY_ENROLLED", "NONCE_SPENT"),
                                nonces=(None, "previously-spent"))
    after, adig = make_history(kinds=("KEY_ENROLLED", "NONCE_SPENT"),
                               nonces=(None, "rewritten-spent"))
    r = inspect_declared_history(**dict(args_for(after, adig), floor_sequence=1,
                                       floor_sha256="0" * 64))
    assert r["reason_code"] == "EXTERNAL_FLOOR_MISMATCH"
    deny_all(r)


def test_modified_first_record_without_updating_second_link_detected():
    records, digests = make_history(kinds=("KEY_ENROLLED", "NONCE_SPENT"),
                                    nonces=(None, "spent"))
    edited = dict(json.loads(records[0]), policy_sha256="b" * 64)
    records[0] = enc(edited)
    r = inspect_declared_history(**args_for(records, digests))
    assert r["reason_code"] == "CHAIN_LINK_MISMATCH"
    deny_all(r)


def test_sequence_gap_is_refused():
    records, digests = make_history(kinds=("KEY_ENROLLED", "NONCE_SPENT"),
                                    nonces=(None, "spent"))
    changed = dict(json.loads(records[1]), sequence=3)
    records[1] = enc(changed)
    r = inspect_declared_history(**args_for(records, digests))
    assert r["reason_code"] == "SEQUENCE_DISCONTINUITY"
    deny_all(r)


def test_unexpected_key_or_policy_not_assumed_authorized():
    records, digests = make_history()
    r = inspect_declared_history(**dict(args_for(records, digests), requested_key_id="unknown-key"))
    assert r["reason_code"] == "KEY_OR_POLICY_NOT_DECLARED"
    deny_all(r)


@pytest.mark.parametrize("bad_entry", [
    {"kind": []}, {"kind": {}}, {"kind": True}, {"nonce": ["fake"]},
    {"sequence": True}, {"key_id": ["fake"]}, {"policy_sha256": None},
])
def test_invalid_python_or_json_field_types_fail_closed_not_crash(bad_entry):
    records, digests = make_history()
    edited = dict(json.loads(records[0]), **bad_entry)
    records[0] = enc(edited)
    r = inspect_declared_history(**args_for(records, digests))
    assert r["inspection"] == "UNKNOWN"
    deny_all(r)


def test_duplicate_json_keys_refused():
    raw = (b'{"key_id":"lab-executor-1","key_id":"fake"}')
    r = inspect_declared_history(**dict(args_for([raw], [_hash(raw)])))
    assert r["reason_code"] == "INVALID_RECORD_ENCODING"
    deny_all(r)


@pytest.mark.parametrize("raw", [b"", b"{}", b"[]\n", b"garbage\n", b" \n", b"\xff\n"])
def test_malformed_history_bytes_not_accepted(raw):
    records, digests = make_history()
    r = inspect_declared_history(**dict(args_for(records, digests), journal_bytes=raw))
    assert r["inspection"] == "UNKNOWN"
    deny_all(r)


def test_boolean_floor_sequence_rejected():
    records, digests = make_history()
    r = inspect_declared_history(**dict(args_for(records, digests), floor_sequence=True))
    assert r["reason_code"] == "INVALID_EXTERNAL_BINDINGS"
    deny_all(r)


def test_deleting_revocation_and_rewriting_self_declared_pin_can_appear_clean():
    records, digests = make_history(kinds=("KEY_ENROLLED", "KEY_REVOKED"))
    revoked = inspect_declared_history(**args_for(records, digests))
    assert revoked["reason_code"] == "DECLARED_KEY_REVOKED"
    # A malicious single custodian can remove the revocation, alter the head
    # pin it also controls, and present a deceptively self-consistent history.
    forged = inspect_declared_history(**args_for(records[:1], digests[:1]))
    assert forged["inspection"] == "REVIEWABLE_ONLY"
    deny_all(forged)
    # An independently preserved floor beyond that revocation is what would
    # reveal the rollback; here it is only supplied by the test controller.
    pinned = dict(args_for(records[:1], digests[:1]),
                  floor_sequence=2, floor_sha256=digests[1])
    detected = inspect_declared_history(**pinned)
    assert detected["reason_code"] == "HISTORY_BELOW_DECLARED_FLOOR"
    deny_all(detected)


def test_revocation_without_prior_enrollment_is_invalid():
    records, digests = make_history(kinds=("KEY_REVOKED",))
    r = inspect_declared_history(**args_for(records, digests))
    assert r["reason_code"] == "INVALID_REVOCATION"
    deny_all(r)
