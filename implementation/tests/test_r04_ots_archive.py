"""R04 OpenTimestamps archival and monotonic-floor negative controls.

Tests prove exact copied bytes and pure floor comparisons, not OTS Bitcoin
finality, authenticated clocks, independently operated custody or live admission.
"""
from __future__ import annotations

import base64
import subprocess
import sys

import pytest

from research.r04_ots.verify_r04 import (
    FILE_SHA256, RECEIPT_SHA256, ArchiveError, HERE,
    audit_archive, compare_external_floor, official_ots_check,
)

CHECKPOINT = HERE / "synthetic_checkpoint_r04.json"
RECEIPT = HERE / "synthetic_checkpoint_r04.ots.b64"
HEX_6 = "519b9b0b20b06256ed77b1a24059ea8ec3f244d7fa1ad8f545c08d6d6ab5c780"
HEX_4 = "f" * 64
FLOOR6 = {"scope": "LAB-E101", "last_seq": 6, "history_sha256": HEX_6}
PREFIX4 = {"scope": "LAB-E101", "last_seq": 4, "history_sha256": HEX_4}


def test_archived_real_pending_receipt_exact_bytes():
    report = audit_archive(CHECKPOINT, RECEIPT)
    assert report["status"] == "EXACT_ARCHIVED_BYTES_MATCHED"
    assert report["checkpoint_sha256"] == FILE_SHA256
    assert report["receipt_sha256"] == RECEIPT_SHA256
    assert report["receipt_bytes"] == 549
    assert report["checkpoint_bytes"] == 613
    assert report["bitcoin_inclusion"] == "NOT_DETERMINED_BY_OFFLINE_CHECK"
    assert report["real_memory_admission"] is False


def test_truncated_checkpoint_rejected(tmp_path):
    p = tmp_path / "partial.json"
    p.write_bytes(CHECKPOINT.read_bytes()[:-12])
    with pytest.raises(ArchiveError, match="checksum"):
        audit_archive(p, RECEIPT)


def test_altered_checkpoint_rejected(tmp_path):
    p = tmp_path / "changed.json"
    p.write_bytes(CHECKPOINT.read_bytes().replace(b"RESEARCH_ONLY", b"RESEARCH_HOLD"))
    with pytest.raises(ArchiveError, match="checksum"):
        audit_archive(p, RECEIPT)


def test_altered_receipt_rejected(tmp_path):
    p = tmp_path / "fake.ots.b64"
    old = base64.b64decode(RECEIPT.read_bytes())
    p.write_bytes(base64.b64encode(old[:-1] + bytes([old[-1] ^ 1])))
    with pytest.raises(ArchiveError, match="receipt checksum"):
        audit_archive(CHECKPOINT, p)


def test_missing_or_noncanonical_receipt_rejected(tmp_path):
    p = tmp_path / "fake.ots.b64"
    p.write_text("X!X", encoding="ascii")
    with pytest.raises(ArchiveError, match="encoding"):
        audit_archive(CHECKPOINT, p)


def test_without_external_floor_is_hold():
    assert compare_external_floor(PREFIX4, None) == "HOLD_MISSING_EXTERNAL_FLOOR"


def test_supplied_external_floor_detects_rollback():
    assert compare_external_floor(PREFIX4, FLOOR6) == "ROLLBACK_REJECTED_RELATIVE_TO_SUPPLIED_FLOOR"


def test_colluding_replacement_of_data_and_floor_is_not_detected():
    assert compare_external_floor(PREFIX4, PREFIX4) == "SAME_CHECKPOINT_NOT_FRESHNESS_PROOF"


def test_equal_sequence_conflicting_hash_is_hold():
    assert compare_external_floor({**FLOOR6, "history_sha256": HEX_4}, FLOOR6) == "HOLD_SPLIT_VIEW"


def test_future_sequence_without_consistency_proof_is_hold():
    assert compare_external_floor({**FLOOR6, "last_seq": 7}, FLOOR6) == "HOLD_UNVERIFIED_EXTENSION"


def test_malformed_floor_and_candidate_are_not_promoted():
    assert compare_external_floor({**FLOOR6, "last_seq": True}, FLOOR6) == "REJECT_INVALID_CANDIDATE"
    assert compare_external_floor(FLOOR6, {**FLOOR6, "last_seq": False}) == "HOLD_INVALID_EXTERNAL_FLOOR"
    assert compare_external_floor({**FLOOR6, "scope": "other"}, FLOOR6) == "REJECT_INVALID_CANDIDATE"


def test_source_claims_cannot_create_independent_custody():
    claimed = {**PREFIX4, "independent": True, "signatures": ["self-claimed"]}
    retained = {**PREFIX4, "independent": True, "signatures": ["self-claimed"]}
    assert compare_external_floor(claimed, retained) == "SAME_CHECKPOINT_NOT_FRESHNESS_PROOF"


def test_official_cli_missing_is_hold():
    receipt = base64.b64decode(RECEIPT.read_bytes())
    result = official_ots_check(CHECKPOINT, receipt, "definitely-nonexistent-ots-executable-r04")
    assert result["status"] == "HOLD_VERIFIER_UNAVAILABLE"


def test_invalid_verifier_executable_does_not_claim_finality():
    receipt = base64.b64decode(RECEIPT.read_bytes())
    result = official_ots_check(CHECKPOINT, receipt, sys.executable)
    assert result["status"] == "OTS_CLI_DID_NOT_VERIFY"


def test_cli_archive_default_reports_only_bytes():
    cmd = [sys.executable, str(HERE / "verify_r04.py")]
    process = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    assert process.returncode == 0
    assert '"bitcoin_inclusion": "NOT_DETERMINED_BY_OFFLINE_CHECK"' in process.stdout
    assert '"real_memory_admission": false' in process.stdout
