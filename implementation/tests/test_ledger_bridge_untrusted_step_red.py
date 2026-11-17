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
from core.source_monitoring import SourceType, VeracityState, SourceAttribution, SourceMonitoringError


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
    assert len(attrs) == 1
    # A replay report is traceable but cannot impersonate a tool execution.
    report = attrs[0]
    assert report.source_type == SourceType.LEDGER_REPORT
    assert report.veracity_state == VeracityState.REPORTED_UNVERIFIED
    assert report.provenance is None
    assert report.attribution_id.startswith("ATTR-LEDGER-")
    assert report.veracity_state != VeracityState.VERIFIED_EMPIRICAL


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


def test_self_declared_status_cannot_force_verification(tmp_path):
    ledger = tmp_path / "self-declared-status.jsonl"
    fake = {
        "event": "STEP_OBSERVED", "tool": "file_fingerprint",
        "status": "COMPLETED", "veracity_state": "VERIFIED_EMPIRICAL",
        "source_type": "EMPIRICAL_OBSERVATION", "result": {"path": "absent.txt"},
    }
    ledger.write_bytes((json.dumps(fake, sort_keys=True) + "\n").encode())
    initial = ledger.read_bytes()
    bridge = EpistemicLedgerBridge()
    bridge.ingest_agent_ledger(ledger)
    assert ledger.read_bytes() == initial
    assert {n.status for n in bridge.engine.nodes.values()} == {NodeEpistemicStatus.RECORDED}
    assert {a.veracity_state for a in bridge.guard.attributions.values()} == {VeracityState.REPORTED_UNVERIFIED}


def test_reported_failed_status_is_not_automatically_contested(tmp_path):
    ledger = tmp_path / "reported-failure.jsonl"
    ledger.write_text(json.dumps({
        "event": "STEP_OBSERVED", "tool": "file_fingerprint",
        "status": "FAILED", "result": {"path": "absent.txt"},
    }) + "\n", encoding="utf-8")
    bridge = EpistemicLedgerBridge()
    bridge.ingest_agent_ledger(ledger)
    assert len(bridge.engine.nodes) == 1
    assert list(bridge.engine.nodes.values())[0].status == NodeEpistemicStatus.RECORDED
    assert list(bridge.guard.attributions.values())[0].veracity_state == VeracityState.REPORTED_UNVERIFIED


def test_unverified_attribution_roundtrips_and_cannot_claim_empirical():
    import pytest
    data = {
        "attribution_id": "ATTR-LEDGER-" + "a" * 64,
        "source_type": "LEDGER_REPORT",
        "assertion": "reported_step_execution:run_tests:fake:COMPLETED",
        "veracity_state": "REPORTED_UNVERIFIED",
        "parent_attribution_ids": [],
    }
    attr = SourceAttribution.from_dict(data)
    assert attr.source_type == SourceType.LEDGER_REPORT
    assert attr.veracity_state == VeracityState.REPORTED_UNVERIFIED
    assert attr.provenance is None
    assert SourceAttribution.from_dict(attr.to_dict()).to_dict() == attr.to_dict()
    for injected in ("VERIFIED_EMPIRICAL", "EXTERNAL_ASSERTION"):
        bad = dict(data, veracity_state=injected)
        with pytest.raises(SourceMonitoringError):
            SourceAttribution.from_dict(bad)
