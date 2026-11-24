# Ario — Numeric Resource Error Contract, Research Sidecar v0.1

**Status: PROPOSAL / NOT ADOPTED / DRAFT / HOLD / PRODUCTION=NO_GO.**  
**Date:** 2026-11-16. **Source:** stacked Draft #241, exact source HEAD `0c1c461de2d7877c5c3c80417b15e327dea58756`. **Issues:** #216, #223, #227.

## Why this exists

A syntactically valid JSON integer of 4301 decimal digits can exceed CPython's configured integer-string conversion limit (4300 on the two verified Windows runtimes, Python 3.13.14 and 3.15.0). The unchanged research intake lab currently catches this ValueError under `INVALID_JSON`. That preserves a fail-closed outcome but confuses syntax errors with interpreter-dependent resource conversion errors.

A new numeric-resource diagnosis is a **proposed supplementary view**, NOT a rewrite of the old `INVALID_JSON` result and NOT a replacement for the original observer. The original legacy observer and memory remain unchanged.

## Proposed interpretation / version

| Layer | Outcome for synthetic 4301-digit valid JSON integer | Meaning |
|---|---|---|
| Existing research intake lab | `UNKNOWN/INVALID_JSON` | Historical structural response, preserved |
| Existing legacy observer | `UNKNOWN` (runtime/context-dependent) | Observational intake, not evidence |
| New sidecar `ario_numeric_resource_diagnostic_v0_1` | `UNKNOWN/NUMERIC_RESOURCE_LIMIT` | An integer token exceeded the explicit or Python conversion budget, in an otherwise syntactically valid and source-shaped record |
| Epistemic Assessment | `NOT_ASSESSED` | No claim promoted to truth |
| Memory | `NONE` | No semantic node, history rewrite or retention activation |

For a 4300-digit token, the old research lab remains `OBSERVED` under the verified 4300-digit CPython setting. New explicit policy choices can be *lower* (e.g., 20 decimal digits), but cannot retrospectively invalidate old `OBSERVED` reports.

## Diagnostic algorithm (research only)

`diagnose_numeric_resource_bytes(raw, limits)` accepts an already allocated, immutable Python bytes snapshot. Its defaults are **not approved production budgets**: 8 MiB raw bytes, 64 KiB per completed LF line, 5000 events, 4300 decimal digits per JSON integer token. It checks those byte budgets before parsing, uses Python's `json.loads` strict syntax parser, and installs a `parse_int` callback to detect integer token length *before converting huge integers*. A counted, syntactically recognized oversized integer is temporarily replaced with `0` **inside this diagnostic parse only**, allowing the rest of the record to be syntactically and minimally envelope-validated. **The placeholder never leaves the call, never alters source bytes, and never enters memory.**

If the *rest* of a record is malformed, the report is `UNKNOWN/OTHER_INVALID_OR_UNSUPPORTED`, not a statement that the entire JSON document was valid and only failed on numeric size. A batch with a malformed suffix is globally UNKNOWN; partial earlier results cannot become accepted memory. The output consists only of fixed reason strings and bounded counts; no source text, paths, goal strings or digests are emitted. Even hashes could be linkable and are intentionally omitted.

The diagnostic uses the same known event kinds/minimum envelope fields as the existing research lab; this is a **candidate schema**, not retroactive proof of all historical event validity. Upstream allocation, deep JSON nesting, CPU/memory worst-case use, source authenticity, symlink/TOCTOU, independent witnesses, lossless decimal semantics and correct producer claims remain **not established**.

## Compatibility and test gates

- Baseline source Git blobs must be pinned; compare unchanged original lab and observer with identical *synthetic* bytes (4300/4301-digit positive and control cases).
- Separate: malformed JSON; duplicate keys; nonstandard NaN/Infinity; finite float overflow; valid integer exceeding interpreter conversion; explicit lower future cap; valid ordinary integers; large string of digits; valid-prefix/invalid-suffix; raw byte ceiling and no final LF.
- Never infer `NUMERIC_RESOURCE_LIMIT` for a malformed document simply because some integer token is long.
- The current generic comparator's reason allowlist **does not** include `NUMERIC_RESOURCE_LIMIT`. The sidecar does **not** inject this reason into that comparator. Any future integration requires a coordinated versioned consumer/allowlist decision, separate external review and explicit owner approval.
- Old `INVALID_JSON`, `OBSERVED`, `ACCEPTED`, raw-line digests, Semantic IDs and `negates` remain byte-for-byte and meaning-preserving as historical reports. No migration, no automated crosswalk, and no `SUPPORTED` assessment.
- No real production corpus was examined here; runtime/configuration-dependent number limits must be measured on intended environments. A passing test is not a global denial-of-service proof.

**Memory != Truth. Claim != Proof. Unknown is valid. Revision != Erasure.**
