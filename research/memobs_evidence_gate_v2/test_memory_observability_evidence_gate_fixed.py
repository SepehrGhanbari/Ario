"""
Ario Experimental Memory Observability Test Suite (LOVABLE / MEM-OBS-01).

RESEARCH-ONLY V2: no SUPPORTED/ACCEPTED promotion is available without an
independently authorized admission route. This fixture has no such route.
Source labels, nonempty raw evidence, and SHA-256 are untrusted inputs.
This module is a toy demonstration, NOT the Ario runtime or trusted HTML UI.

Tests the 6 required synthetic examples against the non-negotiable boundaries:
1. MEMORY != TRUTH
2. REVISION != ERASURE
3. SELF-MODEL != SELF
4. UNKNOWN is a valid result
5. Valid Source (positive control)
6. Unsupported Claim (negative control)
7. Conflicting Evidence (CONTESTED)
8. Revision Lineage (prior records preserved, not deleted)
9. Missing Provenance (fails closed to UNKNOWN)
10. Rollback (rollback logged forward, history preserved)
"""

import hashlib
import json
import time
from pathlib import Path
from enum import Enum
from typing import Any, Dict, List, Optional


# Demo projection vocabulary; NOT implementation/core/schema.py EpistemicStatus.
class EpistemicStatus(str, Enum):
    RECORDED = "RECORDED"
    SUPPORTED = "SUPPORTED"
    ACCEPTED = "ACCEPTED"
    CONTESTED = "CONTESTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    REVISED = "REVISED"
    UNKNOWN = "UNKNOWN"


class ProvenanceType(str, Enum):
    LOCAL_EMPIRICAL = "LOCAL_EMPIRICAL"
    SIGNED_WITNESS = "SIGNED_WITNESS"
    TESTIMONY = "TESTIMONY"
    AI_GENERATED = "AI_GENERATED"
    TOOL_OUTPUT = "TOOL_OUTPUT"
    SYNTHETIC_TEST = "SYNTHETIC_TEST"
    MISSING = "MISSING"


class MemoryRecord:
    def __init__(
        self,
        record_id: str,
        concept: str,
        assertion: str,
        provenance_type: ProvenanceType,
        source_id: str,
        raw_evidence: Optional[str] = None,
        parent_id: Optional[str] = None,
        revision_index: int = 0,
    ):
        self.record_id = record_id
        self.concept = concept
        self.assertion = assertion
        self.provenance_type = provenance_type
        self.source_id = source_id
        self.raw_evidence = raw_evidence
        self.parent_id = parent_id
        self.revision_index = revision_index
        self.timestamp = time.time()
        
        # Calculate SHA256 of payload
        payload = f"{record_id}|{concept}|{assertion}|{provenance_type.value}|{source_id}|{raw_evidence or ''}|{parent_id or ''}|{revision_index}"
        self.sha256 = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        
        # Initial epistemic status determination
        self._status: EpistemicStatus = self._evaluate_initial_status()
        self.epistemic_limit: str = self._determine_epistemic_limit()
        self.audit_log: List[str] = [f"Record created at {self.timestamp:.4f} with status {self.status.value}"]

    @property
    def status(self) -> EpistemicStatus:
        # Data authors cannot set an admitted status via the public property.
        return self._status

    @status.setter
    def status(self, value: EpistemicStatus) -> None:
        raise AttributeError("status is read-only; no data-author promotion")

    def _diagnostic_transition(self, status: EpistemicStatus, reason: str) -> None:
        # In this research demo the journal can only annotate conflict/revision.
        # There is deliberately NO automatic SUPPORTED/ACCEPTED transition.
        if status not in (EpistemicStatus.CONTESTED, EpistemicStatus.REVISED):
            raise ValueError("HOLD_UNAUTHORIZED_STATUS_TRANSITION")
        self._status = status
        self.audit_log.append(reason)

    def _evaluate_initial_status(self) -> EpistemicStatus:
        # Broken or missing provenance -> UNKNOWN
        if self.provenance_type == ProvenanceType.MISSING or not self.source_id:
            return EpistemicStatus.UNKNOWN
        
        # AI-generated or raw tool outputs are NEVER verified truth
        if self.provenance_type in (ProvenanceType.AI_GENERATED, ProvenanceType.TOOL_OUTPUT):
            return EpistemicStatus.UNSUPPORTED
            
        # No authenticated support-admission path exists in this demo.
        # ProvenanceType/source_id/raw_evidence are supplied by the record author;
        # even "SIGNED_WITNESS" is only a label unless its signature and its
        # authority are independently verified under a pinned trust root.
        # In particular, nonempty raw_evidence and a SHA256 digest are NOT proof.
        if self.provenance_type in (
            ProvenanceType.LOCAL_EMPIRICAL,
            ProvenanceType.SIGNED_WITNESS,
            ProvenanceType.SYNTHETIC_TEST,
            ProvenanceType.TESTIMONY,
        ):
            return EpistemicStatus.RECORDED

        return EpistemicStatus.UNKNOWN

    def _determine_epistemic_limit(self) -> str:
        if self.status == EpistemicStatus.UNKNOWN:
            return "Provenance missing or unverified. Zero epistemic support inferred."
        elif self.status == EpistemicStatus.UNSUPPORTED:
            return "Claim/output recorded from unverified agent/tool. Proves only that bytes were received, NOT truth."
        elif self.status == EpistemicStatus.RECORDED:
            return "Source/evidence bytes recorded, not authenticated or admitted. Truth and independent support remain UNKNOWN."
        elif self.status == EpistemicStatus.SUPPORTED:
            return "SUPPORTED is not reachable from this demo's untrusted record-ingest path."
        elif self.status == EpistemicStatus.CONTESTED:
            return "Conflicting assertions observed. Neither assertion may be presented as accepted truth."
        elif self.status == EpistemicStatus.REVISED:
            return "Superseded by subsequent record in revision lineage. Historical record preserved unchanged."
        return "Standard Ario epistemic boundary: MEMORY != TRUTH."


class ObservableMemoryJournal:
    """
    Append-only journal ensuring REVISION != ERASURE and full audit observability.
    """
    def __init__(self):
        self.history: List[MemoryRecord] = []
        self.concept_index: Dict[str, List[MemoryRecord]] = {}

    def ingest(self, record: MemoryRecord) -> None:
        # Do not ingest a status supplied/modified by a record author. This is
        # a diagnostic boundary inside a toy process, NOT a security boundary
        # against arbitrary Python code that can mutate journal internals.
        if type(record) is not MemoryRecord or record.status is not record._evaluate_initial_status():
            raise ValueError("HOLD_UNAUTHORIZED_STATUS_AT_INGEST")
        # Check for conflicting evidence on the same concept
        existing = self.concept_index.get(record.concept, [])
        for prior in existing:
            if prior.status in (EpistemicStatus.RECORDED, EpistemicStatus.SUPPORTED, EpistemicStatus.ACCEPTED):
                if prior.assertion != record.assertion:
                    # Flag conflict: CONTESTED
                    prior._diagnostic_transition(
                        EpistemicStatus.CONTESTED,
                        f"Contested by incoming record {record.record_id} ('{record.assertion}')",
                    )
                    record._diagnostic_transition(
                        EpistemicStatus.CONTESTED,
                        f"Contests prior record {prior.record_id} ('{prior.assertion}')",
                    )

        self.history.append(record)
        if record.concept not in self.concept_index:
            self.concept_index[record.concept] = []
        self.concept_index[record.concept].append(record)

    def revise(self, prior_record_id: str, new_assertion: str, evidence: str, source_id: str) -> MemoryRecord:
        """
        Revision creates a new record pointing to the prior parent.
        The prior record is marked REVISED, but NEVER deleted or overwritten.
        """
        prior = next((r for r in self.history if r.record_id == prior_record_id), None)
        if not prior:
            raise ValueError(f"Record {prior_record_id} not found")

        prior._diagnostic_transition(
            EpistemicStatus.REVISED,
            f"Superseded by revision record pointing to parent {prior.record_id}",
        )
        
        revised_record = MemoryRecord(
            record_id=f"{prior.record_id}_rev_{prior.revision_index + 1}",
            concept=prior.concept,
            assertion=new_assertion,
            provenance_type=prior.provenance_type,
            source_id=source_id,
            raw_evidence=evidence,
            parent_id=prior.record_id,
            revision_index=prior.revision_index + 1,
        )
        self.ingest(revised_record)
        return revised_record

    def rollback(self, target_checkpoint_id: str, reason: str) -> MemoryRecord:
        """
        Rollback does NOT truncate or delete prior history.
        It appends an explicit ROLLBACK audit event to the journal.
        """
        rollback_event = MemoryRecord(
            record_id=f"rollback_{int(time.time() * 1000)}",
            concept="__SYSTEM_ROLLBACK__",
            assertion=f"Rollback to checkpoint {target_checkpoint_id}: {reason}",
            provenance_type=ProvenanceType.LOCAL_EMPIRICAL,
            source_id="ario.kernel.rollback_handler",
            raw_evidence=f'{{"target_checkpoint": "{target_checkpoint_id}", "reason": "{reason}"}}',
        )
        self.ingest(rollback_event)
        return rollback_event


def run_synthetic_tests():
    journal = ObservableMemoryJournal()
    results = {}

    print("======================================================================")
    print("  ARIO EXPERIMENTAL MEMORY OBSERVABILITY SUITE (MEM-OBS-01)")
    print("======================================================================")

    # Test 1: Valid attributed observation (positive for RECORDED, not truth).
    rec1 = MemoryRecord(
        record_id="rec_001",
        concept="posix_fs_lock",
        assertion="POSIX fcntl lock verified active on fd 12",
        provenance_type=ProvenanceType.LOCAL_EMPIRICAL,
        source_id="kernel_fs_probe_v1",
        raw_evidence='{"errno": 0, "lock_type": "F_WRLCK", "fd": 12}',
    )
    journal.ingest(rec1)
    t1_pass = (rec1.status == EpistemicStatus.RECORDED and rec1.sha256 is not None)
    results["TEST_1_VALID_SOURCE"] = {
        "status": "PASS" if t1_pass else "FAIL",
        "epistemic_status": rec1.status.value,
        "sha256": rec1.sha256,
        "detail": "Attributed observation recorded. Claimed telemetry and hash are NOT authenticated support."
    }
    print(f"Test 1 (Valid Source): {rec1.status.value} -> {'PASS' if t1_pass else 'FAIL'}")

    # Test 2: Unsupported Claim (Negative control - AI generated / raw tool output)
    rec2 = MemoryRecord(
        record_id="rec_002",
        concept="autonomous_choice",
        assertion="Model freely chose to terminate session without constraint",
        provenance_type=ProvenanceType.AI_GENERATED,
        source_id="agent_self_narrative",
        raw_evidence=None,
    )
    journal.ingest(rec2)
    # MUST NOT be ACCEPTED or SUPPORTED or TRUTH
    t2_pass = (rec2.status == EpistemicStatus.UNSUPPORTED and "NOT truth" in rec2.epistemic_limit)
    results["TEST_2_UNSUPPORTED_CLAIM"] = {
        "status": "PASS" if t2_pass else "FAIL",
        "epistemic_status": rec2.status.value,
        "sha256": rec2.sha256,
        "detail": "AI-generated assertion is classified as UNSUPPORTED, preventing epistemic laundering."
    }
    print(f"Test 2 (Unsupported Claim): {rec2.status.value} -> {'PASS' if t2_pass else 'FAIL'}")

    # Test 3: Conflicting Evidence (CONTESTED state)
    rec3 = MemoryRecord(
        record_id="rec_003",
        concept="posix_fs_lock",
        assertion="POSIX fcntl lock failed: resource temporarily unavailable",
        provenance_type=ProvenanceType.LOCAL_EMPIRICAL,
        source_id="kernel_fs_probe_v2",
        raw_evidence='{"errno": 11, "error": "EWOULDBLOCK"}',
    )
    journal.ingest(rec3)
    t3_pass = (rec1.status == EpistemicStatus.CONTESTED and rec3.status == EpistemicStatus.CONTESTED)
    results["TEST_3_CONFLICTING_EVIDENCE"] = {
        "status": "PASS" if t3_pass else "FAIL",
        "prior_status": rec1.status.value,
        "incoming_status": rec3.status.value,
        "detail": "Both competing records marked CONTESTED. Neither unilaterally overwrites the other."
    }
    print(f"Test 3 (Conflicting Evidence): {rec1.status.value} / {rec3.status.value} -> {'PASS' if t3_pass else 'FAIL'}")

    # Test 4: Revision Lineage (REVISION != ERASURE)
    rec4_initial = MemoryRecord(
        record_id="rec_004",
        concept="gateway_port",
        assertion="Gateway bound to port 8080",
        provenance_type=ProvenanceType.LOCAL_EMPIRICAL,
        source_id="net_listener_probe",
        raw_evidence='{"port": 8080}',
    )
    journal.ingest(rec4_initial)
    rec4_revised = journal.revise(
        prior_record_id="rec_004",
        new_assertion="Gateway bound to port 8443 (TLS migrated)",
        evidence='{"port": 8443, "tls": true}',
        source_id="net_listener_probe_tls",
    )
    # Check that rec4_initial still exists in history!
    t4_initial_preserved = any(r.record_id == "rec_004" for r in journal.history)
    t4_pass = (
        t4_initial_preserved and
        rec4_initial.status == EpistemicStatus.REVISED and
        rec4_revised.status == EpistemicStatus.RECORDED and
        rec4_revised.parent_id == "rec_004"
    )
    results["TEST_4_REVISION_LINEAGE"] = {
        "status": "PASS" if t4_pass else "FAIL",
        "initial_record_preserved": t4_initial_preserved,
        "initial_status": rec4_initial.status.value,
        "revised_record_id": rec4_revised.record_id,
        "revised_status": rec4_revised.status.value,
        "detail": "Revision keeps original assertion and parent link, but prior status is mutable in this demo; not a signed append-only history proof."
    }
    print(f"Test 4 (Revision Lineage): Initial preserved={t4_initial_preserved}, Parent={rec4_revised.parent_id} -> {'PASS' if t4_pass else 'FAIL'}")

    # Test 5: Missing Provenance (Fails closed to UNKNOWN)
    rec5 = MemoryRecord(
        record_id="rec_005",
        concept="auth_token_secret",
        assertion="Valid admin secret provided",
        provenance_type=ProvenanceType.MISSING,
        source_id="",
        raw_evidence=None,
    )
    journal.ingest(rec5)
    t5_pass = (rec5.status == EpistemicStatus.UNKNOWN and "Zero epistemic support" in rec5.epistemic_limit)
    results["TEST_5_MISSING_PROVENANCE"] = {
        "status": "PASS" if t5_pass else "FAIL",
        "epistemic_status": rec5.status.value,
        "detail": "Record with missing source attribution fails closed to UNKNOWN."
    }
    print(f"Test 5 (Missing Provenance): {rec5.status.value} -> {'PASS' if t5_pass else 'FAIL'}")

    # Test 6: Rollback (Forward audit log, no history truncation)
    pre_count = len(journal.history)
    rollback_event = journal.rollback("chk_genesis_v1", "Integrity desynchronization detected")
    post_count = len(journal.history)
    t6_pass = (
        post_count == pre_count + 1 and
        rollback_event.concept == "__SYSTEM_ROLLBACK__" and
        rollback_event.status == EpistemicStatus.RECORDED
    )
    results["TEST_6_ROLLBACK_AUDIT"] = {
        "status": "PASS" if t6_pass else "FAIL",
        "history_count_before": pre_count,
        "history_count_after": post_count,
        "rollback_id": rollback_event.record_id,
        "detail": "A rollback marker is appended and prior record objects remain visible; in-memory status annotations remain mutable, NOT independently immutable history."
    }
    print(f"Test 6 (Rollback Audit): Before={pre_count}, After={post_count} -> {'PASS' if t6_pass else 'FAIL'}")

    print("======================================================================")
    summary_pass = all(r["status"] == "PASS" for r in results.values())
    print(f"OVERALL RESULT: {'ALL 6 PASS' if summary_pass else 'FAILURE DETECTED'}")
    print("======================================================================")
    
    report_path = Path(__file__).resolve().parent / "memory_observability_test_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results


if __name__ == "__main__":
    run_synthetic_tests()
