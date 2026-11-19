# Ario Cognitive Memory: Metacognitive Source Monitoring Guard Specification (V0.1)

## Purpose & Biological Rationale

This specification formalizes **Module 2: SourceMonitoringGuard** (`implementation/core/source_monitoring.py`) as outlined in **Issue #209**. 

In cognitive psychology and neuroscience, the **Source Monitoring Framework (SMF)** (Johnson, Hashtroudi, & Lindsay, 1993) describes the decision processes by which the brain identifies the origins of memories, thoughts, and assertions—specifically differentiating between:
1. **Internal Source Monitoring**: Discriminating between different internal cognitive operations (e.g., imagination vs. counterfactual simulation vs. speculative hypothesis).
2. **External Source Monitoring**: Discriminating between different external sources (e.g., user input vs. tool output vs. remote server response).
3. **Reality Monitoring**: Distinguishing internal thoughts, generated tokens, and ungrounded hallucinations from actual, perceptual/empirical interaction with the external environment.

In standard LLM architectures, models confabulate because all internal and external tokens share a uniform semantic embedding space without cryptographic provenance. Ario's `SourceMonitoringGuard` guarantees that no assertion generated internally or passed by testimony can be elevated to verified working memory without deterministic empirical grounding.

## Foundational Invariants

1. **Memory != Truth**: Every tagged assertion remains an auditable, fallible claim subject to falsification conditions.
2. **Claim != Proof**: A generated assertion (`INTERNAL_HYPOTHESIS`) or user assertion (`EXTERNAL_TESTIMONY`) requires verified tool execution lock and checksum verification before promotion.
3. **Revision != Erasure**: Invalidated or mismatched assertions are never deleted or silently suppressed; their veracity state transitions to `UNSUPPORTED` or `ATTRIBUTION_MISMATCH`.

## Falsifiable Test Matrix

- **T-SRC-01 (Anti-Self-Citation & Reality Gating)**:
  - An internal hypothesis citing only itself, prior planner tokens, or another unverified hypothesis cannot promote to `VERIFIED_EMPIRICAL`.
  - Violations fail-closed with `SelfCitationError` and mark the claim as `UNSUPPORTED`.
  - Circular citation loops across hypotheses (e.g., A -> B -> A) are detected and fail-closed.
- **T-SRC-02 (Tool Binding Integrity)**:
  - An assertion tagged `EMPIRICAL_OBSERVATION` must be bound to an allowlisted tool with a valid execution lock and stdout SHA-256 checksum.
  - Any discrepancy between expected and observed hashes fails-closed with `AttributionMismatchError` and sets veracity state to `ATTRIBUTION_MISMATCH`.

## Data Contract (`SourceAttributionV1`)

```json
{
  "attribution_id": "ATTR-EMP-4b825dc642cb",
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
  },
  "parent_attribution_ids": ["ATTR-HYP-001"],
  "falsification_condition": "Any non-zero exit code or socket leak"
}
```

## Test Suite

All invariants are executed and validated under `implementation/tests/test_source_monitoring.py`.
