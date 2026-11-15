"""Ario #210: source-grounded RED probes, intentionally xfailed while unresolved.

Review-only; branch is stacked on feature/cognitive-memory-consolidation.
These are *proposed* contracts, not agreed project acceptance criteria.
Each xfail is preserved as a reported negative, not a security pass.
Never treat passing CI with xfails as successful defense validation.
No identity/status/memory authority is conferred by this test module.
"""

import hashlib
import json

import pytest

from core.memory_consolidation import ConsolidationEngine, ConsolidationError


def digest(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@pytest.mark.xfail(strict=True, reason="RED: repeated event must not inflate memory reinforcement")
def test_repeat_same_event_not_independent_reinforcement():
    engine = ConsolidationEngine()
    event = {"concept": "x", "assertion": "report"}
    h = digest("same-record")
    engine.ingest_event_stream([(h, event)])
    original = next(iter(engine.nodes.values()))
    engine.ingest_event_stream([(h, event)])
    updated = next(iter(engine.nodes.values()))
    assert (updated.reinforcement_count, updated.saliency_score) == (
        original.reinforcement_count, original.saliency_score
    )


@pytest.mark.xfail(strict=True, reason="RED: invalid suffix must not leave a partial memory batch")
def test_bad_suffix_rolls_back_entire_batch():
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError):
        engine.ingest_event_stream([
            (digest("valid"), {"concept": "x", "assertion": "valid"}),
            ("not-a-sha256", {"concept": "x", "assertion": "invalid"}),
        ])
    assert engine.nodes == {}
    assert engine.known_ledger_hashes == set()


@pytest.mark.xfail(strict=True, reason="RED: negative decay cycles can inflate salience")
def test_negative_decay_cycles_fail_closed():
    engine = ConsolidationEngine()
    engine.ingest_event_stream([(digest("init"), {"concept": "x", "assertion": "v"})])
    with pytest.raises(ConsolidationError):
        engine.apply_saliency_decay(-3)


@pytest.mark.xfail(strict=True, reason="RED: ledger line digest must bind exact raw bytes")
def test_leading_bytes_change_raw_line_digest(tmp_path):
    event = {"concept": "x", "assertion": "v"}
    raw = json.dumps(event).encode("utf-8")
    a, b = tmp_path / "a.jsonl", tmp_path / "b.jsonl"
    a.write_bytes(raw + b"\n")
    b.write_bytes(b" " + raw + b"\n")
    x, y = ConsolidationEngine(), ConsolidationEngine()
    x.ingest_ledger_file(a)
    y.ingest_ledger_file(b)
    hx = next(iter(x.nodes.values())).source_event_hashes[0]
    hy = next(iter(y.nodes.values())).source_event_hashes[0]
    assert hx != hy


@pytest.mark.xfail(strict=True, reason="RED: malformed event must raise domain exception and leave no state")
def test_non_mapping_event_is_rejected_cleanly():
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError):
        engine.ingest_event_stream([(digest("invalid"), "not-a-dict")])
    assert engine.nodes == {}


@pytest.mark.xfail(strict=True, reason="RED: colon-concatenated node keys collide")
def test_distinct_concept_assertion_pairs_do_not_alias():
    engine = ConsolidationEngine()
    engine.ingest_event_stream([
        (digest("a"), {"concept": "a:b", "assertion": "c"}),
        (digest("b"), {"concept": "a", "assertion": "b:c"}),
    ])
    assert len(engine.nodes) == 2


@pytest.mark.xfail(strict=True, reason="RED: same declared hash cannot represent incompatible payloads")
def test_one_declared_digest_cannot_represent_two_payloads():
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError):
        engine.ingest_event_stream([
            (digest("same"), {"concept": "x", "assertion": "A"}),
            (digest("same"), {"concept": "x", "assertion": "B"}),
        ])
    assert engine.nodes == {}
    assert engine.known_ledger_hashes == set()


@pytest.mark.xfail(strict=True, reason="RED: SHA256 uppercase/lowercase encodings alias a single digest")
def test_uppercase_hex_variant_does_not_inflate_reinforcement():
    engine = ConsolidationEngine()
    event = {"concept": "x", "assertion": "case-insensitive-hex"}
    h = digest("mixed_case_digest")
    engine.ingest_event_stream([(h, event)])
    original = next(iter(engine.nodes.values()))
    engine.ingest_event_stream([(h.upper(), event)])
    updated = next(iter(engine.nodes.values()))
    assert updated.reinforcement_count == original.reinforcement_count
    assert len(updated.source_event_hashes) == 1


def test_positive_control_two_distinct_records_remain_representable():
    engine = ConsolidationEngine()
    engine.ingest_event_stream([
        (digest("distinct-a"), {"concept": "x", "assertion": "A"}),
        (digest("distinct-b"), {"concept": "x", "assertion": "B"}),
    ])
    assert len(engine.nodes) == 2
    assert engine.validate_lineage_integrity() is True
