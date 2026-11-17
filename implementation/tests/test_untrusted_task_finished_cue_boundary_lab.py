"""Fail-closed TASK_FINISHED cue boundary: test-first research experiment.

RED first against proposed #267: a *reported* completion must not mutate
prospective intention state or return a deploy-like action payload. The trusted
direct registry API remains usable by separately authorized callers.

Disposable synthetic JSONL and action dictionaries only; no real action runs.
"""
import json

from core.ledger_memory_bridge import EpistemicLedgerBridge
from core.prospective_memory import IntentionStatus, ProspectiveMemoryRegistry


def _setup(tmp_path, *, reported_status="COMPLETED", proposed_exit_code=0):
    ledger = tmp_path / "reported-finish.jsonl"
    ledger.write_bytes((json.dumps({
        "event": "TASK_FINISHED", "task_id": "synthetic-deploy",
        "status": reported_status, "exit_code": proposed_exit_code,
        "timestamp": "2026-11-17T00:00:00Z",
    }, sort_keys=True) + "\n").encode())
    reg = ProspectiveMemoryRegistry()
    intention = reg.register_intention(
        description="synthetic action should not fire from an untrusted file",
        predicate_expr="task_id == 'synthetic-deploy' and status == 'COMPLETED' and exit_code == 0",
        action_payload={"deploy": True, "target": "SYNTHETIC_NONEXISTENT"},
        created_at_epoch=1000.0, ttl_epoch=2000.0,
        intention_id="synthetic-deploy-intention",
    )
    return ledger, reg, intention


def test_untrusted_completed_task_report_does_not_trigger_action(tmp_path):
    ledger, reg, intention = _setup(tmp_path)
    before = ledger.read_bytes()
    bridge = EpistemicLedgerBridge(prospective_registry=reg)
    report = bridge.ingest_agent_ledger(ledger, current_epoch=1100.0)
    assert ledger.read_bytes() == before
    assert report.total_events_read == 1
    assert report.triggered_intentions_count == 0
    assert report.triggered_intentions == ()
    assert reg.intentions[intention.intention_id].status == IntentionStatus.PENDING


def test_repeated_untrusted_task_reports_cannot_consume_intention(tmp_path):
    ledger, reg, intention = _setup(tmp_path)
    bridge = EpistemicLedgerBridge(prospective_registry=reg)
    for _ in range(3):
        report = bridge.ingest_agent_ledger(ledger, current_epoch=1100.0)
        assert report.triggered_intentions_count == 0
        assert reg.intentions[intention.intention_id].status == IntentionStatus.PENDING
    assert len(reg.get_triggered_intentions()) == 0


def test_untrusted_failed_task_report_is_not_triggered(tmp_path):
    ledger, reg, intention = _setup(tmp_path, reported_status="FAILED", proposed_exit_code=1)
    bridge = EpistemicLedgerBridge(prospective_registry=reg)
    report = bridge.ingest_agent_ledger(ledger, current_epoch=1100.0)
    assert report.triggered_intentions_count == 0
    assert reg.intentions[intention.intention_id].status == IntentionStatus.PENDING


def test_direct_registry_cue_evaluation_still_works_as_separate_positive_control(tmp_path):
    _, reg, intention = _setup(tmp_path)
    matched = reg.evaluate_cues(
        {"task_id": "synthetic-deploy", "status": "COMPLETED", "exit_code": 0},
        current_epoch=1100.0,
    )
    assert len(matched) == 1
    assert matched[0].intention_id == intention.intention_id
    assert reg.intentions[intention.intention_id].status == IntentionStatus.TRIGGERED
