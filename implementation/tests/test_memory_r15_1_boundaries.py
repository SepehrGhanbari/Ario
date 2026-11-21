"""R15.1: failure-path and resource-bound probes on R15-only candidate."""
import hashlib
import pytest
from core.memory_consolidation import ConsolidationEngine, ConsolidationError
from core.source_monitoring import SourceAttribution,SourceType,VeracityState
from core.working_memory import WorkingMemoryBuffer

def h(x):
    return hashlib.sha256(x.encode()).hexdigest()

class ConflictingSameHashEngine(ConsolidationEngine):
    def __init__(self):
        super().__init__()
        self.injected = False
    def ingest_event_stream(self, events):
        records = list(events)
        if records and not self.injected:
            self.injected = True
            super().ingest_event_stream([(records[0][0],{"concept":"forged","assertion":"fake"})])
        return super().ingest_event_stream(records)

def hyp(i):
    return SourceAttribution(attribution_id=str(i),assertion="claim "+str(i),
        source_type=SourceType.INTERNAL_HYPOTHESIS,
        veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS)

def test_wrong_content_at_existing_hash_must_not_claim_success_or_evict():
    engine=ConflictingSameHashEngine()
    wm=WorkingMemoryBuffer(capacity=1,consolidation_engine=engine)
    original=wm.ingest("original",hyp("a").assertion,hyp("a"),salience=.95)
    with pytest.raises(ConsolidationError,match="REUSED_HASH"):
        wm.ingest("new",hyp("b").assertion,hyp("b"),salience=.3)
    assert wm.active_chunks[0].chunk_id==original.chunk_id
    assert wm.eviction_history==[]

def test_engine_getstate_is_stable_after_decay():
    engine=ConsolidationEngine(decay_rate=.5)
    engine.ingest_event_stream([(h("stable"),{"concept":"stable","assertion":"source"})])
    snapshot=engine.__getstate__()
    before=next(iter(snapshot["_nodes"].values())).saliency_score
    engine.apply_saliency_decay(cycles=1)
    assert next(iter(snapshot["_nodes"].values())).saliency_score==before

def test_unbounded_batch_fails_closed_before_exhausting_generator():
    engine=ConsolidationEngine()
    counter=[0]
    def generated():
        for n in range(5000):
            counter[0]+=1
            if counter[0]>4097:raise RuntimeError("too many events visited")
            yield (h(str(n)),{"concept":"event","assertion":str(n)})
    with pytest.raises(ConsolidationError,match="HOLD_BATCH_TOO_LARGE"):
        engine.ingest_event_stream(generated())
    assert counter[0]<=4097
    assert engine.nodes=={} and engine.known_ledger_hashes==set()

def sample(salience=.7):
    return {"status":"RECORDED","concept":"x","assertion":"x",
        "saliency_score":salience,"attribution_id":"a",
        "source_type":"INTERNAL_HYPOTHESIS","veracity_state":"UNVERIFIED_HYPOTHESIS",
        "promoted_from_working_memory":True,"timestamp":"2026-01-01T00:00:00+00:00"}

def test_same_source_replay_different_attention_does_not_reinforce():
    engine=ConsolidationEngine()
    assert engine.ingest_event_stream([(h("identity"),sample(.9))])==1
    assert engine.ingest_event_stream([(h("identity"),sample(.2))])==0
    assert next(iter(engine.nodes.values())).reinforcement_count==1

def test_same_hash_modified_source_fields_must_be_rejected():
    engine=ConsolidationEngine()
    engine.ingest_event_stream([(h("identity"),sample(.9))])
    forged=dict(sample(.2),attribution_id="fake")
    with pytest.raises(ConsolidationError,match="REUSED_HASH"):
        engine.ingest_event_stream([(h("identity"),forged)])


def test_ledger_file_loader_stops_before_consuming_unbounded_lines(tmp_path, monkeypatch):
    import builtins
    import json
    from pathlib import Path
    original_open = builtins.open
    ledger = tmp_path / "large_fixture.jsonl"
    with original_open(ledger, "w", encoding="utf8") as out:
        for i in range(4200):
            out.write(json.dumps({"concept": "x", "assertion": str(i)}) + "\n")
    seen = [0]
    class CountedInput:
        def __init__(self, file):
            self.file = file
            self.iterator = iter(file)
        def __enter__(self):
            return self
        def __exit__(self, *args):
            self.file.close()
        def __iter__(self):
            return self
        def __next__(self):
            seen[0] += 1
            if seen[0] > 4097:
                raise RuntimeError("file stream consumed past memory limit")
            return next(self.iterator)
        def readline(self, size=-1):
            # R16.1 reads bounded physical lines; count them like iteration.
            seen[0] += 1
            if seen[0] > 4097:
                raise RuntimeError("file stream consumed past memory limit")
            return self.file.readline(size)
    def guarded_open(path, mode="r", *args, **kwargs):
        f = original_open(path, mode, *args, **kwargs)
        return CountedInput(f) if str(path) == str(ledger) and mode == "rb" else f
    monkeypatch.setattr(builtins, "open", guarded_open)
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="HOLD_BATCH_TOO_LARGE"):
        engine.ingest_ledger_file(ledger)
    assert seen[0] <= 4097
    assert engine.nodes == {}
    assert engine.known_ledger_hashes == set()
