"""R21.2 research-only regression probes, stacked on R18. No trust authority."""
import json
import sys
import pytest
import ario_cli
import core.memory_consolidation as mc
from core.memory_consolidation import ConsolidationEngine as CE, ConsolidationError


def test_empty_regular_ledger_is_only_empty_clean(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_bytes(b"")
    report = CE.inspect_ledger_integrity(p)
    assert report.is_clean and report.diagnostic == "EMPTY_LEDGER"


@pytest.mark.parametrize("invalid", [
    b"42\n", b"null\n", b"[]\n", b'["abc"]\n',
])
def test_inspector_never_clean_for_non_object_event(tmp_path, invalid):
    p = tmp_path / "bad-shape.jsonl"
    p.write_bytes(invalid)
    r = CE.inspect_ledger_integrity(p)
    assert not r.is_clean and r.corrupt_line_no is None
    assert r.diagnostic.startswith("HOLD_EVENT_MUST_BE_JSON_OBJECT")


def test_structural_budget_prevents_expanded_json_allocation(tmp_path):
    p = tmp_path / "many-objects.jsonl"
    raw = b'{"concept":"c","assertion":"a","x":[' + b"{}," * 55000 + b"{}]}\n"
    assert len(raw) < 1_048_576
    p.write_bytes(raw)
    r = CE.inspect_ledger_integrity(p)
    assert r.diagnostic.startswith("HOLD_LEDGER_STRUCTURE_BUDGET")
    with pytest.raises(ConsolidationError, match="HOLD_LEDGER_STRUCTURE_BUDGET"):
        CE().ingest_ledger_file(p)


def test_direct_stream_oversized_event_is_hold_not_committed():
    e = CE(max_batch_events=2)
    with pytest.raises(ConsolidationError, match="HOLD_EVENT_RESOURCE_BUDGET"):
        e.ingest_event_stream([("a" * 64, {"concept": "huge", "padding": "x" * (8 * 1024 * 1024)})])
    assert e.nodes == {} and not e.known_ledger_hashes


def test_direct_stream_empty_with_sysmax_guarded():
    with pytest.raises(ConsolidationError):
        CE(max_batch_events=sys.maxsize)
    engine = CE()
    engine.max_batch_events = sys.maxsize
    with pytest.raises(ConsolidationError, match="HOLD_INVALID_MAX_BATCH_EVENTS"):
        engine.ingest_event_stream([])


def test_empty_legacy_state_restores_but_not_historical_replay_index():
    e = CE()
    state = e.__getstate__()
    state.pop("_event_payload_digests")
    state.pop("_event_stable_digests")
    restored = CE.__new__(CE)
    restored.__setstate__(state)
    assert restored.ingest_event_stream([("b" * 64, {"concept": "fresh", "assertion": "ok"})]) == 1
    e.ingest_event_stream([("a" * 64, {"concept": "historic", "assertion": "old"})])
    state2 = e.__getstate__()
    state2.pop("_event_payload_digests")
    state2.pop("_event_stable_digests")
    with pytest.raises(ConsolidationError, match="HOLD_LEGACY_SNAPSHOT_REPLAY_INDEX_MISSING"):
        CE.__new__(CE).__setstate__(state2)


@pytest.mark.parametrize("missing", ["payload", "stable", "all_indexes", "invalid_digest"])
def test_restore_checks_replay_coverage_before_changing_state(missing):
    engine = CE()
    event_hash = "a" * 64
    event = {"concept": "historical", "assertion": "recorded"}
    engine.ingest_event_stream([(event_hash, event)])
    original = engine.__getstate__()
    damaged = engine.__getstate__()
    if missing == "all_indexes":
        for key in ("_ledger_hashes", "_event_payload_digests", "_event_stable_digests"):
            damaged[key].clear()
    elif missing == "invalid_digest":
        damaged["_event_payload_digests"][event_hash] = None
    else:
        damaged[f"_event_{missing}_digests"].clear()
    with pytest.raises(ConsolidationError, match="HOLD"):
        engine.__setstate__(damaged)
    assert engine.__getstate__() == original
    assert engine.ingest_event_stream([(event_hash, event)]) == 0


@pytest.mark.parametrize("line", [b"\f\n", b'\x0b{"assertion":"two"}\n'])
def test_invalid_json_whitespace_preserves_ledger_and_engine(tmp_path, line):
    ledger = tmp_path / "input.jsonl"
    contents = b'{"assertion":"one"}\n' + line
    ledger.write_bytes(contents)
    report = CE.inspect_ledger_integrity(ledger)
    assert not report.is_clean and report.corrupt_line_no == 2
    assert report.diagnostic.startswith("CORRUPT_JSON_OR_TRUNCATED_TAIL")
    engine = CE()
    with pytest.raises(ConsolidationError, match="corrupt ledger JSON on line 2"):
        engine.ingest_ledger_file(ledger)
    assert not engine.nodes and not engine.known_ledger_hashes
    assert ledger.read_bytes() == contents


def test_direct_batch_stops_consuming_at_first_resource_failure(monkeypatch):
    monkeypatch.setattr(mc, "MAX_DIRECT_BATCH_APPROX_BYTES", 1)
    def records():
        yield "a" * 64, {"assertion": "one"}
        pytest.fail("consumed another record after the first exceeded the budget")
    engine = CE()
    with pytest.raises(ConsolidationError, match="HOLD_EVENT_RESOURCE_BUDGET"):
        engine.ingest_event_stream(records())
    assert not engine.known_ledger_hashes


def test_direct_batch_rechecks_records_updated_during_iteration(monkeypatch):
    monkeypatch.setattr(mc, "MAX_DIRECT_EVENT_APPROX_BYTES", 2048)
    event = {"assertion": "one"}
    def records():
        yield "a" * 64, event
        event["note"] = "a" * 4096
    engine = CE()
    with pytest.raises(ConsolidationError, match="HOLD_EVENT_RESOURCE_BUDGET"):
        engine.ingest_event_stream(records())
    assert not engine.known_ledger_hashes


def test_encoder_recursion_is_a_domain_hold(monkeypatch):
    def unsupported(*args, **kwargs):
        raise RecursionError("encoder depth limit")
    monkeypatch.setattr(mc.json, "dumps", unsupported)
    engine = CE()
    with pytest.raises(ConsolidationError, match="HOLD"):
        engine.ingest_event_stream([("a" * 64, {"assertion": "one"})])
    assert not engine.nodes and not engine.known_ledger_hashes


def test_cli_range_checked_before_decimal_conversion(tmp_path, capsys):
    ledger = tmp_path / "input.jsonl"
    ledger.write_bytes(b'{"assertion":"one"}\n')
    args = ["--memory-conflicts", "--ledger", str(ledger), "--format", "json",
            "--memory-max-events"]
    assert ario_cli.main([*args, "9" * 4500]) == 2
    assert json.loads(capsys.readouterr().err)["error"] == "INVALID_MEMORY_MAX_EVENTS"
    assert ario_cli.main([*args, "0" * 4500 + "1"]) == 0
    assert json.loads(capsys.readouterr().out)["total_nodes"] == 1
