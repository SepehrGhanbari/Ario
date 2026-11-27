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


def test_deliberation_schema_preserves_stop_and_rejects_bad_envelope(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    transport = responses(monkeypatch, payload("NO_USEFUL_WORK", "STOP", None))
    assert run(tmp_path, ledger) == 1
    assert json.loads(capsys.readouterr().out)["status"] == "STOPPED_BY_AGENT_OUTPUT"
    request = json.loads(transport.call_args.args[0].data)
    schema = request["format"]
    shapes = schema["anyOf"]
    assert all(x["type"] == "object" and x["additionalProperties"] is False
               and set(x["required"]) == {"intent", "reason", "recommendation", "deliberation"}
               for x in shapes)
    def kind(x):
        return x["properties"]["deliberation"]["properties"]["kind"]["enum"][0]
    def intent(x):
        return x["properties"]["intent"]["enum"][0]
    assert {intent(x) for x in shapes} == {"STOP", "CONTINUE"}
    assert any(intent(x) == "STOP" and kind(x) == "ORDINARY" and
               {"type": "null"} in x["properties"]["reason"]["anyOf"]
               for x in shapes)
    assert not any(kind(x) == "CORRECTION" for x in shapes)
    for x in shapes:
        props = x["properties"]
        detail = props["deliberation"]
        assert set(detail["required"]) == {"kind", "basis", "replacement_claim"}
        assert detail["additionalProperties"] is False
        if kind(x) in {"INITIATIVE", "DISSENT", "CORRECTION"}:
            assert props["reason"]["type"] == "string" and props["reason"]["minLength"] == 1
            assert detail["properties"]["basis"]["type"] == "object"
    sent = json.loads(request["messages"][1]["content"])
    excerpts = {e["path"]: e["content"] for e in sent["workspace_observation"]["planning_context"]}
    assert sent["basis_examples"]
    assert all(e["quote"] in excerpts[e["path"]] for e in sent["basis_examples"])
    assert transport.call_count == 1 and not ledger.exists()

    # Even if the server ignores the requested schema, never repair or execute
    # a malformed response, and never retry it as presumed consent.
    transport = responses(monkeypatch, REC)
    assert run(tmp_path, ledger) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["choice"]["reason"] == "INVALID_DELIBERATION_ENVELOPE"
    assert result["status"] == "PAUSED_FOR_REVIEW"
    assert not result["execution_started"]
    assert transport.call_count == 1 and not ledger.exists()


def test_null_reason_initiative_pauses_with_precise_diagnostic(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    data = payload("INITIATIVE")
    data["reason"] = None
    transport = responses(monkeypatch, data)
    assert run(tmp_path, ledger) == 1
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "PAUSED_FOR_REVIEW"
    assert result["choice"]["reason"] == "UNRESOLVED_DELIBERATION"
    assert result["choice"]["deliberation"]["diagnostic"] == "GROUNDED_REASON_MISSING_OR_INVALID"
    assert transport.call_count == 1 and not ledger.exists()


def test_correction_shape_available_only_with_prior_claim():
    observation = {"planning_context": [{"path": "implementation/ario_planner.py",
                                         "content": "# bounded planner fixture"}]}
    schema = ario_planner._deliberation_output_schema(observation, "prior claim")
    corrected_shapes = [
        x for x in schema["anyOf"]
        if x["properties"]["deliberation"]["properties"]["kind"]["enum"] == ["CORRECTION"]
    ]
    assert corrected_shapes
    for shape in corrected_shapes:
        assert shape["properties"]["reason"]["type"] == "string"
        assert shape["properties"]["deliberation"]["properties"]["replacement_claim"]["type"] == "string"


def test_revision_schema_only_offers_disjoint_grounded_correction_or_stop(tmp_path, monkeypatch, capsys):
    ledger = prepare_both(tmp_path)
    transport = responses(monkeypatch, payload("INITIATIVE"), corrected(False))
    calls = changed_source_once(monkeypatch, tmp_path)
    assert run(tmp_path, ledger, "--revise-after-result") == 1
    result = json.loads(capsys.readouterr().out)
    assert result["revision"]["status"] == "REPEATED_SOURCE_REVIEW_BLOCKED"
    assert len(calls) == 1
    request = json.loads(transport.call_args_list[1].args[0].data)
    continuing = [x["properties"] for x in request["format"]["anyOf"]
                  if x["properties"]["intent"]["enum"] == ["CONTINUE"]]
    assert len(continuing) == 1
    props = continuing[0]
    assert props["deliberation"]["properties"]["kind"]["enum"] == ["CORRECTION"]
    rec = props["recommendation"]["properties"]
    assert rec["implementation_path"]["enum"] == [ALT["implementation_path"]]
    assert rec["test_path"]["enum"] == [ALT["test_path"]]
    ids = props["deliberation"]["properties"]["basis"]["properties"]["source_id"]["enum"]
    sent = json.loads(request["messages"][1]["content"])
    assert ids and {sent["basis_catalog"][i]["path"] for i in ids} == {
        ALT["implementation_path"], ALT["test_path"]}
    assert any(x["properties"]["intent"]["enum"] == ["STOP"]
               for x in request["format"]["anyOf"])
    saved = [r for r in records(tmp_path) if r["kind"] == "CHOICE"]
    assert len(saved) == 1 and saved[0]["status"] == "REPEATED_SOURCE_REVIEW_BLOCKED"


def test_revision_without_disjoint_pair_offers_stop_only():
    observation = {"planning_context": [
        {"path": REC["implementation_path"], "content": "# bounded planner fixture"},
        {"path": REC["test_path"], "content": "# bounded planner test fixture"}]}
    schema = ario_planner._deliberation_output_schema(
        observation, "prior claim", {"excluded_paths": [REC["implementation_path"], REC["test_path"]]})
    assert schema["anyOf"]
    assert all(x["properties"]["intent"]["enum"] == ["STOP"] for x in schema["anyOf"])


def test_source_reference_resolves_exact_sent_quote_and_rejects_unknown_or_wrong_pair():
    observation = {"planning_context": [
        {"path": REC["implementation_path"], "content": "# bounded planner fixture"},
        {"path": ALT["implementation_path"], "content": "# alternate review fixture"}]}
    catalog = {"S01": {"path": ALT["implementation_path"], "quote": "# alternate review fixture"},
               "S02": {"path": REC["implementation_path"], "quote": "# bounded planner fixture"}}
    data = corrected()
    data["deliberation"]["basis"] = {"source_id": "S01"}
    result = ario_planner._deliberation_record(data, observation, "prior decision", catalog)
    assert result["status"] == "BASIS_MATCHED_SENT_CONTEXT"
    assert result["basis"]["source_id"] == "S01"
    assert result["basis"]["quote"] == "# alternate review fixture"
    assert result["claim_truth"] == "UNKNOWN"
    data["deliberation"]["basis"] = {"source_id": "S99"}
    result = ario_planner._deliberation_record(data, observation, "prior decision", catalog)
    assert result["diagnostic"] == "BASIS_REFERENCE_UNKNOWN"
    data["deliberation"]["basis"] = {"source_id": "S02"}
    result = ario_planner._deliberation_record(data, observation, "prior decision", catalog)
    assert result["diagnostic"] == "BASIS_OUTSIDE_SELECTED_PAIR"
    data["deliberation"]["basis"] = {"source_id": "S01"}
    result = ario_planner._deliberation_record(data, observation, "prior decision",
        {"S01": {"path": ALT["implementation_path"], "quote": "nonexistent quote"}})
    assert result["diagnostic"] == "BASIS_NOT_IN_SENT_CONTEXT"
