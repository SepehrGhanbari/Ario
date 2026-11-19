"""Adversarial cross-component compatibility probes for Draft PR #229.

All fixtures are source-shaped synthetic records, NOT production telemetry.
Three strict XFAILs are documented contract mismatches awaiting policy review,
not failed security controls that can be resolved by widening trust.
No original Ario files, historical records or key material are modified.
"""

import hashlib
import io
import json

import pytest

import core.memory_consolidation as mc
from ario_agent import parse_task
from core.memory_consolidation import ConsolidationEngine, ConsolidationError


class ReadOnlySyntheticPath:
    def __init__(self, raw: bytes, *, symlink: bool = False):
        self.raw = raw
        self.symlink = symlink

    def exists(self):
        return True

    def is_symlink(self):
        return self.symlink

    def open(self, mode):
        assert mode == "rb"
        return io.BytesIO(self.raw)


def _agent_started(goal="inspect"):
    return {
        "event": "TASK_STARTED",
        "task_id": "TASK-test",
        "goal": goal,
        "step_ids": ["s1"],
        "timestamp": "2026-11-15T00:00:00Z",
    }


def _jsonl(event, padding=b""):
    return json.dumps(event, sort_keys=True).encode("utf-8") + padding + b"\n"


@pytest.mark.xfail(
    strict=True,
    reason="RED cross-component contract: reader skips symlink check enforced by ledger adapter",
)
def test_memory_reader_rejects_symlink_like_source():
    ledger = ReadOnlySyntheticPath(_jsonl(_agent_started()), symlink=True)
    with pytest.raises(ConsolidationError, match="symlink|symbolic"):
        ConsolidationEngine().ingest_ledger_file(ledger)


@pytest.mark.xfail(
    strict=True,
    reason="RED cross-component contract: raw JSONL line exceeds adapter 64KiB limit",
)
def test_memory_reader_rejects_line_larger_than_adapter_limit():
    raw = _jsonl(_agent_started(), padding=b" " * (64 * 1024))
    assert len(raw) > 64 * 1024
    with pytest.raises(ConsolidationError, match="line.*limit"):
        ConsolidationEngine().ingest_ledger_file(ReadOnlySyntheticPath(raw))


@pytest.mark.xfail(
    strict=True,
    reason="RED policy incompatibility: agent accepts large goal, memory rejects its event",
)
def test_agent_accepted_goal_is_representable_in_memory():
    long_goal = "g" * (70 * 1024)
    normalized = parse_task({
        "task_id": "TASK-test",
        "goal": long_goal,
        "actions": [{"step_id": "s1", "tool": "inspect_directory", "path": "."}],
    })
    assert normalized["goal"] == long_goal
    raw = _jsonl(_agent_started(goal=long_goal))
    assert ConsolidationEngine().ingest_ledger_file(ReadOnlySyntheticPath(raw)) == 1


def test_small_completed_agent_envelope_accepted():
    raw = _jsonl(_agent_started())
    engine = ConsolidationEngine()
    assert engine.ingest_ledger_file(ReadOnlySyntheticPath(raw)) == 1
    node = next(iter(engine.nodes.values()))
    assert node.source_event_hashes == (hashlib.sha256(raw).hexdigest(),)
    assert node.assertion == "inspect"


def test_retained_hash_limit_is_per_engine_not_per_file(monkeypatch):
    monkeypatch.setattr(mc, "MAX_MEMORY_STORED_HASHES", 2)
    first = _jsonl(_agent_started("first"))
    second = _jsonl(_agent_started("second"))
    third = _jsonl(_agent_started("third"))
    engine = ConsolidationEngine()
    assert engine.ingest_ledger_file(ReadOnlySyntheticPath(first + second)) == 2
    previous_nodes = engine.nodes
    previous_hashes = engine.known_ledger_hashes
    with pytest.raises(ConsolidationError, match="retained-event limit"):
        engine.ingest_ledger_file(ReadOnlySyntheticPath(third))
    assert engine.nodes == previous_nodes
    assert engine.known_ledger_hashes == previous_hashes


def test_source_shaped_nonsemantic_events_are_counted_not_claimed_as_learning():
    events = [
        _agent_started("Inspect safely"),
        {
            "event": "STEP_OBSERVED",
            "task_id": "TASK-test",
            "step_id": "s1",
            "tool": "inspect_directory",
            "status": "SUCCEEDED",
            "timestamp": "2026-11-15T00:01:00Z",
        },
        {
            "event": "TASK_FINISHED",
            "task_id": "TASK-test",
            "status": "COMPLETED",
            "timestamp": "2026-11-15T00:02:00Z",
        },
    ]
    raw = b"".join(_jsonl(ev) for ev in events)
    engine = ConsolidationEngine()
    assert engine.ingest_ledger_file(ReadOnlySyntheticPath(raw)) == 3
    assert len(engine.known_ledger_hashes) == 3
    assert len(engine.nodes) == 1
