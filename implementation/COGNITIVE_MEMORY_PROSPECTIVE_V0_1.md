# Ario Cognitive Memory: Prospective Memory Registry Specification (V0.1)

## Purpose & Biological Rationale

This specification formalizes **Module 3: ProspectiveMemoryRegistry** (`implementation/core/prospective_memory.py`) as proposed in **Issue #209**.

In cognitive neuroscience, **prospective memory** (centered in the rostrolateral prefrontal cortex, Brodmann Area 10) allows an agent to formulate intentions, hold them across delayed intervals, and execute them upon recognizing specific situational cues.

In autonomous agents, deferred execution typically degenerates into uncontrolled background threads, unconstrained loops, or arbitrary remote code execution (RCE). Ario's `ProspectiveMemoryRegistry` enforces deterministic, step-bounded condition gating that eliminates code injection and prevents phantom background execution.

## Inviolable Security & Epistemic Invariants

1. **T-PROS-01 (Safe Predicate Sandbox)**:
   - Intentions evaluate condition predicates parsed strictly via Python AST.
   - Any function call (`ast.Call`), import (`ast.Import`), assignment, lambda, loop, or dunder/private attribute access (`__*`) is rejected fail-closed at parse time with `ProspectiveSecurityError`.
2. **T-PROS-02 (Deterministic Expiration)**:
   - Every intention mandates a strictly positive Time-To-Live (`ttl_epoch`).
   - If evaluated after its TTL, the intention deterministically transitions to `EXPIRED` and is guaranteed never to emit an action payload or side effect.
3. **Bounded Capacity**:
   - The registry enforces a strict upper bound (`max_pending`, default 50) to prevent unbounded memory allocation and denial of service.

## Data Contract (`DelayedIntentionV1`)

```json
{
  "intention_id": "INT-TRIG-4b825dc642cb",
  "description": "Trigger review on build failure",
  "predicate_expr": "status == 'FAILED' and exit_code != 0",
  "action_payload": {
    "target": "dossier_audit"
  },
  "created_at_epoch": 1763310000.0,
  "ttl_epoch": 1763320000.0,
  "status": "PENDING",
  "source_attribution_id": "ATTR-HYP-001",
  "triggered_at": null
}
```

## Test Suite

All invariants are executed and validated under `implementation/tests/test_prospective_memory.py`.
