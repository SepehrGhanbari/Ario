"""Ario Unified Cognitive Memory: Working Memory Buffer (Module 4).

Operationalizes the Central Executive and Episodic Buffer (Baddeley & Hitch;
Nelson Cowan 4-chunk capacity model) over Ario's epistemically monitored cognition.

Core Invariants:
1. Bounded Attentional Focus: Working memory capacity is strictly bounded (default K=4 chunks).
2. Epistemic Provenance Required: Every chunk must carry a validated SourceAttribution.
3. Dual Eviction Fate:
   - High-salience / rehearsed chunks undergo consolidation to Long-Term Memory (LTM).
   - Low-salience transient noise undergoes adaptive decay/forgetting without LTM pollution.
4. Metacognitive Calibration: Real-time monitoring of empirical vs hypothetical balance
   and active contradiction detection before downstream action commitment.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import math
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.memory_consolidation import (
    ConsolidationError,
    ConsolidationEngine,
    NodeEpistemicStatus,
    SemanticNode,
)
from core.source_monitoring import (
    SourceAttribution,
    SourceMonitoringGuard,
    SourceType,
    VeracityState,
    SourceMonitoringError,
)


class ChunkState(str, Enum):
    ACTIVE = "ACTIVE"
    CONSOLIDATED_TO_LTM = "CONSOLIDATED_TO_LTM"
    DECAYED_FORGOTTEN = "DECAYED_FORGOTTEN"
    DISPLACED = "DISPLACED"


class MetacognitiveVerdict(str, Enum):
    FOCUSED_SUFFICIENCY = "FOCUSED_SUFFICIENCY"
    PARTIAL_NEEDS_RECALL = "PARTIAL_NEEDS_RECALL"
    CONTRADICTION_DETECTED = "CONTRADICTION_DETECTED"
    UNGROUNDED_HYPOTHESIS = "UNGROUNDED_HYPOTHESIS"


@dataclasses.dataclass
class WorkingMemoryChunk:
    chunk_id: str
    concept: str
    assertion: str
    source_attribution: SourceAttribution
    salience: float
    created_step: int
    last_accessed_step: int
    access_count: int = 1
    state: ChunkState = ChunkState.ACTIVE
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    @classmethod
    def compute_chunk_id(cls, concept: str, assertion: str, attribution_id: str) -> str:
        payload = json.dumps(
            {"concept": concept.strip().lower(), "assertion": assertion.strip(), "attribution_id": attribution_id},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]


@dataclasses.dataclass
class EvictionRecord:
    chunk_id: str
    concept: str
    assertion: str
    final_salience: float
    eviction_step: int
    fate: ChunkState
    reason: str


@dataclasses.dataclass
class MetacognitiveAssessment:
    verdict: MetacognitiveVerdict
    active_chunk_count: int
    empirical_ratio: float
    average_salience: float
    contradiction_count: int
    recommended_action: str
    diagnostics: List[str] = dataclasses.field(default_factory=list)


class WorkingMemoryBuffer:
    """Bounded Working Memory Buffer implementing Cowan's 4-chunk capacity."""

    DEFAULT_CAPACITY: int = 4
    DEFAULT_SALIENCE_DECAY: float = 0.05
    DEFAULT_CONSOLIDATION_THRESHOLD: float = 0.65
    REHEARSAL_SALIENCE_BOOST: float = 0.15

    def __init__(
        self,
        capacity: int = DEFAULT_CAPACITY,
        consolidation_engine: Optional[ConsolidationEngine] = None,
        source_guard: Optional[SourceMonitoringGuard] = None,
        salience_decay_rate: float = DEFAULT_SALIENCE_DECAY,
        consolidation_threshold: float = DEFAULT_CONSOLIDATION_THRESHOLD,
    ) -> None:
        # A fractional, infinite or NaN capacity silently disables the bound.
        if type(capacity) is not int or capacity < 1:
            raise ValueError("Working memory capacity must be a positive integer (at least 1)")
        for label, value in (
            ("salience_decay_rate", salience_decay_rate),
            ("consolidation_threshold", consolidation_threshold),
        ):
            if (
                type(value) not in (float, int)
                or not math.isfinite(value)
                or not (0.0 <= value <= 1.0)
            ):
                raise ValueError(f"{label} must be finite and within [0, 1]")
        self.capacity = capacity
        self.consolidation_engine = consolidation_engine
        self.source_guard = source_guard
        self.salience_decay_rate = salience_decay_rate
        self.consolidation_threshold = consolidation_threshold

        self._active_chunks: Dict[str, WorkingMemoryChunk] = {}
        self._eviction_history: List[EvictionRecord] = []
        # Each source-evidence unit may be structurally consolidated once.
        self._consolidated_chunk_ids: Set[str] = set()
        self._current_step: int = 0
        # Chunks re-entered via LTM recall carry no new evidence.
        self._recalled_chunk_ids: Set[str] = set()

    @staticmethod
    def _validate_step(step: Optional[int]) -> None:
        if step is not None and (type(step) is not int or step < 0):
            raise ValueError("step must be a non-negative integer")

    # Validate runtime configuration changes as well as constructor input.
    # Changing the capacity must never silently evict existing memories.
    @property
    def capacity(self) -> int:
        return self._capacity

    @capacity.setter
    def capacity(self, value: int) -> None:
        if type(value) is not int or value < 1:
            raise ValueError("Working memory capacity must be a positive integer (at least 1)")
        if len(getattr(self, "_active_chunks", {})) > value:
            raise ValueError("capacity cannot shrink below the active chunk count")
        self._capacity = value

    @property
    def salience_decay_rate(self) -> float:
        return self._salience_decay_rate

    @salience_decay_rate.setter
    def salience_decay_rate(self, value: float) -> None:
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("salience_decay_rate must be finite and within [0, 1]")
        self._salience_decay_rate = value

    @property
    def consolidation_threshold(self) -> float:
        return self._consolidation_threshold

    @consolidation_threshold.setter
    def consolidation_threshold(self, value: float) -> None:
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError("consolidation_threshold must be finite and within [0, 1]")
        self._consolidation_threshold = value

    @property
    def active_chunks(self) -> List[WorkingMemoryChunk]:
        """Returns active chunks sorted by salience descending."""
        return [
            copy.deepcopy(chunk) for chunk in sorted(
                self._active_chunks.values(),
                key=lambda c: (c.salience, c.last_accessed_step),
                reverse=True,
            )
        ]

    @property
    def active_count(self) -> int:
        return len(self._active_chunks)

    @property
    def eviction_history(self) -> List[EvictionRecord]:
        # Inspection must never mutate internal audit entries.
        return copy.deepcopy(self._eviction_history)

    def ingest(
        self,
        concept: str,
        assertion: str,
        source_attribution: SourceAttribution,
        salience: float = 0.5,
        step: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkingMemoryChunk:
        """Ingests an observation/assertion into working memory, enforcing bounds and provenance."""
        if not concept or not concept.strip():
            raise ValueError("Concept cannot be empty")
        if not assertion or not assertion.strip():
            raise ValueError("Assertion cannot be empty")
        if not isinstance(source_attribution, SourceAttribution):
            raise SourceMonitoringError("Working memory requires a verified SourceAttribution")

        # Reject nonfinite values before *any* eviction, rehearsal or mutation.
        if type(salience) not in (float, int):
            raise ValueError("salience must be a finite number")
        numeric_salience = float(salience)
        if not math.isfinite(numeric_salience):
            raise ValueError("salience must be a finite number")
        clamped_salience = max(0.0, min(1.0, numeric_salience))

        # Dataclass shape is not provenance. A configured guard must recognize
        # the *exact* attribution and accept it before eviction or rehearsal.
        if self.source_guard is not None:
            canonical = self.source_guard.attributions.get(source_attribution.attribution_id)
            if canonical is None or canonical != source_attribution:
                raise SourceMonitoringError("Source attribution not admitted by configured guard")
            if not self.source_guard.filter_working_memory_candidates(
                [source_attribution.attribution_id]
            ):
                raise SourceMonitoringError("Configured source guard refused attribution")

        self._validate_step(step)
        # Copy caller data before any eviction/rehearsal so failure is atomic.
        metadata_copy = copy.deepcopy(metadata or {})
        attribution_copy = copy.deepcopy(source_attribution)
        effective_step = max(self._current_step, step) if step is not None else self._current_step

        chunk_id = WorkingMemoryChunk.compute_chunk_id(concept, assertion, source_attribution.attribution_id)

        # Re-ingestion / Rehearsal of existing active chunk
        if chunk_id in self._active_chunks:
            # Stage *both* internal and returned snapshots before committing.
            # The second deepcopy may fail for hostile user-controlled objects.
            staged = copy.deepcopy(self._active_chunks[chunk_id])
            staged.access_count += 1
            staged.last_accessed_step = effective_step
            staged.salience = min(1.0, max(staged.salience, clamped_salience) + self.REHEARSAL_SALIENCE_BOOST)
            if metadata_copy:
                staged.metadata.update(metadata_copy)
            returned = copy.deepcopy(staged)
            self._current_step = effective_step
            self._active_chunks[chunk_id] = staged
            return returned

        # Prepare the return value before any capacity eviction or LTM write.
        chunk = WorkingMemoryChunk(
            chunk_id=chunk_id,
            concept=concept.strip(),
            assertion=assertion.strip(),
            source_attribution=attribution_copy,
            salience=clamped_salience,
            created_step=effective_step,
            last_accessed_step=effective_step,
            access_count=1,
            state=ChunkState.ACTIVE,
            metadata=metadata_copy,
        )
        returned = copy.deepcopy(chunk)
        self._current_step = effective_step
        if len(self._active_chunks) >= self.capacity:
            self._evict_least_salient()
        self._active_chunks[chunk_id] = chunk
        return returned

    def access(self, chunk_id: str, step: Optional[int] = None) -> Optional[WorkingMemoryChunk]:
        """Accesses an active chunk, applying attentional rehearsal boost."""
        self._validate_step(step)
        if step is not None:
            self._current_step = max(self._current_step, step)

        if chunk_id not in self._active_chunks:
            return None

        chunk = self._active_chunks[chunk_id]
        chunk.access_count += 1
        chunk.last_accessed_step = self._current_step
        chunk.salience = min(1.0, chunk.salience + self.REHEARSAL_SALIENCE_BOOST)
        return copy.deepcopy(chunk)

    def step_tick(self, step: Optional[int] = None) -> List[EvictionRecord]:
        """Advances time/step, applying salience decay and pruning decayed chunks."""
        self._validate_step(step)
        if step is not None:
            self._current_step = max(self._current_step, step)
        else:
            self._current_step += 1

        evicted: List[EvictionRecord] = []
        to_purge: List[str] = []

        for cid, chunk in self._active_chunks.items():
            if chunk.last_accessed_step < self._current_step:
                chunk.salience = max(0.0, chunk.salience - self.salience_decay_rate)

            if chunk.salience <= 0.0:
                to_purge.append(cid)

        for cid in to_purge:
            chunk = self._active_chunks.pop(cid)
            record = self._handle_chunk_exit(chunk, reason="salience_decay_to_zero")
            evicted.append(record)

        return copy.deepcopy(evicted)

    def recall_from_long_term(self, concept_cue: str) -> List[WorkingMemoryChunk]:
        """Directed recall from Long-Term Memory (ConsolidationEngine) into Working Memory."""
        if not self.consolidation_engine:
            return []

        ltm_nodes = self.consolidation_engine.retrieve_active_context(concept_cue)
        recalled_chunks: List[WorkingMemoryChunk] = []

        for node in ltm_nodes:
            # Remembering an ACCEPTED node is not a new empirical verification.
            # The recall is a hypothesis linked to its historical semantic node.
            if self.source_guard is not None:
                attribution = self.source_guard.create_hypothesis(
                    node.assertion,
                    attribution_id=f"recall_{node.node_id}",
                    parent_attribution_ids=(node.node_id,),
                )
            else:
                attribution = SourceAttribution(
                    attribution_id=f"recall_{node.node_id}",
                    source_type=SourceType.INTERNAL_HYPOTHESIS,
                    assertion=node.assertion,
                    veracity_state=VeracityState.UNVERIFIED_HYPOTHESIS,
                    provenance=None,
                    parent_attribution_ids=(node.node_id,),
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            # Re-ingest into working memory with recall salience
            chunk = self.ingest(
                concept=node.concept,
                assertion=node.assertion,
                source_attribution=attribution,
                salience=node.saliency_score,
                metadata={"recalled_from_ltm": True, "ltm_node_id": node.node_id},
            )
            self._recalled_chunk_ids.add(chunk.chunk_id)
            recalled_chunks.append(chunk)

        return recalled_chunks

    def flush_to_long_term(self, min_salience: float = 0.0) -> List[str]:
        """Explicitly flushes/consolidates qualifying active chunks into Long-Term Memory."""
        if not self.consolidation_engine:
            return []

        consolidated_ids: List[str] = []
        for cid, chunk in list(self._active_chunks.items()):
            if (chunk.salience >= min_salience
                    and cid not in self._consolidated_chunk_ids
                    and cid not in self._recalled_chunk_ids):
                self._promote_to_ltm(chunk)
                chunk.state = ChunkState.CONSOLIDATED_TO_LTM
                consolidated_ids.append(cid)

        return consolidated_ids

    def metacognitive_assessment(self) -> MetacognitiveAssessment:
        """Evaluates epistemic health and readiness of current active working memory."""
        if not self._active_chunks:
            return MetacognitiveAssessment(
                verdict=MetacognitiveVerdict.PARTIAL_NEEDS_RECALL,
                active_chunk_count=0,
                empirical_ratio=0.0,
                average_salience=0.0,
                contradiction_count=0,
                recommended_action="Working memory is empty; initiate perception or LTM recall.",
                diagnostics=["EMPTY_WORKING_MEMORY"],
            )

        chunks = list(self._active_chunks.values())
        total = len(chunks)
        # Only a currently admitted empirical record counts as grounding.
        # Without a configured guard, source claims may remain visible but
        # cannot make a FOCUSED_SUFFICIENCY readiness assertion.
        empirical_count = 0
        if self.source_guard is not None:
            for chunk in chunks:
                attr = chunk.source_attribution
                canonical = self.source_guard.attributions.get(attr.attribution_id)
                if (
                    attr.source_type == SourceType.EMPIRICAL_OBSERVATION
                    and attr.veracity_state == VeracityState.VERIFIED_EMPIRICAL
                    and canonical == attr
                    and self.source_guard.filter_working_memory_candidates(
                        [attr.attribution_id], require_verified=True
                    )
                ):
                    empirical_count += 1
        empirical_ratio = empirical_count / total
        avg_salience = sum(c.salience for c in chunks) / total

        # Check for active contradictions across concepts
        contradiction_pairs: List[Tuple[str, str]] = []
        concept_map: Dict[str, List[WorkingMemoryChunk]] = {}
        for c in chunks:
            concept_map.setdefault(c.concept.strip().lower(), []).append(c)

        for concept, group in concept_map.items():
            if len(group) > 1:
                # Check for direct assertion conflicts
                for i in range(len(group)):
                    for j in range(i + 1, len(group)):
                        a1 = group[i].assertion.strip().lower()
                        a2 = group[j].assertion.strip().lower()
                        if a1 != a2 and (
                            ("not " in a1 and a1.replace("not ", "") in a2)
                            or ("not " in a2 and a2.replace("not ", "") in a1)
                            or ("false" in a1 and "true" in a2)
                            or ("true" in a1 and "false" in a2)
                        ):
                            contradiction_pairs.append((group[i].chunk_id, group[j].chunk_id))

        diagnostics: List[str] = []
        if contradiction_pairs:
            verdict = MetacognitiveVerdict.CONTRADICTION_DETECTED
            recommended = "Halt automated action; resolve active contradictions in working memory."
            diagnostics.append(f"CONTRADICTIONS_DETECTED: {len(contradiction_pairs)} pair(s)")
        elif empirical_ratio >= 0.5 and avg_salience >= 0.4:
            verdict = MetacognitiveVerdict.FOCUSED_SUFFICIENCY
            recommended = "Sufficient grounded empirical focus; proceed with planned task."
            diagnostics.append("HIGH_EMPIRICAL_GROUNDING")
        elif empirical_count == 0:
            verdict = MetacognitiveVerdict.UNGROUNDED_HYPOTHESIS
            recommended = "Active focus lacks empirical grounding; execute verification probe."
            diagnostics.append("NO_EMPIRICAL_PROVENANCE")
        else:
            verdict = MetacognitiveVerdict.PARTIAL_NEEDS_RECALL
            recommended = "Partial grounding; query Long-Term Memory or sensory tools for reinforcement."
            diagnostics.append("LOW_EMPIRICAL_RATIO_OR_SALIENCE")

        return MetacognitiveAssessment(
            verdict=verdict,
            active_chunk_count=total,
            empirical_ratio=round(empirical_ratio, 3),
            average_salience=round(avg_salience, 3),
            contradiction_count=len(contradiction_pairs),
            recommended_action=recommended,
            diagnostics=diagnostics,
        )

    def _evict_least_salient(self) -> EvictionRecord:
        """Picks victim based on lowest salience and least recent access."""
        victim_id = min(
            self._active_chunks.keys(),
            key=lambda cid: (
                self._active_chunks[cid].salience,
                self._active_chunks[cid].last_accessed_step,
                self._active_chunks[cid].access_count,
            ),
        )
        victim = self._active_chunks[victim_id]
        # Failures during long-term consolidation must never silently delete
        # an active chunk before its eviction record can be stored.
        record = self._handle_chunk_exit(victim, reason="capacity_limit_exceeded")
        del self._active_chunks[victim_id]
        return record

    def _handle_chunk_exit(self, chunk: WorkingMemoryChunk, reason: str) -> EvictionRecord:
        """Determines whether evicted chunk is consolidated to LTM or adaptively forgotten."""
        should_consolidate = (
            chunk.salience >= self.consolidation_threshold
            or chunk.access_count >= 2
            or chunk.source_attribution.veracity_state == VeracityState.VERIFIED_EMPIRICAL
        )

        if should_consolidate and self.consolidation_engine is not None:
            self._promote_to_ltm(chunk)
            fate = ChunkState.CONSOLIDATED_TO_LTM
        else:
            fate = ChunkState.DECAYED_FORGOTTEN

        record = EvictionRecord(
            chunk_id=chunk.chunk_id,
            concept=chunk.concept,
            assertion=chunk.assertion,
            final_salience=chunk.salience,
            eviction_step=self._current_step,
            fate=fate,
            reason=reason,
        )
        self._eviction_history.append(record)
        return record

    def _promote_to_ltm(self, chunk: WorkingMemoryChunk) -> None:
        """Synthesizes a structured observation event and submits it to ConsolidationEngine."""
        if not self.consolidation_engine:
            return
        if chunk.chunk_id in self._consolidated_chunk_ids:
            return
        if chunk.chunk_id in self._recalled_chunk_ids:
            # Remembering is not re-observing: never re-submit a recall as a new event.
            return

        event_payload = {
            # Structural recording has no implied proof/support.
            "status": NodeEpistemicStatus.RECORDED.value,
            "concept": chunk.concept,
            "assertion": chunk.assertion,
            "saliency_score": chunk.salience,
            "attribution_id": chunk.source_attribution.attribution_id,
            "source_type": chunk.source_attribution.source_type.value,
            "veracity_state": chunk.source_attribution.veracity_state.value,
            "promoted_from_working_memory": True,
            # A repeated flush must not manufacture a new independent event.
            "timestamp": chunk.source_attribution.created_at,
        }
        # Salience is an attentional score, NOT a new empirical source.
        # Stable identity is independent of rehearsal/decay.
        prov = chunk.source_attribution.provenance
        identity = {
            "concept": chunk.concept,
            "assertion": chunk.assertion,
            "attribution_id": chunk.source_attribution.attribution_id,
            "source_type": chunk.source_attribution.source_type.value,
            "veracity_state": chunk.source_attribution.veracity_state.value,
            "source_created_at": chunk.source_attribution.created_at,
            "provenance": None if prov is None else {
                "tool": prov.tool,
                "target": prov.target,
                "exit_code": prov.exit_code,
                "execution_lock_sha256": prov.execution_lock_sha256,
                "stdout_sha256": prov.stdout_sha256,
                "recorded_at": prov.recorded_at,
            },
        }
        event_hash = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        # A new WM instance must not manufacture an independent source when
        # the receiving engine has already seen this evidence identity.
        # Always submit; the engine checks replay content atomically. A known
        # hash by itself is not proof of the same source and cannot mask a
        # conflicting publisher event or a failed transaction.
        self.consolidation_engine.ingest_event_stream([(event_hash, event_payload)])
        self._consolidated_chunk_ids.add(chunk.chunk_id)
