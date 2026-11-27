"""Exercise #430 through Agent/Workflow with existing laboratory fixtures."""
from dataclasses import replace
import hashlib
import json

import pytest

from ario_agent import AgentRequestError, parse_task, run_task
from ario_workflow import run_workflow
from research.rere01.assessment_history_v1 import encode_history, append_history
from tests.test_rere01_v03_guard import _fixture


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def prepare(root):
    policy, rows, _ = _fixture()
    prior = encode_history(rows[:4], policy)
    current = append_history(prior, expected_sha256=sha(prior), additions=rows[4:6])
    (root / "before.json").write_bytes(prior)
    (root / "after.json").write_bytes(current)
    action = {"step_id": "revision", "tool": "inspect_rere_revision",
              "prior_path": "before.json", "prior_sha256": sha(prior),
              "path": "after.json", "expected_sha256": sha(current)}
    return action, prior, current


def task(action, name="REVISION"):
    return {"task_id": name, "goal": "Inspect synthetic revision", "actions": [action]}


def test_agent_withdraws_warrant_and_preserves_history(tmp_path):
    action, prior, current = prepare(tmp_path)
    ledger = tmp_path / "events.jsonl"
    result = run_task(task(action), tmp_path, ledger)
    obs = result["steps"][0]["observation"]
    assert result["status"] == "COMPLETED"
    assert obs["revision_status"] == "VERIFIED_EXTENSION"
    assert obs["prior_event_outcome"] == "CONDITIONALLY_REFUTED_IN_LAB"
    assert obs["event_outcome"] == "UNKNOWN"
    assert obs["withdrawn_assessment_count"] == 1
    assert obs["appended_record_count"] == 2
    assert obs["prior_sha256"] == sha(prior) and obs["current_sha256"] == sha(current)
    assert obs["claim_truth"] == obs["freshness"] == obs["source_authentication"] == "UNKNOWN"
    assert obs["evidence_authorized_for_real_memory"] is False
    assert (tmp_path / "before.json").read_bytes() == prior
    assert (tmp_path / "after.json").read_bytes() == current
    records = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert next(row for row in records if row["event"] == "STEP_OBSERVED")["observation"] == obs


def test_workflow_uses_revision_as_read_only_diagnostic(tmp_path):
    action, _, _ = prepare(tmp_path)
    workflow = {"workflow_id": "W-REVISION", "goal": "Inspect after failure",
                "stages": [
                    {"stage_id": "fail", "task": task({"step_id": "fail", "tool": "verify_text",
                        "path": "before.json", "expected_text": "wrong"}, "FAIL")},
                    {"stage_id": "inspect", "when": {"stage_id": "fail", "status": "STOPPED"},
                     "task": task(action)},
                ]}
    result = run_workflow(workflow, tmp_path, tmp_path / "events.jsonl")
    assert result["status"] == "STOPPED"
    assert [s["status"] for s in result["stages"]] == ["STOPPED", "COMPLETED"]
    assert result["stages"][1]["task_result"]["steps"][0]["observation"]["event_outcome"] == "UNKNOWN"


def test_replay_is_not_new_revision(tmp_path):
    action, prior, _ = prepare(tmp_path)
    (tmp_path / "after.json").write_bytes(prior)
    action["expected_sha256"] = sha(prior)
    obs = run_task(task(action), tmp_path, tmp_path / "events.jsonl")["steps"][0]["observation"]
    assert obs["revision_status"] == "EXACT_REPLAY"
    assert obs["appended_record_count"] == obs["withdrawn_assessment_count"] == 0


@pytest.mark.parametrize("change", ["rollback", "prefix", "policy", "bad_pin"])
def test_invalid_extension_stops_even_with_self_recomputed_pin(tmp_path, change):
    action, prior, current = prepare(tmp_path)
    policy, rows, _ = _fixture()
    if change == "rollback":
        (tmp_path / "before.json").write_bytes(current)
        action["prior_sha256"] = sha(current)
        candidate = prior
    elif change == "prefix":
        candidate = encode_history((replace(rows[0], declared_receipt="altered"), *rows[1:6]), policy)
    elif change == "policy":
        candidate = encode_history(rows[:6], replace(policy, pinned_roots=policy.pinned_roots + (("A", "root-A"),)))
    else:
        candidate = prior
    (tmp_path / "after.json").write_bytes(candidate)
    if change != "bad_pin":
        action["expected_sha256"] = sha(candidate)
    result = run_task(task(action), tmp_path, tmp_path / "events.jsonl")
    assert result["status"] == "STOPPED"
    assert result["steps"][0]["observation"]["ok"] is False


def test_prior_fields_and_workspace_path_are_preflighted(tmp_path):
    action, _, _ = prepare(tmp_path)
    with pytest.raises(AgentRequestError):
        parse_task(task({**action, "prior_sha256": "bad"}))
    with pytest.raises(AgentRequestError):
        parse_task(task({"step_id": "read", "tool": "read_text", "path": "before.json", "prior_path": "after.json"}))
    ledger = tmp_path / "events.jsonl"
    with pytest.raises(AgentRequestError):
        run_task(task({**action, "prior_path": "../outside.json"}), tmp_path, ledger)
    assert not ledger.exists()
