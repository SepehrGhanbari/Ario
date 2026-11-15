# Ario — Shared Event Input Contract (Proposal v0.1)

**Status: PROPOSED / RESEARCH-ONLY / NOT ADOPTED / NO PRODUCTION CHANGE / NO MERGE.**  
**Date:** 2026-11-15. **Review chain:** #210 → #217 → #222 → #224 → #225 → #229 → #230 → #231.  
**Related issues:** #216 (protected memory meaning / V2 ID), #223 (resource limits), #227 (ledger format).  
**Pinned observed sources:** `main=2e7f83c6c7518012bed7fedfb12103ce9b7222ea` for `ario_agent.py`, `ario_workflow.py`, `ledger_observation_adapter.py`, and `ledger_audit_bridge.py`; Draft #231 head `7f61d9388183920221926ed5df6594c6ffefc920` for `core/memory_consolidation.py`.  
This document is **not** an implemented shared validator, a signature, a guarantee of authenticity, or a change to existing runtime policies.

## 1. Problem statement grounded in source

There are four separate actions that must not be conflated:
1. **EMITTED:** Agent/Workflow writes an event via `_append_event`, with sorted, UTF-8 JSON followed by LF. This is a producer-side action, not evidence of a true claim.
2. **OBSERVED:** `ledger_observation_adapter.observe_ledger` reads a local byte source, enforces its own 8 MiB raw file / 64 KiB raw line / 5000 record ceilings and a known event envelope, and returns `OBSERVED` or `UNKNOWN`. `OBSERVED` is **not** source custody, admissible Evidence, or Assessment.
3. **STRUCTURALLY INGESTED:** the Draft Memory ConsolidationEngine accepts some events, retains hashes, optionally extracts a semantic assertion and returns an **integer count of ingested records**. This count does **not** mean the number of semantic nodes or facts.
4. **ASSESSED / SUPPORTED:** would require a separate *explicit authorized evidence-assessment contract*. None of the three preceding actions can promote a claim to verified truth. The historical memory enum `ACCEPTED` remains a problematic **legacy ingestion label** (#216).

Source-grounded incompatibilities were reproduced on exact #231 code with **synthetic inputs only**:
- The observer reports `OBSERVED` on duplicate root and nested JSON keys and `NaN` constants; the memory reader rejects those inputs.
- The observer accepts a `TASK_FINISHED` envelope missing `task_id` because it validates event name and timestamp, not source-specific required fields; the producer's normal event includes `task_id`.
- The direct memory stream accepts a list as an `assertion` and converts it to a string, rather than rejecting that unsupported semantic field type.
- The observer and memory disagree on symlink policy, raw line bytes, total raw file bytes and a producer-accepted long `goal` (three strict RED tests in #230). These are **unresolved**, not implementation permissions.

## 2. Candidate staged response contract

Each stage should return a separately named result; never silently widen a previous result's meaning.

| Stage | Candidate outcomes | Safe interpretation |
|---|---|---|
| Producer emission | `EMITTED` / `EMISSION_FAILED` | Bytes were emitted or failed to write; content not certified |
| Bounded raw-byte observation | `OBSERVED` / `UNKNOWN` / `REJECTED_MALFORMED` | Locally seen bytes; explicit reason, no historical proof |
| Envelope/schema validation | `VALID_ENVELOPE` / `INVALID_ENVELOPE` / `UNSUPPORTED_VERSION` / `UNKNOWN` | Syntax/declared fields only; unknown is not silently coerced to valid |
| Memory input eligibility | `RECORDED` / `NOT_ELIGIBLE` / `RESOURCE_LIMIT` / `UNKNOWN` | Distinguish retained event from event excluded with a reason; no unauthorized durable copy |
| Semantic extraction | `EXTRACTED` / `NO_CLAIM_MAPPED` / `CONTESTED_INPUT` / `UNKNOWN` | Extraction optional; preserving record count is not learning |
| Independent assessment | `NOT_ASSESSED` / `UNKNOWN` / versioned separately authorized values | No support/truth promotion from hashing, replay or local CI |

This is a **proposed API**; current code does not emit this six-stage report. Until a future authorized implementation exists, do **not** claim all stages were enforced.

### No silent drop ≠ unconditional ingestion

A producer-valid event that exceeds a downstream budget **must not silently disappear**, but it may be refused or deferred explicitly, with a typed reason and a limited, privacy-reviewed reference. It must **not** be imported into unlimited memory simply because it passed `parse_task`. A structurally valid `TASK_FINISHED` without an eligible semantic field may remain recorded and report `NO_CLAIM_MAPPED`; it must not become a fabricated proposition like “the task was truly accomplished”.

## 3. Candidate shared parser and envelope matrix

**Byte-level candidate contract:** UTF-8, completed LF-terminated JSONL records (CRLF allowed; a lone CR is not a separator), one unambiguous JSON object per LF record, non-empty record, no duplicate object keys at **any depth**, no nonfinite numeric constants (`NaN/Infinity`), no invalid UTF-8, no discarded trailing fragments. Hash **exact source bytes including LF/CRLF** and label the digest scheme. Require a separate resource preflight to avoid unbounded allocations; a syntactically legitimate over-budget event is `RESOURCE_LIMIT` or `UNKNOWN`, **not a false semantic claim**.

| Event kind in current producers | Source-shaped field candidates beyond `event` and `timestamp` | Evidence scope |
|---|---|---|
| `TASK_STARTED` | `task_id`, `goal` | Goal text is a *declared task*, not accomplished outcome |
| `STEP_OBSERVED` | `task_id`, `step_id`, `status` | Status is a reported observation, not independent proof |
| `GOAL_CRITERION_OBSERVED` | `task_id`, `criterion_id`, `status` | Assessment limited to recorded local check |
| `FAILURE_DIAGNOSTIC_OBSERVED` | `task_id`, `step_id`, `status` | Diagnostic observation, not authority |
| `TASK_FINISHED` | `task_id`, `status` | Completion report, not truth of task goal |
| `WORKFLOW_STARTED` | `workflow_id`, `goal` | Declared intent |
| `WORKFLOW_STAGE_OBSERVED` | `workflow_id`, `stage_id`, `status` | Reported stage status, including `SKIPPED` |
| `WORKFLOW_FINISHED` | `workflow_id`, `status` | Workflow completion report only |

Existing observer requires only `event` from its eight allowlisted kinds plus a non-empty `timestamp`; this table proposes **stricter event-specific minimums**, not the present implementation. It must be checked against actual old logs *before any adoption*; do not retroactively relabel old `OBSERVED` manifests invalid. Future/unknown event types should be `UNSUPPORTED_VERSION/UNKNOWN`, not silently treated as valid or erased.

## 4. Resource interoperation decision (still HOLD #223/#227)

Today's separate ceilings:
- Agent `parse_task` has bounded number of actions but **no general length bound on `goal`**. A source-valid 70 KiB goal is possible.
- Observer: max **64 KiB raw line**, **8 MiB raw ledger**, **5000 events**; rejects symlinks.
- Memory Draft: max **64 KiB compact-serialized event**, **8 MiB compact-serialized batch**, **5000 per call**, **5000 unique hashes per engine**, **16 MiB raw file**; symlink not checked.

These are different dimensions. **Recommendation for review:** label and enforce distinct `raw_line_bytes`, `raw_ledger_bytes`, `compact_event_bytes`, `batch_bytes`, `max_events_per_call`, `max_retained_hashes_per_engine`, and `source_kind` fields in a versioned intake report. Decide whether a shared fail-closed preflight delegates to the bounded observer or a **separately declared** memory source scope. Neither silently increasing Agent limits nor weakening observer bounds is authorized.

Known limitations requiring separate work: producer output amplification, validator CPU, process peak memory before JSON serialization, deeply nested JSON, consumer retention, symlink/snapshot TOCTOU, and whether reported counts represent *seen*, *eligible*, *recorded*, *skipped*, *new nodes*, or *reinforcements*.

## 5. Pre-registered acceptance/rejection probes

1. **Positive:** source-shaped `TASK_STARTED` with valid UTF-8 LF or CRLF: observed and recorded once, exact source hash; no truth promotion.
2. **Positive:** a `TASK_FINISHED` with no semantically eligible assertion can still be structurally counted, but must be marked `NO_CLAIM_MAPPED`, not silently described as a learned fact.
3. **Negative:** duplicate root/nested JSON keys and `NaN` must not be accepted as unambiguous JSON by the shared parser. Present observer accepts them (strict XFAILs).
4. **Negative:** `TASK_FINISHED` missing `task_id` must not be fully event-schema validated under the proposed strict envelope. Present observer only checks `event` and `timestamp` (strict XFAIL).
5. **Negative:** a list/dict used as semantic `assertion` must not be silently coerced to string by an authorized typed semantic extractor (strict XFAIL).
6. **Negative:** a skipped/unmapped input requires an **explicit, privacy-aware report** (proposed; strict XFAIL because report API does not exist).
7. **Legacy:** distinguish `legacy_trimmed_sha256_v0_1` from `raw_line_sha256_v0_2` and never silently reparent historical references.
8. **Cross-component:** preserve #230's three XFAILs: symlink, large raw line, producer-valid long goal.
9. **Identity:** preserve old alias collision RED `("a:b","c")` vs `("a","b:c")` until a versioned, accepted migration plan exists.
10. **Regression:** no existing change to main, old records or source timestamps; independent review and owner adoption required for protected semantic or runtime schema changes.

## 6. Review gate before implementation

- Choose one supported physical input origin (regular file path, independently bounded byte stream, or separately approved exception) with explicit byte limits and symlink/TOCTOU rules.
- Decide whether the producer should enforce a maximum text length or whether the consumer should report a well-defined `RESOURCE_LIMIT` for producer-valid larger logs, **without losing the audit trail**.
- Agree a consistent duplicate-key/nonfinite parser contract, exact event-specific schema, and absence/unknown handling.
- Specify aggregation counters, sensitive-data retention/deletion, digest scheme tag, and replay/idempotence.
- Submit independent negative review (including benign positives), replay and cross-version tests **before** adoption.

**No common runtime parser has been implemented or activated by this document. `UNKNOWN` remains valid; `OBSERVED` never implies `SUPPORTED`.**
