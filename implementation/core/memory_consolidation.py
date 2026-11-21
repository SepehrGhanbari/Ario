"""Ario Cognitive Memory: Episodic-to-Semantic Systems Consolidation Engine.

Implements biological systems consolidation (Complementary Learning Systems)
over Ario's append-only episodic ledgers without violating epistemic invariants:
- Memory != Truth: Consolidated semantic assertions remain auditable claims.
- Claim != Proof: Semantic nodes must cite cryptographic hashes of raw events.
- Revision != Erasure: Raw episodic ledger is strictly immutable.
"""

from __future__ import annotations

import copy
import dataclasses
import functools
import itertools
import hashlib
import json
import threading
import math
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


class ConsolidationError(ValueError):
    """Raised when consolidation violates an epistemic or schema invariant."""
    pass


class NodeEpistemicStatus(str, Enum):
    RECORDED = "RECORDED"      # Structurally ingested; no evidence or truth implied (Issue #216)
    ACCEPTED = "ACCEPTED"      # Legacy operational status
    SUPPORTED = "SUPPORTED"    # Verified by authorized witness or empirical tool
    CONTESTED = "CONTESTED"    # Contradicted by conflicting evidence
    UNSUPPORTED = "UNSUPPORTED"# Falsified or explicitly refuted
    REVISED = "REVISED"        # Superseded by newer verified assessment


@dataclasses.dataclass(frozen=True)
class SemanticNode:
    node_id: str
    concept: str
    assertion: str
    status: NodeEpistemicStatus
    source_event_hashes: Tuple[str, ...]
    saliency_score: float
    created_at: str
    last_reinforced_at: str
    reinforcement_count: int
    falsification_condition: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.node_id or not self.node_id.strip():
            raise ConsolidationError("node_id must be non-empty")
        if not self.concept or not self.concept.strip():
            raise ConsolidationError("concept must be non-empty")
        if not self.assertion or not self.assertion.strip():
            raise ConsolidationError("assertion must be non-empty")
        if not self.source_event_hashes:
            raise ConsolidationError("T-CONS-01: source_event_hashes must contain at least one source event hash")
        for h in self.source_event_hashes:
            if not isinstance(h, str) or len(h) != 64 or not all(c in "0123456789abcdef" for c in h.lower()):
                raise ConsolidationError(f"T-CONS-01: invalid sha256 hash in source_event_hashes: {h}")
        if not (0.0 <= self.saliency_score <= 1.0):
            raise ConsolidationError("saliency_score must be between 0.0 and 1.0")
        if self.reinforcement_count < 1:
            raise ConsolidationError("reinforcement_count must be at least 1")


@dataclasses.dataclass(frozen=True)
class CausalLink:
    from_node_id: str
    to_node_id: str
    relation: str
    weight: float
    evidence_hashes: Tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.from_node_id or not self.to_node_id:
            raise ConsolidationError("from_node_id and to_node_id must be non-empty")
        if not (0.0 <= self.weight <= 1.0):
            raise ConsolidationError("weight must be between 0.0 and 1.0")



@dataclasses.dataclass(frozen=True)
class MemoryConflict:
    """Epistemic conflict record under a shared concept schema."""
    concept: str
    node_ids: Tuple[str, ...]
    assertions: Tuple[str, ...]
    source_event_hashes: Tuple[str, ...]
    saliency_scores: Tuple[float, ...]
    status: NodeEpistemicStatus
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept": self.concept,
            "node_ids": list(self.node_ids),
            "assertions": list(self.assertions),
            "source_event_hashes": list(self.source_event_hashes),
            "saliency_scores": list(self.saliency_scores),
            "status": self.status.value,
            "summary": self.summary,
        }


@dataclasses.dataclass(frozen=True)
class ContestationReport:
    """Structured audit report of epistemic disagreements and contested memories."""
    generated_at: str
    total_nodes: int
    contested_nodes_count: int
    accepted_nodes_count: int
    contested_concepts: Tuple[str, ...]
    conflicts: Tuple[MemoryConflict, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_nodes": self.total_nodes,
            "contested_nodes_count": self.contested_nodes_count,
            "accepted_nodes_count": self.accepted_nodes_count,
            "contested_concepts": list(self.contested_concepts),
            "conflicts": [c.to_dict() for c in self.conflicts],
        }

    def to_markdown(self) -> str:
        lines = [
            "# Ario Cognitive Memory: Contestation & Conflict Audit Report",
            f"- **Generated At:** {self.generated_at}",
            f"- **Total Semantic Nodes:** {self.total_nodes}",
            f"- **Contested Nodes:** {self.contested_nodes_count}",
            f"- **Accepted Nodes:** {self.accepted_nodes_count}",
            "",
            "## Contested Memory Concepts",
        ]
        if not self.conflicts:
            lines.append("_No contested memories or epistemic conflicts detected in semantic graph._")
            return "\n".join(lines)

        for i, c in enumerate(self.conflicts, start=1):
            lines.append(f"### {i}. Concept: `{c.concept}`")
            lines.append(f"- **Summary:** {c.summary}")
            lines.append(f"- **Status:** `{c.status.value}`")
            lines.append("- **Conflicting Assertions:**")
            for nid, assertion, score in zip(c.node_ids, c.assertions, c.saliency_scores):
                lines.append(f"  - Node `{nid}` (saliency: {score:.2f}): \"{assertion}\"")
            lines.append("- **Source Lineage Hashes (Audit Trail):**")
            for h in c.source_event_hashes:
                lines.append(f"  - `{h}`")
            lines.append("")
        return "\n".join(lines)


@dataclasses.dataclass(frozen=True)
class LedgerIntegrityReport:
    """Read-only diagnostic audit of episodic ledger file integrity for crash recovery."""
    ledger_path: str
    total_bytes: int
    valid_lines: int
    is_clean: bool
    corrupt_line_no: Optional[int] = None
    corrupt_line_snippet: Optional[str] = None
    diagnostic: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ledger_path": self.ledger_path,
            "total_bytes": self.total_bytes,
            "valid_lines": self.valid_lines,
            "is_clean": self.is_clean,
            "corrupt_line_no": self.corrupt_line_no,
            "corrupt_line_snippet": self.corrupt_line_snippet,
            "diagnostic": self.diagnostic,
        }


def _synchronized_memory(method):
    """Readers and ancillary mutators see only completed batches.

    This is an in-process RLock, not durable storage or multi-process isolation.
    """
    @functools.wraps(method)
    def guarded(self, *args, **kwargs):
        with self._batch_lock:
            return method(self, *args, **kwargs)
    return guarded


class ConsolidationEngine:
    """Bounded, fail-closed systems consolidation engine for Ario."""

    @staticmethod
    def inspect_ledger_integrity(ledger_path: Path) -> LedgerIntegrityReport:
        """Read-only diagnostic inspection of ledger file for crash analysis without mutations."""
        ledger_path = Path(ledger_path)
        if not ledger_path.exists():
            return LedgerIntegrityReport(
                ledger_path=str(ledger_path),
                total_bytes=0,
                valid_lines=0,
                is_clean=False,
                diagnostic="FILE_NOT_FOUND",
            )
        total_bytes = ledger_path.stat().st_size
        if total_bytes == 0:
            return LedgerIntegrityReport(
                ledger_path=str(ledger_path),
                total_bytes=0,
                valid_lines=0,
                is_clean=True,
                diagnostic="EMPTY_LEDGER",
            )
        valid_lines = 0
        with open(ledger_path, "rb") as f:
            for line_no, raw_line in enumerate(f, start=1):
                clean = raw_line.strip()
                if not clean:
                    continue
                try:
                    decoded = clean.decode("utf-8")
                    json.loads(decoded)
                    valid_lines += 1
                except Exception as exc:
                    snippet = clean[:80].decode("utf-8", errors="replace")
                    return LedgerIntegrityReport(
                        ledger_path=str(ledger_path),
                        total_bytes=total_bytes,
                        valid_lines=valid_lines,
                        is_clean=False,
                        corrupt_line_no=line_no,
                        corrupt_line_snippet=snippet,
                        diagnostic=f"CORRUPT_JSON_OR_TRUNCATED_TAIL: {exc}",
                    )
        return LedgerIntegrityReport(
            ledger_path=str(ledger_path),
            total_bytes=total_bytes,
            valid_lines=valid_lines,
            is_clean=True,
            diagnostic="CLEAN",
        )


    def __init__(
        self,
        decay_rate: float = 0.05,
        retrieval_threshold: float = 0.2,
        node_id_version: str = "v1",
        default_status: NodeEpistemicStatus = NodeEpistemicStatus.RECORDED,
    ) -> None:
        if not (0.0 < decay_rate < 1.0):
            raise ConsolidationError("decay_rate must be between 0.0 and 1.0")
        if not (0.0 <= retrieval_threshold <= 1.0):
            raise ConsolidationError("retrieval_threshold must be between 0.0 and 1.0")
        if node_id_version not in ("v1", "v2"):
            raise ConsolidationError(f"node_id_version must be 'v1' or 'v2': {node_id_version}")
        self.decay_rate = decay_rate
        self.retrieval_threshold = retrieval_threshold
        self.node_id_version = node_id_version
        self.default_status = default_status
        self._nodes: Dict[str, SemanticNode] = {}
        self._legacy_aliases: Dict[str, str] = {}
        self._links: List[CausalLink] = []
        self._ledger_hashes: Set[str] = set()
        # Tracks exact processed event bytes for replay/hash-collision detection.
        self._event_payload_digests: Dict[str, str] = {}
        # A second WM recording with different attention is the SAME source,
        # but cannot replace a different claim or independently corroborate it.
        self._event_stable_digests: Dict[str, str] = {}
        # Snapshot/restore below is only safe if batches do not interleave.
        self._batch_lock = threading.RLock()
        self._batch_running = False  # Reject same-thread reentrant ingestion.

    @staticmethod
    def compute_node_id(concept: str, assertion: str, version: str = "v1") -> str:
        """Compute canonical node identifier.
        
        v1: sha256((concept + ':' + assertion).encode('utf-8'))[:16] (legacy delimiter collision)
        v2: 'SEM-v2-' + sha256(json.dumps([concept, assertion], separators=(',', ':'), sort_keys=True).encode('utf-8'))[:16]
        """
        if version == "v2":
            payload = json.dumps([concept, assertion], separators=(",", ":"), sort_keys=True)
            return f"SEM-v2-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:16]}"
        return f"SEM-{hashlib.sha256((concept + ':' + assertion).encode('utf-8')).hexdigest()[:16]}"

    @_synchronized_memory
    def resolve_node_id(self, identifier: str) -> Optional[str]:
        """Resolve node identifier via exact match or legacy dual-resolver alias."""
        if identifier in self._nodes:
            return identifier
        return self._legacy_aliases.get(identifier)

    @_synchronized_memory
    def get_node(self, identifier: str) -> Optional[SemanticNode]:
        """Retrieve node by exact ID or dual-resolver alias."""
        resolved = self.resolve_node_id(identifier)
        if resolved and resolved in self._nodes:
            return self._nodes[resolved]
        return None

    @property
    @_synchronized_memory
    def nodes(self) -> Dict[str, SemanticNode]:
        return dict(self._nodes)

    @property
    @_synchronized_memory
    def links(self) -> List[CausalLink]:
        return list(self._links)

    @property
    @_synchronized_memory
    def known_ledger_hashes(self) -> Set[str]:
        return set(self._ledger_hashes)

    def ingest_ledger_file(self, ledger_path: Path) -> int:
        """Ingest raw ledger JSONL without modifying or truncating the file."""
        if not ledger_path.exists():
            raise ConsolidationError(f"ledger path does not exist: {ledger_path}")

        initial_size = ledger_path.stat().st_size
        events = []
        with open(ledger_path, "rb") as f:
            for line_no, raw_line in enumerate(f, start=1):
                clean_line = raw_line.strip()
                if not clean_line:
                    continue
                # Match the stream limit during *file reading*, not after
                # allocating an unbounded ledger-sized event list.
                if len(events) >= 4096:
                    raise ConsolidationError("HOLD_BATCH_TOO_LARGE")
                line_hash = hashlib.sha256(clean_line).hexdigest()
                try:
                    event = json.loads(clean_line.decode("utf-8"))
                except Exception as exc:
                    raise ConsolidationError(f"corrupt ledger JSON on line {line_no}") from exc
                events.append((line_hash, event))

        # Invariant T-CONS-02 check: Verify file was not mutated or truncated during read
        after_size = ledger_path.stat().st_size
        if after_size < initial_size:
            raise ConsolidationError("T-CONS-02: Non-Erasure violation: ledger size decreased during ingestion")

        # File ingestion must use the same replay/hash-collision guard as
        # live event ingestion. A second read is not a new independent source.
        return self.ingest_event_stream(events)

    def ingest_event_stream(self, events: Iterable[Tuple[str, Dict[str, Any]]]) -> int:
        """In-memory all-or-nothing batch; not a durable filesystem transaction.

        Preserve the previous graph, hashes and lineage if a later item is
        malformed, a claimed hash is reused with different data, or one
        consolidation step fails. A failure must not silently admit a prefix.
        """
        # Materialize caller-supplied iterables *before* taking the lock: a
        # caller generator must neither observe an uncommitted prefix nor
        # hold the lock (and every reader) while it stalls.
        local = self._thread_state()
        if getattr(local, "materializing", False):
            raise ConsolidationError("HOLD_REENTRANT_EVENT_BATCH")
        local.materializing = True
        try:
            # Fail closed on unbounded generators rather than exhausting memory.
            events = list(itertools.islice(events, 4097))
            if len(events) > 4096:
                raise ConsolidationError("HOLD_BATCH_TOO_LARGE")
        finally:
            local.materializing = False
        with self._batch_lock:
            if self._batch_running:
                raise ConsolidationError("HOLD_REENTRANT_EVENT_BATCH")
            self._batch_running = True
            try:
                return self._ingest_event_stream_locked(events)
            finally:
                self._batch_running = False

    def _thread_state(self) -> threading.local:
        local = self.__dict__.get("_local")
        if local is None:
            local = self.__dict__.setdefault("_local", threading.local())
        return local

    def __getstate__(self) -> Dict[str, Any]:
        # Snapshot under the lock; a lock object is process-local, not state.
        with self._batch_lock:
            # Freeze the entire snapshot *under* the lock. A shallow state
            # would still change if decay altered shared node indexes later.
            state = {key: value for key, value in self.__dict__.items()
                     if key not in ("_batch_lock", "_local")}
            state["_batch_running"] = False
            return copy.deepcopy(state)

    def __setstate__(self, state: Dict[str, Any]) -> None:
        self.__dict__.update(state)
        self._batch_lock = threading.RLock()

    def _ingest_event_stream_locked(self, events: Iterable[Tuple[str, Dict[str, Any]]]) -> int:
        previous = (
            self._nodes,
            self._legacy_aliases,
            self._links,
            self._ledger_hashes,
            self._event_payload_digests,
            self._event_stable_digests,
        )
        # SemanticNode and CausalLink values are frozen; copy mutable indexes.
        self._nodes = self._nodes.copy()
        self._legacy_aliases = self._legacy_aliases.copy()
        self._links = self._links.copy()
        self._ledger_hashes = self._ledger_hashes.copy()
        self._event_payload_digests = self._event_payload_digests.copy()
        self._event_stable_digests = self._event_stable_digests.copy()
        count = 0
        try:
            for h, ev in events:
                if not isinstance(h, str) or len(h) != 64 or any(c not in "0123456789abcdef" for c in h.lower()):
                    raise ConsolidationError(f"invalid event sha256 hash: {h}")
                h = h.lower()  # one event identity regardless of hex case
                if not isinstance(ev, dict):
                    raise ConsolidationError("HOLD_EVENT_MUST_BE_JSON_OBJECT")
                try:
                    encoded = json.dumps(ev, sort_keys=True, allow_nan=False).encode("utf-8")
                except (TypeError, ValueError, OverflowError) as exc:
                    raise ConsolidationError("HOLD_EVENT_NOT_JSON_SERIALIZABLE") from exc
                digest = hashlib.sha256(encoded).hexdigest()
                # Only WM's structural record can vary in *attentional score*
                # without becoming a new evidence identity. All other fields
                # remain strictly bound to the event hash.
                stable = digest
                if (
                    ev.get("promoted_from_working_memory") is True
                    and ev.get("status") == NodeEpistemicStatus.RECORDED.value
                    and all(key in ev for key in (
                        "concept", "assertion", "attribution_id", "source_type",
                        "veracity_state", "timestamp", "saliency_score"
                    ))
                ):
                    stable_record = dict(ev)
                    stable_record.pop("saliency_score")
                    stable_bytes = json.dumps(
                        stable_record, sort_keys=True, allow_nan=False
                    ).encode("utf-8")
                    stable = hashlib.sha256(stable_bytes).hexdigest()
                if h in self._event_payload_digests:
                    if (
                        self._event_payload_digests[h] != digest
                        and self._event_stable_digests.get(h) != stable
                    ):
                        raise ConsolidationError("HOLD_REUSED_HASH_DIFFERENT_EVENT_PAYLOAD")
                    continue  # Identical event, or WM attention-only replay.
                self._process_raw_event(h, ev)
                self._event_payload_digests[h] = digest
                self._event_stable_digests[h] = stable
                self._ledger_hashes.add(h)
                count += 1
        except Exception:
            (self._nodes, self._legacy_aliases, self._links,
             self._ledger_hashes, self._event_payload_digests,
             self._event_stable_digests) = previous
            raise
        return count

    def _process_raw_event(self, event_hash: str, event: Dict[str, Any]) -> None:
        """Consolidate an individual episodic event into semantic schemas."""
        concept = str(event.get("concept", event.get("task_id", event.get("tool", "general")))).strip()
        assertion = str(event.get("assertion", event.get("goal", event.get("action", "")))).strip()
        if not assertion:
            # Nothing to consolidate from an empty event assertion
            return

        node_id = self.compute_node_id(concept, assertion, version=self.node_id_version)
        if self.node_id_version == "v2":
            legacy_id = self.compute_node_id(concept, assertion, version="v1")
            self._legacy_aliases[legacy_id] = node_id

        now_iso = datetime.now(timezone.utc).isoformat()

        # Check for contradiction with existing nodes (Invariant T-CONS-03)
        claimed_value = event.get("value")
        # Caller-supplied status cannot assert proof or choose ACCEPTED/SUPPORTED.
        # Conservative CONTESTED/UNSUPPORTED are diagnostic, not truth claims.
        supplied = event.get("status")
        if supplied == NodeEpistemicStatus.CONTESTED.value:
            status = NodeEpistemicStatus.CONTESTED
        elif supplied == NodeEpistemicStatus.UNSUPPORTED.value:
            status = NodeEpistemicStatus.UNSUPPORTED
        else:
            status = NodeEpistemicStatus.RECORDED
        for existing in self._nodes.values():
            if existing.concept == concept and existing.node_id != node_id:
                # Contradiction detection: opposing assertions or opposite values under same concept
                if event.get("negates") == existing.node_id or (
                    claimed_value is not None and event.get("value") != existing.assertion and "opposite" in str(event.get("relation", "")).lower()
                ):
                    status = NodeEpistemicStatus.CONTESTED
                    # Mark existing node as contested as well
                    updated_existing = dataclasses.replace(existing, status=NodeEpistemicStatus.CONTESTED)
                    self._nodes[existing.node_id] = updated_existing

        if node_id in self._nodes:
            prev = self._nodes[node_id]
            # Reinforce existing schema
            new_hashes = tuple(sorted(set(prev.source_event_hashes + (event_hash,))))
            # A second publisher-controlled event/ID is not proof of an
            # independent source. Preserve its event hash for auditing, but
            # do not let unverified repetition increase support or salience.
            self._nodes[node_id] = dataclasses.replace(
                prev,
                source_event_hashes=new_hashes,
                status=status if status == NodeEpistemicStatus.CONTESTED else prev.status,
            )
        else:
            self._nodes[node_id] = SemanticNode(
                node_id=node_id,
                concept=concept,
                assertion=assertion,
                status=status,
                source_event_hashes=(event_hash,),
                saliency_score=0.7,  # initial operational salience
                created_at=now_iso,
                last_reinforced_at=now_iso,
                reinforcement_count=1,
                falsification_condition=event.get("falsification_condition"),
            )

    @_synchronized_memory
    def apply_saliency_decay(self, cycles: int = 1) -> None:
        """Apply biological forgetting / power-law decay to operational retrieval indices."""
        for node_id, node in list(self._nodes.items()):
            decay_factor = (1.0 - self.decay_rate) ** cycles
            new_score = max(0.0, node.saliency_score * decay_factor)
            self._nodes[node_id] = dataclasses.replace(node, saliency_score=new_score)

    @_synchronized_memory
    def retrieve_active_context(self, concept_cue: Optional[str] = None) -> List[SemanticNode]:
        """Retrieve operational working memory nodes exceeding the retrieval threshold."""
        results = []
        for node in self._nodes.values():
            if node.saliency_score >= self.retrieval_threshold:
                if concept_cue is None or concept_cue.lower() in node.concept.lower():
                    results.append(node)
        # Sort by saliency descending
        return sorted(results, key=lambda n: n.saliency_score, reverse=True)

    @_synchronized_memory
    def validate_lineage_integrity(self) -> bool:
        """T-CONS-01: Verify that every consolidated node points only to ingested ledger hashes."""
        for node in self._nodes.values():
            for h in node.source_event_hashes:
                if h not in self._ledger_hashes:
                    raise ConsolidationError(
                        f"T-CONS-01: Dangling lineage reference: hash {h} not found in ingested ledger"
                    )
        return True

    @_synchronized_memory
    def generate_contestation_report(self) -> ContestationReport:
        """Generate a structured audit report of all contested and contradictory semantic nodes."""
        now_iso = datetime.now(timezone.utc).isoformat()
        total_nodes = len(self._nodes)
        accepted_count = sum(1 for n in self._nodes.values() if n.status == NodeEpistemicStatus.ACCEPTED)

        # Group contested nodes by concept
        contested_by_concept: Dict[str, List[SemanticNode]] = {}
        for node in self._nodes.values():
            if node.status == NodeEpistemicStatus.CONTESTED:
                contested_by_concept.setdefault(node.concept, []).append(node)

        conflicts: List[MemoryConflict] = []
        for concept, nodes in sorted(contested_by_concept.items(), key=lambda x: x[0]):
            node_ids = tuple(n.node_id for n in nodes)
            assertions = tuple(n.assertion for n in nodes)
            all_hashes: List[str] = []
            for n in nodes:
                for h in n.source_event_hashes:
                    if h not in all_hashes:
                        all_hashes.append(h)
            saliency_scores = tuple(n.saliency_score for n in nodes)
            summary = f"Contested assertion conflict across {len(nodes)} schema nodes under concept '{concept}'"
            conflicts.append(
                MemoryConflict(
                    concept=concept,
                    node_ids=node_ids,
                    assertions=assertions,
                    source_event_hashes=tuple(all_hashes),
                    saliency_scores=saliency_scores,
                    status=NodeEpistemicStatus.CONTESTED,
                    summary=summary,
                )
            )

        contested_nodes_count = sum(len(nodes) for nodes in contested_by_concept.values())
        contested_concepts = tuple(sorted(contested_by_concept.keys()))

        return ContestationReport(
            generated_at=now_iso,
            total_nodes=total_nodes,
            contested_nodes_count=contested_nodes_count,
            accepted_nodes_count=accepted_count,
            contested_concepts=contested_concepts,
            conflicts=tuple(conflicts),
        )

    def export_contestation_report(self, output_path: Path, format: str = "markdown") -> Path:
        """Export contestation report to file in markdown or JSON format."""
        report = self.generate_contestation_report()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if format.lower() == "json":
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
        elif format.lower() in ("markdown", "md"):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report.to_markdown())
        else:
            raise ConsolidationError(f"Unsupported export format '{format}', must be 'markdown' or 'json'")
        return output_path
