"""R11: adversarial numerical-bound and returned-event mutation tests.

RESEARCH_ONLY: deliberately RED against R07 head before any patch.
"""
import math
import pytest

from core.source_monitoring import SourceAttribution, SourceType, VeracityState
from core.working_memory import WorkingMemoryBuffer, ChunkState

def hypothesis(i: int):
    return SourceAttribution(
        attribution_id=f"r11-hyp-{i}",
        assertion=f"synthetic hypothesis {i}",
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
    )

@pytest.mark.parametrize("capacity", [float("nan"), float("inf"), 4.1, True, 0])
def test_capacity_must_be_positive_finite_integer(capacity):
    with pytest.raises((TypeError, ValueError)):
        WorkingMemoryBuffer(capacity=capacity)

@pytest.mark.parametrize("decay_rate", [float("nan"), float("inf"), -1.0, 1.1])
def test_invalid_decay_rate_must_be_rejected(decay_rate):
    with pytest.raises((TypeError, ValueError)):
        WorkingMemoryBuffer(salience_decay_rate=decay_rate)

@pytest.mark.parametrize("threshold", [float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_consolidation_threshold_must_be_rejected(threshold):
    with pytest.raises((TypeError, ValueError)):
        WorkingMemoryBuffer(consolidation_threshold=threshold)

@pytest.mark.parametrize("salience", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_initial_salience_must_be_rejected_without_eviction(salience):
    wm = WorkingMemoryBuffer(capacity=1)
    original = wm.ingest("keep", "synthetic hypothesis 1", hypothesis(1), salience=0.7)
    with pytest.raises((TypeError, ValueError)):
        wm.ingest("attack", "synthetic hypothesis 2", hypothesis(2), salience=salience)
    assert wm.active_count == 1
    assert wm.active_chunks[0].chunk_id == original.chunk_id
    assert wm.eviction_history == []

@pytest.mark.parametrize("salience", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_reingestion_salience_must_be_rejected_before_rehearsal(salience):
    wm = WorkingMemoryBuffer()
    a = hypothesis(3)
    before = wm.ingest("x", a.assertion, a, salience=0.5)
    with pytest.raises((TypeError, ValueError)):
        wm.ingest("x", a.assertion, a, salience=salience)
    assert wm.active_chunks[0].salience == before.salience
    assert wm.active_chunks[0].access_count == before.access_count

def test_step_tick_eviction_returns_a_snapshot_not_editable_history():
    wm = WorkingMemoryBuffer(capacity=1, salience_decay_rate=1.0)
    a = hypothesis(4)
    wm.ingest("x", a.assertion, a, salience=0.5)
    outgoing = wm.step_tick()
    assert len(outgoing) == 1
    outgoing[0].reason = "SYNTHETIC_FORGED"
    outgoing[0].final_salience = 0.8
    actual = wm.eviction_history[0]
    assert actual.reason == "salience_decay_to_zero"
    assert actual.final_salience == 0.0
    assert actual.fate == ChunkState.DECAYED_FORGOTTEN

def test_legitimate_default_capacity_and_rehearsal_preserved():
    wm = WorkingMemoryBuffer(capacity=4)
    for i in range(9):
        a = hypothesis(100 + i)
        wm.ingest(f"c{i}", a.assertion, a, salience=0.2 + (i % 3) * 0.1)
        assert 0 <= wm.active_count <= 4
    assert wm.active_count == 4
    for ch in wm.active_chunks:
        assert math.isfinite(ch.salience)
    assert len(wm.eviction_history) == 5

