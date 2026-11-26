"""Epistemic Ledger Memory Bridge for Ario Agent Runtime.

Connects bounded execution JSONL ledgers (from ario_agent.py and ledger_observation_adapter.py)
to Cognitive Memory (ConsolidationEngine, SourceMonitoringGuard, ProspectiveMemoryRegistry).

Epistemic Invariant Guarantees:
1. Read-Only Ingestion: Does not write, mutate, truncate, or overwrite agent execution ledgers.
2. Reported Provenance: replayed STEP_OBSERVED bytes are LEDGER_REPORT / REPORTED_UNVERIFIED, not independent execution evidence.
3. Anti-Self-Citation: replayed JSONL cannot masquerade as authenticated tool execution.
4. Contradiction Preservation: contradictory observations remain CONTESTED without historical erasure.
5. Prospective Cue Boundary: untrusted task-finish reports are counted, never used to trigger queued actions.
6. No-History-Promotion: Repeated unverified steps retain RECORDED status without upgrading to SUPPORTED.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.memory_consolidation import (
    ConsolidationEngine,
    ConsolidationError,
    NodeEpistemicStatus,
    SemanticNode,
)
from core.source_monitoring import SourceMonitoringError, SourceMonitoringGuard
from core.prospective_memory import (
    DelayedIntention,
    ProspectiveMemoryRegistry,
)

MAX_LEDGER_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 128 * 1024
MAX_EVENTS = 10000


class BridgeError(ValueError):
    """Base exception for epistemic ledger bridge violations."""
    pass


@dataclasses.dataclass(frozen=True)
class BridgeAuditSummary:
    """Read-only cryptographic summary of ledger bridge consolidation."""
    ledger_path: str
    ledger_sha256: str
    total_events_read: int
    steps_observed: int
    nodes_consolidated: int
    contested_nodes_count: int
    triggered_intentions_count: int
    triggered_intentions: Tuple[Dict[str, Any], ...] = ()
    reported_task_finishes_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ledger_path": self.ledger_path,
            "ledger_sha256": self.ledger_sha256,
            "total_events_read": self.total_events_read,
            "steps_observed": self.steps_observed,
            "nodes_consolidated": self.nodes_consolidated,
            "contested_nodes_count": self.contested_nodes_count,
            "triggered_intentions_count": self.triggered_intentions_count,
            "triggered_intentions": list(self.triggered_intentions),
            "reported_task_finishes_count": self.reported_task_finishes_count,
        }


class EpistemicLedgerBridge:
    """Bridge between episodic agent execution JSONL and cognitive memory schemas."""

    def __init__(
        self,
        consolidation_engine: Optional[ConsolidationEngine] = None,
        source_guard: Optional[SourceMonitoringGuard] = None,
        prospective_registry: Optional[ProspectiveMemoryRegistry] = None,
        node_id_version: str = "v2",
    ) -> None:
        self.engine = consolidation_engine or ConsolidationEngine(
            node_id_version=node_id_version,
            default_status=NodeEpistemicStatus.RECORDED,
        )
        self.guard = source_guard or SourceMonitoringGuard()
        self.registry = prospective_registry or ProspectiveMemoryRegistry()
        self.node_id_version = node_id_version

    @staticmethod
    def compute_step_execution_lock(action: Dict[str, Any], result: Dict[str, Any]) -> str:
        """Derive deterministic SHA-256 execution lock over step action and result."""
        payload = json.dumps({"action": action, "result": result}, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def ingest_agent_ledger(
        self,
        ledger_path: str | Path,
        current_epoch: Optional[float] = None,
    ) -> BridgeAuditSummary:
        """Ingest agent execution JSONL without mutating the source file."""
        target = Path(ledger_path)
        if target.is_symlink():
            raise BridgeError(f"symbolic-link ledger refused: {target}")
        if not target.exists():
            raise BridgeError(f"ledger file not found: {target}")

        file_size = target.stat().st_size
        if file_size > MAX_LEDGER_BYTES:
            raise BridgeError(f"ledger size {file_size} exceeds bound {MAX_LEDGER_BYTES}")

        file_hasher = hashlib.sha256()
        total_events = 0
        steps_observed = 0
        reported_task_finishes_count = 0
        triggered_intentions: List[Dict[str, Any]] = []

        with target.open("rb") as stream:
            for line_no, raw_line in enumerate(iter(lambda: stream.readline(MAX_LINE_BYTES + 1), b""), start=1):
                if line_no > MAX_EVENTS:
                    raise BridgeError(f"event-count limit {MAX_EVENTS} exceeded on line {line_no}")
                if len(raw_line) > MAX_LINE_BYTES:
                    raise BridgeError(f"line {line_no} exceeds max line bytes {MAX_LINE_BYTES}")
                if not raw_line:
                    break

                file_hasher.update(raw_line)
                clean = raw_line.strip()
                if not clean:
                    continue

                line_hash = hashlib.sha256(clean).hexdigest()
                try:
                    event = json.loads(clean.decode("utf-8"))
                except Exception as exc:
                    raise BridgeError(f"malformed JSON on line {line_no}: {exc}") from exc

                if not isinstance(event, dict):
                    raise BridgeError(f"event on line {line_no} must be a JSON object")

                event_type = event.get("event")
                total_events += 1

                # 1. TASK_STARTED: Preserve the historical goal ID on external testimony.
                if event_type == "TASK_STARTED":
                    task_id = str(event.get("task_id", f"task-{line_no}"))
                    goal = str(event.get("goal", ""))
                    if goal:
                        goal_claim = f"task_goal:{task_id}:{goal}"
                        goal_digest = hashlib.sha256(goal_claim.encode("utf-8")).hexdigest()
                        self.guard.create_external_testimony(
                            assertion=goal_claim,
                            attribution_id=f"ATTR-HYP-{goal_digest[:12]}",
                            falsification_condition=f"task_{task_id}_fails",
                        )
                        self.engine.ingest_event_stream([(
                            line_hash,
                            {
                                "concept": f"task_goal:{task_id}",
                                "assertion": goal,
                                "status": NodeEpistemicStatus.RECORDED.value,
                            },
                        )])

                # 2. STEP_OBSERVED: Unverified report -> recorded semantic node
                elif event_type == "STEP_OBSERVED":
                    steps_observed += 1
                    tool = str(event.get("tool", ""))
                    # Preserve the injected guard input boundary from #381.
                    if not tool.strip() or tool not in self.guard._allowlisted_tools:
                        raise SourceMonitoringError(f"Tool '{tool}' is not allowlisted for ledger import")
                    step_id = str(event.get("step_id", f"step-{line_no}"))
                    task_id = str(event.get("task_id", "unknown"))
                    status = str(event.get("status", "UNKNOWN"))
                    result = event.get("result", {})
                    if not isinstance(result, dict):
                        result = {"raw": result}

                    path_val = str(result.get("path", event.get("path", "")))
                    target_name = path_val or str(result.get("target", tool))
                    stdout_str = json.dumps(result, sort_keys=True)

                    # A JSONL status and self-hashed result are reports, not
                    # independent evidence that the tool actually executed.
                    self.guard.record_unverified_ledger_report(
                        assertion=f"reported_step_execution:{tool}:{target_name}:{status}",
                        record_sha256=line_hash,
                    )

                    # Determine semantic concept and assertion
                    concept = f"agent_tool:{tool}:{target_name}"
                    assertion = stdout_str

                    # Check for contradiction with existing step results
                    claim_data: Dict[str, Any] = {
                        "concept": concept,
                        "assertion": assertion,
                        # Successful and failed self-reports have equal epistemic
                        # standing unless an explicit contradictory observation exists.
                        "status": NodeEpistemicStatus.RECORDED.value,
                    }

                    # If previous observation on same target exists with different assertion, mark conflict
                    for existing in self.engine.nodes.values():
                        if existing.concept == concept and existing.assertion != assertion:
                            claim_data["negates"] = existing.node_id
                            claim_data["status"] = NodeEpistemicStatus.CONTESTED.value
                            break

                    self.engine.ingest_event_stream([(line_hash, claim_data)])

                # 3. TASK_FINISHED: count the untrusted report without
                # evaluating a registry cue that could mutate a pending intention
                # and expose its action_payload.
                elif event_type == "TASK_FINISHED":
                    reported_task_finishes_count += 1

        contested_count = sum(1 for n in self.engine.nodes.values() if n.status == NodeEpistemicStatus.CONTESTED)

        return BridgeAuditSummary(
            ledger_path=str(target),
            ledger_sha256=file_hasher.hexdigest(),
            total_events_read=total_events,
            steps_observed=steps_observed,
            nodes_consolidated=len(self.engine.nodes),
            contested_nodes_count=contested_count,
            triggered_intentions_count=len(triggered_intentions),
            triggered_intentions=tuple(triggered_intentions),
            reported_task_finishes_count=reported_task_finishes_count,
        )
