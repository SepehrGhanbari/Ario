"""Exercise the merged M0 guard through actual bounded execution, not a mock."""
from dataclasses import asdict
import hashlib
import json

import pytest

from ario_agent import AgentRequestError, parse_task, run_task
from ario_cli import execute_request
from ario_workflow import run_workflow
from test_eag_f263_collision import fixture


def request(artifacts):
    return {"audit_id": "INTEGRATION-AUDIT", "rule_versions": ["M0-1.0"],
            "configuration_id": "INTEGRATION", "execution_timestamp": "TEST",
            "artifacts": artifacts}


def prepare(root, payload):
    raw = json.dumps(payload).encode("utf-8")
    (root / "audit.json").write_bytes(raw)
    return {"step_id": "audit", "tool": "audit_m0", "path": "audit.json",
            "expected_sha256": hashlib.sha256(raw).hexdigest()}


def task(action, task_id="AUDIT-TASK"):
    return {"task_id": task_id, "goal": "Structural audit only", "actions": [action]}


@pytest.mark.parametrize("kind,expected", [(None, "PASS"), ("AUDIT_RESULT", "FAIL"), ("empty", "UNKNOWN")])
def test_agent_records_existing_m0_result(tmp_path, kind, expected):
    payload = request({} if kind == "empty" else asdict(fixture(kind)))
    action = prepare(tmp_path, payload)
    direct = execute_request(json.loads((tmp_path / "audit.json").read_text()))
    assert direct["verdict"] == expected
    ledger = tmp_path / "events.jsonl"
    result = run_task(task(action), tmp_path, ledger)
    obs = result["steps"][0]["observation"]
    assert obs["verdict"] == expected
    assert result["status"] == ("COMPLETED" if expected == "PASS" else "STOPPED")
    assert obs["claim_truth"] == obs["source_authentication"] == "UNKNOWN"
    assert obs["independent_admission_authority"] == "NONE"
    assert obs["input_sha256"] == action["expected_sha256"]
    canonical = json.dumps(direct, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode("ascii")
    assert obs["report_sha256"] == hashlib.sha256(canonical).hexdigest()
    if kind == "AUDIT_RESULT":
        assert "UNKNOWN" in obs["violations"]
        assert obs["ancestry"] == "UNKNOWN"
    records = [json.loads(line) for line in ledger.read_text().splitlines()]
    assert next(row for row in records if row["event"] == "STEP_OBSERVED")["observation"] == obs


def test_workflow_stops_normal_continuation_and_runs_diagnostic(tmp_path):
    action = prepare(tmp_path, request({}))
    workflow = {"workflow_id": "W-AUDIT", "goal": "Audit before continuation",
                "stages": [
                    {"stage_id": "audit", "task": task(action)},
                    {"stage_id": "next", "task": task({"step_id": "next", "tool": "git_status"}, "NEXT")},
                    {"stage_id": "diagnose", "when": {"stage_id": "audit", "status": "STOPPED"},
                     "task": task(action, "DIAGNOSE")},
                ]}
    result = run_workflow(workflow, tmp_path, tmp_path / "events.jsonl")
    assert result["status"] == "STOPPED"
    assert [s["status"] for s in result["stages"]] == ["STOPPED", "SKIPPED", "STOPPED"]
    assert result["stages"][2]["task_result"]["steps"][0]["observation"]["verdict"] == "UNKNOWN"


def test_input_pin_mismatch_and_invalid_schema(tmp_path):
    action = prepare(tmp_path, request({}))
    (tmp_path / "audit.json").write_text("{}")
    result = run_task(task(action), tmp_path, tmp_path / "events.jsonl")
    assert result["steps"][0]["observation"]["reason"] == "INPUT_PIN_MISMATCH"
    action = prepare(tmp_path, {"invalid": True})
    result = run_task(task(action, "BAD-SCHEMA"), tmp_path, tmp_path / "events.jsonl")
    assert result["steps"][0]["observation"]["reason"] == "AUDIT_INPUT_OR_EXECUTION_FAILED"


def test_bad_action_rejected_before_execution(tmp_path):
    action = prepare(tmp_path, request({}))
    with pytest.raises(AgentRequestError):
        parse_task(task({**action, "content": "not permitted"}))
    with pytest.raises(AgentRequestError):
        parse_task(task({**action, "expected_sha256": "bad"}))


@pytest.mark.parametrize("raw,reason", [
    (b'{"audit_id":"x","audit_id":"y"}', "AUDIT_INPUT_OR_EXECUTION_FAILED"),
    (b" " * 20001, "INPUT_BYTE_LIMIT"),
])
def test_bounded_input(tmp_path, raw, reason):
    action = prepare(tmp_path, request({}))
    (tmp_path / "audit.json").write_bytes(raw)
    action["expected_sha256"] = hashlib.sha256(raw).hexdigest()
    result = run_task(task(action), tmp_path, tmp_path / "events.jsonl")
    assert result["steps"][0]["observation"]["reason"] == reason
    assert result["status"] == "STOPPED"
