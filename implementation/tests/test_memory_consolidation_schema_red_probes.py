"""Non-authoritative RED probes for Ario memory candidate PR #222.

Review-only, stacked on exact #222 head.
Strict XFAILs mean known weaknesses, NOT verified security defenses.
No source authentication, memory truth, or performance security is claimed.
"""

import hashlib
import io

import pytest

from core.memory_consolidation import (
    ConsolidationEngine,
    ConsolidationError,
    NodeEpistemicStatus,
    SemanticNode,
)


def _sha(seed: bytes) -> str:
    return hashlib.sha256(seed).hexdigest()


class _MemoryPath:
    """Read-only in-memory file adapter. Never writes host filesystem."""

    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    def exists(self) -> bool:
        return True

    def open(self, mode: str):
        assert mode == "rb"
        return io.BytesIO(self.raw)


def _semantic_node(source_event_hashes, falsification_condition=None):
    return SemanticNode(
        node_id="SEM-test",
        concept="auth",
        assertion="A report was recorded",
        status=NodeEpistemicStatus.ACCEPTED,
        source_event_hashes=source_event_hashes,
        saliency_score=0.5,
        created_at="2026-11-15T00:00:00Z",
        last_reinforced_at="2026-11-15T00:00:00Z",
        reinforcement_count=1,
        falsification_condition=falsification_condition,
    )


@pytest.mark.xfail(
    strict=True,
    reason="RED F1a: mutable falsification_condition aliases into frozen node",
)
def test_mutable_falsification_condition_must_fail_closed():
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError):
        engine.ingest_event_stream([
            (
                _sha(b"mutable-condition"),
                {
                    "concept": "auth",
                    "assertion": "A report was recorded",
                    "falsification_condition": {"case": "before"},
                },
            )
        ])
    assert engine.nodes == {}


@pytest.mark.xfail(
    strict=True,
    reason="RED F1b: mutable source-event-hash list bypasses frozen dataclass",
)
def test_mutable_source_hash_list_must_fail_closed():
    with pytest.raises(ConsolidationError):
        _semantic_node([_sha(b"source")], "A falsifier")


@pytest.mark.xfail(
    strict=True,
    reason="RED F2a: duplicate root JSON keys silently overwrite earlier value",
)
def test_duplicate_json_key_is_rejected():
    ledger = _MemoryPath(
        b'{"concept":"auth","assertion":"ALLOW","assertion":"DENY"}\n'
    )
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError):
        engine.ingest_ledger_file(ledger)
    assert engine.nodes == {}
    assert engine.known_ledger_hashes == set()


@pytest.mark.xfail(
    strict=True,
    reason="RED F2b: nested duplicate JSON keys are also ambiguous",
)
def test_nested_duplicate_json_key_is_rejected():
    ledger = _MemoryPath(
        b'{"concept":"auth","assertion":"A","meta":{"source":"A","source":"B"}}\n'
    )
    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError):
        engine.ingest_ledger_file(ledger)
    assert engine.nodes == {}


def test_control_simple_json_ledger_remains_ingestable():
    raw = b'{"concept":"auth","assertion":"A"}\n'
    engine = ConsolidationEngine()
    assert engine.ingest_ledger_file(_MemoryPath(raw)) == 1
    node = next(iter(engine.nodes.values()))
    assert node.assertion == "A"
    assert node.source_event_hashes == (_sha(raw),)


def test_control_immutable_semantic_node_is_valid():
    node = _semantic_node((_sha(b"source"),), "Counterexample")
    assert node.source_event_hashes == (_sha(b"source"),)
    assert node.falsification_condition == "Counterexample"
