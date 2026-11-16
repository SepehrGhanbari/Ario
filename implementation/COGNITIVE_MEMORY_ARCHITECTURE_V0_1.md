# Ario Unified Cognitive Memory Architecture Specification (V0.1)

## 1. Executive Summary & Epistemic Alignment

Standard generative AI systems treat memory as unstructured context appending or naive vector search (RAG). This design is prone to confabulation, catastrophic forgetting, and ungrounded self-reinforcement. 

Ario's cognitive memory architecture grounds biological memory mechanisms (Tulving's episodic/semantic distinction, McClelland's Complementary Learning Systems, and Johnson's Source Monitoring Framework) into mathematically verifiable, append-only structures governed by Ario's founding epistemic laws:
- **Memory != Truth**: A stored memory is an auditable claim about what was observed or inferred at time $t$, not an inviolable ontological fact.
- **Claim != Proof**: Speculative assertions (`INTERNAL_HYPOTHESIS`) require verifiable empirical tool execution locks (`EMPIRICAL_OBSERVATION`) before promotion to verified evidence.
- **Revision != Erasure**: Raw episodic ledgers (`agent-events.jsonl`) are strictly append-only; updates preserve contradictions as `CONTESTED` schemas rather than silently rewriting history.

```
+---------------------------------------------------------------------------------+
|                                 WORKING MEMORY                                  |
|   - Bounded Context Buffer (MAX_CONTEXT_TOTAL_CHARS <= 16,000)                  |
|   - Central Executive Step Observer (MAX_STEPS <= 8)                            |
+---------------------------------------------------------------------------------+
         ^                                                        |
         | (Gated Cue Retrieval)                                  | (Atomic Event Logging)
         |                                                        v
+-----------------------------+                        +--------------------------+
|    SourceMonitoringGuard    |                        |  Episodic Event Ledger   |
|     [Reality Monitoring]    |                        |   (agent-events.jsonl)   |
|   - Anti-Self-Citation      |                        |  - Append-Only           |
|   - Tool Binding Locks      |                        |  - SHA-256 Hash Chained  |
+-----------------------------+                        +--------------------------+
         ^                                                        |
         |                                                        | (Offline Replay Batch)
         |                                                        v
+---------------------------------------------------------------------------------+
|                              CONSOLIDATION ENGINE                               |
|   - Extracts Semantic Schemas & Causal DAG Edges                                |
|   - Power-Law Saliency Weighting (Operational Decay)                            |
|   - Cryptographic Lineage Hash Preservation (T-CONS-01)                         |
+---------------------------------------------------------------------------------+
         |                                                        |
         v                                                        v
+-----------------------------+                        +--------------------------+
|   Semantic Knowledge Graph  |                        | Prospective Memory Reg.  |
|  - Decontextualized Rules   |                        |  - Safe Predicate Sandbox|
|  - Contradiction Preserved  |                        |  - Deterministic TTL     |
+-----------------------------+                        +--------------------------+
```

---

## 2. Interlocking Module Specifications

### Module 1: `ConsolidationEngine` (`implementation/core/memory_consolidation.py`)
- **Biological Correlate**: Hippocampal-neocortical transfer during offline replay / slow-wave sleep.
- **Function**: Ingests sequential, chronological events from `agent-events.jsonl` into generalized, decontextualized semantic schemas.
- **Invariants**:
  - `T-CONS-01 (Lineage Traceability)`: Every `SemanticNode` mandates at least one valid SHA-256 back-reference to an ingested raw event.
  - `T-CONS-02 (Non-Erasure Principle)`: Ledger byte counts must be monotonically non-decreasing.
  - `T-CONS-03 (Contradiction Preservation)`: Conflicting empirical reports yield a `CONTESTED` status rather than artificial averaging.
  - `T-CONS-04 (Saliency Decay)`: Power-law decay reduces working memory footprint without erasing dormant schemas.

### Module 2: `SourceMonitoringGuard` (`implementation/core/source_monitoring.py`)
- **Biological Correlate**: Prefrontal reality-monitoring network (Johnson et al. Source Monitoring Framework).
- **Function**: Labels every incoming assertion with an immutable origin tag and gates context injection.
- **Taxonomy**:
  1. `INTERNAL_HYPOTHESIS`: Speculative token generation by the local planner.
  2. `EMPIRICAL_OBSERVATION`: Deterministic execution of allowlisted tools (`git_status`, `inspect_directory`, `run_tests`, `compile_python`) backed by exit codes, stdout hashes, and execution locks.
  3. `EXTERNAL_TESTIMONY`: User prompts or external webhook payloads.
- **Invariants**:
  - `T-SRC-01 (Anti-Self-Citation)`: A claim citing only internal hypotheses or circular loops is marked `UNSUPPORTED` and denied promotion to working memory (`SelfCitationError`).
  - `T-SRC-02 (Tool Binding Integrity)`: Mismatched execution locks or stdout checksums fail closed (`AttributionMismatchError`).

### Module 3: `ProspectiveMemoryRegistry` (`implementation/core/prospective_memory.py`)
- **Biological Correlate**: Rostrolateral prefrontal cortex (Brodmann Area 10) prospective memory network.
- **Function**: Manages delayed conditional intentions without spawning background execution daemons or unconstrained loops.
- **Invariants**:
  - `T-PROS-01 (Safe Predicate Sandbox)`: Predicate conditions are strictly validated against an allowlisted AST subset. Arbitrary calls (`Call`), imports (`Import`), lambdas, loops, or dunders (`__*`) raise `ProspectiveSecurityError`.
  - `T-PROS-02 (Deterministic Expiration)`: Intentions evaluated after their TTL epoch transition to `EXPIRED` and never trigger execution payloads.

---

## 3. Data Contracts

### A. `SemanticNodeV1`
```json
{
  "node_id": "SEM-SCHEMA-202611-001",
  "concept": "planner_loopback_binding",
  "assertion": "Ollama planner communication binds to numerical loopback to avoid DNS TOCTOU",
  "status": "ACCEPTED",
  "source_event_hashes": ["4b825dc642cb6eb9a060e54bf8d69288fbee49048a3f81e3a9b1c7d2e4f6a8b0"],
  "saliency_score": 0.94,
  "falsification_condition": "Any successful non-loopback socket connection under _local_ollama_endpoint"
}
```

### B. `SourceAttributionV1`
```json
{
  "attribution_id": "ATTR-EMP-001",
  "source_type": "EMPIRICAL_OBSERVATION",
  "assertion": "pytest implementation/tests/test_planner_transport.py verified",
  "veracity_state": "VERIFIED_EMPIRICAL",
  "provenance": {
    "tool": "run_tests",
    "target": "implementation/tests/test_planner_transport.py",
    "exit_code": 0,
    "execution_lock_sha256": "4b825dc642cb6eb9a060e54bf8d69288fbee49048a3f81e3a9b1c7d2e4f6a8b0",
    "stdout_sha256": "8a3f81e3a9b1c7d2e4f6a8b04b825dc642cb6eb9a060e54bf8d69288fbee4904",
    "recorded_at": "2026-11-16T12:00:00Z"
  }
}
```

### C. `DelayedIntentionV1`
```json
{
  "intention_id": "INT-PROSPECTIVE-01",
  "description": "Trigger benchmark when loopback is accepted",
  "predicate_expr": "concept == 'planner_loopback' and status == 'ACCEPTED'",
  "action_payload": {"task": "schedule_regression_benchmark"},
  "created_at_epoch": 1000.0,
  "ttl_epoch": 2000.0,
  "status": "PENDING"
}
```

---

## 4. Falsifiable Test Matrix Summary

| Test ID | Module | Invariant | Verified Behavior |
| :--- | :--- | :--- | :--- |
| `T-CONS-01` | ConsolidationEngine | Lineage Traceability | Rejects dangling/untracked hashes fail-closed (`ConsolidationError`). |
| `T-CONS-02` | ConsolidationEngine | Non-Erasure Principle | Ledger bytes strictly monotonic and non-decreasing. |
| `T-CONS-03` | ConsolidationEngine | Contradiction Preservation | Conflicting claims yield `CONTESTED` status. |
| `T-CONS-04` | ConsolidationEngine | Bounded Retrieval | Inactive nodes decay below retrieval threshold. |
| `T-SRC-01` | SourceMonitoringGuard | Anti-Self-Citation | Rejects self-citation and circular rationalization (`SelfCitationError`). |
| `T-SRC-02` | SourceMonitoringGuard | Tool Binding Integrity | Discrepancies in execution locks fail closed (`AttributionMismatchError`). |
| `T-PROS-01` | ProspectiveMemoryRegistry | Safe Predicate Sandbox | Code injection (`eval`, `import`, dunder) fails closed at parse time. |
| `T-PROS-02` | ProspectiveMemoryRegistry | Deterministic Expiration | Stale intentions transition to `EXPIRED` without side effects. |
| `T-INT-01` | Integration | Full Lifecycle Pipeline | Verified hypothesis -> ledger -> consolidated schema -> prospective cue. |

Total test suite: **19 passing tests** (108 total regression tests passing).
