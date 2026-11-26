"""R16 research-only probes against #315 head b02e805."""
import json, os, subprocess, sys
import pytest
from core.source_monitoring import SourceAttribution, SourceType, VeracityState
from core.memory_consolidation import ConsolidationEngine, ConsolidationError
from core.working_memory import WorkingMemoryBuffer

def hyp(i):
    return SourceAttribution(attribution_id=i, assertion=f"claim {i}", source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS, created_at="2026-01-01T00:00:00+00:00")

def wm_hash(attr, concept):
    cap = []
    class Spy(ConsolidationEngine):
        def ingest_event_stream(self, ev):
            ev = list(ev); cap.extend(ev); return super().ingest_event_stream(ev)
    w = WorkingMemoryBuffer(consolidation_engine=Spy())
    w.ingest(concept, attr.assertion, attr, salience=0.9); w.flush_to_long_term()
    return cap[0][0]

def test_decay_eviction_failure_must_not_lose_chunk():
    eng = ConsolidationEngine(); t = hyp("decay")
    eng.ingest_event_stream([(wm_hash(t, "d"), {"concept": "squat", "assertion": "other"})])
    wm = WorkingMemoryBuffer(consolidation_engine=eng, salience_decay_rate=1.0)
    wm.ingest("d", t.assertion, t, salience=0.5); wm.ingest("d", t.assertion, t, salience=0.5)
    with pytest.raises(ConsolidationError):
        wm.step_tick()
    assert "d" in [c.concept for c in wm.active_chunks]   # still present, or recorded; never silently gone
    assert wm.eviction_history == []

def test_batch_limit_is_explicitly_configurable_for_large_ledgers(tmp_path):
    p = tmp_path / "l.jsonl"
    p.write_text("".join(json.dumps({"concept": f"c{i%50}", "assertion": f"a{i}"}) + "\n" for i in range(5000)))
    with pytest.raises(ConsolidationError, match="HOLD_BATCH_TOO_LARGE"):
        ConsolidationEngine().ingest_ledger_file(p)               # default stays fail-closed
    eng = ConsolidationEngine(max_batch_events=10000)             # explicit, reviewed bound
    assert eng.ingest_ledger_file(p) == 5000
    with pytest.raises(ConsolidationError):
        ConsolidationEngine(max_batch_events=0)

@pytest.mark.xfail(strict=True, reason="DESIGN_HOLD: caller-chosen hashes allow squatting WM identity hashes")
def test_hash_squatting_must_not_wedge_working_memory():
    eng = ConsolidationEngine(); victim = hyp("victim")
    eng.ingest_event_stream([(wm_hash(victim, "c"), {"concept": "squat", "assertion": "unrelated"})])
    wm = WorkingMemoryBuffer(capacity=1, consolidation_engine=eng)
    wm.ingest("c", victim.assertion, victim, salience=0.9)
    wm.ingest("new", "claim new", hyp("new"), salience=0.95)
    assert "new" in [c.concept for c in wm.active_chunks]

# ---- positive baselines ----
def test_decay_eviction_still_works_when_save_succeeds():
    eng = ConsolidationEngine(); t = hyp("ok")
    wm = WorkingMemoryBuffer(consolidation_engine=eng, salience_decay_rate=1.0)
    wm.ingest("d", t.assertion, t, salience=0.5); wm.ingest("d", t.assertion, t, salience=0.5)
    recs = wm.step_tick()
    assert [r.concept for r in recs] == ["d"] and wm.active_chunks == [] and len(eng.nodes) == 1

def test_cli_memory_conflicts_small_ledger_still_works(tmp_path):
    p = tmp_path / "l.jsonl"
    p.write_text("".join(json.dumps({"concept": "c", "assertion": f"a{i}"}) + "\n" for i in range(10)))
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    r = subprocess.run([sys.executable, os.path.join(here, "ario_memory_cli.py"), "--memory-conflicts", "--ledger", str(p),
                        "--format", "json"], capture_output=True, text=True, cwd=here)
    assert r.returncode == 0 and json.loads(r.stdout)["total_nodes"] == 10
