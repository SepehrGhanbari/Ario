from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from core.memory_consolidation import ConsolidationEngine, ConsolidationError, NodeEpistemicStatus
from core.prospective_memory import (
    DelayedIntention,
    IntentionStatus,
    ProspectiveMemoryError,
    ProspectiveMemoryRegistry,
    ProspectiveSecurityError,
)


def test_crash_orphan_tmp_journal_cleanup(tmp_path: Path):
    """Simulate a crash during journal write leaving orphan temp files; verify cleanup."""
    registry = ProspectiveMemoryRegistry()
    registry.register_intention(
        intention_id="INT-CLEANUP-01",
        description="Persistent Intention",
        predicate_expr="concept == 'auth' and status == 'ACCEPTED'",
        action_payload={"op": "notify"},
        created_at_epoch=100.0,
        ttl_epoch=500.0,
    )
    journal_path = tmp_path / "intentions.json"
    registry.save_journal(journal_path)
    assert journal_path.exists()

    # Create orphan temporary files simulating prior crashed processes
    orphan1 = tmp_path / "intentions.json.tmp.4891"
    orphan2 = tmp_path / "intentions.json.tmp.9182"
    orphan1.write_text("partial write junk", encoding="utf-8")
    orphan2.write_text("another crashed process", encoding="utf-8")

    # Clean up orphan journals
    removed = ProspectiveMemoryRegistry.cleanup_orphan_journals(tmp_path)
    assert removed == 2
    assert not orphan1.exists()
    assert not orphan2.exists()
    assert journal_path.exists()

    # Loaded registry recovers cleanly
    reloaded = ProspectiveMemoryRegistry.load_journal(journal_path)
    assert len(reloaded.intentions) == 1
    assert "INT-CLEANUP-01" in reloaded.intentions


def test_crash_corrupt_truncated_journal_fails_closed(tmp_path: Path):
    """A truncated journal file caused by abrupt power loss fails closed."""
    journal_path = tmp_path / "truncated.json"
    journal_path.write_text('{"version": "1.0", "intentions": [{"intention_id": "INT-TRUNC"', encoding="utf-8")

    with pytest.raises(ProspectiveMemoryError, match="Corrupt or unreadable journal JSON"):
        ProspectiveMemoryRegistry.load_journal(journal_path)


def test_crash_bitflip_tampered_journal_fails_closed(tmp_path: Path):
    """A bitflip or tampering in journal payload triggers SHA-256 digest failure."""
    registry = ProspectiveMemoryRegistry()
    registry.register_intention(
        intention_id="INT-TAMPER-01",
        description="Tamper Target",
        predicate_expr="concept == 'crypto' and status == 'ACCEPTED'",
        action_payload={"op": "key_rotate"},
        created_at_epoch=100.0,
        ttl_epoch=500.0,
    )
    journal_path = tmp_path / "tampered.json"
    registry.save_journal(journal_path)

    # Mutate action_payload on disk without updating digest
    with open(journal_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["intentions"][0]["action_payload"]["op"] = "malicious_exploit"
    with open(journal_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    with pytest.raises(ProspectiveSecurityError, match="T-PROS-01: Integrity digest mismatch"):
        ProspectiveMemoryRegistry.load_journal(journal_path)


def test_crash_zero_byte_journal_fails_closed(tmp_path: Path):
    """A zero-byte journal file fails closed."""
    empty_journal = tmp_path / "empty.json"
    empty_journal.write_bytes(b"")

    with pytest.raises(ProspectiveMemoryError, match="Corrupt or unreadable journal JSON"):
        ProspectiveMemoryRegistry.load_journal(empty_journal)


def test_crash_non_json_binary_garbage_journal_fails_closed(tmp_path: Path):
    """Random binary garbage on disk fails closed."""
    garbage_journal = tmp_path / "garbage.json"
    garbage_journal.write_bytes(os.urandom(256))

    with pytest.raises(ProspectiveMemoryError, match="Corrupt or unreadable journal JSON"):
        ProspectiveMemoryRegistry.load_journal(garbage_journal)


def test_crash_post_reboot_ttl_reconciliation_offline_expiration(tmp_path: Path):
    """Intentions whose TTL lapsed during system downtime expire deterministically on reboot."""
    registry = ProspectiveMemoryRegistry()
    registry.register_intention(
        intention_id="INT-EXPIRED-OFFLINE-01",
        description="Should expire during downtime",
        predicate_expr="concept == 'net' and status == 'ACCEPTED'",
        action_payload={"op": "ping"},
        created_at_epoch=1000.0,
        ttl_epoch=1100.0,
    )
    registry.register_intention(
        intention_id="INT-EXPIRED-OFFLINE-02",
        description="Also should expire during downtime",
        predicate_expr="concept == 'net' and status == 'ACCEPTED'",
        action_payload={"op": "ping"},
        created_at_epoch=1000.0,
        ttl_epoch=1200.0,
    )
    registry.register_intention(
        intention_id="INT-SURVIVING-01",
        description="Should remain active after reboot",
        predicate_expr="concept == 'net' and status == 'ACCEPTED'",
        action_payload={"op": "ping"},
        created_at_epoch=1000.0,
        ttl_epoch=2000.0,
    )

    journal_path = tmp_path / "reboot_journal.json"
    registry.save_journal(journal_path)

    # Simulated reboot occurs at epoch 1500.0
    reboot_epoch = 1500.0
    reloaded = ProspectiveMemoryRegistry.load_journal(journal_path)

    # Initial state on load preserves pending status
    assert reloaded.intentions["INT-EXPIRED-OFFLINE-01"].status == IntentionStatus.PENDING
    assert reloaded.intentions["INT-EXPIRED-OFFLINE-02"].status == IntentionStatus.PENDING
    assert reloaded.intentions["INT-SURVIVING-01"].status == IntentionStatus.PENDING

    # Run post-reboot sweep
    expired_count = reloaded.reconcile_expired_intentions(reboot_epoch)
    assert expired_count == 2
    assert reloaded.intentions["INT-EXPIRED-OFFLINE-01"].status == IntentionStatus.EXPIRED
    assert reloaded.intentions["INT-EXPIRED-OFFLINE-02"].status == IntentionStatus.EXPIRED
    assert reloaded.intentions["INT-SURVIVING-01"].status == IntentionStatus.PENDING


def test_crash_ledger_inspection_clean_file(tmp_path: Path):
    """Read-only inspection on clean ledger reports valid lines and clean status."""
    ledger = tmp_path / "clean_ledger.jsonl"
    lines = [
        json.dumps({"task_id": f"T{i}", "assertion": f"Assertion {i}"})
        for i in range(5)
    ]
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = ConsolidationEngine.inspect_ledger_integrity(ledger)
    assert report.is_clean is True
    assert report.valid_lines == 5
    assert report.corrupt_line_no is None
    assert report.diagnostic == "CLEAN"


def test_crash_ledger_inspection_detects_corrupt_tail_without_modifying_file(tmp_path: Path):
    """Crash leaving a truncated trailing line is detected without mutating the ledger file."""
    ledger = tmp_path / "crashed_ledger.jsonl"
    clean_lines = [
        json.dumps({"task_id": "T1", "assertion": "Valid 1"}),
        json.dumps({"task_id": "T2", "assertion": "Valid 2"}),
    ]
    corrupted_content = "\n".join(clean_lines) + '\n{"task_id": "T3", "assertion": "truncated_tail...'
    ledger.write_text(corrupted_content, encoding="utf-8")

    initial_bytes = ledger.read_bytes()
    initial_stat = ledger.stat()

    report = ConsolidationEngine.inspect_ledger_integrity(ledger)
    assert report.is_clean is False
    assert report.valid_lines == 2
    assert report.corrupt_line_no == 3
    assert "CORRUPT_JSON_OR_TRUNCATED_TAIL" in report.diagnostic

    # Invariant: File bytes and size must remain strictly unmodified
    after_bytes = ledger.read_bytes()
    assert initial_bytes == after_bytes
    assert ledger.stat().st_size == initial_stat.st_size


def test_crash_ledger_inspection_nonexistent_and_empty(tmp_path: Path):
    """Nonexistent and empty ledger files are classified cleanly."""
    missing = tmp_path / "nonexistent.jsonl"
    rep1 = ConsolidationEngine.inspect_ledger_integrity(missing)
    assert rep1.is_clean is False
    assert rep1.diagnostic == "FILE_NOT_FOUND"

    empty = tmp_path / "empty.jsonl"
    empty.write_bytes(b"")
    rep2 = ConsolidationEngine.inspect_ledger_integrity(empty)
    assert rep2.is_clean is True
    assert rep2.diagnostic == "EMPTY_LEDGER"


def test_crash_ledger_ingest_fails_closed_on_corrupt_line(tmp_path: Path):
    """Ingesting a corrupted ledger strictly raises ConsolidationError fail-closed."""
    ledger = tmp_path / "corrupt.jsonl"
    ledger.write_text('{"concept": "c1", "assertion": "a1"}\n{"corrupt line not json\n', encoding="utf-8")

    engine = ConsolidationEngine()
    with pytest.raises(ConsolidationError, match="corrupt ledger JSON on line 2"):
        engine.ingest_ledger_file(ledger)


def test_crash_e2e_reboot_state_reconstruction(tmp_path: Path):
    """End-to-end crash simulation and state reconstruction across process reboot."""
    ledger_path = tmp_path / "agent-events.jsonl"
    journal_path = tmp_path / "intentions.json"

    # Process 1: Ingest events and setup state
    ev1 = {"concept": "network", "assertion": "Port 8080 active", "value": "OPEN"}
    ev2 = {"concept": "network", "assertion": "Port 8080 inactive", "value": "CLOSED", "relation": "opposite"}
    ev3 = {"concept": "db", "assertion": "Schema migrated to v2"}
    events = [ev1, ev2, ev3]
    with open(ledger_path, "w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")

    proc1_engine = ConsolidationEngine()
    proc1_engine.ingest_ledger_file(ledger_path)
    proc1_report = proc1_engine.generate_contestation_report()

    proc1_registry = ProspectiveMemoryRegistry()
    proc1_registry.register_intention(
        intention_id="INT-E2E-01",
        description="Health check",
        predicate_expr="concept == 'network' and status == 'CONTESTED'",
        action_payload={"op": "investigate_network"},
        created_at_epoch=100.0,
        ttl_epoch=1000.0,
    )
    proc1_registry.save_journal(journal_path)

    # Process 1 "crashes" -> all in-memory references are destroyed
    del proc1_engine
    del proc1_registry

    # Process 2 (Post-Crash Reboot):
    # Step 1: Diagnostic ledger preflight
    ledger_audit = ConsolidationEngine.inspect_ledger_integrity(ledger_path)
    assert ledger_audit.is_clean is True
    assert ledger_audit.valid_lines == 3

    # Step 2: Reconstruct semantic graph from immutable ledger
    proc2_engine = ConsolidationEngine()
    ingested_count = proc2_engine.ingest_ledger_file(ledger_path)
    assert ingested_count == 3
    assert len(proc2_engine.nodes) == 3

    # Step 3: Verify contestation report identity
    proc2_report = proc2_engine.generate_contestation_report()
    assert proc2_report.contested_nodes_count == proc1_report.contested_nodes_count
    assert proc2_report.accepted_nodes_count == proc1_report.accepted_nodes_count
    assert proc2_report.contested_concepts == proc1_report.contested_concepts
    assert len(proc2_report.conflicts) == 1
    assert proc2_report.conflicts[0].concept == "network"

    # Step 4: Reconstruct prospective intention registry
    proc2_registry = ProspectiveMemoryRegistry.load_journal(journal_path)
    assert len(proc2_registry.intentions) == 1
    assert "INT-E2E-01" in proc2_registry.intentions
    assert proc2_registry.intentions["INT-E2E-01"].status == IntentionStatus.PENDING

    # Step 5: Test intention trigger against reconstructed contested node
    cue_context = {"concept": "network", "status": "CONTESTED"}
    triggered = proc2_registry.evaluate_cues(cue_context, current_epoch=500.0)
    assert len(triggered) == 1
    assert triggered[0].intention_id == "INT-E2E-01"
    assert proc2_registry.intentions["INT-E2E-01"].status == IntentionStatus.TRIGGERED
