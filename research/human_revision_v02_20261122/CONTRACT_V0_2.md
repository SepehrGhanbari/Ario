# Human Self-Revision v0.2 — scoped event projection (Issue #220)

Status: **RESEARCH_ONLY / DRAFT / HOLD / SYNTHETIC / NO_MERGE**.

This is an additive companion to existing [Draft PR #226](https://github.com/SepehrGhanbari/Ario/pull/226), **not** a substitute for its `implementation/human_revision_policy.py`, Issue #210, or the main memory architecture. No existing source files are changed.

## Five independent distinctions

1. **RECORDED_STATEMENT**: reference to a historically recorded *claim*, not its truth or a current preference.
2. **SYSTEM_INTERPRETATION**: a model-generated reading with an explicit parent statement; can be superseded but never becomes a person's utterance.
3. **PERSON_CORRECTION**: proposed scoped change of interpretation, targeting the exact current interpretation reference. An unbound or stale target is UNKNOWN.
4. **USE_PERMISSION / USE_WITHDRAWAL**: independent future-use policy signal. A correction does not grant reuse by itself. Withdrawal denies future use in the requested scope without pretending archival deletion occurred.
5. **DISPUTE / unresolved**: disagreement, unauthorized actor, missing ancestry and scope mismatch all remain visible without invented resolution.

## Interface and nonclaims

`project(events, subject_ref=..., scope=...)` takes a caller-supplied ordered list of synthetic eight-field dicts: event_id, kind, subject_ref, actor_ref, scope, ref, target_ref and authority.

`EXTERNALLY_VERIFIED` is **a declaration supplied by the caller**. The function does not authenticate it, provide person-ID verification, detect forged attestations, or decide legal retention. With a verified *premise* and exact scope it returns at most `REVIEWABLE / CURRENT_REF_ONLY`, never a mandatory memory action. A later SYSTEM_INTERPRETATION cannot override a correction. Duplicate event IDs, unknown authority, unsupported source/target and cross-scope corrections fail closed.

`historical_statement_refs`, `system_interpretation_refs`, `current_interpretation_ref`, `permission` and `unresolved` are deliberately different output fields. They contain only synthetic refs. The projection has **no persistence, no real data, no network, no keys and no memory-core imports**. It never rewrites recorded events. Privacy law and rights to restriction, rectification and erasure require a separate policy and must not be defeated by append-only claims.

## Known unresolved risks

- Caller-controlled authority may be forged: cannot establish real human attribution.
- The corpus is author-authored and public: no blind or independent study.
- Inputs are only declared complete. A missing historical event or a forged event stream cannot be discovered.
- Simple ordered processing is a v0.2 toy model, not temporal, legal, or inter-device conflict reconciliation.
- Rejecting ambiguous/stale cases can cause false rejections until an independently reviewed policy clarifies them.
- Proposed `CURRENT_REF_ONLY` is not automatically enforced by any downstream system or stale cache.

## Reproduction

From `research/human_revision_v02_20261122/`, run `python -B -m unittest -v test_reference.py`. All nine cases are fictional and publicly labeled.

## Non-novelty

This composes ordinary event sourcing, provenance links and purpose-limited consent/revocation. W3C PROV-O describes provenance, and data protection laws may provide independent rectification/restriction obligations. No claim of scientific novelty, mental-state detection or a deployed human-rights mechanism.
