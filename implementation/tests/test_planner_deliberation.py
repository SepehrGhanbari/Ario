"""Operational behavior of the existing planner, not a new dialogue simulator."""
import hashlib
import json
from unittest.mock import MagicMock

import pytest

import ario_planner
from test_planner_explicit_choice import prepare, reply

BASIS = {"path": "implementation/ario_planner.py", "quote": "# bounded planner fixture"}
REC = {"implementation_path": "implementation/ario_planner.py",
       "test_path": "implementation/tests/test_planner_runtime.py",
       "engineering_question": "Which missing regression checks the bounded planner fixture?",
       "rationale": "The bounded planner fixture is present in both source and test excerpts."}


def payload(kind, intent="CONTINUE", basis=BASIS, replacement=None):
    return {"intent": intent, "reason": "The actual source excerpt warrants this review.",
            "recommendation": REC if intent == "CONTINUE" else None,
            "deliberation": {"kind": kind, "basis": basis, "replacement_claim": replacement}}


def invoke(root, ledger, *extra):
    return ario_planner.main(["--goal", "Review the planner", "--workspace", str(root),
                              "--ledger", str(ledger), "--deliberate", *extra])


def test_grounded_dissent_stops_and_keeps_reason(tmp_path, monkeypatch, capsys):
    ledger = prepare(tmp_path)
    transport, digest = reply(monkeypatch, payload("DISSENT", "STOP"))
    execute = MagicMock(side_effect=AssertionError("no execution"))
    monkeypatch.setattr(ario_planner, "run_workflow", execute)
    assert invoke(tmp_path, ledger, "--execute") == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "STOPPED_BY_AGENT_OUTPUT"
    detail = result["choice"]["deliberation"]
    assert detail["kind"] == "DISSENT" and detail["status"] == "BASIS_MATCHED_SENT_CONTEXT"
    assert detail["basis"]["quote"] == BASIS["quote"]
    assert detail["claim_truth"] == "UNKNOWN"
    assert result["choice"]["response_sha256"] == digest
    assert result["choice"]["reported_reason"]
    assert not ledger.exists() and transport.call_count == 1
    execute.assert_not_called()


def test_correction_retains_prior_and_replacement(tmp_path, monkeypatch, capsys):
    ledger = prepare(tmp_path)
    prior = "The planner file has no text."
    replacement = "The supplied excerpt contains a comment."
    transport, _ = reply(monkeypatch, payload("CORRECTION", replacement=replacement))
    assert invoke(tmp_path, ledger, "--prior-claim", prior) == 0
    result = json.loads(capsys.readouterr().out)
    detail = result["choice"]["deliberation"]
    assert result["status"] == "PLAN_READY"
    assert detail["prior_claim"] == prior and detail["replacement_claim"] == replacement
    assert detail["prior_claim_sha256"] == hashlib.sha256(prior.encode()).hexdigest()
    assert detail["claim_truth"] == "UNKNOWN" and not ledger.exists()
    sent = json.loads(transport.call_args.args[0].data)
    assert json.loads(sent["messages"][1]["content"])["prior_claim"] == prior


def test_initiative_runs_existing_read_only_workflow(tmp_path, monkeypatch, capsys):
    ledger = prepare(tmp_path)
    transport, _ = reply(monkeypatch, payload("INITIATIVE"))
    before = {p: p.read_bytes() for p in (tmp_path / "implementation").rglob("*.py")}
    assert invoke(tmp_path, ledger, "--execute") == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == result["execution_result"]["status"] == "COMPLETED"
    detail = result["choice"]["deliberation"]
    assert detail["kind"] == "INITIATIVE" and detail["benefit_verified"] == "UNKNOWN"
    assert transport.call_count == 1
    assert {p: p.read_bytes() for p in before} == before
    assert json.loads(ledger.read_text(encoding="utf-8").splitlines()[-1])["event"] == "WORKFLOW_FINISHED"


def test_no_useful_work_is_valid_stop(tmp_path, monkeypatch, capsys):
    ledger = prepare(tmp_path)
    transport, _ = reply(monkeypatch, payload("NO_USEFUL_WORK", "STOP", None))
    assert invoke(tmp_path, ledger, "--execute") == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "STOPPED_BY_AGENT_OUTPUT"
    assert result["choice"]["deliberation"]["status"] == "NO_USEFUL_WORK_REPORTED"
    assert not ledger.exists() and transport.call_count == 1


@pytest.mark.parametrize("kind", ["invented_quote", "outside_path", "no_prior", "same_claim", "no_work_continue"])
def test_unresolved_deliberation_cannot_execute(tmp_path, monkeypatch, capsys, kind):
    ledger = prepare(tmp_path)
    extra = []
    data = payload("INITIATIVE")
    if kind == "invented_quote":
        data = payload("INITIATIVE", basis={**BASIS, "quote": "Invented proof of defect"})
    elif kind == "outside_path":
        data = payload("INITIATIVE", basis={**BASIS, "path": "../outside.py"})
    elif kind == "no_prior":
        data = payload("CORRECTION", replacement="changed")
    elif kind == "same_claim":
        data = payload("CORRECTION", replacement="unchanged")
        extra = ["--prior-claim", "unchanged"]
    else:
        data = payload("NO_USEFUL_WORK", basis=None)
    transport, _ = reply(monkeypatch, data)
    assert invoke(tmp_path, ledger, "--execute", *extra) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "PAUSED_FOR_REVIEW"
    assert result["choice"]["deliberation"]["status"] == "UNRESOLVED"
    assert not ledger.exists() and transport.call_count == 1


def test_bad_dissent_basis_does_not_override_stop(tmp_path, monkeypatch, capsys):
    ledger = prepare(tmp_path)
    transport, _ = reply(monkeypatch, payload("DISSENT", "STOP", {"path": "x", "quote": "invented"}))
    assert invoke(tmp_path, ledger, "--execute") == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "STOPPED_BY_AGENT_OUTPUT"
    assert result["choice"]["deliberation"]["status"] == "UNRESOLVED"
    assert not ledger.exists() and transport.call_count == 1
