# Ario Event Intake Validator Lab — v0.1

**Status:** PROPOSED / RESEARCH-ONLY / NOT ADOPTED / NOT CONNECTED / NO MERGE.  
**Date:** 2026-11-15. **Base:** Draft PR #232, c456f9886fdebe0aee0d529f554603dcf4c04384.  
**Related:** #216, #223, #227, #229, #230, #231, #232.  
**Scope:** New standalone code module, its tests and this report only.

## Purpose

This is an **experimental read-only preflight**, not an addition to current Ario Agent, Workflow, observer or memory call chains. The implementation reports the *reason* a caller-supplied UTF-8 JSONL snapshot is structurally accepted or blocked under the **proposed** shared event-envelope contract in #232. No semantic memory is created or assessed.

**Implemented API (only in the lab):**
- `inspect_jsonl_bytes(raw: bytes, *, limits: IntakeLimits())` — bounded inspection of caller-provided bytes.
- `inspect_jsonl_file(path, *, limits: IntakeLimits())` — rejects a final-path symlink, reads at most `max_ledger_bytes + 1` bytes and calls the same validator.

Both return JSON-compatible metadata, including `status` (`OBSERVED` or `UNKNOWN`), reason codes, per-record envelope results, raw SHA-256 digests with explicit `raw_line_sha256_v0_2` scheme, counts, `source_authenticity=UNKNOWN`, `assessment=NOT_ASSESSED`, and `memory_mutation=NONE`. No record's `goal`, `observation`, sensitive content or source file pathname is included.

The word `OBSERVED` here **only** means all parsed records passed the proposed structural envelope check within the selected research budget. It is not the existing observer's authority, not admissible evidence, not source identity, and not truth.

## Proposed strict parser implemented in the lab

- LF-terminated JSONL; CRLF accepted, lone CR is not a record separator.
- Strict UTF-8, JSON object per line, duplicate keys forbidden recursively, `NaN` / `Infinity` rejected.
- Exact raw SHA-256 line digests including final LF or CRLF, plus whole-source hash only when all records pass.
- Eight known Ario producer event types with event-specific minimum non-empty string fields, checked against current Agent/Workflow emitter shapes. No new event kind is silently treated as approved.
- Budget defaults copied *for comparison only* from current observer: 8 MiB raw ledger; 64 KiB raw line; 5000 records.
- Fail closed **globally**: a malformed suffix or budget breach sets `status=UNKNOWN`, `eligible_records=0` and `file_sha256=null`; earlier per-record `VALID_ENVELOPE` metadata means only that the earlier line passed, **not** a committed partial intake.
- Source-content-free explanations: no source text echoed in errors.

## What the lab intentionally does NOT implement

- No changes to `ledger_observation_adapter.observe_ledger`, `ConsolidationEngine`, `ario_agent`, `ario_workflow`, or archives.
- No memory-side persistence, source authentication, truth verification, independent attestation, ID v2, `ACCEPTED` replacement, `SUPPORTED` promotion, Cross-IRG, keys, privacy retention/erasure or new trust rights.
- No proof against file replacement or race attacks; final-path `is_symlink()` is not a guarantee against ancestor symlinks or TOCTOU. Only a single bounded snapshot is inspected.
- `inspect_jsonl_bytes` receives already allocated bytes; its size check does not limit caller allocation. JSON decoding within a bounded 64 KiB line still consumes CPU and memory; this is not a certified DOS defense.
- Event-specific minimum fields may reject legacy logs accepted by the original observer; historic approval/compatibility needs corpus-based independent review.
- `eligible_records` counts proposed envelope eligibility for *review*, not durable `RECORDED` events. There is no assertion extraction or semantic-memory claim.
- The physical reader's path policy is not a universally agreed shared security contract. Existing producer-accepted long goals can be rejected with explicit `LINE_SIZE_LIMIT`, without falsely labeling them untrue or deleting evidence.
- No approval of Option B V1→V2 memory sidecar, no historical ID remapping; these decisions remain HOLD in #216.

## Tests and acceptance criteria

Tests cover all eight known event types, LF/CRLF and embedded CR, duplicate and nested keys, nonfinite numbers, bad UTF-8, invalid JSON, missing required fields, unsupported kinds, empty/partial sources, raw ledger/line/count limits, oversized goals, globally blocked partial batches, immutable read-only file behavior, and real final-path symlink refusal where the OS supports it.

**This laboratory baseline must not silently turn a strict-XFAIL into a claimed security pass.** The earlier #232 test suite's unresolved XFAILs still show production interoperation mismatches; the new lab's success only shows a stand-alone validator can implement *one proposed interpretation*. Any integration needs a separate owner-approved architecture and an independent review.

**Verdict:** candidate for falsification and comparative research; **NOT IMPLEMENTED IN PRODUCTION / NOT AUTHORIZED / TRUST_ACTIVATION=NO_GO**.
