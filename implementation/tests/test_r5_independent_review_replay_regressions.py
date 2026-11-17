"""R5 independent-review findings: untrusted R5 report -> source-bound regressions.

TEST FIRST against PR #271 exact HEAD 9778d650875f14bddfaa946acbca4f2097365954.
Deliberately reproduce one reporting defect before minimal fix; other tests
codify non-authority and design limits, not production custody.
Synthetic data only; no key handling, signer, clock service or disk writes.
"""
import json

from authority_history_readonly_lab import _hash, GENESIS, RECORD_VERSION, inspect_declared_history

KEY_A = "key-A"
KEY_B = "key-B"
PIN = "a" * 64
NONCE = "nonce-shared-across-keys"


def chain(*events):
    prev, lines, hashes = GENESIS, [], []
    for i, (kind, kid, nonce, policy) in enumerate(events, 1):
        record = {
            "version": RECORD_VERSION, "sequence": i, "previous_sha256": prev,
            "kind": kind, "key_id": kid, "nonce": nonce, "policy_sha256": policy,
        }
        line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        prev = _hash(line)
        lines.append(line)
        hashes.append(prev)
    return lines, hashes


def inspect(lines, hashes, *, kid=KEY_A, policy=PIN, nonce=NONCE,
            floor_seq=0, floor_hash=GENESIS, head=None):
    return inspect_declared_history(
        journal_bytes=b"\n".join(lines) + b"\n", expected_head_sha256=head or hashes[-1],
        floor_sequence=floor_seq, floor_sha256=floor_hash,
        requested_key_id=kid, expected_policy_sha256=policy,
        requested_nonce=nonce,
    )


def deny(r):
    assert r["custody_independence"] == "NOT_ESTABLISHED"
    assert r["policy_origin_authenticated"] is False
    assert r["revocation_source_authenticated"] is False
    for x in ("authority_granted", "evidence_admission_allowed", "memory_write_allowed",
              "signing_allowed", "trust_activation_allowed"):
        assert r[x] is False


def test_revocation_reason_is_not_hidden_by_wrong_expected_policy():
    events = [
        ("KEY_ENROLLED", KEY_A, None, PIN),
        ("KEY_REVOKED", KEY_A, None, PIN),
    ]
    lines, hashes = chain(*events)
    honest = inspect(lines, hashes)
    assert honest["reason_code"] == "DECLARED_KEY_REVOKED"
    # EXPECTED RED on #271: mismatched caller policy currently masks revocation
    # with KEY_OR_POLICY_NOT_DECLARED even for a known terminally revoked key.
    wrong_pin = inspect(lines, hashes, policy="c" * 64)
    assert wrong_pin["reason_code"] == "DECLARED_KEY_REVOKED"
    assert wrong_pin["inspection"] == "UNKNOWN"
    deny(wrong_pin)


def test_conservative_global_nonce_scope_is_exposed_and_not_a_new_privilege():
    lines, hashes = chain(
        ("KEY_ENROLLED", KEY_A, None, PIN),
        ("KEY_ENROLLED", KEY_B, None, PIN),
        ("NONCE_SPENT", KEY_A, NONCE, PIN),
    )
    # Global nonce uniqueness is an explicit v0.1 research choice here:
    # no other key can reuse an already spent nonce. Not per-key scoping.
    for kid in (KEY_A, KEY_B):
        result = inspect(lines, hashes, kid=kid)
        assert result["reason_code"] == "DECLARED_NONCE_SPENT"
        assert result["nonce_declared_spent"] is True
        deny(result)


def test_cross_key_duplicate_nonce_is_invalid_even_with_self_consistent_head():
    lines, hashes = chain(
        ("KEY_ENROLLED", KEY_A, None, PIN),
        ("KEY_ENROLLED", KEY_B, None, PIN),
        ("NONCE_SPENT", KEY_A, NONCE, PIN),
        ("NONCE_SPENT", KEY_B, NONCE, PIN),
    )
    result = inspect(lines, hashes, kid=KEY_B)
    assert result["reason_code"] == "DUPLICATE_NONCE_SPEND"
    deny(result)


def test_honest_but_stale_floor_does_not_detect_later_revocation_omission():
    lines, hashes = chain(
        ("KEY_ENROLLED", KEY_A, None, PIN),
        ("KEY_REVOKED", KEY_A, None, PIN),
    )
    assert inspect(lines, hashes)["reason_code"] == "DECLARED_KEY_REVOKED"
    # The 'independent' floor only covers enrollment (seq 1). A caller
    # truncating later history and re-pinning its head still passes.
    stale_floor = inspect(lines[:1], hashes[:1], floor_seq=1, floor_hash=hashes[0])
    assert stale_floor["inspection"] == "REVIEWABLE_ONLY"
    assert stale_floor["reason_code"] == "DECLARED_HISTORY_CONSISTENT"
    deny(stale_floor)
    # Only a floor retained at the revocation event prevents this particular rollback.
    fresh_floor = inspect(lines[:1], hashes[:1], floor_seq=2, floor_hash=hashes[1])
    assert fresh_floor["reason_code"] == "HISTORY_BELOW_DECLARED_FLOOR"
    deny(fresh_floor)


def test_floor_with_hash_detects_equal_length_fork_at_floor():
    first, sha_a = chain(
        ("KEY_ENROLLED", KEY_A, None, PIN),
        ("KEY_REVOKED", KEY_A, None, PIN),
    )
    altered, sha_b = chain(
        ("KEY_ENROLLED", KEY_A, None, PIN),
        ("NONCE_SPENT", KEY_A, NONCE, PIN),
    )
    assert sha_a[1] != sha_b[1]
    r = inspect(altered, sha_b, floor_seq=2, floor_hash=sha_a[1])
    assert r["reason_code"] == "EXTERNAL_FLOOR_MISMATCH"
    deny(r)


def test_revoked_key_id_cannot_be_reenrolled_under_a_new_policy():
    lines, hashes = chain(
        ("KEY_ENROLLED", KEY_A, None, PIN),
        ("KEY_REVOKED", KEY_A, None, PIN),
        ("KEY_ENROLLED", KEY_A, None, "b" * 64),
    )
    r = inspect(lines, hashes)
    assert r["reason_code"] == "DUPLICATE_OR_REVOKED_ENROLLMENT"
    deny(r)
