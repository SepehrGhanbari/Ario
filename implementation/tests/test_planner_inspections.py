"""Planner compilation of the three merged inspection consumers, no Ollama needed."""
from dataclasses import asdict
import hashlib
import json

import pytest

import ario_planner
from ario_agent import AgentRequestError, run_task
from ledger_observation_adapter import observe_ledger
from ario_workflow import run_workflow
from research.rere01.assessment_history_v1 import encode_history, append_history
from tests.test_rere01_v03_guard import _fixture
from test_eag_f263_collision import fixture


def write(root, name, data):
    (root / name).write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def inputs(root):
    prior = root / "prior.jsonl"
    run_task({"task_id": "PRIOR", "goal": "prior execution", "actions": [
        {"step_id": "read", "tool": "inspect_directory", "path": "."}]}, root, prior)
    manifest_pin = write(root, "manifest.json", json.dumps(observe_ledger(prior)).encode())
    audit_pin = write(root, "audit.json", json.dumps({
        "audit_id": "PLAN-AUDIT", "rule_versions": ["M0-1.0"],
        "configuration_id": "PLAN", "execution_timestamp": "TEST",
        "artifacts": asdict(fixture(None)),
    }).encode())
    policy, rows, _ = _fixture()
    before = encode_history(rows[:4], policy)
    before_pin = write(root, "before.json", before)
    after = append_history(before, expected_sha256=before_pin, additions=rows[4:6])
    after_pin = write(root, "after.json", after)
    return {"goal": "Inspect prior execution and lab revision",
            "revision": {"path": "after.json", "prior_path": "before.json",
                         "expected_sha256": after_pin, "prior_sha256": before_pin},
            "audit": {"path": "audit.json", "expected_sha256": audit_pin},
            "ledger": {"path": "prior.jsonl", "manifest_path": "manifest.json",
                       "expected_sha256": manifest_pin}}


def test_planner_runs_three_real_consumers_in_fixed_order(tmp_path):
    payload = inputs(tmp_path)
    output = tmp_path / "new.jsonl"
    originals = {p.name: p.read_bytes() for p in tmp_path.iterdir() if p.is_file()}
    plan = ario_planner.plan_inspections(payload, tmp_path, output)
    assert not output.exists()
    assert [s["stage_id"] for s in plan["stages"]] == ["stage-ledger", "stage-audit", "stage-revision"]
    result = run_workflow(plan, tmp_path, output)
    assert result["status"] == "COMPLETED"
    observations = [s["task_result"]["steps"][0]["observation"] for s in result["stages"]]
    assert observations[0]["ledger_status"] == "OBSERVED"
    assert observations[1]["verdict"] == "PASS"
    assert observations[2]["event_outcome"] == "UNKNOWN"
    assert observations[2]["withdrawn_assessment_count"] == 1
    assert all(o["claim_truth"] == "UNKNOWN" for o in observations)
    assert {name: (tmp_path / name).read_bytes() for name in originals} == originals


def test_bad_ledger_stops_later_stages(tmp_path):
    payload = inputs(tmp_path)
    output = tmp_path / "new.jsonl"
    plan = ario_planner.plan_inspections(payload, tmp_path, output)
    prior = tmp_path / "prior.jsonl"
    prior.write_bytes(prior.read_bytes().replace(b"PRIOR", b"OTHER"))
    result = run_workflow(plan, tmp_path, output)
    assert result["status"] == "STOPPED"
    assert [s["status"] for s in result["stages"]] == ["STOPPED", "SKIPPED", "SKIPPED"]


@pytest.mark.parametrize("kind", ["tool", "pin", "escape", "active", "empty"])
def test_invalid_inputs_never_produce_a_plan(tmp_path, kind):
    payload = inputs(tmp_path)
    output = tmp_path / "new.jsonl"
    if kind == "tool":
        payload["audit"]["tool"] = "replace_text"
    elif kind == "pin":
        payload["revision"]["prior_sha256"] = "bad"
    elif kind == "escape":
        payload["revision"]["prior_path"] = "../outside.json"
    elif kind == "active":
        payload["ledger"]["path"] = "new.jsonl"
    else:
        payload = {"goal": "no inputs"}
    with pytest.raises(AgentRequestError):
        ario_planner.plan_inspections(payload, tmp_path, output)
    assert not output.exists()


def test_cli_plan_only_and_explicit_execution_without_ollama(tmp_path, monkeypatch, capsys):
    payload = inputs(tmp_path)
    request = tmp_path / "request.json"
    request.write_text(json.dumps(payload), encoding="utf-8")
    output = tmp_path / "new.jsonl"
    def forbidden(*args, **kwargs):
        pytest.fail("inspection planner must not call Ollama")
    monkeypatch.setattr(ario_planner, "request_plan", forbidden)
    argv = ["--inspection-request", str(request), "--workspace", str(tmp_path), "--ledger", str(output)]
    assert ario_planner.main(argv) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "PLAN_READY"
    assert not output.exists()
    assert ario_planner.main(argv + ["--execute"]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "COMPLETED"
    assert output.exists()


def test_duplicate_inspection_request_rejected(tmp_path):
    request = tmp_path / "request.json"
    request.write_bytes(b'{"goal":"first","goal":"second"}')
    with pytest.raises(AgentRequestError):
        ario_planner.read_inspection_request(request)
