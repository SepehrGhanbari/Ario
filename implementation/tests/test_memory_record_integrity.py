"""Regression for #223 / #258: record isolation and unambiguous ingestion."""
import hashlib
from dataclasses import replace
import pytest
from core.memory_consolidation import ConsolidationEngine, ConsolidationError, CausalLink
from core.ledger_memory_bridge import EpistemicLedgerBridge, BridgeError
from core.source_monitoring import SourceMonitoringGuard, SelfCitationError, VeracityState

H = "a" * 64

def test_nested_falsification_is_not_admitted_and_batch_rolls_back():
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="HOLD_INVALID_FALSIFICATION_CONDITION"):
        engine.ingest_event_stream([(H, {"assertion": "a", "falsification_condition": {"mutable": True}})])
    assert engine.nodes == {} and not engine.known_ledger_hashes
    engine.ingest_event_stream([(H, {"assertion": "a", "falsification_condition": "testable"})])
    assert next(iter(engine.nodes.values())).falsification_condition == "testable"

def test_record_hash_lists_are_frozen_on_construction():
    engine = ConsolidationEngine()
    engine.ingest_event_stream([(H, {"assertion": "a"})])
    node = next(iter(engine.nodes.values()))
    hashes = [H]
    copy = replace(node, source_event_hashes=hashes)
    link = CausalLink(node.node_id, node.node_id, "reference", 0.5, hashes)
    hashes[0] = "b" * 64
    assert copy.source_event_hashes == (H,)
    assert link.evidence_hashes == (H,)

@pytest.mark.parametrize("bad", [
    b'{"assertion":"a","assertion":"b"}\n',
    b'{"assertion":"a","metadata":{"x":1,"x":2}}\n',
])
def test_duplicate_keys_are_not_clean_or_ingested(tmp_path, bad):
    path = tmp_path / "ledger.jsonl"
    raw = b'{"assertion":"valid"}\n' + bad
    path.write_bytes(raw)
    engine = ConsolidationEngine()
    report = engine.inspect_ledger_integrity(path)
    assert not report.is_clean and report.diagnostic.startswith("HOLD_LEDGER_JSON_UNSUPPORTED")
    with pytest.raises(ConsolidationError, match="HOLD_LEDGER_JSON_UNSUPPORTED"):
        engine.ingest_ledger_file(path)
    assert engine.nodes == {} and not engine.known_ledger_hashes
    assert path.read_bytes() == raw

def test_bridge_rejects_ambiguous_event_before_recording(tmp_path):
    path = tmp_path / "agent.jsonl"
    path.write_bytes(b'{"event":"TASK_STARTED","goal":"one","goal":"two"}\n')
    bridge = EpistemicLedgerBridge()
    with pytest.raises(BridgeError, match="malformed JSON"):
        bridge.ingest_agent_ledger(path)
    assert not bridge.guard.attributions and not bridge.engine.nodes

def test_unrelated_and_duplicate_evidence_are_not_corroboration():
    guard = SourceMonitoringGuard(allowlisted_tools={"run_tests"})
    assertion = "tool_exit:run_tests:sample:0"
    obs = guard.record_empirical_observation(assertion, "run_tests", "sample", 0, "out", "lock", attribution_id="obs")
    guard.create_hypothesis("unrelated", attribution_id="unrelated")
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion("unrelated", ["obs", "obs"])
    assert guard.attributions["unrelated"].veracity_state is VeracityState.UNSUPPORTED
    assert guard.attributions["unrelated"].parent_attribution_ids == ("obs",)
    guard.create_hypothesis(assertion, attribution_id="matched")
    result = guard.evaluate_claim_promotion("matched", ["obs", "obs"])
    assert result.veracity_state is VeracityState.VERIFIED_EMPIRICAL
    assert result.parent_attribution_ids == ("obs",)
    assert guard.filter_working_memory_candidates(["matched"], require_verified=True)
