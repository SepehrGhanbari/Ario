"""W44 research-only adversarial fixed-pin checks; no real keys or Ario ledger."""
from __future__ import annotations

from dataclasses import replace
import hashlib
import mmap
import os
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from research.w44_external_pin_probe import (
    MAX_W44_BYTES, SignedPin, VerifierAnchor, checkpoint_hash,
    pin_payload, verify_pinned_file,
)

ARTIFACT = "w44-public-synthetic-jsonl"
OLD = (b'{"event":"TASK_STARTED","timestamp":"2026-11-21T00:00:00Z",'
       b'"task_id":"w44","status":"AAAA"}\n'
       b'{"event":"TASK_STARTED","timestamp":"2026-11-21T00:00:00Z",'
       b'"task_id":"w44","status":"BBBB"}\n')
NEW = OLD.replace(b'"AAAA"', b'"CCCC"').replace(b'"BBBB"', b'"DDDD"')
assert len(NEW) == len(OLD)


def _key_and_anchor(data=OLD, seq=7, artifact=ARTIFACT, signer=None):
    signer = signer or Ed25519PrivateKey.generate()  # synthetic, ephemeral only
    digest = hashlib.sha256(data).hexdigest()
    msg = pin_payload(artifact, seq, len(data), digest)
    pin = SignedPin(artifact, seq, len(data), digest, signer.sign(msg))
    pub = signer.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    anchor = VerifierAnchor(artifact, seq, checkpoint_hash(pin), pub)
    return signer, pin, anchor


def _target(tmp_path, value=OLD):
    path = tmp_path / "synthetic.jsonl"
    path.write_bytes(value)
    return path


def _check(result, expected_status, expected_reason):
    assert result["status"] == expected_status
    assert result["reason"] == expected_reason
    assert result["may_use"] is False
    assert result["historical_event_truth"] == "UNKNOWN"
    assert result["custody_independence"] == "NOT_ESTABLISHED"
    assert result["evidence_admission"] == "NOT_EVALUATED"


def test_valid_byte_match_is_only_a_non_authorizing_observation(tmp_path):
    path = _target(tmp_path)
    _, pin, anchor = _key_and_anchor()
    _check(verify_pinned_file(path, pin=pin, anchor=anchor),
           "PIN_MATCH_ONLY", "EXACT_BYTES_MATCH_VERIFIER_ANCHOR")


def test_valid_jsonl_content_mutation_rejected_even_with_original_inode(tmp_path):
    path = _target(tmp_path)
    _, pin, anchor = _key_and_anchor()
    inode = path.stat().st_ino
    with path.open("r+b") as stream:
        stream.write(NEW)
    assert path.stat().st_ino == inode
    _check(verify_pinned_file(path, pin=pin, anchor=anchor),
           "UNKNOWN", "INPUT_DIGEST_MISMATCH")


def test_actor_self_signed_pin_does_not_override_separately_pinned_floor(tmp_path):
    path = _target(tmp_path, NEW)
    _, _, verifier_anchor = _key_and_anchor()
    _, attacker_pin, _ = _key_and_anchor(NEW)
    _check(verify_pinned_file(path, pin=attacker_pin, anchor=verifier_anchor),
           "UNKNOWN", "CHECKPOINT_NOT_AT_VERIFIER_FLOOR")


def test_forged_signature_with_matching_digest_and_floor_rejected(tmp_path):
    path = _target(tmp_path)
    _, valid_pin, anchor = _key_and_anchor()
    adversary = Ed25519PrivateKey.generate()
    payload = pin_payload(valid_pin.artifact_id, valid_pin.sequence,
                          valid_pin.byte_length, valid_pin.sha256)
    forged_pin = replace(valid_pin, signature=adversary.sign(payload))
    _check(verify_pinned_file(path, pin=forged_pin, anchor=anchor),
           "UNKNOWN", "CHECKPOINT_SIGNATURE_UNTRUSTED")


def test_stale_authorized_checkpoint_not_accepted_when_verifier_floor_advanced(tmp_path):
    path = _target(tmp_path, OLD)
    signer = Ed25519PrivateKey.generate()
    _, old_pin, _ = _key_and_anchor(OLD, seq=6, signer=signer)
    _, _, verifier_floor = _key_and_anchor(NEW, seq=7, signer=signer)
    _check(verify_pinned_file(path, pin=old_pin, anchor=verifier_floor),
           "UNKNOWN", "CHECKPOINT_NOT_AT_VERIFIER_FLOOR")


def test_same_sequence_equivocation_blocked_by_externally_retained_hash(tmp_path):
    signer = Ed25519PrivateKey.generate()
    _, _, floor = _key_and_anchor(OLD, seq=7, signer=signer)
    _, conflicting, _ = _key_and_anchor(NEW, seq=7, signer=signer)
    _check(verify_pinned_file(_target(tmp_path, NEW), pin=conflicting, anchor=floor),
           "UNKNOWN", "CHECKPOINT_NOT_AT_VERIFIER_FLOOR")


def test_unattested_future_sequence_is_not_auto_advanced(tmp_path):
    signer = Ed25519PrivateKey.generate()
    _, _, floor = _key_and_anchor(OLD, seq=7, signer=signer)
    _, future_pin, _ = _key_and_anchor(NEW, seq=8, signer=signer)
    _check(verify_pinned_file(_target(tmp_path, NEW), pin=future_pin, anchor=floor),
           "UNKNOWN", "CHECKPOINT_NOT_AT_VERIFIER_FLOOR")


def test_missing_floor_fails_closed(tmp_path):
    _, pin, _ = _key_and_anchor()
    _check(verify_pinned_file(_target(tmp_path), pin=pin, anchor=None),
           "UNKNOWN", "VERIFIER_ANCHOR_REQUIRED")


def test_missing_signed_pin_fails_closed(tmp_path):
    _, _, anchor = _key_and_anchor()
    _check(verify_pinned_file(_target(tmp_path), pin=None, anchor=anchor),
           "UNKNOWN", "SIGNED_PIN_REQUIRED")


def test_artifact_binding_mismatch_fails_closed_before_read(tmp_path):
    _, pin, anchor = _key_and_anchor()
    wrong = replace(anchor, artifact_id="other-artifact")
    _check(verify_pinned_file(_target(tmp_path), pin=pin, anchor=wrong),
           "UNKNOWN", "ARTIFACT_BINDING_MISMATCH")


def test_truncated_and_overlarge_read_images_fail_closed(tmp_path):
    path = _target(tmp_path)
    _, pin, anchor = _key_and_anchor()
    for data in (OLD[:10], OLD + b"x"):
        with patch("research.w44_external_pin_probe.read_bounded_regular", return_value=data):
            _check(verify_pinned_file(path, pin=pin, anchor=anchor),
                   "UNKNOWN", "INPUT_LENGTH_MISMATCH")


def test_false_reader_bytes_with_matching_size_fail_closed(tmp_path):
    path = _target(tmp_path)
    _, pin, anchor = _key_and_anchor()
    with patch("research.w44_external_pin_probe.read_bounded_regular", return_value=NEW):
        _check(verify_pinned_file(path, pin=pin, anchor=anchor),
               "UNKNOWN", "INPUT_DIGEST_MISMATCH")


def test_malformed_pin_and_anchor_fail_closed(tmp_path):
    path = _target(tmp_path)
    _, pin, anchor = _key_and_anchor()
    for invalid in (replace(pin, byte_length=MAX_W44_BYTES + 1),
                    replace(pin, sequence=True),
                    replace(pin, sha256="0"*63),
                    replace(pin, artifact_id="non-ascii-☃")):
        _check(verify_pinned_file(path, pin=invalid, anchor=anchor),
               "UNKNOWN", "SIGNED_PIN_MALFORMED")
    for invalid in (replace(anchor, public_key_bytes=b"\0"),
                    replace(anchor, checkpoint_sha256="zz"*32)):
        _check(verify_pinned_file(path, pin=pin, anchor=invalid),
               "UNKNOWN", "VERIFIER_ANCHOR_MALFORMED")


def test_entire_anchor_control_is_not_independence_and_can_falsely_pin(tmp_path):
    """If the actor owns both content and trust root, cryptography cannot help."""
    path = _target(tmp_path, NEW)
    _, self_pin, self_anchor = _key_and_anchor(NEW)
    _check(verify_pinned_file(path, pin=self_pin, anchor=self_anchor),
           "PIN_MATCH_ONLY", "EXACT_BYTES_MATCH_VERIFIER_ANCHOR")
    # Positive byte agreement is deliberately NOT a custody independence claim.


def test_replaced_file_after_positive_read_is_not_ongoing_immutability(tmp_path):
    path = _target(tmp_path)
    _, pin, anchor = _key_and_anchor()
    result = verify_pinned_file(path, pin=pin, anchor=anchor)
    path.write_bytes(NEW)
    _check(result, "PIN_MATCH_ONLY", "EXACT_BYTES_MATCH_VERIFIER_ANCHOR")
    _check(verify_pinned_file(path, pin=pin, anchor=anchor),
           "UNKNOWN", "INPUT_DIGEST_MISMATCH")


@pytest.mark.skipif(os.name != "posix", reason="POSIX mapped write/held descriptor injection")
def test_w43_real_two_read_mmap_aba_rejected_with_independent_pin(tmp_path):
    """Replay W43's two real os.read calls under the fixed verifier anchor."""
    path = _target(tmp_path)
    _, pin, anchor = _key_and_anchor(OLD)
    first_line = OLD.splitlines(keepends=True)[0]
    second_old = OLD[len(first_line):]
    second_new = NEW[len(first_line):]
    mixed = first_line + second_new
    assert mixed != OLD and len(mixed) == len(OLD)
    fdopen = os.fdopen
    inode = path.stat().st_ino
    marks = []

    with path.open("r+b") as writer:
        with mmap.mmap(writer.fileno(), len(OLD), access=mmap.ACCESS_WRITE) as view:
            view[len(first_line):] = second_new
            view[len(first_line):] = second_old  # prime dirty mapped page

            class ReadInjector:
                def __init__(self, stream):
                    self.stream = stream

                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    return self.stream.__exit__(*args)

                def __getattr__(self, name):
                    return getattr(self.stream, name)

                def read(self, count=-1):
                    if not marks:
                        prefix = os.read(self.stream.fileno(), len(first_line))
                        assert prefix == first_line
                        view[len(first_line):] = second_new
                        marks.append("NATIVE_READ_INTERLEAVED_MAPPED_WRITE")
                        suffix = os.read(self.stream.fileno(), count-len(prefix))
                        return prefix + suffix
                    data = self.stream.read(count)
                    marks.append("ABA_RESTORED_AFTER_REPEAT_READ")
                    view[len(first_line):] = second_old
                    return data

            def hooked(fd, mode="r", *args, **kwargs):
                stream = fdopen(fd, mode, *args, **kwargs)
                if mode == "rb" and os.fstat(stream.fileno()).st_ino == inode:
                    return ReadInjector(stream)
                return stream

            with patch("os.fdopen", side_effect=hooked):
                outcome = verify_pinned_file(path, pin=pin, anchor=anchor)
            assert path.read_bytes() == OLD
            assert marks, "native read interleaving did not run"
            assert outcome["status"] == "UNKNOWN", outcome
            assert outcome["reason"] in ("INPUT_DIGEST_MISMATCH", "BOUNDED_INPUT_READ_REJECTED")
            assert outcome["may_use"] is False


@pytest.mark.skipif(os.name != "nt", reason="Windows preexisting mapped handle test")
def test_windows_real_preexisting_mmap_view_cannot_be_admitted(tmp_path):
    """W41 may reject at open; pinned verification must not admit changed bytes."""
    path = _target(tmp_path)
    _, pin, anchor = _key_and_anchor(OLD)
    with path.open("r+b") as writer:
        view = mmap.mmap(writer.fileno(), len(OLD), access=mmap.ACCESS_WRITE)
    try:
        view[:] = NEW
        result = verify_pinned_file(path, pin=pin, anchor=anchor)
        assert result["status"] == "UNKNOWN"
        assert result["reason"] in ("BOUNDED_INPUT_READ_REJECTED", "INPUT_DIGEST_MISMATCH")
        assert not result["may_use"]
    finally:
        view[:] = OLD
        view.close()
