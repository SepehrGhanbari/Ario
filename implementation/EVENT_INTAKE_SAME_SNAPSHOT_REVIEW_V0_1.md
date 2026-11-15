# Ario — Same-Snapshot Differential Review (v0.1)

**Date:** 2026-11-15. **Status:** RESEARCH / OBSERVATIONS ONLY / NOT ADOPTED / NOT INTEGRATED / DRAFT-HOLD.
**Pinned code:** Draft PR #235 HEAD f4259c4ad59514fa6d06c90434b8287ae1c79246.
**Files examined:** implementation/ledger_observation_adapter.py (blob 39d16808ff7ebe976633c64fd2e3f30fc96ba2e3); implementation/event_intake_validator_lab.py (blob c5c77860909fce1f946b7cc16b3d8fb10f9f411c).

## Reproduction boundary

The same immutable Python bytes object was passed directly to the experimental lab and replayed to the unchanged legacy observer through a read-only in-memory Path adapter. The legacy observer made precisely one in-memory read in each case. No existing physical ledger, repository file, or history was changed. This compares parser and envelope behavior on identical bytes; it is NOT a test of the legacy observer's physical file-open safety, TOCTOU or independent provenance.

## Thirteen synthetic cases

| Case | Existing observer | Experimental lab | Interpretation |
|---|---|---|---|
| Healthy task start | OBSERVED | OBSERVED | Structural agreement |
| Healthy task finished | OBSERVED | OBSERVED | Structural agreement |
| Complete CRLF record | OBSERVED | OBSERVED | Same raw-byte digest |
| Duplicate root JSON key | OBSERVED | UNKNOWN | Reproduced parser-policy difference |
| Duplicate nested JSON key | OBSERVED | UNKNOWN | Reproduced parser-policy difference |
| Nonfinite NaN value | OBSERVED | UNKNOWN | Reproduced JSON strictness difference |
| TASK_FINISHED missing task_id | OBSERVED | UNKNOWN | Proposed stronger event-specific schema (not existing promise) |
| Unknown event kind | UNKNOWN | UNKNOWN | Explicit refusal in both |
| No final LF | UNKNOWN | UNKNOWN | Completed-record policy agreement |
| Lone CR between JSON objects | UNKNOWN | UNKNOWN | Framing agreement after earlier fix |
| Invalid UTF-8 | UNKNOWN | UNKNOWN | Refusal in both |
| Producer-valid 70 KiB goal | UNKNOWN | UNKNOWN | Raw-line ceiling; not evidence that the goal is false |
| JSON escape for unpaired Unicode surrogate | OBSERVED | OBSERVED | Potential Unicode interoperability review item, NOT claimed a proven violation |

**Nine status agreements, four differences.** For the four differences, the old parser's OBSERVED is not authenticated Evidence and the stricter lab's UNKNOWN is not an assertion of falsehood. For all three cases where both returned OBSERVED on normal source-shaped input, full-source SHA-256 values agreed exactly. The test also preserves a valid-prefix/invalid-suffix example where old OBSERVED contrasts with new UNKNOWN; it does not count as part of the thirteen-case matrix.

## Independent #235 review status and limits

CodeRabbit completed a COMMENTED source review of parent #233 and flagged (1) metadata PermissionError escaping the file reader, (2) potential blocking FIFO. Candidate #235 guarded both conditions and its exact-head Linux and Windows GitHub CI succeeded. CodeRabbit's distinct review request on #235 returned REVIEW RATE LIMITED, therefore no independent final review of #235 exists. This new comparison is performed by the project research assistant and is NOT a separate independent reviewer attestation.

The #235 file-reader uses final-path symlink checking, regular-file stat, POSIX O_NONBLOCK/O_NOFOLLOW where supported and fstat on the opened handle. These controls do not close ancestor-path symlinks, all path races, simultaneous file changes, resource retention or external source custody. The same-snapshot differential here does not establish physical-source security.

## Next decision gate

Keep #235 and this research branch DRAFT/HOLD. Obtain a completed independent review on exact #235 head; do not interpret a review request as approval. Decide whether a future versioned observer should reject duplicate keys and nonfinite JSON and whether historical missing IDs are UNKNOWN or accepted legacy envelopes. Do not silently rewrite past OBSERVED manifests.

A possible later, separately authorized read-only bridge would extract a bounded snapshot once, run both parsers on those same bytes and emit comparison-only AGREE/DISAGREE/UNKNOWN metadata, never source content or truth. This file adds no such runtime bridge. Owner approval and negative tests are required before any production change; #216 memory V2 semantics, #223 resource limits and #227 shared ledger policy remain HOLD.

**MEMORY ≠ TRUTH; CLAIM ≠ PROOF; REVIEW ≠ AUTHORIZATION. TRUST_ACTIVATION=NO_GO.**
