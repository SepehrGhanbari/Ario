"""R13: distinguish raw claims and repeated author-controlled IDs from independent proof."""
import hashlib
import pytest
from core.memory_consolidation import ConsolidationEngine,NodeEpistemicStatus

def event_hash(i):
    return hashlib.sha256(f"research-only-{i}".encode()).hexdigest()

def make_hypothesis(i,assertion="publisher's unverified statement"):
    return {"concept":"subject","assertion":assertion,"source_type":"INTERNAL_HYPOTHESIS",
            "veracity_state":"UNVERIFIED_HYPOTHESIS","attribution_id":f"PUBLISHER-{i}",
            "status":"RECORDED"}

def test_synthetic_hypothesis_ids_do_not_multiply_support():
    e=ConsolidationEngine(node_id_version="v2")
    for i in range(5): e.ingest_event_stream([(event_hash(i),make_hypothesis(i))])
    node=next(iter(e.nodes.values()))
    assert len(node.source_event_hashes)==5  # preserve all events, no erasure
    assert node.reinforcement_count==1
    assert node.saliency_score==0.7
    assert node.status==NodeEpistemicStatus.RECORDED
    assert e.validate_lineage_integrity()

def test_unmarked_raw_duplicates_do_not_create_independent_reinforcement():
    e=ConsolidationEngine(node_id_version="v2")
    for i in range(3):
        e.ingest_event_stream([(event_hash("unknown"+str(i)),{"concept":"n","assertion":"same thing"})])
    node=next(iter(e.nodes.values()))
    assert len(node.source_event_hashes)==3
    assert node.reinforcement_count==1

def test_new_unreviewed_event_defaults_to_recorded():
    e=ConsolidationEngine(node_id_version="v2")
    e.ingest_event_stream([(event_hash("raw"),{"concept":"n","assertion":"unproven"})])
    assert next(iter(e.nodes.values())).status==NodeEpistemicStatus.RECORDED

def test_arbitrary_caller_accepted_or_supported_status_is_not_truth():
    for attempted in ["SUPPORTED","ACCEPTED"]:
        e=ConsolidationEngine(node_id_version="v2")
        e.ingest_event_stream([(event_hash(attempted),{"concept":"n","assertion":"unproven","status":attempted})])
        assert next(iter(e.nodes.values())).status==NodeEpistemicStatus.RECORDED

def test_distinct_claims_are_still_retained_without_false_consensus():
    e=ConsolidationEngine(node_id_version="v2")
    e.ingest_event_stream([(event_hash("yes"),{"concept":"decision","assertion":"A","value":"YES"})])
    node=next(iter(e.nodes.values()))
    e.ingest_event_stream([(event_hash("no"),{"concept":"decision","assertion":"not A","negates":node.node_id})])
    assert len(e.nodes)==2
    assert all(n.status==NodeEpistemicStatus.CONTESTED for n in e.nodes.values())

def test_replaying_same_event_hash_does_not_increment_reinforcement():
    e=ConsolidationEngine(node_id_version="v2")
    h=event_hash("x"); event={"concept":"x","assertion":"same"}
    e.ingest_event_stream([(h,event)])
    e.ingest_event_stream([(h,event)])
    node=next(iter(e.nodes.values()))
    assert node.reinforcement_count==1
    assert len(node.source_event_hashes)==1
