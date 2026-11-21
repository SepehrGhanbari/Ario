"""R13.1 batch failure must not leave a prefix accepted."""
import hashlib
import pytest
from core.memory_consolidation import ConsolidationEngine,ConsolidationError
def h(x): return hashlib.sha256(x.encode()).hexdigest()
def test_invalid_second_hash_does_not_commit_first():
    e=ConsolidationEngine()
    with pytest.raises(ConsolidationError):
        e.ingest_event_stream([(h("a"),{"concept":"c","assertion":"a"}),("bad",{"concept":"c","assertion":"b"})])
    assert e.nodes=={} and e.known_ledger_hashes==set()
def test_reused_hash_conflicting_payload_is_atomic():
    e=ConsolidationEngine()
    with pytest.raises(ConsolidationError,match="REUSED_HASH"):
        e.ingest_event_stream([(h("same"),{"concept":"c","assertion":"a"}),(h("same"),{"concept":"c","assertion":"b"})])
    assert e.nodes=={} and e.known_ledger_hashes==set()
def test_wrong_event_type_rolls_back_whole_batch():
    e=ConsolidationEngine()
    with pytest.raises((ConsolidationError,TypeError,AttributeError)):
        e.ingest_event_stream([(h("a"),{"concept":"c","assertion":"a"}),(h("wrong"),["not","a","dict"])])
    assert e.nodes=={} and e.known_ledger_hashes==set()
def test_good_batch_preserves_all_event_hashes_without_self_reinforcement():
    e=ConsolidationEngine()
    assert e.ingest_event_stream([(h("a"),{"concept":"c","assertion":"a"}),(h("b"),{"concept":"c","assertion":"a"})])==2
    n=next(iter(e.nodes.values()))
    assert set(n.source_event_hashes)=={h("a"),h("b")} and n.reinforcement_count==1
