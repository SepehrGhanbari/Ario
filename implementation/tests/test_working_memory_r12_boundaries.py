"""R12 research-only RED probes against #308 head 05f1c3c."""
import math, threading
import pytest
from core.source_monitoring import SourceAttribution, SourceType, VeracityState, SourceMonitoringGuard
from core.working_memory import WorkingMemoryBuffer
from core.memory_consolidation import ConsolidationEngine

def hyp(i, created_at=None):
    kw = {"created_at": created_at} if created_at else {}
    return SourceAttribution(attribution_id=f"r12-{i}", assertion=f"h {i}",
        source_type=SourceType.INTERNAL_HYPOTHESIS, veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS, **kw)

def test_uncopyable_metadata_must_not_evict_or_promote_first():
    eng = ConsolidationEngine(); wm = WorkingMemoryBuffer(capacity=1, consolidation_engine=eng)
    wm.ingest("keep", "h 1", hyp(1), salience=0.9)
    with pytest.raises(Exception):
        wm.ingest("attack", "h 2", hyp(2), salience=0.1, step=50, metadata={"x": threading.Lock()})
    assert wm.active_count == 1 and wm.eviction_history == [] and eng.nodes == {} and wm._current_step == 0

def test_uncopyable_metadata_must_not_partially_rehearse():
    wm = WorkingMemoryBuffer(); a = hyp(3); before = wm.ingest("x", a.assertion, a, salience=0.2)
    with pytest.raises(Exception):
        wm.ingest("x", a.assertion, a, salience=0.2, metadata={"x": threading.Lock()})
    after = wm.active_chunks[0]
    assert (after.access_count, after.salience) == (before.access_count, before.salience)

@pytest.mark.parametrize("step", [float("inf"), float("nan"), -1, 2.5, True])
def test_invalid_step_rejected_without_mutation(step):
    wm = WorkingMemoryBuffer()
    with pytest.raises((TypeError, ValueError)):
        wm.ingest("a", "h 4", hyp(4), step=step)
    with pytest.raises((TypeError, ValueError)):
        wm.step_tick(step=step)
    with pytest.raises((TypeError, ValueError)):
        wm.access("missing", step=step)
    assert wm.active_count == 0 and wm._current_step == 0

@pytest.mark.parametrize("guarded", [False, True])
def test_recall_then_flush_must_not_self_reinforce(guarded):
    eng = ConsolidationEngine(); g = SourceMonitoringGuard() if guarded else None
    s = g.create_hypothesis("the bridge is safe", attribution_id="seed") if g else SourceAttribution(
        attribution_id="seed", assertion="the bridge is safe", source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS, created_at="2026-01-01T00:00:00+00:00")
    seed = WorkingMemoryBuffer(consolidation_engine=eng, source_guard=g)
    seed.ingest("bridge", s.assertion, s, salience=0.3); seed.flush_to_long_term()
    for _ in range(5):
        w = WorkingMemoryBuffer(consolidation_engine=eng, source_guard=g)
        w.recall_from_long_term("bridge"); w.flush_to_long_term()
        for k in range(4):  # force the eviction path too
            f = g.create_hypothesis(f"h f{k}", attribution_id=f"r12-f{k}") if g else hyp(f"f{k}")
            w.ingest(f"filler{k}", f.assertion, f)
    node = list(n for n in eng.nodes.values() if n.concept == "bridge")[0]
    assert node.reinforcement_count == 1 and len(node.source_event_hashes) == 1

@pytest.mark.parametrize("salience", ["0.95", b"0.9", True])
def test_non_numeric_salience_rejected(salience):
    with pytest.raises((TypeError, ValueError)):
        WorkingMemoryBuffer().ingest("s", "h s", hyp("s"), salience=salience)

# ---- positive regressions ----
def test_valid_int_steps_and_metadata_still_work():
    eng = ConsolidationEngine(); wm = WorkingMemoryBuffer(capacity=1, consolidation_engine=eng)
    wm.ingest("a", "h a", hyp("a"), salience=0.9, step=3, metadata={"k": [1]})
    wm.ingest("b", "h b", hyp("b"), salience=0.2, step=4)
    assert wm.active_count == 1 and len(wm.eviction_history) == 1 and len(eng.nodes) == 1
    assert wm.step_tick() and wm._current_step == 5 or wm._current_step == 5

def test_recalled_chunk_still_usable_and_genuine_new_evidence_still_reinforces():
    eng = ConsolidationEngine()
    w1 = WorkingMemoryBuffer(consolidation_engine=eng)
    w1.ingest("bridge", "the bridge is safe", hyp("e1", "2026-01-01T00:00:00+00:00"), salience=0.9); w1.flush_to_long_term()
    w2 = WorkingMemoryBuffer(consolidation_engine=eng)
    rec = w2.recall_from_long_term("bridge"); assert rec and rec[0].metadata["recalled_from_ltm"]
    second = SourceAttribution(attribution_id="r12-e2", assertion="the bridge is safe",
        source_type=SourceType.INTERNAL_HYPOTHESIS, veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
        created_at="2026-01-02T00:00:00+00:00")
    w2.ingest("bridge", "the bridge is safe", second, salience=0.9); w2.flush_to_long_term()
    assert list(eng.nodes.values())[0].reinforcement_count == 2
