"""Real prior execution ledger verification through the bounded runtime."""
import hashlib
import json

import pytest

from ario_agent import AgentRequestError, parse_task, run_task
from ario_workflow import run_workflow
from ledger_observation_adapter import observe_ledger


def task(action, name="VERIFY"):
    return {"task_id": name, "goal": "Check prior ledger", "actions": [action]}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(root):
    prior = root / "prior.jsonl"
    run_task(task({"step_id": "read", "tool": "inspect_directory", "path": "."}, "PRIOR"), root, prior)
    raw = prior.read_bytes()
    manifest = json.dumps(observe_ledger(prior), sort_keys=True).encode("utf-8")
    (root / "manifest.json").write_bytes(manifest)
    action = {"step_id": "verify", "tool": "verify_ledger_manifest",
              "path": "prior.jsonl", "manifest_path": "manifest.json",
              "expected_sha256": sha(manifest)}
    return action, raw, manifest


def test_real_ledger_match_is_recorded_without_modifying_input(tmp_path):
    action, raw, manifest = prepare(tmp_path)
    output = tmp_path / "new.jsonl"
    result = run_task(task(action), tmp_path, output)
    obs = result["steps"][0]["observation"]
    assert result["status"] == "COMPLETED"
    assert obs["ledger_status"] == "OBSERVED" and obs["ledger_sha256"] == sha(raw)
    assert obs["event_count"] == len(raw.splitlines())
    assert obs["claim_truth"] == obs["freshness"] == obs["source_authentication"] == "UNKNOWN"
    assert obs["independent_admission_authority"] == "NONE"
    assert (tmp_path / "prior.jsonl").read_bytes() == raw
    assert (tmp_path / "manifest.json").read_bytes() == manifest
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert next(row for row in rows if row["event"] == "STEP_OBSERVED")["observation"] == obs


@pytest.mark.parametrize("change,status", [("modify","REJECTED"), ("delete","REJECTED"),
    ("partial","UNKNOWN"), ("manifest","REJECTED"), ("duplicate","UNKNOWN")])
def test_changed_or_unreadable_inputs_stop(tmp_path, change, status):
    action, raw, manifest = prepare(tmp_path)
    prior = tmp_path / "prior.jsonl"
    if change == "modify":
        prior.write_bytes(raw.replace(b"PRIOR", b"OTHER"))
    elif change == "delete":
        prior.write_bytes(b"".join(raw.splitlines(keepends=True)[:-1]))
    elif change == "partial":
        prior.write_bytes(raw[:-1])
    elif change == "manifest":
        (tmp_path / "manifest.json").write_bytes(manifest + b" ")
    else:
        forged = b'{"status":"OBSERVED",' + manifest[1:]
        (tmp_path / "manifest.json").write_bytes(forged)
        action["expected_sha256"] = sha(forged)
    result = run_task(task(action), tmp_path, tmp_path / "new.jsonl")
    assert result["status"] == "STOPPED"
    assert result["steps"][0]["observation"]["ledger_status"] == status


def test_active_output_ledger_rejected_before_write(tmp_path):
    action, raw, _ = prepare(tmp_path)
    prior = tmp_path / "prior.jsonl"
    with pytest.raises(AgentRequestError):
        run_task(task(action), tmp_path, prior)
    assert prior.read_bytes() == raw
    workflow = {"workflow_id": "W", "goal": "verify", "stages": [{"stage_id": "v", "task": task(action)}]}
    with pytest.raises(AgentRequestError):
        run_workflow(workflow, tmp_path, prior)
    assert prior.read_bytes() == raw


def test_manifest_shape_and_path_refused(tmp_path):
    action, _, _ = prepare(tmp_path)
    with pytest.raises(AgentRequestError):
        parse_task(task({**action, "expected_sha256": "bad"}))
    with pytest.raises(AgentRequestError):
        parse_task(task({"step_id": "r", "tool": "read_text", "path": "prior.jsonl", "manifest_path": "manifest.json"}))
    output = tmp_path / "new.jsonl"
    with pytest.raises(AgentRequestError):
        run_task(task({**action, "manifest_path": "../outside.json"}), tmp_path, output)
    assert not output.exists()


def test_workflow_can_use_verification_as_read_only_diagnostic(tmp_path):
    action, _, _ = prepare(tmp_path)
    workflow = {"workflow_id": "W", "goal": "verify after failure", "stages": [
        {"stage_id": "fail", "task": task({"step_id": "fail", "tool": "verify_text",
            "path": "manifest.json", "expected_text": "wrong"}, "FAIL")},
        {"stage_id": "verify", "when": {"stage_id": "fail", "status": "STOPPED"}, "task": task(action)},
    ]}
    result = run_workflow(workflow, tmp_path, tmp_path / "new.jsonl")
    assert result["status"] == "STOPPED"
    assert [s["status"] for s in result["stages"]] == ["STOPPED", "COMPLETED"]
    assert result["stages"][1]["task_result"]["steps"][0]["observation"]["ledger_status"] == "OBSERVED"
