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

### Module 4: `WorkingMemoryBuffer` (`implementation/core/working_memory.py`)
- **Biological Correlate**: Central Executive & Episodic Buffer (Baddeley & Hitch; Nelson Cowan 4-chunk capacity model).
- **Function**: Manages the agent's bounded attentional focus, dynamic salience weighting, temporal decay, adaptive forgetting, and metacognitive confidence calibration.
- **Invariants**:
  - `T-WM-01 (Strict Cowan Bound)`: Working memory buffer capacity is strictly constrained to $K=4$ active informational chunks by default to prevent context pollution and attention exhaustion.
  - `T-WM-02 (Provenance Gate)`: Every ingested chunk must carry an audited `SourceAttribution` verified by `SourceMonitoringGuard`. Unattributed claims are rejected fail-closed (`SourceMonitoringError`).
  - `T-WM-03 (Dual Eviction Fate)`: High-salience/rehearsed chunks are automatically promoted to Long-Term Memory via `ConsolidationEngine`; low-salience noise is adaptively forgotten without LTM pollution.
  - `T-WM-04 (Metacognitive Monitoring)`: Real-time assessment flags ungrounded hypotheses, active contradictions across co-residing chunks, and recommends directed recall when empirical grounding is insufficient.

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

### D. `ContestationReportV1` & `MemoryConflictV1`
```json
{
  "generated_at": "2026-11-16T18:00:00Z",
  "total_nodes": 24,
  "contested_nodes_count": 2,
  "accepted_nodes_count": 22,
  "contested_concepts": ["network_policy"],
  "conflicts": [
    {
      "concept": "network_policy",
      "node_ids": ["SEM-325e6fc935972794", "SEM-de9bdc9ae6d009de"],
      "assertions": ["Loopback strictly bound to 127.0.0.1", "Proxy redirection enabled on port 8080"],
      "source_event_hashes": [
        "4b825dc642cb6eb9a060e54bf8d69288fbee49048a3f81e3a9b1c7d2e4f6a8b0",
        "8a3f81e3a9b1c7d2e4f6a8b04b825dc642cb6eb9a060e54bf8d69288fbee4904"
      ],
      "saliency_scores": [0.70, 0.70],
      "status": "CONTESTED",
      "summary": "Contested assertion conflict across 2 schema nodes under concept 'network_policy'"
    }
  ]
}
```

### E. `IntentionJournalV1` (Atomic Persistence & Tamper Detection)
```json
{
  "version": "1.0",
  "exported_at": "2026-11-16T18:00:00Z",
  "max_pending": 50,
  "records_count": 3,
  "integrity_digest": "1aead788ab79cf458b34ed0eb75a576015358519e740c0f6f798c240b2004a82",
  "intentions": [
    {
      "intention_id": "INT-PROSPECTIVE-01",
      "description": "Trigger benchmark when loopback is accepted",
      "predicate_expr": "concept == 'planner_loopback' and status == 'ACCEPTED'",
      "action_payload": {"task": "schedule_regression_benchmark"},
      "created_at_epoch": 1000.0,
      "ttl_epoch": 2000.0,
      "status": "PENDING"
    }
  ]
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
| `T-CONS-05/06` | ConsolidationEngine | Contestation Reporting | Structured conflict audit reports (JSON & Markdown) preserving audit lineage. |
| `T-SRC-01` | SourceMonitoringGuard | Anti-Self-Citation | Rejects self-citation and circular rationalization (`SelfCitationError`). |
| `T-SRC-02` | SourceMonitoringGuard | Tool Binding Integrity | Discrepancies in execution locks fail closed (`AttributionMismatchError`). |
| `T-PROS-01` | ProspectiveMemoryRegistry | Safe Predicate Sandbox | Code injection (`eval`, `import`, dunder) fails closed at parse time. |
| `T-PROS-02` | ProspectiveMemoryRegistry | Deterministic Expiration | Stale intentions transition to `EXPIRED` without side effects. |
| `T-PROS-07..10` | ProspectiveMemoryRegistry | Journal Persistence & Recovery | Atomic persistence, SHA-256 integrity check, AST re-validation on load, reboot TTL sweep. |
| `T-SEC-01..32` | Security Boundaries | Adversarial Hardening | AST injection fuzzing (walrus, comprehensions, f-strings), tool smuggling, multi-hop circularity. |
| `T-CLI-01..08` | CLI Interface | Command Audit Execution | `--memory-conflicts` report generation (JSON/Markdown) and `--inspect-ledger` crash integrity. |
| `T-CRASH-01..11` | Crash Recovery | Resilience & State Replay | Orphan journal temp cleanup, bitflip/truncation fail-closed, offline TTL sweep, reboot replay. |
| `T-INT-01` | Integration | Full Lifecycle Pipeline | Verified hypothesis -> ledger -> consolidated schema -> prospective cue. |
| `T-BRG-01..08` | EpistemicLedgerBridge | Agent Runtime Bridge | Ingests real agent execution JSONL, empirical tool locks, prospective triggers, v2 canonical IDs. |

Total test suite: **86 specialized cognitive memory tests** (1,227 overall repository regression tests passing).

---

## 5. Operational CLI & Crash Recovery Interface

### A. Epistemic Contestation Audit via CLI
Generate human-readable or machine-readable audit reports of contested memories directly from episodic ledgers:
```bash
# Markdown format (default)
python implementation/ario_cli.py --memory-conflicts --ledger agent-events.jsonl

# Export to JSON
python implementation/ario_cli.py --memory-conflicts --ledger agent-events.jsonl --format json --output conflicts.json
```

### B. Read-Only Ledger Crash Inspection
Audit an episodic ledger for truncated tails or abrupt termination without mutating file bytes:
```bash
python implementation/ario_cli.py --inspect-ledger --ledger agent-events.jsonl
```

### C. Agent Execution Ledger Bridge to Cognitive Memory
Bridge bounded agent execution ledgers into cognitive memory schemas and evaluate prospective intentions:
```bash
# Markdown format (default)
python implementation/ario_cli.py --bridge-agent-ledger --ledger agent-events.jsonl

# Export to JSON
python implementation/ario_cli.py --bridge-agent-ledger --ledger agent-events.jsonl --format json --output bridge_summary.json
```

---

## 6. Resolution of Issue #216 Epistemic Invariants & v2 Identifiers

### A. Epistemic Separation: RECORDED vs SUPPORTED
To prevent conceptual boundary ambiguity between memory ingestion and truth claims (*Memory != Truth*), nodes ingested from caller streams default to `RECORDED`. Transitions to `SUPPORTED` occur strictly when empirical tool execution locks or authorized external witnesses are verified.

### B. Delimiter-Free Canonical Node Identifiers (v2)
Legacy identifiers derived from `sha256(concept + ":" + assertion)` exhibited colon delimiter aliasing: `("a:b", "c") == ("a", "b:c")`.
The v2 canonical identifier format computes:
```python
node_id = "SEM-v2-" + sha256(json.dumps([concept, assertion], separators=(',', ':'), sort_keys=True))[:16]
```
A dual resolver maintains backwards compatibility by transparently resolving legacy `SEM-<hash>` queries to their canonical `SEM-v2-<hash>` counterpart.

### C. No-History-Promotion Invariant
Re-ingesting an unverified assertion increases operational reinforcement and updates saliency, but strictly preserves `RECORDED` status. History repetition cannot promote an assertion into `SUPPORTED` truth without empirical evidence.

### D. Continuous Integration Workflow
The test suite is enforced on every push and pull request via `.github/workflows/implementation-regression.yml`:
1. `m0-regression`: Full repository test suite (1,217 tests).
2. `cognitive-memory-invariants`: Dedicated check verifying all 76 memory consolidation, source monitoring, prospective registry, security boundary, and crash recovery tests.
3. `windows-differential-advisory`: Cross-platform Windows execution ensuring canonical path handling.

## Local source-lineage inspection (opt-in research CLI)

The existing memory CLI can inspect a disposable, caller-pinned Agent JSONL ledger or a combined memory/source-history snapshot. Use a retained SHA-256 pin; computing a fresh self-pin does not establish historical integrity. With no node ID, list at most 100 exact semantic node IDs; pass an exact ID for source resolution. Output is always JSON. Example from repository root:

```powershell
python .\implementation\ario_memory_cli.py --memory-lineage --ledger "$HOME\Ario\runtime\inspection-events.jsonl" --expected-sha256 "<retained digest>"
python .\implementation\ario_memory_cli.py --memory-lineage --snapshot "$HOME\Ario\runtime\memory.json" --expected-sha256 "<retained digest>" --node-id "<exact node ID>"
```

Exit 0: local node index or fully matched local WM-event references; 1: partial/unresolved diagnostic (including ledger-reference-only); 2: invalid input or failed validation. The exact-node reader shares the recall lineage algorithm and does not create recall attributions, activate empirical authority, write the input or install a live memory state. Optional `--output` creates a new JSON report exclusively. Pins are byte integrity only; claim truth, source authenticity, freshness and independent admission remain unknown or absent. No snapshot migration or autonomous local-chat activation.
