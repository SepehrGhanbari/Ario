"""Exploratory R12 post-patch RED probes; these tests are not part of Perplexity's R12."""
import pytest
from core.memory_consolidation import ConsolidationEngine
from core.source_monitoring import SourceAttribution, SourceType, VeracityState
from core.working_memory import WorkingMemoryBuffer

def hyp(i):
    return SourceAttribution(
        attribution_id=f"r12-followup-{i}", assertion=f"statement-{i}",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
    )

class SucceedsOnceOnly:
    def __init__(self): self.called=0
    def __deepcopy__(self, memo):
        self.called+=1
        if self.called>=2: raise RuntimeError("second copy intentionally fails")
        return self

def test_failed_returned_snapshot_cannot_erase_prior_memory():
    engine=ConsolidationEngine()
    wm=WorkingMemoryBuffer(capacity=1,consolidation_engine=engine)
    good=wm.ingest("keep", "statement-1", hyp(1), salience=.9)
    payload=SucceedsOnceOnly()
    with pytest.raises(RuntimeError,match="second copy"):
        wm.ingest("attack", "statement-2", hyp(2), salience=.1,
                  metadata={"object":payload})
    assert wm.active_chunks[0].chunk_id==good.chunk_id
    assert wm.eviction_history==[]
    assert len(engine.nodes)==0

def test_runtime_capacity_mutation_must_not_disable_bound():
    wm=WorkingMemoryBuffer(capacity=4)
    with pytest.raises((ValueError,TypeError)):
        wm.capacity=float("nan")

def test_recall_flush_does_not_report_phantom_new_consolidation():
    engine=ConsolidationEngine()
    wm=WorkingMemoryBuffer(consolidation_engine=engine)
    wm.ingest("bridge","statement-1",hyp(1),salience=.6)
    wm.flush_to_long_term()
    n=engine.retrieve_active_context("bridge")[0]
    before=n.reinforcement_count
    remembered=WorkingMemoryBuffer(consolidation_engine=engine)
    r=remembered.recall_from_long_term("bridge")
    assert r
    flushed=remembered.flush_to_long_term()
    assert engine.retrieve_active_context("bridge")[0].reinforcement_count == before
    assert flushed==[], "flushing recalled evidence must not claim a new LTM consolidation"
