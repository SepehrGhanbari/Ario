"""W40: bounded JSONL byte snapshot and deterministic path-race regressions.

Only temporary synthetic JSONL data. No signer, production keys, or network.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from ledger_observation_adapter import MAX_LEDGER_BYTES, observe_ledger
from ledger_audit_bridge import verify_observation_manifest


def line(kind="TASK_STARTED", status="STARTED"):
    return json.dumps({"event": kind, "timestamp": "2026-11-21T00:00:00Z",
                       "task_id": "synthetic", "status": status}).encode() + b"\n"


def test_legitimate_read_has_original_hash_and_no_write(tmp_path):
    p = tmp_path / "events.jsonl"
    raw = line() + line("TASK_FINISHED", "COMPLETED")
    p.write_bytes(raw)
    result = observe_ledger(p)
    assert result["status"] == "OBSERVED"
    assert result["sha256"] == hashlib.sha256(raw).hexdigest()
    assert result["bytes_read"] == len(raw)
    assert result["event_count"] == 2
    assert p.read_bytes() == raw
    assert result["epistemic_limit"].startswith("This manifest describes bytes")


def test_missing_file_and_final_symlink_fail_closed(tmp_path):
    p = tmp_path / "missing.jsonl"
    assert observe_ledger(p)["status"] == "UNKNOWN"
    outside = tmp_path / "outside.jsonl"
    outside.write_bytes(line())
    try:
        p.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink unsupported: {exc!r}")
    result = observe_ledger(p)
    assert result["status"] == "UNKNOWN"
    assert not result["observations"]


@pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor-relative open race injection")
def test_leaf_symlink_substitution_at_open_rejected(tmp_path):
    p = tmp_path / "events.jsonl"
    outside = tmp_path / "outside.jsonl"
    p.write_bytes(line())
    outside.write_bytes(line("TASK_FINISHED", "MALICIOUS_SYNTHETIC"))
    native = os.open
    hits = []

    def swap(name, flags, *args, **kwargs):
        if name == p.name and "dir_fd" in kwargs and not hits:
            hits.append("leaf-swapped")
            p.unlink()
            p.symlink_to(outside)
        return native(name, flags, *args, **kwargs)

    with patch("os.open", side_effect=swap):
        result = observe_ledger(p)
    assert hits == ["leaf-swapped"]
    assert result["status"] == "UNKNOWN"
    assert result["observations"] == []
    assert outside.read_bytes() == line("TASK_FINISHED", "MALICIOUS_SYNTHETIC")


@pytest.mark.skipif(os.name != "posix", reason="POSIX descriptor-relative open race injection")
def test_parent_symlink_substitution_at_open_rejected(tmp_path):
    real_parent = tmp_path / "ledger"
    real_parent.mkdir()
    p = real_parent / "events.jsonl"
    p.write_bytes(line())
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / p.name).write_bytes(line("TASK_FINISHED", "MALICIOUS_SYNTHETIC"))
    native = os.open
    hits = []

    def swap(name, flags, *args, **kwargs):
        if name == "ledger" and "dir_fd" in kwargs and not hits:
            hits.append("parent-swapped")
            real_parent.rename(tmp_path / "ledger-saved")
            real_parent.symlink_to(outside, target_is_directory=True)
        return native(name, flags, *args, **kwargs)

    with patch("os.open", side_effect=swap):
        result = observe_ledger(p)
    assert hits == ["parent-swapped"]
    assert result["status"] == "UNKNOWN"
    assert result["observations"] == []


def test_ledger_cap_still_fail_closed(tmp_path):
    p = tmp_path / "events.jsonl"
    p.write_bytes(line() + b"X" * MAX_LEDGER_BYTES)
    r = observe_ledger(p)
    assert r["status"] == "UNKNOWN"
    assert not r["observations"]


def test_invalid_and_unfinished_jsonl_still_unknown(tmp_path):
    p = tmp_path / "events.jsonl"
    for raw in (b"{bad json}\n", line().rstrip(b"\n"), b""):
        p.write_bytes(raw)
        result = observe_ledger(p)
        assert result["status"] == "UNKNOWN"
        assert not result["observations"]


def test_bridge_rejects_obsolete_manifest_after_write(tmp_path):
    p = tmp_path / "events.jsonl"
    p.write_bytes(line())
    manifest = observe_ledger(p)
    assert manifest["status"] == "OBSERVED"
    p.write_bytes(line("TASK_FINISHED", "COMPLETED"))
    verified = verify_observation_manifest(manifest, p)
    assert verified["status"] == "REJECTED"


def test_acquisition_is_single_bounded_read_not_path_open(tmp_path):
    p = tmp_path / "events.jsonl"
    p.write_bytes(line())
    import ledger_observation_adapter as adapter
    original = adapter.read_bounded_regular
    observed = []

    def once(path, cap):
        observed.append((Path(path), cap))
        return original(path, cap)

    with patch.object(adapter, "read_bounded_regular", side_effect=once):
        with patch.object(Path, "open", side_effect=AssertionError("unsafe second pathname open")):
            r = adapter.observe_ledger(p)
    assert r["status"] == "OBSERVED"
    assert observed == [(p, MAX_LEDGER_BYTES)]
