"""Untrusted STEP_OBSERVED ledger provenance: deliberately RED characterization.

Security contract proposal for #216. This tests *existing* #210 bridge code
with a fake tool-output event, without invoking a tool or checking the target.
No production signer, memory activation or external credentials involved.

Expected RED until upstream governance decides that unverified JSONL reports
must not be labeled as independently SUPPORTED / VERIFIED_EMPIRICAL.
Do NOT mark xfail or silently lower expectations. Do NOT merge as-is.
"""
import json

from core.ledger_memory_bridge import EpistemicLedgerBridge
from core.memory_consolidation import NodeEpistemicStatus
from core.source_monitoring import VeracityState


def _untrusted_step(tmp_path):
    non_existent_target = tmp_path / "never-created-source.txt"
    assert not non_existent_target.exists()
    ledger = tmp_path / "synthetic-untrusted-agent-ledger.jsonl"
    ledger.write_bytes(
        (json.dumps({
            "event": "STEP_OBSERVED",
            "timestamp": "2026-11-17T00:00:00Z",
            "tool": "file_fingerprint",
            "task_id": "untrusted-synthetic-task",
            "step_id": "fake-step-1",
            "status": "COMPLETED",
            "result": {
                "path": str(non_existent_target),
                "sha256": "0" * 64,
                "bytes": 12345,
                "note": "SELF_DECLARED_ONLY_NO_REAL_FILE",
            },
        }, sort_keys=True) + "\n").encode("utf-8")
    )
    return ledger, non_existent_target


def test_untrusted_completed_jsonl_cannot_create_supported_memory(tmp_path):
    ledger, non_existent_target = _untrusted_step(tmp_path)
    before = ledger.read_bytes()
    bridge = EpistemicLedgerBridge()
    summary = bridge.ingest_agent_ledger(ledger)
    assert summary.steps_observed == 1
    assert not non_existent_target.exists()
    assert ledger.read_bytes() == before
    nodes = [node for node in bridge.engine.nodes.values()
             if node.concept.startswith("agent_tool:file_fingerprint:")]
    assert len(nodes) == 1
    # Desired epistemic safety: an untrusted report can only be RECORDED.
    # EXPECTED RED on #210: implementation currently assigns SUPPORTED.
    assert nodes[0].status == NodeEpistemicStatus.RECORDED


def test_untrusted_completed_jsonl_cannot_authenticate_execution(tmp_path):
    ledger, non_existent_target = _untrusted_step(tmp_path)
    bridge = EpistemicLedgerBridge()
    bridge.ingest_agent_ledger(ledger)
    assert not non_existent_target.exists()
    attrs = list(bridge.guard.attributions.values())
    observations = [a for a in attrs if a.assertion.startswith("step_execution:")]
    assert len(observations) == 1
    # Desired safety: self-declared tool metadata is not authenticated execution.
    # EXPECTED RED on #210: guard hashes the supplied bytes and marks VERIFIED.
    assert observations[0].veracity_state != VeracityState.VERIFIED_EMPIRICAL


def test_untrusted_task_goal_remains_recorded_positive_control(tmp_path):
    ledger = tmp_path / "synthetic-goal-ledger.jsonl"
    ledger.write_text(json.dumps({
        "event": "TASK_STARTED",
        "timestamp": "2026-11-17T00:00:00Z",
        "task_id": "synthetic-task",
        "goal": "Unverified future goal",
    }) + "\n", encoding="utf-8")
    bridge = EpistemicLedgerBridge()
    bridge.ingest_agent_ledger(ledger)
    nodes = list(bridge.engine.nodes.values())
    assert len(nodes) == 1
    assert nodes[0].status == NodeEpistemicStatus.RECORDED
