"""R14.1 exploratory concurrency-isolation probes against R14-only correction."""
import hashlib
import threading
import time
import pytest
from core.memory_consolidation import ConsolidationEngine
from core.source_monitoring import EmpiricalProvenance, SourceMonitoringError

def h(t): return hashlib.sha256(t.encode()).hexdigest()

def test_reader_cannot_observe_partial_failed_batch():
    eng=ConsolidationEngine()
    first=threading.Event()
    observed=[]
    def bad_batch():
        yield h("bad-first"),{"concept":"ghost","assertion":"not durable"}
        first.set()
        assert release.wait(1.0)
        yield "BAD_HASH",{}
    release=threading.Event()
    errors=[]
    def writer():
        try:eng.ingest_event_stream(bad_batch())
        except Exception as e:errors.append(type(e).__name__)
    t=threading.Thread(target=writer);t.start()
    assert first.wait(1.0)
    read_t=threading.Thread(target=lambda:observed.append(eng.nodes.copy()))
    read_t.start()
    time.sleep(.05)
    release.set()
    t.join(timeout=2);read_t.join(timeout=2)
    assert errors and not t.is_alive() and not read_t.is_alive()
    assert observed==[{}]   # only committed snapshot visible

def test_failed_batch_must_not_erase_parallel_saliency_decay():
    eng=ConsolidationEngine(decay_rate=.5)
    eng.ingest_event_stream([(h("stable"),{"concept":"stable","assertion":"there"})])
    first=threading.Event();release=threading.Event()
    def bad_batch():
        yield h("transient"),{"concept":"ghost","assertion":"here"}
        first.set();assert release.wait(1.0)
        yield "INVALID",{}
    def writer():
        with pytest.raises(Exception):
            eng.ingest_event_stream(bad_batch())
    t=threading.Thread(target=writer);t.start();assert first.wait(1.0)
    decayer=threading.Thread(target=lambda:eng.apply_saliency_decay(cycles=1))
    decayer.start();time.sleep(.05);release.set()
    t.join(timeout=2);decayer.join(timeout=2)
    assert not t.is_alive() and not decayer.is_alive()
    assert round(next(iter(eng.nodes.values())).saliency_score,3)==.35
    assert len(eng.nodes)==1

def test_nested_generator_ingest_must_not_commit_silently_then_rollback():
    eng=ConsolidationEngine()
    successful_returns=[]
    def bad():
        yield h("outer"), {"concept":"outer","assertion":"outer"}
        successful_returns.append(eng.ingest_event_stream([
            (h("inner"),{"concept":"inner","assertion":"inner"})]))
        yield "BAD",{}
    with pytest.raises(Exception):
        eng.ingest_event_stream(bad())
    # The inner commit must NOT report success then disappear; reject nested
    # ingestion upfront instead, leaving no hidden successful return.
    assert successful_returns==[]
    assert eng.nodes=={}

def test_boolean_exit_code_from_serialized_provenance_must_reject():
    data={"tool":"run_tests","target":"test","exit_code":False,
    "execution_lock_sha256":"a"*64,"stdout_sha256":"b"*64,"recorded_at":"x"}
    with pytest.raises((SourceMonitoringError,ValueError,TypeError)):
        EmpiricalProvenance.from_dict(data)
