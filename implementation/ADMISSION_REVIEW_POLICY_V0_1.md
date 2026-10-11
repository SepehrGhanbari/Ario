# Ario — Admission Review Policy v0.1

**Status:** PROPOSED — DESIGN ONLY; NO ADMISSION AUTHORITY GRANTED  
**Baseline:** `main` at `642eb38c192da1629490ca79a91c12a958e03309` (PR #60 merged)  
**Depends on:** `EVIDENCE_ADMISSION_CONTRACT_V0_1.md` (EA-0.1), `candidate_dossier_builder.py`, M0 F10/F11/F12/F15 boundaries.  
**Change type:** additive specification; no runtime, schema, M0, ledger, archive, or historical mutation.

## 1. Purpose

Define a versioned, reviewable boundary between a candidate dossier and a *possible future* admission decision. A dossier created from verified local ledger bytes remains **a candidate**, not admissible M0 `Evidence`. This policy specifies what a reviewer must inspect, which outcomes are possible, and what cannot be concluded.

The EA-0.1 contract explicitly forbids `ADMITTED` in v0.1. This policy respects that prohibition: **no invocation or manual acknowledgement of this policy can produce `ADMITTED`, construct M0 `Evidence`, or issue an M0 verdict**. A later separately authorized version must define and test admission before any such outcome exists.

`OBSERVED != CANDIDATE != ADMITTED_EVIDENCE != ASSESSMENT != TRUTH`

## 2. Roles and authority

- **Observer:** adapter/bridge; checks bounded ledger bytes and manifest consistency only. Cannot approve anything.
- **Proposer:** agent or human stating a `claim_id`, `claim_scope`, and `proposed_support_relation`; has no approval power over their own proposal.
- **Reviewer:** explicitly identified human or separately authorized review process, independent of the particular proposal decision. Identity and authority are **declared, not authenticated by the existing ledger**. Being the proposer, reviewer, and data source in one chain cannot generate independent corroboration.
- **Policy maintainer:** changes future policies through reviewed, versioned changes; cannot retroactively rewrite historical decisions.

**RP-01 — Explicit authorization:** Review requires a versioned authorization record outside candidate content. Absent or unverifiable authorization: `UNKNOWN`, not implicit approval. In v0.1 even a valid human approval is only a *review recommendation*, never evidence admission.

**RP-02 — No self-approval:** Agent proposals and outputs cannot authorize their own evidentiary status. A human acknowledgement is a governance action, not independent proof of the reported event's real-world occurrence.

## 3. Review input envelope (future representation, not a current API)

A review request MUST declare all of the following, without altering its candidate dossier:

1. `policy_version`: exact string `ARP-0.1`.
2. `candidate`: an immutable snapshot of the EA-0.1 candidate dossier, including full ledger SHA-256, line number, event type, and record SHA-256.
3. `candidate_digest`: canonical serialization method and digest, or `UNKNOWN` if no serialization is defined. Do not substitute an arbitrary JSON hash for a stable canonical digest.
4. `reviewer_id`, `reviewer_role`, `authorization_reference`: declared identities and authority, explicitly separated from evidence.
5. `requested_claim_id`, `requested_claim_scope`, `requested_support_relation`: bounded request; must not silently change the proposal.
6. `corroboration_refs`: each externally supplied source with source type, provenance, observation scope, and relationship to the ledger record; an empty set is legitimate and cannot be interpreted as independent support.
7. `review_rule_ids`: exact versions of rules applied, and a written basis for each assessment of sufficiency.
8. `limitations`: explicit origin, time, independence, and semantic constraints.
9. `recorded_at`: reviewer's declared clock reading; not independently authenticated merely by inclusion.
10. `decision`: one of the permitted review-only outcomes below.

Malformed, missing, ambiguous, or colliding references never default to acceptable. Field names describe a future interface; **none is implemented or validated by this document**.

## 4. Allowed review-only outcomes

| Outcome | Meaning | Admission authority |
|---|---|---|
| `NOT_EVALUATED` | Request has not been reviewed | None |
| `UNKNOWN` | Required facts, identity/authority, or corroboration cannot be established | None |
| `REJECTED` | A stated structural/policy requirement demonstrably fails | None |
| `NEEDS_CORROBORATION` | Material is traceable but insufficient for a particular requested claim | None |
| `REVIEWABLE` | Minimum review envelope is well formed; a reviewer may inspect it | None |
| `RECOMMENDED_FOR_FUTURE_REVIEW` | A separately identified reviewer recommends further evaluation under a future admission contract | None |

**`ADMITTED`, `ACCEPTED_AS_EVIDENCE`, `M0_PASS`, or any truth verdict are FORBIDDEN in ARP-0.1.** A human may approve procedural progression, but this does not change the candidate's `admission_decision=NOT_EVALUATED` or override EA-0.1.

## 5. Required review checks

**RP-03 — Fresh snapshot binding.** When verification is requested, compare against a fresh bounded ledger read; bind every conclusion to its exact SHA-256. A changed file invalidates reuse of prior matching-claim assertions.

**RP-04 — Typed reference integrity.** Require exact resolution of the line and record digest. Do not cast reported statuses, `AuditResult`s, or verdicts to evidence. Preserve F11/F15 protections.

**RP-05 — Claim proportionality.** Distinguish `the ledger reports WORKFLOW_FINISHED` from `the workflow met its objective`. The latter requires separate, relevant observations and review not supplied by ledger status text alone.

**RP-06 — Source independence.** Adapter output, Bridge verification, Builder dossier, and later review of the same bytes form one dependency lineage. Repetition, hashes, signatures without verified signers, or multiple reviewers do not inherently create independent world observations.

**RP-07 — Provenance and time.** Check actual authentication method and its limits. Unsupported author attribution, event occurrence time, and cross-epoch continuity remain `UNKNOWN`.

**RP-08 — Failure preservation.** Keep `UNKNOWN`, `REJECTED`, incomplete records, and contradictory inputs visible; no subset-only success that conceals failure.

**RP-09 — Determinism and versioning.** A future deterministic checker must report rule IDs, inputs, and stable decision boundaries; subjective reviewer judgements are recorded as judgements, not falsely deterministic facts.

**RP-10 — Append-only review trail.** Future review records should link candidate digest, reviewer authorization reference, policy version, outcome, and rationale. Amendments append superseding decisions; never overwrite prior records. No review trail writer is authorized by v0.1.

**RP-11 — Escalation barrier.** Neither review eligibility nor a recommendation is an M0 `Evidence` object, `Assessment`, `AuditResult`, or ontology-level conclusion.

**RP-12 — Separation of duties.** A future admission system requires a separately versioned decision authority and an explicit, auditable conversion contract; this policy alone supplies neither.

## 6. Adversarial acceptance matrix for future implementation

| ID | Input | Required outcome |
|---|---|---|
| ARP-T01 | Verified candidate, no corroboration | Reviewable at most; never admitted |
| ARP-T02 | Agent proposing its own `COMPLETED` status as proof | Reject claimed semantic upgrade / request corroboration |
| ARP-T03 | Same bytes echoed by adapter, bridge and builder as three sources | Treat as one dependent lineage |
| ARP-T04 | Candidate locator/digest mismatches live ledger | Reject or UNKNOWN; no promotion |
| ARP-T05 | Unknown or missing reviewer authority | UNKNOWN; no authorization implied |
| ARP-T06 | Human approval without corroborating source | Procedural approval only; `NOT_EVALUATED` admission stays unchanged |
| ARP-T07 | Prior M0 PASS offered as independent evidence | Wrong kind; preserve F11/F15 barrier |
| ARP-T08 | Two independent source *claims* but shared upstream event | Do not assume independence |
| ARP-T09 | Source timestamp treated as authenticated occurrence time | UNKNOWN time/authenticity |
| ARP-T10 | Evidence requested for stronger claim than dossier scope | Reject expansion or require separate, explicit review |
| ARP-T11 | Bad or contradictory provenance entries | REJECTED/UNKNOWN with explicit reason |
| ARP-T12 | Review recommendation fed to M0 `Evidence` directly | Forbidden; no conversion |
| ARP-T13 | Reviewer changes an earlier decision in-place | Refuse overwrite; append new version only |
| ARP-T14 | Proposal includes `ADMITTED` despite EA-0.1 | Reject unsupported state |

## 7. Planned gates (not yet performed)

**Gate A — Document review:** Approve this proposal's terminology and conflict handling; keep status `PROPOSED` until formal governance acceptance.

**Gate B — Read-only review evaluator:** New independent module and focused adversarial tests may classify review requests using only review-only outcomes. Must never set `ADMITTED`, modify dossiers, write to ledger, or call M0. Any reviewer identity or authorization validation not independently supplied must remain UNKNOWN.

**Gate C — Future admission decision:** Design separate versioned criteria, authenticated roles, independence/provenance requirements and a genuinely explicit admission decision. Requires its own approval; cannot be inferred from Gate B tests passing.

**Gate D — Future M0 conversion:** Separate narrow mapping to typed M0 `Evidence`/`Assessment`, preserving F10/F11/F12/F15 and full regression gates; not authorized by ARP-0.1.

## 8. Explicit open questions

- Which external authority can authenticate reviewer identity and permit review? **UNKNOWN.**
- Which independent sources can authenticate historical ledger origin and execution? **UNKNOWN.**
- What specific claim types, evidence thresholds, revocation procedures and appeals will later qualify for actual admission? **NOT SPECIFIED.**
- How should canonical dossier serialization be defined for stable signing and integrity? **NOT SPECIFIED.**

No defaults may silently fill these gaps. This document is a review policy proposal, not proof of implementation or authorization to admit evidence.
