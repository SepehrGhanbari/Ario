"""Ario Cognitive Memory: Episodic-to-Semantic Systems Consolidation Engine.

Implements a bounded episodic-to-assertion index inspired by CLS;
it does NOT simulate biological consolidation or authenticate sources.
- Memory != Truth: an ingested assertion is not a verified fact.
- Claim != Proof: local byte hashes and caller-declared digests do not
  establish external authenticity or independent evidence.
- Revision != Erasure: ingestion does not edit input-ledger bytes.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


# Candidate-only budgets, aligned with the existing ledger observation adapter's
# nominal event/line limits. They are NOT approved production thresholds.
MAX_MEMORY_BATCH_EVENTS = 5000
MAX_MEMORY_STORED_HASHES = 5000
MAX_MEMORY_EVENT_BYTES = 64 * 1024
MAX_MEMORY_BATCH_BYTES = 8 * 1024 * 1024
RECORD_DIGEST_SCHEME = "raw_line_sha256_v0_2"
LEGACY_RECORD_DIGEST_SCHEME = "legacy_trimmed_sha256_v0_1"


class ConsolidationError(ValueError):
    """Raised when consolidation violates an epistemic or schema invariant."""
    pass


def _reject_duplicate_object_keys(pairs):
    """Preserve audit interpretability by rejecting ambiguous JSON object keys."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ConsolidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


class NodeEpistemicStatus(str, Enum):
    ACCEPTED = "ACCEPTED"  # LEGACY: structural ingestion ONLY, not truth
    CONTESTED = "CONTESTED"
    UNSUPPORTED = "UNSUPPORTED"
    REVISED = "REVISED"


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
        if not isinstance(self.source_event_hashes, tuple):
            raise ConsolidationError("T-CONS-01: source_event_hashes must be an immutable tuple")
        if not self.source_event_hashes:
            raise ConsolidationError("T-CONS-01: source_event_hashes must contain at least one source event hash")
        for h in self.source_event_hashes:
            if not isinstance(h, str) or len(h) != 64 or not all(c in "0123456789abcdef" for c in h.lower()):
                raise ConsolidationError(f"T-CONS-01: invalid sha256 hash in source_event_hashes: {h}")
        if not (0.0 <= self.saliency_score <= 1.0):
            raise ConsolidationError("saliency_score must be between 0.0 and 1.0")
        if self.reinforcement_count < 1:
            raise ConsolidationError("reinforcement_count must be at least 1")
        if self.falsification_condition is not None and not isinstance(self.falsification_condition, str):
            raise ConsolidationError("falsification_condition must be a string or None")


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


class ConsolidationEngine:
    """Bounded, fail-closed systems consolidation engine for Ario."""

    def __init__(self, decay_rate: float = 0.05, retrieval_threshold: float = 0.2) -> None:
        if not (0.0 < decay_rate < 1.0):
            raise ConsolidationError("decay_rate must be between 0.0 and 1.0")
        if not (0.0 <= retrieval_threshold <= 1.0):
            raise ConsolidationError("retrieval_threshold must be between 0.0 and 1.0")
        self.decay_rate = decay_rate
        self.retrieval_threshold = retrieval_threshold
        self._nodes: Dict[str, SemanticNode] = {}
        self._links: List[CausalLink] = []
        self._ledger_hashes: Set[str] = set()
        self._declared_hash_payloads: Dict[str, str] = {}

    @property
    def nodes(self) -> Dict[str, SemanticNode]:
        return dict(self._nodes)

    @property
    def links(self) -> List[CausalLink]:
        return list(self._links)

    @property
    def known_ledger_hashes(self) -> Set[str]:
        return set(self._ledger_hashes)

    def ingest_ledger_file(self, ledger_path: Path) -> int:
        """Read one bounded byte snapshot; never write to the input ledger.

        SHA-256 binds exact raw line bytes, not source authenticity or custody.
        A second local read detects some concurrent edits, not future tampering.
        """
        if not ledger_path.exists():
            raise ConsolidationError(f"ledger path does not exist: {ledger_path}")
        try:
            max_ledger_bytes = 16 * 1024 * 1024
            with ledger_path.open("rb") as stream:
                snapshot = stream.read(max_ledger_bytes + 1)
            if len(snapshot) > max_ledger_bytes:
                raise ConsolidationError("ledger exceeds 16 MiB bounded snapshot limit")
            # Completed JSONL records must end in LF (CRLF is allowed).
            # The independent ledger_observation_adapter also requires LF.
            if snapshot and not snapshot.endswith(b"\n"):
                raise ConsolidationError("incomplete JSONL line: missing final LF")
            events = []
            for line_no, raw_line in enumerate(snapshot.splitlines(keepends=True), start=1):
                if not raw_line.strip():
                    raise ConsolidationError(f"invalid blank JSONL record on line {line_no}")
                h = hashlib.sha256(raw_line).hexdigest()
                try:
                    event = json.loads(raw_line.decode("utf-8"), object_pairs_hook=_reject_duplicate_object_keys)
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ConsolidationError(f"corrupt ledger JSON on line {line_no}") from exc
                if not isinstance(event, dict):
                    raise ConsolidationError(f"invalid ledger event type on line {line_no}")
                events.append((h, event))
            with ledger_path.open("rb") as stream:
                compared = stream.read(max_ledger_bytes + 1)
            if compared != snapshot:
                raise ConsolidationError("T-CONS-02: ledger changed during ingestion")
        except OSError as exc:
            raise ConsolidationError("ledger could not be read consistently") from exc
        return self.ingest_event_stream(events)

    def ingest_event_stream(self, events: Iterable[Tuple[str, Dict[str, Any]]]) -> int:
        """Atomically ingest caller-declared digest/event pairs with budgets.

        Per-call event/serialized-byte limits and a lifetime stored-hash cap
        are candidate limits, NOT proof of bounded CPU or process memory.
        Streamed digests are NOT independently authenticated or byte verified.
        """
        old_nodes = self._nodes.copy()
        old_links = self._links.copy()
        old_hashes = self._ledger_hashes.copy()
        old_payloads = self._declared_hash_payloads.copy()
        count = 0
        total_event_bytes = 0
        try:
            for item in events:
                if count >= MAX_MEMORY_BATCH_EVENTS:
                    raise ConsolidationError("memory stream event-count limit exceeded")
                if not isinstance(item, (list, tuple)) or len(item) != 2:
                    raise ConsolidationError("event item must be (hash, event) pair")
                h, ev = item
                if not isinstance(h, str) or len(h) != 64 or any(ch not in "0123456789abcdef" for ch in h.lower()):
                    raise ConsolidationError(f"invalid event sha256 hash: {h}")
                if not isinstance(ev, dict):
                    raise ConsolidationError("event payload must be a JSON object")
                h = h.lower()  # uppercase/lowercase hex encode the SAME digest
                canonical = json.dumps(ev, sort_keys=True, ensure_ascii=False,
                                       separators=(",", ":"), allow_nan=False)
                encoded = canonical.encode("utf-8")
                if len(encoded) > MAX_MEMORY_EVENT_BYTES:
                    raise ConsolidationError("memory event serialized-size limit exceeded")
                total_event_bytes += len(encoded)
                if total_event_bytes > MAX_MEMORY_BATCH_BYTES:
                    raise ConsolidationError("memory batch serialized-size limit exceeded")
                if h not in self._ledger_hashes and len(self._ledger_hashes) >= MAX_MEMORY_STORED_HASHES:
                    raise ConsolidationError("memory retained-event limit exceeded")
                fingerprint = hashlib.sha256(encoded).hexdigest()
                if h in self._declared_hash_payloads and self._declared_hash_payloads[h] != fingerprint:
                    raise ConsolidationError("declared hash is reused for a different payload")
                self._declared_hash_payloads[h] = fingerprint
                self._ledger_hashes.add(h)
                self._process_raw_event(h, ev)
                count += 1
        except Exception as exc:
            self._nodes = old_nodes
            self._links = old_links
            self._ledger_hashes = old_hashes
            self._declared_hash_payloads = old_payloads
            if isinstance(exc, ConsolidationError):
                raise
            raise ConsolidationError("batch ingestion aborted without committing partial state") from exc
        return count

    def _process_raw_event(self, event_hash: str, event: Dict[str, Any]) -> None:
        """Consolidate an individual episodic event into semantic schemas."""
        concept = str(event.get("concept", event.get("task_id", event.get("tool", "general")))).strip()
        assertion = str(event.get("assertion", event.get("goal", event.get("action", "")))).strip()
        if not assertion:
            # Nothing to consolidate from an empty event assertion
            return

        # Legacy IDs are deliberately preserved; collision/migration is HOLD #216.
        node_id = f"SEM-{hashlib.sha256((concept + ':' + assertion).encode('utf-8')).hexdigest()[:16]}"
        if node_id in self._nodes and event_hash in self._nodes[node_id].source_event_hashes:
            return  # repeated event is not new evidence or reinforcement
        now_iso = datetime.now(timezone.utc).isoformat()

        # Check for contradiction with existing nodes (Invariant T-CONS-03)
        claimed_value = event.get("value")
        status = NodeEpistemicStatus.ACCEPTED
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
            # Saliency reinforcement: bounded power-law boost
            new_saliency = min(1.0, prev.saliency_score + (1.0 - prev.saliency_score) * 0.3)
            self._nodes[node_id] = dataclasses.replace(
                prev,
                source_event_hashes=new_hashes,
                saliency_score=new_saliency,
                last_reinforced_at=now_iso,
                reinforcement_count=prev.reinforcement_count + 1,
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

    def apply_saliency_decay(self, cycles: int = 1) -> None:
        """Apply exponential *operational salience* decay, not biological forgetting."""
        if type(cycles) is not int or cycles < 0:
            raise ConsolidationError("decay cycles must be a non-negative integer")
        for node_id, node in list(self._nodes.items()):
            decay_factor = (1.0 - self.decay_rate) ** cycles
            new_score = max(0.0, node.saliency_score * decay_factor)
            self._nodes[node_id] = dataclasses.replace(node, saliency_score=new_score)

    def retrieve_active_context(self, concept_cue: Optional[str] = None) -> List[SemanticNode]:
        """Retrieve operational working memory nodes exceeding the retrieval threshold."""
        results = []
        for node in self._nodes.values():
            if node.saliency_score >= self.retrieval_threshold:
                if concept_cue is None or concept_cue.lower() in node.concept.lower():
                    results.append(node)
        # Sort by saliency descending
        return sorted(results, key=lambda n: n.saliency_score, reverse=True)

    def validate_lineage_integrity(self) -> bool:
        """T-CONS-01: Verify that every consolidated node points only to ingested ledger hashes."""
        for node in self._nodes.values():
            for h in node.source_event_hashes:
                if h not in self._ledger_hashes:
                    raise ConsolidationError(
                        f"T-CONS-01: Dangling lineage reference: hash {h} not found in ingested ledger"
                    )
        return True
