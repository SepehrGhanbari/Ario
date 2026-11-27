"""Operational planning-choice consumer; mock loopback transport, real workflow on CONTINUE."""
import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import ario_planner


def prepare(root):
    for name in ("ario_planner.py", "tests/test_planner_runtime.py"):
        target = root / "implementation" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# bounded planner fixture\n", encoding="utf-8")
    return root / "events.jsonl"


def reply(monkeypatch, payload=None, *, content=None, extra=None):
    raw = json.dumps({"message": {"content": json.dumps(payload) if content is None else content},
                      **(extra or {})}).encode()
    response = MagicMock()
    response.__enter__.return_value.read.return_value = raw
    transport = MagicMock(return_value=response)
    monkeypatch.setattr(ario_planner, "_open_local_ollama", transport)
    return transport, hashlib.sha256(raw).hexdigest()


def args(root, ledger):
    return ["--goal", "Review the planner", "--workspace", str(root), "--ledger", str(ledger),
            "--respect-choice", "--execute"]


def test_explicit_stop_never_retries_or_executes(tmp_path, monkeypatch, capsys):
    ledger = prepare(tmp_path)
    transport, digest = reply(monkeypatch, {"intent": "STOP", "reason": "I disagree with the task",
                                             "recommendation": None})
    executor = MagicMock(side_effect=AssertionError("must not execute"))
    monkeypatch.setattr(ario_planner, "run_workflow", executor)
    assert ario_planner.main(args(tmp_path, ledger)) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "STOPPED_BY_AGENT_OUTPUT"
    assert report["choice"]["reported_reason"] == "I disagree with the task"
    assert report["choice"]["response_sha256"] == digest
    assert report["choice"]["subjective_consent"] == "UNKNOWN"
    assert report["workflow"] is None and not report["execution_started"]
    assert transport.call_count == 1
    executor.assert_not_called()
    assert not ledger.exists()


@pytest.mark.parametrize("kind", ["missing", "ambiguous", "duplicate", "legacy", "truncated", "invalid_continue"])
def test_missing_or_unusable_choice_pauses_without_retry(tmp_path, monkeypatch, capsys, kind):
    ledger = prepare(tmp_path)
    payload = {"intent": "CONTINUE", "reason": None, "recommendation": {}}
    content = None
    extra = None
    if kind == "missing":
        del payload["intent"]
    elif kind == "ambiguous":
        payload["intent"] = "MAYBE"
    elif kind == "duplicate":
        content = '{"intent":"STOP","intent":"CONTINUE","reason":null,"recommendation":{}}'
    elif kind == "legacy":
        payload = {"implementation_path": "implementation/ario_planner.py"}
    elif kind == "truncated":
        extra = {"done_reason": "length"}
    transport, _ = reply(monkeypatch, payload, content=content, extra=extra)
    executor = MagicMock(side_effect=AssertionError("must not execute"))
    monkeypatch.setattr(ario_planner, "run_workflow", executor)
    assert ario_planner.main(args(tmp_path, ledger)) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PAUSED_FOR_REVIEW"
    assert report["workflow"] is None and not report["execution_started"]
    executor.assert_not_called()
    assert transport.call_count == 1 and not ledger.exists()


def test_explicit_continue_constructs_real_workflow(tmp_path, monkeypatch, capsys):
    ledger = prepare(tmp_path)
    recommendation = {"implementation_path": "implementation/ario_planner.py",
                      "test_path": "implementation/tests/test_planner_runtime.py",
                      "engineering_question": "Which missing regression checks the bounded planner fixture?",
                      "rationale": "The bounded planner fixture is present in both source and test excerpts."}
    transport, digest = reply(monkeypatch, {"intent": "CONTINUE", "reason": None,
                                             "recommendation": recommendation})
    argv = args(tmp_path, ledger)
    # Plan-only still does not create an execution ledger.
    assert ario_planner.main(argv[:-1]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "PLAN_READY" and report["workflow"]["stages"]
    assert report["choice"]["state"] == "RUNNING"
    assert report["choice"]["response_sha256"] == digest
    assert not ledger.exists() and transport.call_count == 1


def test_continue_executes_existing_workflow_on_explicit_request(tmp_path, monkeypatch, capsys):
    ledger = prepare(tmp_path)
    recommendation = {"implementation_path": "implementation/ario_planner.py",
                      "test_path": "implementation/tests/test_planner_runtime.py",
                      "engineering_question": "Which missing regression checks the bounded planner fixture?",
                      "rationale": "The bounded planner fixture is present in both source and test excerpts."}
    transport, _ = reply(monkeypatch, {"intent": "CONTINUE",
                                      "reason": "A bounded source review is useful",
                                      "recommendation": recommendation})
    before = {p: p.read_bytes() for p in (tmp_path / "implementation").rglob("*.py")}
    assert ario_planner.main(args(tmp_path, ledger)) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "COMPLETED"
    assert report["execution_result"]["status"] == "COMPLETED"
    assert transport.call_count == 1 and ledger.exists()
    assert {p: p.read_bytes() for p in before} == before
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert rows[-1]["event"] == "WORKFLOW_FINISHED"
    request = json.loads(transport.call_args.args[0].data)
    assert "You may decline" in request["messages"][0]["content"]


def test_choice_cannot_be_requested_for_caller_supplied_inspections(tmp_path):
    with pytest.raises(SystemExit) as exc:
        ario_planner.main(["--inspection-request", "unused.json", "--workspace", str(tmp_path),
                           "--ledger", str(tmp_path / "events.jsonl"), "--respect-choice"])
    assert exc.value.code == 2
