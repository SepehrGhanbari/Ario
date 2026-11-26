import json
from pathlib import Path
"""Tests for Ario Prospective Memory Registry & Condition Gating.

Validates core invariants from Issue #209:
- T-PROS-01: Safe Predicate Sandbox (Code/Syntax Injection Rejection)
- T-PROS-02: Deterministic Expiration (TTL Gating Without Action Emission)
- Situational Cue Triggering & Capacity Bounding
"""

import pytest
from core.prospective_memory import (
    DelayedIntention,
    IntentionStatus,
    ProspectiveMemoryError,
    ProspectiveMemoryRegistry,
    ProspectiveSecurityError,
    validate_predicate_ast,
)


def test_t_pros_01_safe_predicate_sandbox_rejects_injection():
    """T-PROS-01: Injection attempts (import, eval, dunder, call) fail closed at parse time."""
    registry = ProspectiveMemoryRegistry()

    dangerous_predicates = [
        "__import__('os').system('ls')",
        "eval('1 + 1') == 2",
        "open('/etc/passwd').read()",
        "event.__class__.__bases__",
        "exec('x = 1')",
        "(lambda x: x)(1) == 1",
        "[x for x in range(10)]",
    ]

    for bad_expr in dangerous_predicates:
        with pytest.raises(ProspectiveSecurityError, match="T-PROS-01"):
            registry.register_intention(
                description="Malicious intention attempt",
                predicate_expr=bad_expr,
                action_payload={"action": "noop"},
                created_at_epoch=100.0,
                ttl_epoch=200.0,
            )


def test_t_pros_01_valid_predicate_ast_allowed():
    """T-PROS-01: Allowlisted boolean logic and comparisons parse successfully."""
    valid_exprs = [
        "task_id == 'T-101' and test_status == 'PASSED'",
        "error_count > 0 or retry_attempt <= 3",
        "metric >= 0.95 and not is_draft",
        "branch in ['main', 'release']",
    ]
    for expr in valid_exprs:
        ast_node = validate_predicate_ast(expr)
        assert ast_node is not None


def test_t_pros_02_deterministic_expiration():
    """T-PROS-02: Intentions evaluated after TTL epoch transition to EXPIRED and never emit actions."""
    registry = ProspectiveMemoryRegistry()

    intention = registry.register_intention(
        description="Verify planner response time after run",
        predicate_expr="run_completed == True",
        action_payload={"notify": "audit_log"},
        created_at_epoch=1000.0,
        ttl_epoch=1100.0,
        intention_id="INT-EXP-TEST",
    )
    assert intention.status == IntentionStatus.PENDING

    # Cue occurs at t=1200.0 (past TTL of 1100.0), even though condition evaluates True
    triggered = registry.evaluate_cues(
        cue_context={"run_completed": True},
        current_epoch=1200.0,
    )

    # Invariant: Must NOT trigger any actions
    assert len(triggered) == 0

    # Invariant: Status must transition to EXPIRED
    expired = registry.intentions["INT-EXP-TEST"]
    assert expired.status == IntentionStatus.EXPIRED
    assert len(registry.get_expired_intentions()) == 1


def test_valid_cue_evaluation_and_trigger():
    """Valid cue within TTL triggers the intention deterministically."""
    registry = ProspectiveMemoryRegistry()

    registry.register_intention(
        description="Trigger check on review completion",
        predicate_expr="status == 'COMPLETED' and exit_code == 0",
        action_payload={"step": "archive_audit"},
        created_at_epoch=1000.0,
        ttl_epoch=2000.0,
        intention_id="INT-TRIG-01",
    )

    # Cue matches at t=1500.0
    triggered = registry.evaluate_cues(
        cue_context={"status": "COMPLETED", "exit_code": 0},
        current_epoch=1500.0,
    )

    assert len(triggered) == 1
    assert triggered[0].intention_id == "INT-TRIG-01"
    assert triggered[0].status == IntentionStatus.TRIGGERED
    assert triggered[0].triggered_at is not None

    # Subsequent evaluation does not re-trigger
    re_triggered = registry.evaluate_cues(
        cue_context={"status": "COMPLETED", "exit_code": 0},
        current_epoch=1600.0,
    )
    assert len(re_triggered) == 0


def test_capacity_bounding_and_cancellation():
    """Registry enforces capacity bounds and supports cancellation."""
    registry = ProspectiveMemoryRegistry(max_pending=2)

    registry.register_intention("Task 1", "x == 1", {}, 10.0, 20.0, intention_id="I-1")
    registry.register_intention("Task 2", "x == 2", {}, 10.0, 20.0, intention_id="I-2")

    # Exceeding capacity raises error
    with pytest.raises(ProspectiveMemoryError, match="capacity reached"):
        registry.register_intention("Task 3", "x == 3", {}, 10.0, 20.0, intention_id="I-3")

    # Cancel I-1
    cancelled = registry.cancel_intention("I-1")
    assert cancelled.status == IntentionStatus.CANCELLED

    # Now capacity allows registering I-3
    registry.register_intention("Task 3", "x == 3", {}, 10.0, 20.0, intention_id="I-3")
    assert len(registry.get_pending_intentions()) == 2


def test_intention_serialization():
    """DelayedIntention serializes and restores cleanly."""
    intention = DelayedIntention(
        intention_id="INT-SER-01",
        description="Audit verification step",
        predicate_expr="coverage >= 0.9",
        action_payload={"target": "coverage_report"},
        created_at_epoch=500.0,
        ttl_epoch=1000.0,
    )
    d = intention.to_dict()
    restored = DelayedIntention.from_dict(d)
    assert restored == intention


def test_t_pros_07_journal_atomic_save_and_load(tmp_path: Path):
    """Save registry to disk and reload; verify state and integrity."""
    journal_path = tmp_path / "intentions_journal.json"
    registry = ProspectiveMemoryRegistry(max_pending=10)

    i1 = registry.register_intention("Task 1", "x == 1", {"action": "act_1"}, 100.0, 500.0, intention_id="INT-1")
    i2 = registry.register_intention("Task 2", "y == 2", {"action": "act_2"}, 100.0, 300.0, intention_id="INT-2")

    # Trigger INT-1
    registry.evaluate_cues({"x": 1}, current_epoch=200.0)
    assert registry.intentions["INT-1"].status == IntentionStatus.TRIGGERED

    # Expire INT-2
    registry.evaluate_cues({"y": 2}, current_epoch=400.0)
    assert registry.intentions["INT-2"].status == IntentionStatus.EXPIRED

    # Add PENDING INT-3
    i3 = registry.register_intention("Task 3", "z == 3", {"action": "act_3"}, 200.0, 800.0, intention_id="INT-3")

    # Save journal
    count = registry.save_journal(journal_path)
    assert count == 3
    assert journal_path.exists()

    # Reconstruct from journal
    loaded = ProspectiveMemoryRegistry.load_journal(journal_path)
    assert len(loaded.intentions) == 3
    assert loaded.intentions["INT-1"].status == IntentionStatus.TRIGGERED
    assert loaded.intentions["INT-2"].status == IntentionStatus.EXPIRED
    assert loaded.intentions["INT-3"].status == IntentionStatus.PENDING
    assert loaded.intentions["INT-3"].action_payload == {"action": "act_3"}


def test_t_pros_08_journal_tamper_detection_checksum(tmp_path: Path):
    """Tampering with journal file contents on disk is detected via sha256 checksum."""
    journal_path = tmp_path / "tamper_test_journal.json"
    registry = ProspectiveMemoryRegistry()
    registry.register_intention("Audit", "x == 10", {"target": "log"}, 100.0, 200.0)
    registry.save_journal(journal_path)

    # Modify intention payload directly in the JSON file without updating digest
    with open(journal_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["intentions"][0]["description"] = "TAMPERED DESCRIPTION"
    with open(journal_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    # Loading must fail closed due to integrity digest mismatch
    with pytest.raises(ProspectiveSecurityError, match="Integrity digest mismatch"):
        ProspectiveMemoryRegistry.load_journal(journal_path)


def test_t_pros_09_journal_tamper_detection_ast_revalidation(tmp_path: Path):
    """Tampering predicate expression to inject disallowed AST fails on load even if digest is forged."""
    journal_path = tmp_path / "tamper_ast_journal.json"
    registry = ProspectiveMemoryRegistry()
    registry.register_intention("Clean", "flag == True", {"notify": "admin"}, 100.0, 300.0)
    registry.save_journal(journal_path)

    # Tamper with predicate AND forge the checksum
    with open(journal_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["intentions"][0]["predicate_expr"] = "__import__('os').system('echo hacked')"
    # Recompute checksum so checksum passes, but AST revalidation catches it
    import hashlib
    canon = json.dumps(data["intentions"], sort_keys=True, separators=(",", ":")).encode("utf-8")
    data["integrity_digest"] = hashlib.sha256(canon).hexdigest()
    with open(journal_path, "w", encoding="utf-8") as f:
        json.dump(data, f)

    with pytest.raises(ProspectiveSecurityError, match="T-PROS-01"):
        ProspectiveMemoryRegistry.load_journal(journal_path, enforce_ast_revalidation=True)


def test_t_pros_10_journal_reboot_ttl_reconciliation(tmp_path: Path):
    """Post-recovery sweep transitions overdue intentions to EXPIRED without firing actions."""
    journal_path = tmp_path / "reboot_journal.json"
    registry = ProspectiveMemoryRegistry()

    # Created at t=100, TTL at t=200
    registry.register_intention("Nightly Sync", "sync_ready == True", {"sync": "db"}, 100.0, 200.0, intention_id="INT-SYNC")
    registry.save_journal(journal_path)

    # System reboots at t=350.0 (past TTL of 200)
    recovered = ProspectiveMemoryRegistry.load_journal(journal_path)
    assert recovered.intentions["INT-SYNC"].status == IntentionStatus.PENDING

    # Run sweep reconciliation
    expired_count = recovered.reconcile_expired_intentions(current_epoch=350.0)
    assert expired_count == 1
    assert recovered.intentions["INT-SYNC"].status == IntentionStatus.EXPIRED

    # Even if cue now matches, it must not trigger
    triggered = recovered.evaluate_cues({"sync_ready": True}, current_epoch=360.0)
    assert len(triggered) == 0
