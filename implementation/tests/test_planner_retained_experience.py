"""Restarted planner consumes retained results, not a second decision engine."""
import json

import ario_planner
from test_planner_deliberation import payload, invoke
from test_planner_result_revision import (
    prepare_both, responses, changed_source_once, corrected, REC, ALT
)


def run(root, ledger, *extra):
    return invoke(root, ledger, "--execute", "--experience-dir", str(root / "experience"), *extra)


def records(root):
    return [json.loads(p.read_bytes())["payload"]
            for p in (root / "experience").glob("*.experience.json")]


def test_restart_recall_changes_execution_and_allows_changed_conditions(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    source = tmp_path / REC["implementation_path"]
    original = source.read_bytes()
    transport = responses(monkeypatch, payload("INITIATIVE"), corrected())
    calls = changed_source_once(monkeypatch, tmp_path)
    assert run(tmp_path, ledger, "--revise-after-result") == 1
    first = json.loads(capsys.readouterr().out)
    assert first["revision"]["status"] == "ALTERNATIVE_REVIEW_COMPLETED"
    assert first["revision"]["repair_verified"] == "UNKNOWN"
    initial_bytes = ledger.read_bytes()
    old_rows = {p.name: p.read_bytes() for p in (tmp_path / "experience").glob("*.experience.json")}
    assert len(old_rows) == 4
    assert len(calls) == 2

    # Restore the original observable pre-attempt conditions (test fixture only).
    source.write_bytes(original)
    transport = responses(monkeypatch, payload("INITIATIVE"))
    assert run(tmp_path, ledger) == 1
    blocked = json.loads(capsys.readouterr().out)
    assert blocked["status"] == "RETAINED_FAILURE_SAME_CONDITIONS"
    assert blocked["experience"]["blocked_by"]
    assert len(calls) == 2 and transport.call_count == 1
    assert ledger.read_bytes() == initial_bytes
    sent = json.loads(json.loads(transport.call_args.args[0].data)["messages"][1]["content"])
    assert any(r["failure_kind"] == "READ_BOUNDARY_CHANGED" and
               r["same_observed_conditions"] and r["cause"] == "UNKNOWN"
               for r in sent["retained_experience"])

    source.write_bytes(original + b"# different stable fixture\n")
    responses(monkeypatch, payload("INITIATIVE"))
    assert run(tmp_path, ledger) == 0
    changed = json.loads(capsys.readouterr().out)
    assert changed["status"] == "COMPLETED"
    assert changed["experience"]["blocked_by"] == [] and len(calls) == 3
    assert ledger.read_bytes().startswith(initial_bytes)
    assert all((tmp_path / "experience" / name).read_bytes() == raw
               for name, raw in old_rows.items())
    assert all(p["claim_truth"] == "UNKNOWN" for p in records(tmp_path) if p["kind"] == "OUTCOME")


def test_stop_remains_choice_not_failure(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    transport = responses(monkeypatch, payload("NO_USEFUL_WORK", "STOP", None))
    assert run(tmp_path, ledger) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "STOPPED_BY_AGENT_OUTPUT"
    assert not ledger.exists()
    assert transport.call_count == 1
    assert len(records(tmp_path)) == 1
    assert records(tmp_path)[0]["kind"] == "CHOICE"
    assert records(tmp_path)[0]["failure"] is False
    responses(monkeypatch, payload("INITIATIVE"))
    assert run(tmp_path, ledger) == 0


def test_missing_native_prefix_does_not_authorize_retained_failure(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    source = tmp_path / REC["implementation_path"]
    original = source.read_bytes()
    responses(monkeypatch, payload("INITIATIVE"))
    calls = changed_source_once(monkeypatch, tmp_path)
    assert run(tmp_path, ledger) == 1
    capsys.readouterr()
    # Disposable fixture only: demonstrate missing historical native ledger.
    ledger.unlink()
    source.write_bytes(original)
    responses(monkeypatch, payload("INITIATIVE"))
    assert run(tmp_path, ledger) == 0
    result = json.loads(capsys.readouterr().out)
    assert not result["experience"]["blocked_by"]
    assert not result["experience"]["recalled"]
    assert len(calls) == 2
