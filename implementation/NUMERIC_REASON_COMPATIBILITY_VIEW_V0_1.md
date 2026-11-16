# Ario — Read-only Numeric Reason Compatibility View v0.1

**Status:** RESEARCH_ONLY / DRAFT / PROPOSED / NOT ADOPTED / NOT INTEGRATED.  
**Date:** 2026-11-16. **Parent:** Draft #243 head `8ea3e50223c28a148ba8a48f9fffcd5bb4d4a88c`.  
**Issues:** #216, #223, #227. **Other preregistered review:** #238, #241.

## Why a separate view, not an expanded parser allowlist?

The old same-snapshot comparator accepts only versioned reason strings returned through its **strict-lab** interface. The numerical-resource sidecar is NOT that interface: it returns `status=UNKNOWN` and a separate `proposed_numeric_reason` alongside the `existing_lab_status`, and it is not authorized to override either the legacy observer or current strict lab. Merely adding `NUMERIC_RESOURCE_LIMIT` to `_ALLOWED_CANDIDATE_REASON_CODES` in `ario_same_snapshot_comparator.py` would be misleading and would invite a compatibility bypass.

The new `numeric_reason_compatibility_view.compare_numeric_reason_views(raw)` is standalone research code: one already-allocated immutable `bytes` snapshot is passed to the *unchanged* `compare_snapshot` and separately to `diagnose_numeric_resource_bytes`. Both old and new paths receive identical source bytes; the view checks whether the proposed sidecar agrees about what the existing strict lab observed before offering a **non-authoritative metadata-only relation**.

## Proposed relation values

| Input | Existing comparator (unchanged) | Separate diagnosis | This view (NOT ADOPTED) |
|---|---|---|---|
| Syntactically valid integer exceeds actual CPython conversion cap | Usually `AGREE_UNKNOWN`: old lab `UNKNOWN/INVALID_JSON` | `UNKNOWN/NUMERIC_RESOURCE_LIMIT` | `PROPOSED_NUMERIC_RECLASSIFICATION`, diagnostic only |
| Small integer, ordinary event | `AGREE_OBSERVED` | `NO_NUMERIC_RESOURCE_OBSERVED` | `NO_NUMERIC_LIMIT_OBSERVED` |
| Existing lab accepts 21-digit integer but proposed cap is 20 | `AGREE_OBSERVED` remains historical | `UNKNOWN/NUMERIC_RESOURCE_LIMIT` | `PROPOSED_LOWER_NUMERIC_LIMIT`, no retrospective rejection |
| Incomplete LF or malformed suffix | `UNKNOWN`/other | Not safely numeric-only | `UNKNOWN_COMPARISON / NO_NUMERIC_DECISION` |
| `NaN`/float overflow, unknown schema | Original structural statuses only | Other invalid/unsupported | `UNKNOWN_COMPARISON / NO_NUMERIC_DECISION` |

`UNKNOWN_COMPARISON` remains the default for any inconsistent, unexpected or unclassifiable response. The new reason is **not** copied into the historical comparator's allowlist, and no source text, task, credential, host path, or digest is returned by this view.

## Pre-registered acceptance / falsification cases

1. **Legacy stability:** original old observer and strict lab are not modified. Their observed statuses and original hashes remain what they were for the same bytes. No V1 evidence, semantic IDs, `ACCEPTED` or `negates` rewritten.
2. **Exact same bytes:** no two independent physical file opens; input is immutable caller-owned bytes. A different real physical source/witness/custody cannot be established here.
3. **Typed report checks:** reject unfamiliar report values, unknown reason text, mismatch in old-lab status, and mismatch in old-lab reason, without echoing source content.
4. **Positive/negative controls:** 4300 vs 4301 decimal digits, nested oversized integer, huge digit string, explicit cap below old behavior, invalid JSON, nonfinite JSON floats, missing LF, larger-than-cap snapshots.
5. **Semantic firewall:** `source_authenticity=UNKNOWN`, `assessment=NOT_ASSESSED`, `memory_mutation=NONE`, `history_mutation=NONE`, `contract_adoption=NOT_ADOPTED` on every returned path. No `SUPPORTED`, no automatic memory input.

## Remaining questions and limitations

- Not a sandbox. Both imported parser functions are trusted research modules; malicious Python callbacks can perform side effects independently of returned metadata checks.
- Already allocated input bytes and repeated parsing use CPU and memory; no continuous deadline, process isolation or peak memory bound is established.
- More complex legacy event shapes and real-corpus compatibility are UNKNOWN; old `OBSERVED` remains historical and neither version judges a proposition true.
- The proposed `NUMERIC_RESOURCE_LIMIT` identifier, integer digit cap, exact numeric semantics, reason-code versioning and downstream consumer compatibility are **not approved**.
- No upstream Agent/Workflow, current observer, current strict lab, existing comparator, `ConsolidationEngine`, V2 memory ID, signer, governance or trust route is changed.

**MEMORY != TRUTH. CLAIM != PROOF. UNKNOWN is valid. NO MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO.**
