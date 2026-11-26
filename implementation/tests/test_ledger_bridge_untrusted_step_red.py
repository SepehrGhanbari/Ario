"""Untrusted STEP_OBSERVED ledger provenance: preserved RED then proposed GREEN.

The original test-only #266 commit reproducibly failed on the original #210
bridge. This stacked research branch implements the strict reported-only
versioned path. No tools, production keys, or live memory are exercised.
Do not merge this Draft branch without independent governance review.
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
    # Historical RED on #210: original bridge assigned SUPPORTED.
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


def test_replayed_report_cannot_promote_hypothesis_or_enter_verified_context(tmp_path):
    import pytest
    from core.source_monitoring import SelfCitationError, SourceMonitoringGuard
    ledger, _ = _untrusted_step(tmp_path)
    guard = SourceMonitoringGuard()
    guard.create_hypothesis("Claim: nonexistent file was fingerprinted",
                            attribution_id="claim")
    bridge = EpistemicLedgerBridge(source_guard=guard)
    bridge.ingest_agent_ledger(ledger)
    report_ids = [i for i, attr in guard.attributions.items()
                  if attr.source_type == SourceType.LEDGER_REPORT]
    assert len(report_ids) == 1
    assert guard.filter_working_memory_candidates(report_ids, require_verified=True) == []
    with pytest.raises(SelfCitationError):
        guard.evaluate_claim_promotion("claim", report_ids)
    assert guard.attributions["claim"].veracity_state != VeracityState.VERIFIED_EMPIRICAL


def test_direct_empirical_guard_api_remains_distinct_from_ledger_replay():
    from core.source_monitoring import SourceMonitoringGuard
    guard = SourceMonitoringGuard()
    attr = guard.record_empirical_observation(
        assertion="tool_exit:run_tests:synthetic/test.py:0",
        tool="run_tests", target="synthetic/test.py",
        exit_code=0, stdout="test result", execution_lock="test-local-lock",
    )
    # Existing direct API behavior is preserved; this test does NOT establish
    # authentication because we ourselves supplied the execution metadata.
    assert attr.source_type == SourceType.EMPIRICAL_OBSERVATION
    assert attr.veracity_state == VeracityState.VERIFIED_EMPIRICAL
    assert attr.provenance is not None
