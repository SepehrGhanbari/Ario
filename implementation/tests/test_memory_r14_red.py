"""R14 research-only RED probes against #313 head d83183a."""
import hashlib, sys, threading
import pytest
from core.source_monitoring import (SourceMonitoringGuard, SourceType, VeracityState,
    AttributionMismatchError, SourceMonitoringError, SelfCitationError)
from core.memory_consolidation import ConsolidationEngine
from core.working_memory import WorkingMemoryBuffer, MetacognitiveVerdict

H = lambda s: hashlib.sha256(s.encode()).hexdigest()
A = "tool_exit:run_tests:t:0"

def _mismatch_and_good(g):
    with pytest.raises(AttributionMismatchError):
        g.record_empirical_observation(A, "run_tests", "t", 0, "out", "WRONG-LOCK",
            attribution_id="bad", expected_execution_lock_sha256=H("REAL-LOCK"))
    g.record_empirical_observation(A, "run_tests", "t", 0, "out", "REAL-LOCK", attribution_id="good")

def test_lock_mismatch_record_cannot_be_laundered_by_promotion():
    g = SourceMonitoringGuard(); _mismatch_and_good(g)
    with pytest.raises(SourceMonitoringError):
        g.evaluate_claim_promotion("bad", ["good"])
    assert g.attributions["bad"].veracity_state == VeracityState.ATTRIBUTION_MISMATCH
    assert g.filter_working_memory_candidates(["bad"], require_verified=True) == []

def test_deep_lineage_failure_leaves_claim_unchanged():
    g = SourceMonitoringGuard(); prev = ()
    for i in range(sys.getrecursionlimit() + 50):
        g.create_hypothesis(f"h{i}", attribution_id=f"n{i}", parent_attribution_ids=prev); prev = (f"n{i}",)
    g.create_hypothesis("claim", attribution_id="claim")
    try:
        g.evaluate_claim_promotion("claim", [prev[0]])
    except SelfCitationError:
        pass  # unsupported is the correct outcome; it must be recorded as a revision
    claim = g.attributions["claim"]
    hist = g.attribution_history("claim")
    # Either untouched, or the change is visible in history; never a silent overwrite.
    assert claim == hist[-1]

def test_concurrent_failed_batch_does_not_erase_other_commit():
    eng = ConsolidationEngine(); started = threading.Event()
    def bad_batch():
        yield (H("a1"), {"concept": "x", "assertion": "A first"})
        started.set(); threading.Event().wait(0.3)
        yield ("not-a-hash", {})
    def run_a():
        with pytest.raises(Exception):
            eng.ingest_event_stream(bad_batch())
    ta = threading.Thread(target=run_a); ta.start(); started.wait()
    tb = threading.Thread(target=lambda: eng.ingest_event_stream([(H("b1"), {"concept": "y", "assertion": "B committed"})]))
    tb.start(); ta.join(); tb.join()
    assert H("b1") in eng.known_ledger_hashes
    assert any(n.concept == "y" for n in eng.nodes.values())
    assert H("a1") not in eng.known_ledger_hashes

def test_hash_case_is_canonical_for_replay_and_collision():
    eng = ConsolidationEngine(); h = H("e1")
    eng.ingest_event_stream([(h, {"concept": "c", "assertion": "claim"})])
    with pytest.raises(Exception):
        eng.ingest_event_stream([(h.upper(), {"concept": "c", "assertion": "claim", "extra": "DIFFERENT"})])
    assert eng.ingest_event_stream([(h.upper(), {"concept": "c", "assertion": "claim"})]) == 0
    assert len(list(eng.nodes.values())[0].source_event_hashes) == 1

def test_bool_exit_code_rejected():
    with pytest.raises(SourceMonitoringError):
        SourceMonitoringGuard().record_empirical_observation(
            "tool_exit:run_tests:t:False", "run_tests", "t", False, "o", "l")

# ---- positive baselines ----
def test_genuine_bound_observation_still_grounds_working_memory():
    g = SourceMonitoringGuard(); _mismatch_and_good(g)
    wm = WorkingMemoryBuffer(source_guard=g); wm.ingest("t", A, g.attributions["good"], salience=0.9)
    assert wm.metacognitive_assessment().verdict == MetacognitiveVerdict.FOCUSED_SUFFICIENCY

def test_hypothesis_with_exact_bound_evidence_still_promotes():
    g = SourceMonitoringGuard(); _mismatch_and_good(g)
    g.create_hypothesis(A, attribution_id="hyp")
    assert g.evaluate_claim_promotion("hyp", ["good"]).veracity_state == VeracityState.VERIFIED_EMPIRICAL
    assert len(g.attribution_history("hyp")) == 2

def test_sequential_batches_and_rollback_still_work():
    eng = ConsolidationEngine()
    assert eng.ingest_event_stream([(H("s1"), {"concept": "k", "assertion": "a"})]) == 1
    with pytest.raises(Exception):
        eng.ingest_event_stream([(H("s2"), {"concept": "k", "assertion": "b"}), ("bad", {})])
    assert eng.known_ledger_hashes == {H("s1")}
