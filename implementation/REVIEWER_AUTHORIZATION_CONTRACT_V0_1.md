# Ario — Reviewer Authorization Contract v0.1

**Status:** PROPOSED / DESIGN ONLY / NO AUTHENTICATION IMPLEMENTED  
**Baseline:** `main` at `2bd117d2379f9c6ee752a97a1a2179d28fb4858d` (PR #61 merged)  
**Dependencies:** `ADMISSION_REVIEW_POLICY_V0_1.md` (ARP-0.1), `EVIDENCE_ADMISSION_CONTRACT_V0_1.md` (EA-0.1), `admission_review_evaluator.py`.  
**Scope:** Authentication and authorization *prerequisites* for an independently governed future review process.  
**Non-goals:** Evidence admission, M0 conversion, truth evaluation, ledger writing, or unilateral agent authority.

## 1. Fundamental distinctions

`CLAIMED_IDENTITY != AUTHENTICATED_IDENTITY != AUTHORIZED_ACTION != CORRECT_DECISION`

A `reviewer_id`, a role string, an `authorization_reference`, an agent's own assertion, or a signed message with no trusted key binding is **not** identity authentication. Identity authentication alone does not grant any permission; authorization for a narrowly defined action does not prove the reviewed claim or certify the quality of the decision.

The current `admission_review_evaluator.py` does **not** authenticate a reviewer or verify an authorization grant. Its `UNKNOWN` output for a structurally valid candidate is the required safe outcome, not a defect to be bypassed.

## 2. Actors and trust boundaries

- **Proposer:** presents candidate dossier and proposed support relation; never grants itself review authority.
- **Reviewer principal:** the individual or process whose identity would be independently authenticated.
- **Authorization issuer:** a separately designated governance authority able to grant only declared review permissions. This role is **not yet instantiated or trusted**.
- **Verifier:** a bounded component that might later check a trusted identity binding and a grant against explicit rules. No such verifier exists in RAC-0.1.
- **Policy maintainer:** updates rule versions through explicit review; cannot silently change earlier decisions or retroactively expand grants.

A person acting as both proposer and reviewer of the same candidate presents a separation-of-duties conflict. Different labels on the same principal do not establish independence. A human clicking “approve” is a governance action, not independent evidence that the historical event occurred.

## 3. Future authorization record (proposed only)

An externally issued, reviewable authorization envelope SHOULD specify:

1. `authorization_contract_version`: exact version identifier, initially `RAC-0.1`.
2. `grant_id`: unique identifier within the trusted issuer's namespace.
3. `issuer_id` and `issuer_trust_basis`: who grants the permission and how the issuer's authority is anchored outside the candidate and ledger.
4. `principal_id` and `identity_binding_method`: the authenticated reviewer and a verifiable identity-to-principal binding.
5. `permitted_action`: an explicit review-only action, never `ADMIT_EVIDENCE`, `M0_PASS`, or `ASSERT_TRUTH`.
6. `policy_version` and `claim_scope`: narrow applicable review policy and claim category/scope.
7. `candidate_binding`: exact dossier digest under an explicitly versioned canonical serialization, or an independently verified equivalent; unspecified canonicalization remains `UNKNOWN`.
8. `validity_start`, `validity_end`, and `verification_time_basis`: independently interpretable time window, with trusted clock assumptions disclosed.
9. `revocation_reference` and `revocation_check`: an authoritative, current revocation state or an explicit `UNKNOWN`.
10. `separation_of_duties`: known relationship of proposer, source operator, issuer, and reviewer; unresolved conflicts remain visible.
11. `signature_or_attestation` and `verification_result`: signed bytes alone are insufficient without a trusted key/issuer and binding.
12. `grant_limitations` and `rule_version`: explicit constraints and the exact verification policy used.

A field being present, correctly shaped, or self-described as verified is never sufficient for authentication.

## 4. Invariants

**RAC-01 — No self-authorization.** Neither the candidate, ledger, originating agent, nor reviewer may mint trusted review authority for their own case.

**RAC-02 — Trust anchor required.** The authority and identity bindings must resolve to separately trusted, versioned anchors; absent anchors produce `UNKNOWN`.

**RAC-03 — Typed role separation.** Authentication, action authorization, evidence sufficiency, and claim assessment remain distinct typed conclusions.

**RAC-04 — Least privilege.** A grant authorizes only the named action, policy version, candidate scope, and permitted time window; no wildcard escalation.

**RAC-05 — No implicit admission.** Even fully verified *future* review authorization authorizes only an eligible review step. EA-0.1 and ARP-0.1 still forbid `ADMITTED`.

**RAC-06 — Candidate binding.** Review grants must not migrate across altered dossiers, ledger digests, claim scopes, or records; canonical digest rules cannot be invented retroactively.

**RAC-07 — Verifiable issuer.** A declared issuer, untrusted public key, unchecked signature, local account name, or Git commit author string does not establish a trust anchor.

**RAC-08 — Revocation-aware.** Missing, stale, unverifiable, or conflicting revocation information blocks an affirmative authorization decision; no default `ACTIVE`.

**RAC-09 — Explicit time limits.** Expired, not-yet-effective, clock-ambiguous, or unverifiably dated grants cannot be treated as valid.

**RAC-10 — Separation-of-duties disclosure.** Identical or inadequately distinguished source/proposer/reviewer/issuer roles cannot satisfy independent-review requirements merely by changing identifiers.

**RAC-11 — No historical rewriting.** Grants and revocations form a versioned append-only history; later decisions supersede earlier entries by reference, never erase them.

**RAC-12 — Deterministic failure.** Malformed, duplicate, colliding, unsupported-version, or wrong-scope inputs yield typed refusal or `UNKNOWN`, with a specific rule ID; never fall through to authority.

**RAC-13 — No semantic elevation.** Valid authorization neither authenticates historical ledger events nor supplies independent corroboration or establishes truth.

**RAC-14 — Bounded implementation.** Future verifier must use explicit size/count limits, read-only input processing, stable rules, and negative tests; no privileged side effects.

## 5. Proposed authorization-check outcomes

| Outcome | Meaning | Available in RAC-0.1 |
|---|---|---|
| `NOT_CHECKED` | No independent verification performed | Specification-level default |
| `UNKNOWN` | Identity, authority, binding, time, or revocation cannot be verified | Required safe outcome |
| `REJECTED` | A declared requirement demonstrably fails | Future checker only |
| `VERIFIED_FOR_REVIEW_ONLY` | Independent issuer/identity/action/scope/time/revocation checks all passed | **NOT IMPLEMENTED; FORBIDDEN TO ASSERT IN RAC-0.1** |

`VERIFIED_FOR_REVIEW_ONLY` is not evidence admission. No status in RAC-0.1 permits `ADMITTED`, `ACCEPTED_AS_EVIDENCE`, an M0 verdict, or a truth conclusion.

## 6. Mandatory adversarial scenarios for later verification

| Case | Condition | Required behavior |
|---|---|---|
| RAC-T01 | Reviewer supplies only their name and `human` role | `UNKNOWN` |
| RAC-T02 | Agent grants itself authority for its own candidate | Refuse self-authorization |
| RAC-T03 | Well-formed grant but issuer has no trusted anchor | `UNKNOWN` |
| RAC-T04 | Cryptographic signature present but signer binding untrusted | `UNKNOWN` |
| RAC-T05 | Grant valid for dossier A presented for dossier B | Reject wrong binding |
| RAC-T06 | Grant permits review but request asks for `ADMITTED` | Reject unauthorized escalation |
| RAC-T07 | Valid principal, action outside grant scope | Reject wrong scope |
| RAC-T08 | Expired or not-yet-active grant | Reject effective-time violation |
| RAC-T09 | Revocation status missing or stale | `UNKNOWN` |
| RAC-T10 | Grant explicitly revoked by trusted issuer | Reject revoked grant |
| RAC-T11 | Same principal masquerades as distinct proposer and reviewer | Do not infer independence |
| RAC-T12 | Duplicated or conflicting grant IDs | `UNKNOWN` or reject; never choose favorable grant |
| RAC-T13 | Review succeeds but external execution claim is uncorroborated | No truth/evidence escalation |
| RAC-T14 | Authorization revoked later | Preserve original record and append the revocation |
| RAC-T15 | Unknown canonical dossier serialization | Do not report verified binding |
| RAC-T16 | Validly authorized human agrees with candidate | Procedural permission only; admission remains `NOT_EVALUATED` |

## 7. Phased delivery and gates

**Gate A — Document only:** Add this proposed contract in a new file, leaving the ledger, archives, M0 core, EA-0.1 and ARP-0.1 semantics unchanged.

**Gate B — Read-only authorization *preflight*:** A separate future module may validate shapes and refuse unsupported self-assertions; when real trust anchors or canonical binding are absent it MUST return `UNKNOWN` or `NOT_CHECKED`. Passing structure tests is not verification.

**Gate C — Independent verification design:** Before any affirmative review authorization, explicitly approve an issuer trust anchor, enrollment/key binding method, grant scope, clock model, revocation authority, canonical dossier serialization, and separation-of-duties checks. This requires new, separately approved specifications and adversarial tests.

**Gate D — Limited ARP integration:** A separately approved future change may pass a genuinely verified, typed review-only authorization outcome to the review evaluator. No change to EA-0.1 admission prohibition, M0 evidence types or epistemic verdicts is implied.

## 8. Unresolved decisions

No trusted authorization issuer, identity enrollment provider, trusted key store, canonical dossier digest standard, trusted clock, revocation registry, or independent corroborating evidence provider has yet been selected or implemented. **These are intentionally UNKNOWN.** Do not implement a pretend verifier that relies on any self-declared string, static hard-coded “trusted reviewer”, or agent-supplied grant.

**Acceptance statement:** RAC-0.1 is a reviewable design proposal, not proof that any reviewer has been authenticated or authorized. Approval of this *document* never confers a real-world privilege.
