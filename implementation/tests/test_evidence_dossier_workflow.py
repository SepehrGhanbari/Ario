"""Combined CLI with a real Agent ledger and the original EA/ARP contracts."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

import evidence_dossier_workflow as combined
from ario_agent import run_task
from candidate_dossier_builder import build_candidate_dossier
from admission_review_evaluator import evaluate_review_request
from ledger_observation_adapter import observe_ledger

CLI = Path(__file__).resolve().parents[1] / "ario_cli.py"


def prepare(root):
    ledger = root / "events.jsonl"
    run_task({"task_id": "T", "goal": "inspect", "actions": [
        {"step_id": "read", "tool": "inspect_directory", "path": "."}]}, root, ledger)
    manifest = observe_ledger(ledger)
    assert manifest["status"] == "OBSERVED"
    line = next(o["line"] for o in manifest["observations"] if o["event"] == "TASK_FINISHED")
    proposal = {"line": line, "claim_id": "c1", "claim_scope": "ledger reports completion",
                "proposed_support_relation": "Only reported task status"}
    review = {"policy_version": "ARP-0.1", "candidate_digest": "UNKNOWN",
              "reviewer_id": "declared-reviewer", "reviewer_role": "declared",
              "authorization_reference": None, "requested_claim_id": "c1",
              "requested_claim_scope": "ledger reports completion",
              "requested_support_relation": "Only reported task status",
              "corroboration_refs": [], "review_rule_ids": ["ARP-0.1"],
              "limitations": "No independent authority", "recorded_at": "declared",
              "decision": "NOT_EVALUATED"}
    request = {"proposal": proposal, "review": review}
    mp, rp = root / "manifest.json", root / "request.json"
    mp.write_text(json.dumps(manifest), encoding="utf-8")
    rp.write_text(json.dumps(request), encoding="utf-8")
    return (mp, ledger, rp), manifest, request


def call(paths, *extra):
    return subprocess.run([sys.executable, "-B", str(CLI), "--evidence-dossier",
                           *map(str, paths), *extra], cwd=CLI.parent,
                          capture_output=True, text=True, check=False)


def test_combined_cli_reuses_real_dossier_and_review_without_writes(tmp_path):
    paths, manifest, request = prepare(tmp_path)
    before = [p.read_bytes() for p in paths]
    child = call(paths)
    assert child.returncode == 1, child.stderr
    report = json.loads(child.stdout)
    expected = build_candidate_dossier(manifest, paths[1], **request["proposal"])
    assert report["candidate"] == expected
    assert report["review"] == evaluate_review_request(
        {**request["review"], "candidate": expected}, manifest, paths[1])
    assert report["status"] == "SCREENED"
    assert report["review"]["status"] == "UNKNOWN"
    assert report["candidate"]["admission_decision"] == report["admission_decision"] == "NOT_EVALUATED"
    assert report["input_sha256"] == {
        "manifest": hashlib.sha256(before[0]).hexdigest(),
        "request": hashlib.sha256(before[2]).hexdigest()}
    assert report["candidate"]["source_ledger"]["sha256"] == hashlib.sha256(before[1]).hexdigest()
    assert report["claim_truth"] == report["source_independence"] == "UNKNOWN"
    assert report["independent_admission_authority"] == "NONE"
    assert [p.read_bytes() for p in paths] == before


@pytest.mark.parametrize("change", ["claim_scope", "forbidden_decision", "injected_candidate"])
def test_separate_proposal_and_review_boundaries(tmp_path, change):
    paths, _, request = prepare(tmp_path)
    if change == "claim_scope":
        request["review"]["requested_claim_scope"] = "objective achieved"
    elif change == "forbidden_decision":
        request["review"]["decision"] = "ADMITTED"
    else:
        request["review"]["candidate"] = {"status": "ADMITTED"}
    paths[2].write_text(json.dumps(request), encoding="utf-8")
    child = call(paths)
    assert child.returncode == 2, child.stderr
    report = json.loads(child.stdout)
    assert report["status"] == "REJECTED"
    assert report["admission_decision"] == "NOT_EVALUATED"
    if change != "injected_candidate":
        assert report["review"]["status"] == "REJECTED"
    else:
        assert report["candidate"] is None


def test_changed_ledger_before_build_prevents_review(tmp_path):
    paths, _, _ = prepare(tmp_path)
    paths[1].write_bytes(paths[1].read_bytes().replace(b"COMPLETED", b"OTHER"))
    report = combined.inspect_dossier_files(*paths)
    assert report["status"] == "REJECTED"
    assert report["review"] is None


def test_changed_ledger_between_build_and_review_is_not_hidden(tmp_path, monkeypatch):
    paths, _, _ = prepare(tmp_path)
    real = combined.evaluate_review_request

    def change_then_review(request, manifest, ledger):
        path = Path(ledger)
        path.write_bytes(path.read_bytes().replace(b"COMPLETED", b"OTHER"))
        return real(request, manifest, ledger)

    monkeypatch.setattr(combined, "evaluate_review_request", change_then_review)
    report = combined.inspect_dossier_files(*paths)
    assert report["candidate"]["status"] == "CANDIDATE"
    assert report["review"]["status"] == report["status"] == "REJECTED"
    assert report["admission_decision"] == "NOT_EVALUATED"


@pytest.mark.parametrize("kind", ["duplicate", "oversize", "missing"])
def test_bad_request_is_unknown(tmp_path, kind):
    paths, _, _ = prepare(tmp_path)
    if kind == "duplicate":
        paths[2].write_bytes(b'{"proposal":{},"proposal":{}}')
    elif kind == "oversize":
        with paths[2].open("wb") as stream:
            stream.truncate(4 * 1024 * 1024 + 1)
    else:
        paths[2].unlink()
    report = combined.inspect_dossier_files(*paths)
    assert report["status"] == "UNKNOWN"
    assert report["candidate"] is None and report["review"] is None


def test_combined_cli_rejects_m0_ledger_option(tmp_path):
    paths, _, _ = prepare(tmp_path)
    dest = tmp_path / "output.jsonl"
    child = call(paths, "--ledger", str(dest))
    assert child.returncode == 2
    assert not dest.exists()
