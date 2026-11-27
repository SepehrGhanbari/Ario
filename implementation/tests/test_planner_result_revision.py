"""Result-driven revision on the actual source-review executor."""
import json
from unittest.mock import MagicMock

import pytest

import ario_planner
from test_planner_deliberation import REC, payload, invoke
from test_planner_explicit_choice import prepare


ALT = {**REC, "implementation_path": "implementation/ario_workflow.py",
       "test_path": "implementation/tests/test_workflow_runtime.py"}
ALT_BASIS = {"path": ALT["implementation_path"], "quote": "# alternate review fixture"}


def prepare_both(root):
    ledger = prepare(root)
    for name in (ALT["implementation_path"], ALT["test_path"]):
        (root / name).write_text("# alternate review fixture\n", encoding="utf-8")
    return ledger


def responses(monkeypatch, *payloads):
    replies = []
    for data in payloads:
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "message": {"content": json.dumps(data)}}).encode()
        replies.append(response)
    transport = MagicMock(side_effect=replies)
    monkeypatch.setattr(ario_planner, "_open_local_ollama", transport)
    return transport


def changed_source_once(monkeypatch, root, *, second_failure=False):
    real = ario_planner.run_workflow
    seen = []

    def execute(workflow, workspace, ledger):
        seen.append(workflow)
        if len(seen) == 1 or second_failure:
            path = root / workflow["stages"][0]["task"]["actions"][0]["path"]
            # A real line-boundary change after planning, not a fabricated failure.
            with path.open("a", encoding="utf-8") as handle:
                handle.write("# changed after plan\n")
        return real(workflow, workspace, ledger)

    monkeypatch.setattr(ario_planner, "run_workflow", execute)
    return seen


def corrected(alternate=True):
    data = payload("CORRECTION", basis=ALT_BASIS if alternate else
                   {"path": REC["implementation_path"], "quote": "# bounded planner fixture"},
                   replacement="The preceding source review stopped; inspect a different pair.")
    if alternate:
        data["recommendation"] = ALT
    return data


def run(root, ledger):
    return invoke(root, ledger, "--execute", "--revise-after-result")


def test_actual_failure_feedback_drives_distinct_review(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    transport = responses(monkeypatch, payload("INITIATIVE"), corrected())
    calls = changed_source_once(monkeypatch, tmp_path)
    assert run(tmp_path, ledger) == 1
    result = json.loads(capsys.readouterr().out)
    revision = result["revision"]
    assert result["status"] == result["execution_result"]["status"] == "STOPPED"
    assert revision["status"] == "ALTERNATIVE_REVIEW_COMPLETED"
    assert revision["execution_result"]["status"] == "COMPLETED"
    assert revision["feedback"]["failure_kind"] == "READ_BOUNDARY_CHANGED"
    assert revision["feedback"]["observations"][-1]["status"] == "FAILED"
    assert revision["choice"]["deliberation"]["prior_claim"] == calls[0]["stages"][0]["task"]["goal"]
    assert revision["repair_verified"] == "UNKNOWN"
    assert len(calls) == transport.call_count == 2
    assert calls[0]["workflow_id"] != calls[1]["workflow_id"]
    assert not ario_planner._source_review_paths(calls[0]).intersection(
        ario_planner._source_review_paths(calls[1]))
    sent = json.loads(transport.call_args_list[1].args[0].data)
    assert json.loads(sent["messages"][1]["content"])["execution_feedback"] == revision["feedback"]
    events = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert [row["status"] for row in events if row["event"] == "WORKFLOW_FINISHED"] == ["STOPPED", "COMPLETED"]


def test_new_ids_do_not_allow_same_source_review(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    transport = responses(monkeypatch, payload("INITIATIVE"), corrected(False))
    calls = changed_source_once(monkeypatch, tmp_path)
    assert run(tmp_path, ledger) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["revision"]["status"] == "REPEATED_SOURCE_REVIEW_BLOCKED"
    assert len(calls) == 1 and transport.call_count == 2
    assert result["revision"]["execution_result"] is None


def test_completed_initial_work_does_not_trigger_extra_request(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    transport = responses(monkeypatch, payload("INITIATIVE"))
    assert run(tmp_path, ledger) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["revision"]["status"] == "NOT_NEEDED"
    assert transport.call_count == 1


def test_revision_stop_is_honored(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    transport = responses(monkeypatch, payload("INITIATIVE"),
                          payload("NO_USEFUL_WORK", "STOP", None))
    calls = changed_source_once(monkeypatch, tmp_path)
    assert run(tmp_path, ledger) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["revision"]["status"] == "STOPPED_BY_AGENT_OUTPUT"
    assert result["status"] == "STOPPED" and len(calls) == 1
    assert transport.call_count == 2


def test_second_failure_never_creates_third_attempt(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    transport = responses(monkeypatch, payload("INITIATIVE"), corrected())
    calls = changed_source_once(monkeypatch, tmp_path, second_failure=True)
    assert run(tmp_path, ledger) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["revision"]["status"] == "ALTERNATIVE_REVIEW_STOPPED"
    assert len(calls) == transport.call_count == 2


def test_no_revision_on_unobserved_failure(tmp_path):
    workflow = {"workflow_id": "w", "stages": [{"stage_id": "s", "task": {
        "task_id": "t", "actions": [{"step_id": "x", "tool": "read_text", "path": "x"}]}}]}
    result = {"workflow": workflow, "execution_result": {
        "workflow_id": "w", "status": "STOPPED", "stages": [
            {"stage_id": "s", "task_id": "t", "status": "STOPPED", "error": "unavailable"}]}}
    revision = ario_planner.revise_after_result(result, tmp_path, tmp_path / "ledger",
                                                model="unused", ollama_url="unused", timeout=1)
    assert revision["status"] == "NO_CONCRETE_FAILURE_TO_REVISE"


def test_revision_requires_explicit_execute(tmp_path):
    with pytest.raises(SystemExit) as exc:
        invoke(tmp_path, tmp_path / "ledger", "--revise-after-result")
    assert exc.value.code == 2


def test_alternate_without_correction_is_not_executed(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    data = payload("INITIATIVE", basis=ALT_BASIS)
    data["recommendation"] = ALT
    transport = responses(monkeypatch, payload("INITIATIVE"), data)
    calls = changed_source_once(monkeypatch, tmp_path)
    assert run(tmp_path, ledger) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["revision"]["status"] == "CORRECTION_REQUIRED"
    assert len(calls) == 1 and transport.call_count == 2
