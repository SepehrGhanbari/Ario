# Ario Event-Intake / Observer Comparison Bridge — Proposal v0.1

**Status: PROPOSED / RESEARCH-ONLY / NOT INTEGRATED / NOT ADOPTED / NO MERGE.**  
**Date:** 2026-11-15. **Base:** Draft #233. **Related:** #216, #223, #227, #232 and #233.  
**Purpose:** Compare local event input to current observer behavior and a separate strict intake lab without silently accepting, discarding, or promoting evidence.

## Source-grounded differences

The existing ledger_observation_adapter.observe_ledger checks eight known event kinds, a nonblank timestamp, LF-terminated records, final-path symlink, and 8 MiB raw ledger / 64 KiB raw line / 5000 event limits. It does not reject duplicate JSON keys or NaN and does not enforce event-family-specific IDs.

The experimental event_intake_validator_lab rejects duplicate keys and nonfinite constants and checks source-shaped fields. It is NOT called by existing Agent, Workflow, observer or memory. CodeRabbit identified two path hazards in Draft #233: an unhandled PermissionError from symlink checking and a potential blocking open on a FIFO. A separate stacked candidate guards metadata access and verifies a regular, nonblocking POSIX descriptor. This fixes only the lab's read boundary, not the original observer.

## Proposed staged integration — not implemented

**Gate A: strictly read-only comparison.**
1. Obtain one bounded immutable byte snapshot from a permitted regular source. Fail closed on symlink, special input, permission failure, and unsupported shape. Document ancestor-symlink and TOCTOU limits.
2. Compare the old observer semantics and new strict lab semantics on the SAME bytes. A future read-only byte-input helper for the existing observer may be needed. Two separate file opens do not establish common custody; do not present them as equal snapshots.
3. Return only a diagnostic differential result: legacy observer status, research parser status, record counts, reason code, digest scheme, and AGREE/DISAGREE/UNKNOWN. No raw goal, text, private observation or unnecessary pathname should appear. Hashes can be linkable and should not be treated as anonymous.
4. If the components disagree, return DISAGREE/UNKNOWN as metadata. Do not silently invalidate old manifests, admit unsupported data, erase old events, or create semantic memory.

**Gate B: compatibility decision.**
1. Check all eight producer event kinds, malformed and valid controls, LF/CRLF, duplicate keys, NaN, missing IDs, unknown future kinds, long goals and rejection reasons.
2. Differentiate raw-line bytes, total raw-ledger bytes, compact-event bytes, per-call events, retained hashes, and each independently named limit. A producer-valid oversized goal must generate RESOURCE_LIMIT or UNKNOWN, never false "claim is untrue" or indefinite private retention.
3. Replay specifically authorized redacted historical fixtures only; production distributions are UNKNOWN until measured. Require a privacy/retention review for metadata and digests.
4. Require independent review of schema compatibility and the external-origin/custody limitations.

**Gate C: possible separately authorized runtime integration.**
A future, versioned observer adapter may compare or route records only after explicit owner adoption, reviewed false positives/negatives, full CI and a reversible compatibility plan. Its current public API must not be silently changed. It must never call memory ingestion, forge witnesses, infer selfhood, promote ACCEPTED to SUPPORTED, enable V2 node IDs or sign anything.

## Falsification matrix

| Case | Expected research behavior |
|---|---|
| Healthy LF/CRLF source-shaped records | Structural success only; no truth claim |
| Duplicate keys, NaN, missing required event ID | Explicit versioned disagreement rather than silent interpretation |
| Unknown future event kind | UNSUPPORTED_VERSION or UNKNOWN, not erase/auto-map |
| Producer-valid oversized goal | RESOURCE_LIMIT reason; no silent disappearance or indefinite storage |
| Incomplete line, lone CR separator, invalid UTF-8 | Reject / UNKNOWN, zero globally eligible records |
| Directory, symlink, FIFO without writer, permission denial | Bounded rejection, no blocking open and no raw path leak |
| File changes between two parser invocations | UNKNOWN, no assertion that differing reads are one witness |
| Missing semantic claim in a structurally valid event | A future NO_CLAIM_MAPPED, not fabricated assessment |
| Ambiguous legacy SEM or unspecified source digest scheme | UNKNOWN; separate protected decision #216 |

## Explicit boundary

The code under review is a standalone input-validator lab, not the bridge described here. No actual common-snapshot parser or integration, no durable rejection ledger, no independent source authentication, no Assessment, no V2 migration and no trust activation exist as a result of this proposal.

**Owner and independent review required before implementation. DRAFT/HOLD/PRODUCTION=NO_GO.**
