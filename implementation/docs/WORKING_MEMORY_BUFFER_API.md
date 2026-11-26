# Working Memory Buffer (Module 4) — API Specification & Interface Guide

## 1. Overview & Cognitive Neuroscience Foundations
The `WorkingMemoryBuffer` module (`core/working_memory.py`) operationalizes the **Central Executive** and **Episodic Buffer** within Ario's epistemically monitored autonomous cognitive architecture.

Standard LLM and agent frameworks suffer from context window pollution, where outdated, hypothetical, or circular assertions accumulate indefinitely, causing degradation of task performance and self-referential hallucinations.

In human cognition (Baddeley & Hitch, 1974; Nelson Cowan, 2001; Tulving, 1985; Johnson's Source Monitoring Framework, 1993):
1. **Bounded Attentional Capacity:** Working memory focus is strictly bounded to $K \approx 4$ active chunks of information.
2. **Dynamic Salience & Temporal Decay:** Unattended items decay in activation; frequently rehearsed or emotionally/task-salient items persist.
3. **Dual Eviction Fate:** When new information arrives into a saturated buffer, high-salience items and verified empirical facts undergo consolidation to Long-Term Memory (LTM), while low-salience noise undergoes adaptive forgetting without polluting LTM.
4. **Metacognitive Monitoring:** Real-time metacognitive self-assessment evaluates empirical vs. hypothetical grounding and flags conflicting beliefs before taking physical action.

---

## 2. Data Contracts & Enums

### `ChunkState`
State of a chunk across its operational lifecycle:
- `ACTIVE`: Currently present within the active attention buffer ($\le K$).
- `CONSOLIDATED_TO_LTM`: Displaced from working memory but preserved into semantic LTM due to high salience, rehearsal, or empirical provenance.
- `DECAYED_FORGOTTEN`: Pruned and discarded due to salience decay or low utility, preserving epistemic hygiene.
- `DISPLACED`: Transient state during buffer reallocation.

### `MetacognitiveVerdict`
Readiness evaluation returned by `metacognitive_assessment()`:
- `FOCUSED_SUFFICIENCY`: High empirical grounding and sufficient salience; safe to proceed with downstream planning/execution.
- `PARTIAL_NEEDS_RECALL`: Weak empirical grounding or low average salience; recommends sensory probe or directed LTM recall.
- `CONTRADICTION_DETECTED`: Opposing or mutually exclusive assertions exist within co-residing concepts in the active buffer; automated action must halt.
- `UNGROUNDED_HYPOTHESIS`: Active focus is dominated by unverified internal hypotheses without external empirical receipts.

### `WorkingMemoryChunk`
Dataclass representing an active attentional unit:
```python
@dataclasses.dataclass
class WorkingMemoryChunk:
    chunk_id: str                          # Deterministic 16-char hex hash
    concept: str                           # Conceptual topic / anchor
    assertion: str                         # Concrete proposition
    source_attribution: SourceAttribution  # Verified epistemic provenance
    salience: float                        # Attentional weight in [0.0, 1.0]
    created_step: int                      # Tick step when first ingested
    last_accessed_step: int                # Tick step of most recent rehearsal/access
    access_count: int                      # Rehearsal frequency counter
    state: ChunkState                      # Lifecycle status
    metadata: Dict[str, Any]               # Optional contextual metadata
```

### `EvictionRecord`
Audit record logged when a chunk leaves the active buffer:
```python
@dataclasses.dataclass
class EvictionRecord:
    chunk_id: str
    concept: str
    assertion: str
    final_salience: float
    eviction_step: int
    fate: ChunkState                       # CONSOLIDATED_TO_LTM vs DECAYED_FORGOTTEN
    reason: str
```

### `MetacognitiveAssessment`
Output of real-time epistemic self-monitoring:
```python
@dataclasses.dataclass
class MetacognitiveAssessment:
    verdict: MetacognitiveVerdict
    active_chunk_count: int
    empirical_ratio: float                 # Ratio of VERIFIED_EMPIRICAL chunks
    average_salience: float                # Mean attentional weight
    contradiction_count: int               # Count of detected conflicting pairs
    recommended_action: str                # Actionable directive for agent loop
    diagnostics: List[str]                 # Diagnostic strings and telemetry
```

---

## 3. Class `WorkingMemoryBuffer` Interface

### Constructor
```python
WorkingMemoryBuffer(
    capacity: int = 4,
    consolidation_engine: Optional[ConsolidationEngine] = None,
    source_guard: Optional[SourceMonitoringGuard] = None,
    salience_decay_rate: float = 0.05,
    consolidation_threshold: float = 0.65,
)
```
- `capacity`: Maximum simultaneous chunks ($K \ge 1$, default $4$).
- `consolidation_engine`: Optional LTM instance for promotion and recall.
- `source_guard`: Optional validator for runtime source checking.
- `salience_decay_rate`: Reduction in salience per unaccessed `step_tick` ($0.05$).
- `consolidation_threshold`: Minimum salience required for promotion to LTM on eviction ($0.65$).

### Methods

#### `ingest(concept, assertion, source_attribution, salience=0.5, step=None, metadata=None) -> WorkingMemoryChunk`
Ingests an observation or proposition. If capacity is exceeded, evicts the least salient item. If an identical chunk already exists, applies rehearsal boost ($+0.15$ salience).

#### `access(chunk_id, step=None) -> Optional[WorkingMemoryChunk]`
Simulates focused attention/rehearsal on an active chunk, incrementing `access_count`, updating `last_accessed_step`, and boosting `salience`.

#### `step_tick(step=None) -> List[EvictionRecord]`
Advances the temporal clock. Applies `salience_decay_rate` to unaccessed chunks. Chunks reaching $\le 0.0$ salience are purged and recorded.

#### `recall_from_long_term(concept_cue) -> List[WorkingMemoryChunk]`
Executes cue-based retrieval from `ConsolidationEngine`, reconstructs fallible `INTERNAL_HYPOTHESIS` attributions referencing LTM parent nodes, and ingests qualifying items into active attention.

#### `flush_to_long_term(min_salience=0.0) -> List[str]`
Forces consolidation of qualifying active chunks to LTM, useful prior to agent sleep/checkpointing.

#### `metacognitive_assessment() -> MetacognitiveAssessment`
Computes the current epistemic health, grounding ratio, and contradiction status across active memory.

---

## 4. Usage Example
```python
from core.working_memory import WorkingMemoryBuffer, MetacognitiveVerdict
from core.source_monitoring import SourceAttribution, SourceType, VeracityState, EmpiricalProvenance

# 1. Initialize buffer with Cowan capacity K=4
wm = WorkingMemoryBuffer(capacity=4)

# 2. Ingest empirical tool observation
provenance = EmpiricalProvenance(
    tool="curl_probe",
    target="https://api.example.com",
    exit_code=0,
    execution_lock_sha256="0" * 64,
    stdout_sha256="1" * 64,
    recorded_at="2026-11-19T12:00:00Z"
)
attr = SourceAttribution(
    attribution_id="attr_001",
    source_type=SourceType.EMPIRICAL_OBSERVATION,
    assertion="API responded with HTTP 200 OK",
    veracity_state=VeracityState.VERIFIED_EMPIRICAL,
    provenance=provenance,
    created_at="2026-11-19T12:00:00Z"
)

chunk = wm.ingest(
    concept="api_health",
    assertion="API responded with HTTP 200 OK",
    source_attribution=attr,
    salience=0.9
)

# 3. Perform metacognitive self-check before taking action
assessment = wm.metacognitive_assessment()
if assessment.verdict == MetacognitiveVerdict.FOCUSED_SUFFICIENCY:
    print("Epistemic state sound:", assessment.recommended_action)
```

---

## 5. Synthetic Multi-Scenario Policy Comparison

`benchmarks/policy_comparison.py` runs four deterministic synthetic scenarios: a balanced stream, epistemic noise flooding, competition between empirical evidence and unverified claims, and a longer temporal stream. The scenarios can be exported as JSON and Markdown for CI artifacts:

```bash
python benchmarks/policy_comparison.py --events 200 --seed 42 \
  --output artifacts/policy-results.json \
  --markdown artifacts/policy-report.md
```

The script compares FIFO, LRU, random replacement, and Ario's cognitive buffer. It reports active empirical items separately from total items retained. Classical baselines have only a bounded active buffer; Ario's total preservation metric also counts a unique empirical assertion only when its matching node exists in the modeled LTM. Noise rejection is defined as unique synthetic noise absent from both active memory and modeled LTM at the end. A scenario with no noise reports `N/A`.

**Interpretation limitation:** these are synthetic, seed-dependent simulations, not empirical cognitive-science validation or evidence of production superiority. The baselines and Ario do not have identical storage capabilities, so results are descriptive and must not be presented as an apples-to-apples policy win. CI preserves the raw JSON and readable report for inspection; it does not define a performance target or claim a benchmark regression based on wall-clock timing.

Fuzz/property tests use fixed seeds by default and accept `ARIO_FUZZ_SEED=<integer>` for reproduction of one generated run. For example:

```bash
ARIO_FUZZ_SEED=999 python -m pytest -v tests/test_working_memory_fuzz.py
```

A failed randomized invariant reports its seed so the run can be repeated exactly.
