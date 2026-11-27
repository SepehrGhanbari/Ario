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

import copy
import dataclasses
import hashlib
import io
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.memory_consolidation import (
    ConsolidationEngine,
    ConsolidationError,
    NodeEpistemicStatus,
    SemanticNode,
    _loads_ledger_line,
    _JSON_WHITESPACE,
    _event_digest,
    ledger_line_digests,
)
from core.source_monitoring import SourceMonitoringError, SourceMonitoringGuard
from core.prospective_memory import (
    DelayedIntention,
    ProspectiveMemoryRegistry,
)

MAX_LEDGER_BYTES = 16 * 1024 * 1024
MAX_LINE_BYTES = 128 * 1024
MAX_EVENTS = 10000
# These inspections report structure, not authenticated empirical execution.
NATIVE_INSPECTION_REPORT_TOOLS = frozenset({"audit_m0", "inspect_rere_revision", "verify_ledger_manifest"})


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
    legacy_native_projections_retained: int = 0

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
            "legacy_native_projections_retained": self.legacy_native_projections_retained,
        }


class EpistemicLedgerBridge:
    """Bridge between episodic agent execution JSONL and cognitive memory schemas."""

    def __init__(
        self,
        consolidation_engine: Optional[ConsolidationEngine] = None,
        source_guard: Optional[SourceMonitoringGuard] = None,
        prospective_registry: Optional[ProspectiveMemoryRegistry] = None,
        node_id_version: str = "v2",
        *,
        report_only_tools: Optional[Set[str]] = None,
    ) -> None:
        self.engine = consolidation_engine or ConsolidationEngine(
            node_id_version=node_id_version,
            default_status=NodeEpistemicStatus.RECORDED,
        )
        self.guard = source_guard or SourceMonitoringGuard()
        self.registry = prospective_registry or ProspectiveMemoryRegistry()
        self.node_id_version = node_id_version
        # A caller-injected guard retains its existing allowlist by default.
        # Explicit report-only opt-in is separate from empirical admission and
        # cannot introduce arbitrary new tools into the replay boundary.
        extra = (NATIVE_INSPECTION_REPORT_TOOLS if source_guard is None else frozenset()
                 ) if report_only_tools is None else frozenset(report_only_tools)
        if not extra <= NATIVE_INSPECTION_REPORT_TOOLS:
            raise BridgeError("unsupported report-only inspection tool")
        self._report_only_tools = extra

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
        """Parse first, then atomically apply to engine and guard in-process."""
        target = Path(ledger_path)
        if target.is_symlink():
            raise BridgeError(f"symbolic-link ledger refused: {target}")
        if not target.exists():
            raise BridgeError(f"ledger file not found: {target}")

        file_size = target.stat().st_size
        if file_size > MAX_LEDGER_BYTES:
            raise BridgeError(f"ledger size {file_size} exceeds bound {MAX_LEDGER_BYTES}")

        # Read at most the existing byte budget. Preflight framing on exactly
        # the bytes subsequently consumed, before any guard or memory writes.
        # This is not a publisher-authenticated or durable filesystem snapshot.
        with target.open("rb") as source:
            raw = source.read(MAX_LEDGER_BYTES + 1)
        if len(raw) > MAX_LEDGER_BYTES:
            raise BridgeError("ledger exceeds byte budget during read")
        if raw and not raw.endswith(b"\n"):
            raise BridgeError("HOLD_INCOMPLETE_JSONL_LINE")
        records, ledger_sha256 = self._parse_agent_ledger(raw)
        # Match the joint-snapshot lock order. Never replace a live RLock.
        locks = sorted((self.engine._batch_lock, self.guard._lock), key=id)
        with locks[0], locks[1]:
            if self.engine._batch_running or getattr(
                    self.engine._thread_state(), "materializing", False):
                raise ConsolidationError("HOLD_REENTRANT_EVENT_BATCH")
            # All six graph containers hold immutable records or scalar values.
            # Guard revisions contain mutable lists, so deep-copy them.
            engine_fields = ("_nodes", "_legacy_aliases", "_links", "_ledger_hashes",
                             "_event_payload_digests", "_event_stable_digests")
            engine_before = {name: getattr(self.engine, name).copy()
                             for name in engine_fields}
            guard_before = copy.deepcopy((self.guard._attributions,
                                          self.guard._revisions,
                                          self.guard._active_verified_ids))
            try:
                return self._commit_agent_records(target, ledger_sha256, records)
            except BaseException:
                for name, value in engine_before.items():
                    setattr(self.engine, name, value)
                (self.guard._attributions, self.guard._revisions,
                 self.guard._active_verified_ids) = guard_before
                raise
            # The registry is never accessed or mutated by this import. Do not
            # roll back unrelated registry activity from another caller.

    def _parse_agent_ledger(self, raw: bytes) -> Tuple[List[Tuple[int, str, Dict[str, Any]]], str]:
        records: List[Tuple[int, str, Dict[str, Any]]] = []
        file_hasher = hashlib.sha256()
        with io.BytesIO(raw) as stream:
            for line_no, raw_line in enumerate(iter(lambda: stream.readline(MAX_LINE_BYTES + 1), b""), start=1):
                if line_no > MAX_EVENTS:
                    raise BridgeError(f"event-count limit {MAX_EVENTS} exceeded on line {line_no}")
                if len(raw_line) > MAX_LINE_BYTES:
                    raise BridgeError(f"line {line_no} exceeds max line bytes {MAX_LINE_BYTES}")
                if not raw_line:
                    break

                file_hasher.update(raw_line)
                clean = raw_line.strip(_JSON_WHITESPACE)
                if not clean:
                    continue

                line_hash, _ = ledger_line_digests(raw_line)
                try:
                    event = _loads_ledger_line(clean.decode("utf-8"))
                except Exception as exc:
                    raise BridgeError(f"malformed JSON on line {line_no}: {exc}") from exc

                if not isinstance(event, dict):
                    raise BridgeError(f"event on line {line_no} must be a JSON object")

                records.append((line_no, line_hash, event))
        return records, file_hasher.hexdigest()

    def _commit_agent_records(self, target: Path, ledger_sha256: str,
                              records: List[Tuple[int, str, Dict[str, Any]]]) -> BridgeAuditSummary:
        total_events = 0
        steps_observed = 0
        reported_task_finishes_count = 0
        legacy_native_projections_retained = 0
        triggered_intentions: List[Dict[str, Any]] = []
        for line_no, line_hash, event in records:
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
                native = "observation" in event
                # Preserve the injected guard input boundary from #381.
                # A report-only tool is not added to the empirical allowlist.
                if not tool.strip() or not (tool in self.guard._allowlisted_tools
                        or (native and tool in self._report_only_tools)):
                    raise SourceMonitoringError(f"Tool '{tool}' is not allowlisted for ledger import")
                status = str(event.get("status", "UNKNOWN"))
                result = event.get("result", {})
                if not isinstance(result, dict):
                    result = {"raw": result}

                path_val = str(result.get("path", event.get("path", "")))
                target_name = path_val or str(result.get("target", tool))
                stdout_str = json.dumps(result, sort_keys=True)

                if native:
                    if "result" in event or type(event["observation"]) is not dict:
                        raise BridgeError("HOLD_AMBIGUOUS_NATIVE_STEP_OBSERVATION")
                    task_id, step_id = event.get("task_id"), event.get("step_id")
                    if not all(type(v) is str and v.strip() for v in (task_id, step_id)):
                        raise BridgeError("HOLD_INVALID_NATIVE_STEP_IDENTITY")
                    # An earlier version could have recorded this same native
                    # line as an empty legacy result. Preserve that historical
                    # projection; the existing replay check below still must
                    # validate its exact retained payload digest.
                    old_concept = f"agent_tool:{tool}:{target_name}"
                    old_id = self.engine.compute_node_id(
                        old_concept.strip(), stdout_str.strip(), version=self.engine.node_id_version)
                    old_node = self.engine.nodes.get(old_id)
                    if (line_hash in self.engine._event_payload_digests
                            and old_node is not None and line_hash in old_node.source_event_hashes):
                        legacy_native_projections_retained += 1
                    else:
                        # Different task/step identities may describe different
                        # times or targets. Do not invent a contradiction merely
                        # because two audit tools returned different reports.
                        target_name = "native:" + json.dumps([task_id, step_id],
                                                               ensure_ascii=True, separators=(",", ":"))
                        stdout_str = json.dumps(event["observation"], sort_keys=True)

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

                # A replay after a later contradiction must retain the original
                # projection, not recalculate it from the newer graph. Verify
                # the retained payload digest against the exact base projection
                # or a historical conflict projection, never hash membership alone.
                if line_hash in self.engine._event_payload_digests:
                    retained = self.engine._event_payload_digests[line_hash]
                    node_id = self.engine.compute_node_id(
                        concept.strip(), assertion.strip(), version=self.engine.node_id_version)
                    node = self.engine.nodes.get(node_id)
                    if node is None or line_hash not in node.source_event_hashes:
                        raise ConsolidationError("HOLD_REUSED_HASH_DIFFERENT_EVENT_PAYLOAD")
                    if retained == _event_digest(claim_data):
                        continue
                    for existing in self.engine.nodes.values():
                        if existing.concept == concept and existing.assertion != assertion:
                            prior = dict(claim_data, negates=existing.node_id,
                                         status=NodeEpistemicStatus.CONTESTED.value)
                            if retained == _event_digest(prior):
                                break
                    else:
                        raise ConsolidationError("HOLD_REUSED_HASH_DIFFERENT_EVENT_PAYLOAD")
                    continue

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
            ledger_sha256=ledger_sha256,
            total_events_read=total_events,
            steps_observed=steps_observed,
            nodes_consolidated=len(self.engine.nodes),
            contested_nodes_count=contested_count,
            triggered_intentions_count=len(triggered_intentions),
            triggered_intentions=tuple(triggered_intentions),
            reported_task_finishes_count=reported_task_finishes_count,
            legacy_native_projections_retained=legacy_native_projections_retained,
        )
