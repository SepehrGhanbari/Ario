"""R21.2 research-only regression probes, stacked on R18. No trust authority."""
import json
import sys
import pytest
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
