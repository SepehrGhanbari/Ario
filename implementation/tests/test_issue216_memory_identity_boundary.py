"""Issue #216: concrete collision refusal and research identity/status contracts."""
import hashlib
import json

import pytest

from core.memory_consolidation import (
    ConsolidationEngine, ConsolidationError, NodeEpistemicStatus, ledger_line_digests,
)

PAIRS = (("a:b", "c"), ("a", "b:c"))


def event(pair, **extra):
    record = dict(concept=pair[0], assertion=pair[1], **extra)
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest(), record


def recover(engine):
    raw = engine.to_snapshot()
    return ConsolidationEngine.from_snapshot(raw, expected_sha256=hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize("order", [PAIRS, PAIRS[::-1]])
def test_v1_collision_refuses_entire_batch_without_conflating_lineage(order):
    engine = ConsolidationEngine(node_id_version="v1")
    first, second = map(event, order)
    assert engine.compute_node_id(*order[0]) == engine.compute_node_id(*order[1])
    empty = engine.to_snapshot()
    with pytest.raises(ConsolidationError, match="HOLD_SEMANTIC_NODE_ID_COLLISION"):
        engine.ingest_event_stream([first, second])
    assert engine.to_snapshot() == empty
    assert engine.ingest_event_stream([first]) == 1
    original = engine.to_snapshot()
    for current in (engine, recover(engine)):
        with pytest.raises(ConsolidationError, match="HOLD_SEMANTIC_NODE_ID_COLLISION"):
            current.ingest_event_stream([event(("unrelated", "prefix")), second])
        assert current.to_snapshot() == original
        assert current.known_ledger_hashes == {first[0]}
        assert next(iter(current.nodes.values())).source_event_hashes == (first[0],)
        assert current.ingest_event_stream([first]) == 0


@pytest.mark.parametrize("order", [PAIRS, PAIRS[::-1]])
def test_v2_ambiguous_alias_is_not_a_negation_target_after_recovery(order):
    engine = ConsolidationEngine(node_id_version="v2")
    engine.ingest_event_stream(map(event, order))
    engine = recover(engine)
    alias = engine.compute_node_id(*order[0], version="v1")
    assert engine.resolve_node_id(alias) is None
    ids = [engine.compute_node_id(*pair, version="v2") for pair in order]
    assert len(set(ids)) == 2
    # The existing raw-event interface accepts exact negation targets only.
    engine.ingest_event_stream([event((order[0][0], "different"), negates=alias)])
    assert all(engine.get_node(i).status == NodeEpistemicStatus.RECORDED for i in ids)
    engine.ingest_event_stream([event((order[0][0], "explicit opposition"), negates=ids[0])])
    assert engine.get_node(ids[0]).status == NodeEpistemicStatus.CONTESTED
    assert engine.get_node(ids[1]).status == NodeEpistemicStatus.RECORDED
    assert recover(engine).resolve_node_id(alias) is None


def test_v2_digest_collision_guard_even_if_digest_provider_collides(monkeypatch):
    engine = ConsolidationEngine(node_id_version="v2")
    original_compute = ConsolidationEngine.compute_node_id
    forced = original_compute("first", "claim", version="v2")

    def collide(concept, assertion, version="v1"):
        return forced if version == "v2" else original_compute(concept, assertion, version)

    monkeypatch.setattr(ConsolidationEngine, "compute_node_id", staticmethod(collide))
    before = engine.to_snapshot()
    with pytest.raises(ConsolidationError, match="HOLD_SEMANTIC_NODE_ID_COLLISION"):
        engine.ingest_event_stream([event(("first", "claim")), event(("other", "claim"))])
    assert engine.to_snapshot() == before


@pytest.mark.parametrize("version", ["v1", "v2"])
@pytest.mark.parametrize("label", ["ACCEPTED", "SUPPORTED", "REVISED"])
def test_untrusted_raw_label_is_not_an_authorized_assessment(version, label):
    engine = ConsolidationEngine(node_id_version=version)
    record = event(("claim", "unverified report"), status=label)
    assert engine.ingest_event_stream([record]) == 1
    assert engine.ingest_event_stream([record] * 100) == 0
    restored = recover(engine)
    node = next(iter(restored.nodes.values()))
    assert node.status == NodeEpistemicStatus.RECORDED
    assert node.reinforcement_count == 1
    assert node.source_event_hashes == (record[0],)


def test_current_v2_encoding_and_line_scheme_are_explicit_not_a_new_id_version():
    # Keep the actual 16-hex research encoding, not the proposed full-hash version.
    pairs = [("é", "x"), ("e\u0301", "x")]
    for pair in pairs:
        canonical = json.dumps(list(pair), separators=(",", ":"), sort_keys=True)
        expected = "SEM-v2-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
        assert ConsolidationEngine.compute_node_id(*pair, version="v2") == expected
    assert len({ConsolidationEngine.compute_node_id(*p, version="v2") for p in pairs}) == 2
    line = b'{"goal":"same"}'
    values = [ledger_line_digests(v) for v in (line+b"\n", line+b"\r\n", b" "+line+b"\n")]
    assert len({v[0] for v in values}) == 1
    assert len({v[1] for v in values}) == 3
