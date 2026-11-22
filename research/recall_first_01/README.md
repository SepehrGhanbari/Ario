# RECALL-FIRST-01 — remembered answers without self-reasoning loops

**Date:** 2026-11-22  
**Mode:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO  
**Owner requirement:** Ario should remember a previously answered question or decision across turns/sessions instead of repeatedly analyzing the same settled question from scratch. A remembered answer is **not** verified external truth.

## Exact comparative source boundary

This standalone synthetic Python research fixture **does not import or change** the actual Ario memory engine. Its target is a missing behavior in the current experimental interfaces, not a claim of a verified production fault. Sources inspected from the pinned **unmerged research head** `3af6349d1c9dd128d7e1aa908b5f52320b1b3bb6`:

- `implementation/core/memory_consolidation.py` Git blob `41db5f53c720181bcc152c66cc116a218e7a4468`: `retrieve_active_context(concept_cue)` filters by salience threshold and literal concept substring and sorts by salience. That alone does not establish question→prior-answer recall or a correction-aware version contract.
- `implementation/core/working_memory.py` Git blob `9cae51d260da8c309e4e29290e2e38fc05ec4648`: `recall_from_long_term` uses the above nodes and re-ingests as a **hypothesis**, not a new empirical witness. The transient working-memory buffer and its rehearsal mechanics are not a durable answer/decision index.
- Existing founder requirement on [Issue #209](https://github.com/SepehrGhanbari/Ario/issues/209#issuecomment-7078883522); protected status and V1/V2 policy remain [Issue #216](https://github.com/SepehrGhanbari/Ario/issues/216), independent evidence admission remains [Issue #81](https://github.com/SepehrGhanbari/Ario/issues/81).

**No baseline RED test was executed on Ario's full runtime source here.** Source review shows a missing explicit interface; this standalone positive comparator cannot prove runtime integration.

## Tested minimal behavior

- Write synthetic previous question/answer/decision into a bounded local JSONL journal with an explicit source/message reference and SHA-256 event chain. Return stable `answer_id`, original source reference and version. Index using `(scope, NFC-casefold-whitespace-normalized question)`; exact key matches work without recomputation.
- Bind a **known-equivalent paraphrase only by explicit experimental operator action**; semantic equivalence is *not* inferred automatically. Unknown paraphrase remains UNKNOWN, not guessed. Multiple candidate answers for the same key are `UNKNOWN_AMBIGUOUS`.
- Cross-session reopen reconstructs the index from the durable synthetic journal. Repeated reads do **not** append new evidence, raise salience, or cause any invocation of model recomputation (no model is present in the lab).
- Corrections append a new version linked to the same answer ID. Previous answer text remains retrievable as history; a later identical question returns the newer version.
- `TIME_SENSITIVE` synthetic answers: a historical question returns `RECALLED_HISTORICAL`; a question about current validity returns `RECHECK_REQUIRED`. The heuristic is only a manually supplied classification, **not a semantic freshness adjudicator**.
- The **only** support assessment projected is `NOT_EVALUATED`; no `SUPPORTED` or `ACCEPTED` transition exists. Strict JSON event-schema parsing denies a forged `status: SUPPORTED`, local tampering, duplicate keys, truncated tails, and cross-scope alias insertion.

## Reproduce (stdlib, no installed packages)

```sh
cd research/recall_first_01
python -B -m unittest -v test_recall_first_lab.py
```

**Actually executed before publishing:** `20 tests / 20 PASS`; locally mutated `_effective_assessment` from `NOT_EVALUATED` to `SUPPORTED`: three distinct tests FAIL, so promotion regression is detected (expected mutant RED, actual test exit 1).

## Boundaries / reasons not to adopt as Ario runtime

1. This is a **demonstrator**: no bridge to Ario's conversation ingestion, `SemanticNode`, source-monitoring guard, memory persistence or versioned snapshot authorization. It does not establish Ario's functional recall rate or latency.
2. Automatic paraphrase matching, reference resolution, intent detection and answer factual freshness evaluation are NOT IMPLEMENTED. Explicit aliases are metadata assertions, not independent semantic proof.
3. SHA-256 links local bytes only; an operator controlling the journal can truncate it and replace its head. No external floor, witness independence, true historical timestamp, or rollback resistance is established. Single-writer lab, not a concurrent transaction engine or hardened file system.
4. Recalled content is historical evidence of **what was previously recorded**, not proof that a factual statement is true or that a historic decision remains authorized today. Repetition does not create corroboration.
5. Version 1 data, code and existing history remain untouched. The proposed V1 preserved + optional V2 interpretation remains *unadopted* under #216. This PR is research-only and cannot authorize protected memory semantics, real keys or production.

**Next scoped engineering target after review:** design a **read-only adapter** from actual approved source IDs and message/decision records to this lookup contract, test paraphrase disambiguation and freshness, then decide if bounded implementation can be authorized without creating a parallel memory. Do not merge a standalone demo as if it were Ario's real recall engine.
