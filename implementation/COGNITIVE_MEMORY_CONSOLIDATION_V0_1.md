# Ario Cognitive Memory: Consolidation Engine Specification (V0.1)

## Purpose & Scope

This specification formalizes the **ConsolidationEngine** (`implementation/core/memory_consolidation.py`) as proposed in **Issue #209**. It operationalizes biological systems consolidation (Complementary Learning Systems) over Ario's append-only episodic ledgers (`agent-events.jsonl`) without weakening Ario's founding epistemic contracts:
1. **Memory != Truth**: Consolidated semantic nodes remain fallible assertions, not established ontological facts.
2. **Claim != Proof**: Every semantic node must retain an immutable SHA-256 lineage back-reference to raw episodic events.
3. **Revision != Erasure**: Ingestion and consolidation are strictly read-only relative to the underlying ledger; past events are never mutated or deleted.

## Core Invariants & Falsifiable Verification

- **T-CONS-01 (Lineage Traceability)**: Every semantic node requires at least one valid SHA-256 hash pointing to an ingested ledger line. Dangling or fabricated hashes trigger `ConsolidationError` fail-closed.
- **T-CONS-02 (Non-Erasure Principle)**: Raw ledger byte count and content are strictly immutable during ingestion.
- **T-CONS-03 (Contradiction Preservation)**: Opposing observations or claims under the same conceptual domain yield a `CONTESTED` epistemic state rather than an artificial consensus.
- **T-CONS-04 (Saliency Decay & Retrieval Threshold)**: Operational retrieval uses power-law decay to prevent working memory saturation while retaining full reconstitutability from raw ledger hashes.

## Test Suite

All invariants are executed and validated under `implementation/tests/test_memory_consolidation.py`.
