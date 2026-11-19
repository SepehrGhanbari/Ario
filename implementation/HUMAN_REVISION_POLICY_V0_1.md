# Human Revision Policy v0.1 — non-persistent prototype

**Status:** experimental helper and synthetic tests only. Not a production memory feature.

## Purpose

Classify whether a supplied correction event is eligible for scoped review, while preserving distinctions among a historical record, a current interpretation and a future-use instruction.

The helper does not authenticate a person. EXTERNALLY_VERIFIED is an assertion supplied by an upstream authority mechanism; this module does not verify that mechanism. It does not persist, delete, redact, mutate, or retrieve personal data.

## Decision states

| Result | Meaning |
|---|---|
| ACCEPTABLE_FOR_SCOPED_REVIEW | Supplied external-authority status and exact scope permit review only |
| REJECTED | Explicitly invalid authority, replay, or scope mismatch |
| UNKNOWN | Required context or authority is missing/unknown |

A reviewable correction may return DO_NOT_USE_SUPERSEDED_INTERPRETATION_IN_THIS_SCOPE. This is a caller-facing policy recommendation, not an applied mutation or guaranteed system-wide cache invalidation.

## Required event fields

- event_id: caller-supplied replay identifier.
- target_reference: prior interpretation being corrected.
- subject_reference: subject to whom the correction pertains.
- scope: exact scope of the requested future-use change.
- new_interpretation_reference: reference to the replacement interpretation.
- authority_status: externally supplied authority classification.

There is deliberately no explanation/reason field. A person need not justify a correction.

## Safety and privacy boundaries

- Historical records are not modified.
- No personal data is stored.
- No deletion, retention, restriction, or redaction policy is decided.
- No authentication or identity verification is performed.
- No third-party authority is inferred.
- No correction applies outside its exact declared scope.
- Unknown authority remains UNKNOWN.
- No identity, psychological, consciousness, or true-self verdict is produced.

REVISION is not ERASURE, but this does not imply permanent retention. Any future persistence requires separate privacy/legal review covering retention limits, erasure, restriction, redaction, access control and stale-cache invalidation.

## Tests

From implementation/: python -m pytest tests/test_human_revision_policy.py

The synthetic suite covers authorized-for-review, unknown/unverified authority, scope mismatch, replay, missing context, third-party assertions, no-explanation correction, and non-persistence/no-mutation guarantees.

## Decision gate

Before integration with memory/consolidation, compare with Issue #210 and existing RECORDED/ACCEPTED semantics. If the helper duplicates or conflicts with those contracts, retain the proposal as research-only. Do not connect it to production memory without separately reviewed authorization, privacy, retention and deletion design.
