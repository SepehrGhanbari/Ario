"""Actual Ario bounded-agent invocation and #290 offline comparator."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

import ario_self_audit_adapter as adapter
from test_pr_claim_audit import CLAIM, body, evidence


def prepare(tmp_path: Path, *, claim_text=None, evidence_data=None):
    claim = tmp_path / "claim.md"
    snapshot = tmp_path / "evidence.json"
    claim.write_text(body() if claim_text is None else claim_text, encoding="utf-8")
    snapshot.write_text(
        json.dumps(evidence() if evidence_data is None else evidence_data),
        encoding="utf-8",
    )
    return claim, snapshot, tmp_path / "audit-events.jsonl"


def invoke(tmp_path: Path, task_id="SELF-AUDIT-001"):
    return adapter.inspect_with_agent(
        workspace=tmp_path, ledger=tmp_path / "audit-events.jsonl",
        task_id=task_id, pr_body="claim.md", evidence="evidence.json",
    )


def test_engine_fingerprints_and_journals_without_modifying_sources(tmp_path):
    claim, snapshot, journal = prepare(tmp_path)
    before = claim.read_bytes(), snapshot.read_bytes()
    result = invoke(tmp_path)
    assert result["status"] == "UNKNOWN"
    assert result["claim_correspondence"] == "MATCH"
    assert result["agent_task_status"] == "COMPLETED"
    assert result["execution_attestation"] == "NOT_ESTABLISHED"
    assert result["evidence_admission"] == "NOT_EVALUATED"
    assert result["memory_updated"] is False and result["trust_activated"] is False
    assert (claim.read_bytes(), snapshot.read_bytes()) == before
    events = [json.loads(line) for line in journal.read_text().splitlines()]
    assert [entry["event"] for entry in events] == [
        "TASK_STARTED", "STEP_OBSERVED", "STEP_OBSERVED", "TASK_FINISHED"
    ]
    assert [entry["tool"] for entry in events[1:3]] == [
        "file_fingerprint", "file_fingerprint"
    ]
    assert result["input_fingerprints"]["claim_sha256"] == events[1]["observation"]["sha256"]
    assert result["input_fingerprints"]["evidence_sha256"] == events[2]["observation"]["sha256"]


def test_changed_count_is_diagnostic_mismatch_not_truth(tmp_path):
    prepare(tmp_path, claim_text=body({**CLAIM, "passed": 1141}))
    out = invoke(tmp_path)
    assert out["claim_correspondence"] == "MISMATCH"
    assert out["differences"] == ["passed"]
    assert out["status"] == "UNKNOWN"


def test_insufficient_evidence_is_unknown(tmp_path):
    prepare(tmp_path, evidence_data={})
    out = invoke(tmp_path)
    assert out["status"] == out["claim_correspondence"] == "UNKNOWN"


def test_duplicate_json_member_is_unknown(tmp_path):
    _, snapshot, _ = prepare(tmp_path)
    snapshot.write_text('{"run":{},"run":{}}', encoding="utf-8")
    out = invoke(tmp_path)
    assert out["claim_correspondence"] == "UNKNOWN"
    assert out["reason"] == "INVALID_LOCAL_SNAPSHOT"


def test_post_fingerprint_mutation_cannot_be_a_match(tmp_path):
    _, snapshot, _ = prepare(tmp_path)
    real_run = adapter.run_task

    def change_after_agent(*args, **kwargs):
        observed = real_run(*args, **kwargs)
        snapshot.write_text("{}", encoding="utf-8")
        return observed

    with patch.object(adapter, "run_task", side_effect=change_after_agent):
        out = invoke(tmp_path)
    assert out["status"] == out["claim_correspondence"] == "UNKNOWN"
    assert out["reason"] == "INPUT_CHANGED_AFTER_AGENT_FINGERPRINT"
    assert "input_fingerprints" not in out


@pytest.mark.parametrize(("claim_path", "evidence_path"), [
    ("../claim.md", "evidence.json"),
    ("/tmp/outside", "evidence.json"),
    ("claim.md", "claim.md"),
])
def test_bad_paths_refused_before_journal(tmp_path, claim_path, evidence_path):
    prepare(tmp_path)
    out = adapter.inspect_with_agent(
        workspace=tmp_path, ledger=tmp_path / "audit-events.jsonl",
        task_id="SAFE-ID", pr_body=claim_path, evidence=evidence_path,
    )
    assert out["status"] == out["claim_correspondence"] == "UNKNOWN"
    assert out["agent_task_status"] == "NOT_RUN"
    assert not (tmp_path / "audit-events.jsonl").exists()


def test_missing_evidence_stops_agent(tmp_path):
    _, snapshot, journal = prepare(tmp_path)
    snapshot.unlink()
    out = invoke(tmp_path)
    assert out["claim_correspondence"] == "UNKNOWN"
    assert out["agent_task_status"] == "STOPPED"
    assert journal.is_file()


def test_duplicate_task_id_does_not_append_new_history(tmp_path):
    prepare(tmp_path)
    first = invoke(tmp_path)
    journal = tmp_path / "audit-events.jsonl"
    prior = journal.read_bytes()
    second = invoke(tmp_path)
    assert first["claim_correspondence"] == "MATCH"
    assert second["claim_correspondence"] == "UNKNOWN"
    assert journal.read_bytes() == prior


def test_cli_invokes_real_agent_and_offline_auditor(tmp_path):
    prepare(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-B", str(Path(adapter.__file__)),
         "--workspace", str(tmp_path),
         "--ledger", str(tmp_path / "audit-events.jsonl"),
         "--task-id", "CLI-001", "--pr-body", "claim.md",
         "--evidence", "evidence.json"],
        capture_output=True, encoding="utf-8", text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["claim_correspondence"] == "MATCH"
    assert out["agent_task_status"] == "COMPLETED"
    assert out["status"] == "UNKNOWN"
