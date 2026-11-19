import dataclasses
"""Adversarial Security Boundary Tests for Ario Cognitive Memory Architecture.

Rigorous verification of sandbox invariants, reality monitoring limits,
lineage immutability, and fail-closed security properties across all 3 modules.
- Suite 1: AST Injection & Condition Bypass (Prospective Memory Sandbox - T-PROS-01)
- Suite 2: Provenance Forgery & Reality Monitoring Spoofing (Source Monitoring Guard - T-SRC-01/02)
- Suite 3: Lineage Integrity, Non-Erasure & Ledger Tampering (Consolidation Engine - T-CONS-01/02/03)
"""

import hashlib
import json
from pathlib import Path

import pytest
from core.memory_consolidation import (
    ConsolidationEngine,
    ConsolidationError,
    NodeEpistemicStatus,
    SemanticNode,
)
from core.prospective_memory import (
    IntentionStatus,
    ProspectiveMemoryError,
    ProspectiveMemoryRegistry,
    ProspectiveSecurityError,
    validate_predicate_ast,
)
from core.source_monitoring import (
    AttributionMismatchError,
    EmpiricalProvenance,
    SelfCitationError,
    SourceAttribution,
    SourceMonitoringError,
    SourceMonitoringGuard,
    SourceType,
    VeracityState,
)


def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


# ==============================================================================
# Suite 1: AST Injection & Sandbox Boundaries (Prospective Memory - T-PROS-01)
# ==============================================================================


@pytest.mark.parametrize(
    "adversarial_expr",
    [
        # Walrus operator assignment
        "(x := 1) == 1",
        # List / Dict / Set Comprehensions
        "[x for x in range(5)] == [0, 1, 2, 3, 4]",
        "{x: 1 for x in [1, 2]}",
        "{x for x in (1, 2)}",
        # Generator expressions
        "(x for x in (1, 2))",
        # Formatted string / f-strings
        "f'{1+1}' == '2'",
        # Dunder and private attribute smuggling
        "x.__class__ == 'dict'",
        "x.__bases__[0]",
        "x._internal_state == True",
        "__builtins__['int']('1') == 1",
        # Builtin / dangerous tokens
        "eval('2 > 1')",
        "exec('print(1)')",
        "open('/dev/null')",
        "compile('x = 1', '', 'single')",
        "import sys",
        "globals()",
        "locals()",
        # Arbitrary function calls
        "len(items) > 0",
        "abs(delta) < 5",
        "str(code) == '200'",
        # Lambda definition
        "(lambda: True)()",
        # Syntax corruption
        "x === 1",
        "((x > 1",
    ],
)
def test_ast_sandbox_rejects_adversarial_injections(adversarial_expr: str):
    """T-PROS-01: Any expression violating AST allowlist or containing dangerous tokens fails closed."""
    with pytest.raises(ProspectiveSecurityError):
        validate_predicate_ast(adversarial_expr)


def test_prospective_registry_capacity_saturation_boundary():
    """Registry enforces strict hard capacity and rejects overflow without corruption."""
    reg = ProspectiveMemoryRegistry(max_pending=3)
    reg.register_intention("Task A", "x == 1", {}, 10.0, 20.0)
    reg.register_intention("Task B", "x == 2", {}, 10.0, 20.0)
    reg.register_intention("Task C", "x == 3", {}, 10.0, 20.0)

    # 4th registration must raise ProspectiveMemoryError
    with pytest.raises(ProspectiveMemoryError, match="capacity reached"):
        reg.register_intention("Task D (overflow)", "x == 4", {}, 10.0, 20.0)

    # State remains uncorrupted with exactly 3 pending items
    assert len(reg.get_pending_intentions()) == 3


# ==============================================================================
# Suite 2: Provenance Forgery & Reality Monitoring Boundaries (Source Monitoring - T-SRC-01/02)
# ==============================================================================


def test_empirical_observation_rejects_unallowlisted_or_injected_tools():
    """Guard rejects non-allowlisted tool executions and shell metacharacter injections."""
    guard = SourceMonitoringGuard()

    malicious_tools = [
        "bash",
        "sh",
        "curl",
        "wget",
        "run_tests; rm -rf /",
        "run_tests\ncat /etc/shadow",
        "python -c 'import os'",
    ]

    for tool in malicious_tools:
        with pytest.raises(SourceMonitoringError, match="not allowlisted"):
            guard.record_empirical_observation(
                assertion="Attacker observation",
                tool=tool,
                target="suite",
                exit_code=0,
                stdout="OK",
                execution_lock="lock_token",
            )


def test_empirical_observation_fails_on_lock_or_stdout_hash_mismatch():
    """T-SRC-02: Cryptographic mismatch in execution lock or stdout triggers AttributionMismatchError."""
    guard = SourceMonitoringGuard()
    raw_stdout = "Test run: 10 passed in 0.05s"
    raw_lock = "lock-secret-seed-9988"
    valid_lock_hash = _sha256(raw_lock)
    valid_stdout_hash = _sha256(raw_stdout)

    # Case A: Lock hash forged / mismatched
    with pytest.raises(AttributionMismatchError, match="execution lock mismatch"):
        guard.record_empirical_observation(
            assertion="Unit tests passed",
            tool="run_tests",
            target="tests/",
            exit_code=0,
            stdout=raw_stdout,
            execution_lock=raw_lock,
            expected_execution_lock_sha256=_sha256("forged_lock_different"),
        )

    # Case B: Stdout tampered / mismatched
    with pytest.raises(AttributionMismatchError, match="stdout hash mismatch"):
        guard.record_empirical_observation(
            assertion="Unit tests passed",
            tool="run_tests",
            target="tests/",
            exit_code=0,
            stdout=raw_stdout,
            execution_lock=raw_lock,
            expected_stdout_sha256=_sha256("tampered output with fake success"),
        )


def test_anti_self_citation_circular_loops_multi_hop():
    """T-SRC-01: Multi-hop circular citation topologies are detected and rejected fail-closed."""
    guard = SourceMonitoringGuard()

    # Step 1: Claim A
    hyp_a = guard.create_hypothesis("Hypothesis A: Cache improves throughput")
    # Step 2: Claim B cites A
    hyp_b = guard.create_hypothesis("Hypothesis B: Benchmarks confirm A", parent_attribution_ids=(hyp_a.attribution_id,))
    # Step 3: Claim C cites B
    hyp_c = guard.create_hypothesis("Hypothesis C: Latency numbers prove B", parent_attribution_ids=(hyp_b.attribution_id,))

    # Attempt to promote A by citing C (closing the circle A -> B -> C -> A)
    with pytest.raises(SelfCitationError, match="Circular citation loop"):
        guard.evaluate_claim_promotion(hyp_a.attribution_id, supporting_ids=[hyp_c.attribution_id])


def test_unverified_hypothesis_cannot_promote_without_empirical_node():
    """T-SRC-01: A web of speculative hypotheses and external testimony cannot promote each other."""
    guard = SourceMonitoringGuard()

    hyp1 = guard.create_hypothesis("Hypothesis 1: Optimizer reduces memory")
    hyp2 = guard.create_hypothesis("Hypothesis 2: LLM reasoning confirms hypothesis 1")
    ext1 = guard.create_external_testimony("External user claim: Optimizer works great")

    # Trying to promote hyp1 using hyp2 and ext1
    with pytest.raises(SelfCitationError, match="Anti-Self-Citation"):
        guard.evaluate_claim_promotion(
            hyp1.attribution_id,
            supporting_ids=[hyp2.attribution_id, ext1.attribution_id],
        )

    # State of hyp1 must be UNSUPPORTED, never VERIFIED_EMPIRICAL
    assert guard.attributions[hyp1.attribution_id].veracity_state == VeracityState.UNSUPPORTED


def test_working_memory_filter_boundary():
    """Corrupted attributions and ungrounded hypotheses are blocked from working memory."""
    guard = SourceMonitoringGuard()
    hyp = guard.create_hypothesis("Raw speculative hypothesis")
    ext = guard.create_external_testimony("Unvetted user tip")

    # When require_verified is True, ungrounded claims are rejected
    filtered = guard.filter_working_memory_candidates(
        [hyp.attribution_id, ext.attribution_id],
        require_verified=True,
    )
    assert len(filtered) == 0


# ==============================================================================
# Suite 3: Lineage Integrity & Non-Erasure Boundaries (Consolidation - T-CONS-01/02/03)
# ==============================================================================


def test_ledger_shrinking_raises_non_erasure_violation(tmp_path: Path):
    """T-CONS-02: Non-Erasure principle: any ledger shrinkage raises ConsolidationError."""
    ledger_path = tmp_path / "shrinking_ledger.jsonl"
    events = [
        {"concept": "c1", "assertion": "event 1"},
        {"concept": "c2", "assertion": "event 2"},
    ]
    with open(ledger_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    engine = ConsolidationEngine()

    # Monkey-patch stat to simulate file shrinkage during read
    orig_stat = Path.stat
    calls = []

    def shrinking_stat(self, *args, **kwargs):
        res = orig_stat(self, *args, **kwargs)
        if self == ledger_path:
            calls.append(1)
            if len(calls) >= 3:
                import os
                return os.stat_result((res.st_mode, res.st_ino, res.st_dev, res.st_nlink, res.st_uid, res.st_gid, res.st_size - 10, res.st_atime, res.st_mtime, res.st_ctime))
        return res

    import unittest.mock
    with unittest.mock.patch.object(Path, "stat", shrinking_stat):
        with pytest.raises(ConsolidationError, match="T-CONS-02: Non-Erasure violation"):
            engine.ingest_ledger_file(ledger_path)


def test_corrupted_jsonl_ledger_line_fails_closed(tmp_path: Path):
    """Corrupted or invalid JSON lines in episodic ledger fail closed immediately."""
    ledger_path = tmp_path / "corrupt_ledger.jsonl"
    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write('{"concept": "good", "assertion": "ok"}\n')
        f.write('MALFORMED_NON_JSON_CORRUPTED_LINE\n')

    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="corrupt ledger JSON on line 2"):
        engine.ingest_ledger_file(ledger_path)


def test_consolidation_dangling_lineage_detection():
    """T-CONS-01: Lineage integrity verification detects dangling or fabricated hashes."""
    engine = ConsolidationEngine()
    real_hash = _sha256("real-event-1")
    engine.ingest_event_stream([(real_hash, {"concept": "crypto", "assertion": "Valid claim"})])
    assert engine.validate_lineage_integrity() is True

    # Inject an uningested ghost hash into an existing node
    node_id = list(engine.nodes.keys())[0]
    ghost_hash = _sha256("fabricated-ghost-event")
    corrupt_node = dataclasses.replace(
        engine.nodes[node_id],
        source_event_hashes=(real_hash, ghost_hash),
    )
    engine._nodes[node_id] = corrupt_node

    with pytest.raises(ConsolidationError, match="T-CONS-01: Dangling lineage reference"):
        engine.validate_lineage_integrity()
