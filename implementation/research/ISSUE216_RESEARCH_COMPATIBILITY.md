# Issue #216 — research compatibility resolution candidate (v0.1)

Base: `b792d3bc7fb1d960f1943aac087f8aebbaf930b6`. Scope: one collision fix and targeted regressions. No production migration or protected semantic adoption.

## Existing implementation and decision boundary

- Raw ingest produces RECORDED, not ACCEPTED or SUPPORTED. CONTESTED/UNSUPPORTED supplied by untrusted inputs are diagnostic labels only, not an authorized assessment or proven refutation. REVISED cannot be asserted by raw ingest. Repeated inputs are not independent support.
- Historical ACCEPTED/SUPPORTED artifacts remain untouched. Existing data-only snapshot recovery refuses their installation into an active engine, rather than silently promoting or downgrading. Historical ACCEPTED conveys only the old structural recording claim; independent support is UNKNOWN. Legacy pickle is not safe for untrusted input.
- Existing research ID encodings remain frozen: v1 is SHA256 of concept + colon + assertion, first 16 hex; v2 is SHA256 of Python JSON array encoding (ensure_ascii=True, separators comma/colon, sort_keys=True), first 16 hex, SEM-v2- prefix. The engine's existing strip/string conversion remains unchanged; no NFC normalization or full-hash ID migration is adopted. Neither ID is a proof of semantic equivalence.
- Exact v2 IDs are readable; the derived v1 alias returns None when ambiguous, including after validated snapshot recovery. Raw negation references use exact IDs only, not a guessed alias. Existing conflict labels are scoped diagnostics. Separate authorized evidence/assessment contract remains #81/#276.
- New correction: a node-ID collision between distinct normalized pairs refuses the batch without modifying its existing lineage, in either version. This prevents new conflation; it cannot recover historical provenance already conflated by earlier prototypes. Archive bytes and IDs are unchanged.
- #426 settled the named physical-line hash schemes: legacy_trimmed_v0_1 is stored identity, raw_line_v0_2 is report-only. No inverse alias or automatic migration of historical raw-only references.
- Historical T-CONS-04 labels remain intact. For this reconciliation call source anti-self-citation T-SRC-01 (existing code) and saliency decay MEM-DECAY-01 (new documentation-only cross-reference); no historical test renaming.

## Validation and disposition

Reuse #424–#426 and the existing legacy-resolution, safe-snapshot, source-monitoring, bridge and replay tests. New focused matrix covers both arrival orders, whole-batch refusal, populated-state preservation after recovery, collision injection for the existing truncated v2 digest, exact versus ambiguous negation, unauthorized raw labels and repeat inputs, encoding and digest scheme. Run normal regression and restore workflows. Explicitly separate research correctness from external evidence admission, retrospective migration, and production adoption. This candidate does not ratify the proposed full-length V2/dual-axis policy in #216; independent review may decide the bounded implementation concern is resolved and record remaining design topics separately. No closure until requested review. CI pending.
