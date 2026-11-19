"""Byte-preservation checks: the original public OTS file must never be CRLF-normalized."""
from __future__ import annotations

import hashlib

import pytest

from research.r04_ots.verify_r04 import FILE_SHA256, ArchiveError, HERE, audit_archive


def test_r04_git_checkout_keeps_exact_original_lf_bytes():
    original = (HERE / "synthetic_checkpoint_r04.json").read_bytes()
    assert len(original) == 613
    assert original.endswith(b"\n")
    assert b"\r\n" not in original
    assert hashlib.sha256(original).hexdigest() == FILE_SHA256


def test_r04_crlf_transformation_is_rejected_not_silently_normalized(tmp_path):
    original = (HERE / "synthetic_checkpoint_r04.json").read_bytes()
    transformed = original.replace(b"\n", b"\r\n")
    assert transformed != original
    candidate = tmp_path / "transformed.json"
    candidate.write_bytes(transformed)
    with pytest.raises(ArchiveError, match="checkpoint checksum mismatch"):
        audit_archive(candidate, HERE / "synthetic_checkpoint_r04.ots.b64")
