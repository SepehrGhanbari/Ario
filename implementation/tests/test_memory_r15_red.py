"""R15 research-only RED probes against #314 head e661141."""
import copy, hashlib, pickle, threading, time
import pytest
from core.source_monitoring import SourceMonitoringGuard, SourceAttribution, SourceType, VeracityState
from core.memory_consolidation import ConsolidationEngine
from core.working_memory import WorkingMemoryBuffer

H = lambda s: hashlib.sha256(s.encode()).hexdigest()

def hyp(i, created_at="2026-01-01T00:00:00+00:00"):
    return SourceAttribution(attribution_id=i, assertion=f"claim {i}", source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS, created_at=created_at)

def test_generator_cannot_observe_uncommitted_batch_state():
    eng = ConsolidationEngine(); wm = WorkingMemoryBuffer(consolidation_engine=eng); seen = {}
    def gen():
        yield (H("u1"), {"concept": "bridge", "assertion": "uncommitted claim"})
        seen["nodes"] = len(eng.nodes)
        wm.recall_from_long_term("bridge")
        yield ("bad", {})
    with pytest.raises(Exception):
        eng.ingest_event_stream(gen())
    assert seen["nodes"] == 0
    assert wm.active_chunks == []

def test_stalled_generator_does_not_block_readers():
    eng = ConsolidationEngine(); go = threading.Event()
    def slow():
        yield (H("s1"), {"concept": "x", "assertion": "a"}); go.wait(5)
    t = threading.Thread(target=lambda: eng.ingest_event_stream(slow())); t.start(); time.sleep(0.1)
    r = threading.Thread(target=lambda: eng.nodes); r.start(); r.join(1.0)
    blocked = r.is_alive(); go.set(); t.join(); r.join()
    assert not blocked

def test_filter_candidates_returns_snapshots_not_live_registry():
    g = SourceMonitoringGuard()
    g.record_empirical_observation("tool_exit:run_tests:t:0", "run_tests", "t", 0, "o", "l", attribution_id="good")
    g.filter_working_memory_candidates(["good"])[0].provenance.metadata["expected_lock_sha256"] = "FORGED"
    assert g.attributions["good"].provenance.metadata == {}
    g.record_empirical_observation("tool_exit:run_tests:t:0", "run_tests", "t", 0, "o", "l", attribution_id="good")

@pytest.mark.parametrize("op", [copy.deepcopy, lambda e: pickle.loads(pickle.dumps(e))])
def test_engine_snapshot_copy_still_possible(op):
    eng = ConsolidationEngine(); eng.ingest_event_stream([(H("c1"), {"concept": "k", "assertion": "a"})])
    clone = op(eng)
    assert clone.known_ledger_hashes == eng.known_ledger_hashes
    clone.ingest_event_stream([(H("c2"), {"concept": "k", "assertion": "b"})])
    assert H("c2") not in eng.known_ledger_hashes

class _RacyEngine(ConsolidationEngine):
    hook = None
    @property
    def known_ledger_hashes(self):
        s = ConsolidationEngine.known_ledger_hashes.fget(self)
        if _RacyEngine.hook:
            h, _RacyEngine.hook = _RacyEngine.hook, None; h()
        return s

def test_concurrent_promotion_of_same_evidence_does_not_lose_chunks():
    eng = _RacyEngine(); attr = hyp("same")
    wa = WorkingMemoryBuffer(consolidation_engine=eng); wa.ingest("c", attr.assertion, attr, salience=0.9)
    wb = WorkingMemoryBuffer(capacity=1, consolidation_engine=eng); wb.ingest("c", attr.assertion, attr, salience=0.7)
    _RacyEngine.hook = lambda: wa.flush_to_long_term()   # A commits between B's check and B's ingest
    wb.ingest("o", "claim o", hyp("o"), salience=0.5)
    assert [c.concept for c in wb.active_chunks] == ["o"]
    assert len(wb.eviction_history) == 1
    assert len(list(eng.nodes.values())[0].source_event_hashes) == 1

# ---- positive baselines ----
def test_valid_batch_and_rollback_still_work():
    eng = ConsolidationEngine()
    assert eng.ingest_event_stream(iter([(H("p1"), {"concept": "k", "assertion": "a"})])) == 1
    with pytest.raises(Exception):
        eng.ingest_event_stream(iter([(H("p2"), {"concept": "k", "assertion": "b"}), ("bad", {})]))
    assert eng.known_ledger_hashes == {H("p1")}

def test_concurrent_valid_batches_both_commit():
    eng = ConsolidationEngine()
    ts = [threading.Thread(target=lambda i=i: eng.ingest_event_stream([(H(f"t{i}"), {"concept": "k", "assertion": f"a{i}"})])) for i in range(8)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(eng.known_ledger_hashes) == 8
