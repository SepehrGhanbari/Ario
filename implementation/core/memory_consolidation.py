"""Ario Cognitive Memory: Episodic-to-Semantic Systems Consolidation Engine.

Implements biological systems consolidation (Complementary Learning Systems)
over Ario's append-only episodic ledgers without violating epistemic invariants:
- Memory != Truth: Consolidated semantic assertions remain auditable claims.
- Claim != Proof: Semantic nodes must cite cryptographic hashes of raw events.
- Revision != Erasure: Raw episodic ledger is strictly immutable.
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


class ConsolidationError(ValueError):
    """Raised when consolidation violates an epistemic or schema invariant."""
    pass


class NodeEpistemicStatus(str, Enum):
    ACCEPTED = "ACCEPTED"
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

        for h, ev in events:
            self._ledger_hashes.add(h)
            self._process_raw_event(h, ev)

        return len(events)

    def ingest_event_stream(self, events: Iterable[Tuple[str, Dict[str, Any]]]) -> int:
        count = 0
        for h, ev in events:
            if not isinstance(h, str) or len(h) != 64:
                raise ConsolidationError(f"invalid event sha256 hash: {h}")
            self._ledger_hashes.add(h)
            self._process_raw_event(h, ev)
            count += 1
        return count

    def _process_raw_event(self, event_hash: str, event: Dict[str, Any]) -> None:
        """Consolidate an individual episodic event into semantic schemas."""
        concept = str(event.get("concept", event.get("task_id", event.get("tool", "general")))).strip()
        assertion = str(event.get("assertion", event.get("goal", event.get("action", "")))).strip()
        if not assertion:
            # Nothing to consolidate from an empty event assertion
            return

        node_id = f"SEM-{hashlib.sha256((concept + ':' + assertion).encode('utf-8')).hexdigest()[:16]}"
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
        """Apply biological forgetting / power-law decay to operational retrieval indices."""
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
