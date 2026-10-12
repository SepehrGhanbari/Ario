# Ario — Human-Governed Trust Anchor & Authorization Verification Contract v0.1

**Status:** PROPOSED — DESIGN ONLY / NO ACTIVE TRUST ROOT / NO KEYS GENERATED
**Baseline:** `main` at `720faebba96b332b75c55510e9067ed9485bf664` (PR #62 merged and locally synchronized)
**Dependencies:** `REVIEWER_AUTHORIZATION_CONTRACT_V0_1.md` (RAC-0.1), `reviewer_authorization_preflight.py`, `ADMISSION_REVIEW_POLICY_V0_1.md` (ARP-0.1), `EVIDENCE_ADMISSION_CONTRACT_V0_1.md` (EA-0.1).
**Scope:** Define the initial trust-root governance and future technical verification conditions for **review-only** authority.
**Non-goals:** Truth arbitration, evidence admission, identity-as-consciousness claims, active key management, M0 conversion, historical ledger mutation, and autonomous agent credential issuance.

## 1. Approved governance decision

For the initial phase, the project founder and human overseer is the **sole designated bootstrap trust-root custodian**. This is a *governance designation*, not evidence of the custodian's infallibility or the truth of any claim. No other person or agent receives signing or delegation authority by default. The custodian may later delegate narrowly scoped authority through explicit, auditable, revocable procedures. No permanent one-person dependency is intended.

**Foundational boundary:**

`CLAIMED_IDENTITY != AUTHENTICATED_IDENTITY != AUTHORIZED_ACTION != CORRECT_DECISION != TRUTH`

A valid signature demonstrates control of the corresponding private key over specified bytes, assuming correct cryptographic verification and a trusted public-key binding. It does **not** independently establish the natural person's identity, the authenticity of historical ledger events, evidence independence, or the merits of a review.

## 2. Bootstrap trust model

1. **Human custodian:** controls the initial signing key through an out-of-repository environment. The signing private key and recovery secrets MUST never be stored in the Ario repository, ledger, artifacts, CI secrets exposed to untrusted jobs, or agent-accessible working directories.
2. **Offline or constrained key initialization:** generation and secure-storage process must be separately reviewed and explicitly approved **before execution**. This document does not generate a key or select a particular hardware product.
3. **Public trust-anchor enrollment:** a verifier must begin with a specifically approved public-key fingerprint or immutable public-key identity. A key supplied inside the candidate or authorization request MUST NOT appoint itself as trusted.
4. **Enrollment confirmation:** the human custodian explicitly checks and approves the fingerprint through a separate trusted procedure; this is the root-of-trust ceremony, not a cryptographic proof of personal identity.
5. **Independent verifier:** reads trusted anchor configuration and a bounded signed grant; verifies cryptographic integrity and the exact review-only permission; cannot mint, sign, or elevate grants.
6. **No automatic Ario authority:** Ario, Codex and other agents may prepare proposals and unsigned requests but do not acquire access to signing secrets or self-issue reviewer permissions.

**Explicit open question:** Which concrete hardware/software key store, initial enrollment medium, and recovery custodian are acceptable? **UNDECIDED**; no production activation until resolved.

## 3. Signature and canonicalization profile — design requirements

A future implementation MUST use one fixed, documented, versioned signature profile. The initial *candidate* is Ed25519 with versioned canonical JSON serialization (e.g. an explicitly adopted RFC 8785 / JCS profile), but **neither algorithm nor canonicalization is activated by this proposal**.

The implementation specification must define: exact UTF-8 encoding, canonical serialization and duplicate-key rejection, signature domain separation (e.g. `ARIO-REVIEW-GRANT-V1`), algorithm identifiers, key IDs/fingerprints, signed field coverage, deterministic parser constraints, allowable clock representation, and cross-platform reproducibility. Reject unknown critical fields, malformed encodings, algorithm substitution, and signature ambiguity. Canonicalization tests must cover Unicode, number types, ordering, escaped strings and duplicate keys; do not assume that an ordinary `json.dumps()` or PowerShell `ConvertTo-Json` result is stable signed material.

Public-key pinning and key rotation must be separate from ordinary applicant-controlled inputs. A syntactically valid signature with an untrusted key remains `UNKNOWN`, not `VERIFIED`.

## 4. Future review-only grant envelope

The signed portion of a future grant MUST bind at least:

- `grant_version`, `grant_id`, `issuer_key_id`, `subject_principal_id`, `subject_identity_binding_ref`;
- `allowed_action`: **exactly** `REVIEW_CANDIDATE` for this profile; never `ADMIT_EVIDENCE`, `M0_PASS`, `ASSERT_TRUTH`, or `ISSUE_ROOT_GRANT`;
- `policy_version`, `candidate_digest_profile`, `candidate_digest`, `claim_scope` and optional stricter permitted claim categories;
- `not_before`, `expires_at`, `issued_at`, applicable clock/time policy and `audience` (Ario deployment/verifier context);
- `delegation_allowed`: `false` for v0.1, `nonce` or equivalent replay-control field, `revocation_registry_id`, and required reviewer/proposer separation constraints;
- explicit limitations and signature-profile version.

All fields must be present, versioned, typed and covered by the signature. No wildcard scope and no implicit unlimited validity. A grant naming a principal is not enough: the verifier must also authenticate that a review action is actually initiated by the authorized principal, through a separately approved identity/session-binding protocol. Possession of a copied signed grant alone must not suffice.

## 5. Revocation, rotation and recovery

- **Revocation first:** an affirmative decision requires a fresh, authenticated revocation status tied to the issuer and grant. Missing, unavailable, stale, contradictory or untrusted revocation data leads to `UNKNOWN`; explicitly revoked grants lead to `REJECTED`.
- **No silent time assumptions:** an independently sourced, documented verification clock and maximum acceptable skew are required. Untrusted caller timestamps must not establish validity.
- **Root rotation:** a new root must be enrolled through a separately approved ceremony, not merely signed by an already compromised root. Preserve old fingerprints, effective times and superseding events as append-only audit history.
- **Emergency freeze:** a human-governed process must suspend grant verification when a root is suspected compromised; fail closed until independent recovery.
- **Loss/recovery:** losing the sole root must not trigger a fabricated replacement or a bypass. Until a new root has been independently enrolled, review authorization remains `UNKNOWN`/unavailable. Design a future succession or multi-party recovery path before production deployment.
- **Audit trail:** append grant creation, verification, revocation, rotation and correction records; never overwrite old records. A local append-only log by itself does not prove external historical authenticity.

## 6. Normative invariants

**TA-01 — Human-governed bootstrap, not human truth sovereignty.** The initial custodian controls delegation of review permission but cannot certify facts by fiat.

**TA-02 — Private-key isolation.** No private keys, seed phrases or recovery material are accessible to Ario, Codex, the repository, or ordinary agent execution.

**TA-03 — No self-enrollment.** Trust anchors cannot be accepted merely because they are bundled with a grant, request, candidate or model output.

**TA-04 — Review-only least privilege.** All verified grants are constrained to `REVIEW_CANDIDATE`; no authority to admit evidence, invoke M0 conclusions, edit history or delegate authority.

**TA-05 — Subject binding.** A verified signature and valid grant do not prove the current requester is the authorized human; authenticate the actual principal separately.

**TA-06 — Candidate and scope binding.** Changes to dossier content, ledger digest, claim scope, policy or verifier audience invalidate a grant rather than silently migrating it.

**TA-07 — Fresh revocation and trusted time.** Missing trustworthy revocation or clock status prevents an affirmative authorization outcome.

**TA-08 — Separation of duties.** The same source/proposer/reviewer cannot count as independent corroboration merely because the reviewer has a valid grant.

**TA-09 — No evidence promotion.** `VERIFIED_FOR_REVIEW_ONLY` (if implemented later) never implies `ADMITTED`, valid M0 `Evidence`, `Assessment`, `PASS`, or truth.

**TA-10 — Versioned cryptography.** Accepted signatures require one fixed profile with canonicalization, key-binding, domain separation and strict parser rules; any unknown profile fails closed.

**TA-11 — Explicit rollback/freeze.** Revocation, root compromise and unavailable trust services must have auditable fail-closed handling without hidden bypasses.

**TA-12 — History preservation.** Changes of grants, keys and governance are append-only and explicitly supersede earlier versions; do not silently alter recorded past decisions.

**TA-13 — No privilege by workflow success.** CI PASS, task COMPLETED, reviewer recommendations and human clicks do not create a trusted issuer or admissible witness.

**TA-14 — Contestable governance.** Every grant and review action must be open to documented challenge, revocation and policy revision. No claim of ethical infallibility follows from human governance.

**TA-15 — Bounded implementation.** All prospective parsers and checks have explicit size/count limits and adversarial tests, avoid secrets in logs, and perform no privileged writes during verification.

## 7. Authorization outcomes

| Outcome | Meaning | v0.1 availability |
|---|---|---|
| `NOT_CHECKED` | No independent trust check executed | Existing preflight semantics |
| `UNKNOWN` | Trust anchor, identity, signed binding, clock or revocation cannot be established | Required safe result |
| `REJECTED` | A specific supported contract violation is detected | Existing preflight / future verifier |
| `VERIFIED_FOR_REVIEW_ONLY` | All separately implemented, approved grant and principal checks passed | **NOT IMPLEMENTED, MUST NOT BE PRODUCED YET** |

All outcomes remain distinct from `ADMITTED`, `M0_PASS`, and semantic truth.

## 8. Adversarial verification test matrix — future implementation

| ID | Attack / condition | Expected boundary |
|---|---|---|
| TA-T01 | Public key arrives inside request as its own root | No trusted enrollment; `UNKNOWN` |
| TA-T02 | Correct signature by untrusted key | `UNKNOWN` |
| TA-T03 | Forged or altered grant body | `REJECTED` |
| TA-T04 | Duplicate JSON keys / unstable canonicalization | `REJECTED` |
| TA-T05 | Unsupported algorithm or signature profile | `REJECTED`/`UNKNOWN`, never verified |
| TA-T06 | Grant allows `ADMIT_EVIDENCE` | `REJECTED` |
| TA-T07 | Candidate digest or claim scope changes | `REJECTED` |
| TA-T08 | Expired or not-yet-active grant | `REJECTED` under trusted clock |
| TA-T09 | Revocation source unavailable or stale | `UNKNOWN` |
| TA-T10 | Authenticated issuer has revoked grant | `REJECTED` |
| TA-T11 | Copied signed grant used by an unbound caller | Not verified for caller |
| TA-T12 | Valid grant reused against another deployment | `REJECTED` by audience |
| TA-T13 | Agent signs its own grant using generated key | No trust-anchor elevation |
| TA-T14 | Reviewer is also proposer | No independence or self-evidence upgrade |
| TA-T15 | Root key lost or suspected compromised | Freeze; fail closed, preserve history |
| TA-T16 | Root rotation without independent enrollment | No automatic successor root |
| TA-T17 | Human with valid grant confirms unsupported event | Review authority only, no semantic truth |
| TA-T18 | Two reviewers approve same source bytes | No independent observation inflation |
| TA-T19 | Signature passes but authenticated subject binding absent | `UNKNOWN` |
| TA-T20 | Current code sees an unsigned but well-formed record | Preflight result remains `UNKNOWN`/`NOT_CHECKED` |

## 9. Delivery stages and explicit gates

**Gate A — Document only (current):** Add this proposed design as a new file. No keys, enrollment, implementation, M0 changes or ledger mutation.

**Gate B — Cryptographic profile specification (separate review):** Specify chosen algorithms, pinned-root ceremony, signed envelope serialization, exact byte examples and cross-platform test vectors. Do not generate a production signing key.

**Gate C — Independent verification implementation (separate authorization):** A read-only verifier may validate the pin, signature, exact scope, subject binding, time and fresh revocation state. Until each is actually implemented and independently exercised, do not output `VERIFIED_FOR_REVIEW_ONLY`.

**Gate D — Human-approved key enrollment / activation (separate explicit user approval):** Generate and enroll a production key through a trusted, auditable process with backup/recovery and freeze plans. Never ask the custodian to paste private keys, secret passphrases or recovery phrases into chat.

**Gate E — ARP integration (new review and PR):** Pass a typed, independently verified review-only authorization result to the existing evaluator. No automatic Evidence admission or truth upgrade. Retest the M0 F10/F11/F12/F15 firewall.

## 10. Acceptance and unknowns

The human-governed initial custodian arrangement is approved as a design direction. The exact trust-anchor storage, cryptographic profile, issuer enrollment method, verifier deployment, clock source, revocation mechanism, second-person recovery, and future delegation policies remain **UNDECIDED**. They must not be filled silently or simulated as fact.

**Acceptance boundary:** This document is a proposed contract, not evidence of an active trusted root or an implemented authentication system. A signature can authorize a process only under the independently implemented controls; it cannot create truth.
