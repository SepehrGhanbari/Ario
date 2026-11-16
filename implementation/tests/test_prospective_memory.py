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
