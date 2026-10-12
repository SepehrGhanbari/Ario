# ARIO TB-004 v0.2 — Evidence-bound evaluation identity and declared prior-chain validation

**State:** ISOLATED SYNTHETIC REPAIR CANDIDATE — no production authority and not merged.
**Exact starting point:** `SepehrGhanbari/Ario` `main` at `dc66dcdc5380e04ba225e09ec799d84d1ab472b8`.
**Change discipline:** Three **new** implementation paths only; legacy TB-004 v0.1, M0, agent, governance, archive, signer, and tracked/untracked user files remain untouched.

## 1. Threats and explicit boundaries

This version addresses **local synthetic evidence identity** and **declared prior-evaluation chain consistency**. It does **not** authenticate a historian, a controller, a prior record's custody, a trusted timestamp, a witness, a signing key, an externally retained head, any event's truth, or the completeness of historical records. `LAB` is an attacker-reproducible **string**, not a credential; a fully compromised controller can construct a completely self-consistent alternative case.

`UNKNOWN`, `NOT_ESTABLISHED`, `NOT_EVALUATED` and `INCONCLUSIVE` remain the correct results for real-world identity, production custody, historical truth, production continuity, cryptographic authentication, evidence admission and authorization. Even a v0.2 `CONDITIONALLY_USABLE_FOR_NAMED_COMPARISON` is a bounded laboratory condition only.

## 2. Versioning and compatibility

- **New module:** `implementation/witness_compromise_recovery_experiment_v0_2.py`.
- **New tests:** `implementation/tests/test_witness_compromise_recovery_experiment_v0_2.py`.
- **New contract:** this document.
- **New profile:** `ARIO-WITNESS-COMPROMISE-EXPERIMENT-0.2`.
- **New policy:** `ARIO-TB4-LAB-POLICY-0.2`.
- **New report kind:** `EXPERIMENTAL_COMPROMISE_RECOVERY_V0_2`.
- **New evaluation namespace:** `TB4-V02-EVAL-` plus all 64 lowercase SHA-256 hex digits.
- **No silent v0.1 history upgrade:** v0.1 prior-evaluation policy and old arbitrary evaluation IDs are rejected from v0.2 chains. No historical artifact or v0.1 identifier is rewritten. A future migration protocol would require a separately approved artifact and audit design.
- All input collections, epoch transition and compromise/recovery rules from v0.1 are preserved except the stricter handling of prior-evaluation histories and the above result metadata.

## 3. Evidence-bound assessment identity

V0.1's `evaluation_id` hashed `artifact/epoch/sequence/property/policy/usability/supersedes/reasons`, but **omitted observation IDs, frozen-reference IDs, their checkpoint digests, support references, compromise window details, proposal details and controller-completeness declarations**. Distinct declared evidentiary cases with the same outward status and reason codes could therefore share an ID.

V0.2 computes:

1. `evidence_digest = SHA256(CANONICAL({"domain":"ARIO-TB4-CASE-V0.2","case":asdict(case)}))`. CANONICAL uses compact sorted-key ASCII JSON, forbids NaN, and sorts each bounded input collection by the *unique declared* kind-specific ID. It includes all fields of **the full synthetic RecoveryCase**, including its lab completeness declarations, the expected head pin, the prior evaluations, unused declarations, and candidate/self observations. Collection reordering does not change the digest.
2. `evaluation_id = "TB4-V02-EVAL-" + SHA256(CANONICAL({domain,profile,artifact,epoch,sequence,property,policy,usability,supersedes,reasons,evidence_digest}))`, retaining the full digest rather than truncating to 20 hex digits.
3. The new `RecoveryEvaluation.evidence_digest` exposes the commitment; this is **a local checksum**, not a signature, receipt, or independent source of evidence.

Thus **same v0.2 evaluation ID implies the same canonical declared case and local assessment contents up to SHA-256 collision resistance**, provided the *actual source module* is trusted. It does not imply the case statements are true or externally witnessed. Inclusion of all input declarations intentionally permits unrelated-declaration changes to change ID; that is the chosen conservative v0.2 case-identity contract.

## 4. Prior chain: stricter, still only lab-declared

A `PriorEvaluation` in v0.2 must now carry:

- `evidence_digest: str`: SHA-256 of the original declared v0.2 case, as emitted when the evaluation was created.
- `reason_codes: tuple[str,...]`: the former evaluation's complete sorted unique reason codes.
- Its old fields (`evaluation_id`, `artifact_id`, `epoch_id`, `sequence`, `policy`, `usability`, `supersedes_evaluation_id`, `origin`, `support_ref`).

For every prior evaluation, the engine **recomputes its v0.2 evaluation ID** from the declared record fields and `evidence_digest`. A changed/replaced ID, reason, predecessor, status, digest, epoch, artifact, sequence or policy with an unrecomputed ID is rejected (`PRIOR_EVALUATION_CONTENT_BINDING_MISMATCH`, or existing structural rejection). A fabricated but internally consistent digest can still be created by a fully compromised controller; the engine does not re-execute historical evidence or verify the original case from the digest.

For the **target artifact's** prior chain, the engine requires:

- Every participating prior record has declared `origin == LAB`. Candidate/self/derived/unknown-origin records are **preserved in the invalid report but cannot become a supersession head** (`NON_LAB_PRIOR_CANNOT_SUPPLY_HEAD`). This is a *synthetic source policy*, not authentication of `LAB`.
- If any prior target record exists, `expected_previous_evaluation_id` is mandatory (`MISSING_CONTROLLER_DECLARED_PRIOR_HEAD`). This is an input supplied by the laboratory controller, not an independently stored head or a freshness guarantee.
- The supplied expected ID must name the **unique tip** of the target chain; an old ancestor, a different artifact, or a missing record cannot silently stand in for the current head (`CONTROLLER_DECLARED_HEAD_MISMATCH` / existing errors).
- The existing duplicate, branching, scope and chronological-order checks remain.
- The report retains `original_evaluations` and `original_artifacts` unchanged and returns no new evaluation on invalid prior history; it never mutates or deletes supplied input records.

Omission of **all** earlier history together with the expected pin is **undetectable without an external retained head**, which is intentionally outside v0.2. A dishonest controller may label a forged record LAB and recompute all digests; the above checks do not solve this. This is explicitly **NOT a trust-root implementation**.

## 5. Reproductions and success criteria

The legacy version v0.1 remains byte-for-byte unchanged, with its earlier tests run alongside v0.2.

The v0.2 test module executes the 32 original synthetic scenarios and existing controls, adapting their prior fixtures to v0.2's explicit case-binding contract. New adversarial tests cover:

- Different observation IDs, timing, support references, frozen-reference IDs and hashes, proposal IDs, artifact digests, control roots, scope labels, inventory and controller declarations yield different evaluation identities.
- Input collection order permutation preserves the canonical ID.
- Fabricated arbitrary prior ID and edits to previously frozen prior fields are rejected.
- Candidate/self/derived/unresolved prior histories cannot become a declared LAB head.
- Prior history missing the controller-declared head pin is not silently superseded; a mismatched ancestor cannot become the head.
- A consistently declared, ordered multi-evaluation history does permit a strictly scoped new supersession.
- Legacy v0.1 policy histories cannot be silently inserted in v0.2.
- All report-level non-authority fields remain conservative and outputs do not mutate input.

**Pre-patch evidence:** The owner's Phase 0 Windows isolated run: `435 passed, 1 skipped, 5 xfailed, 92 subtests passed`; the five xfails include two v0.1 defects concerning IDs and candidate priors. Phase 0 is kept separately; this candidate does not hide or erase those negative findings.

**Candidate acceptance gate:** v0.2 tests pass in a separate snapshot; existing TB-004 v0.1 tests still pass without modification; full tracked regression is clean apart from documented skips/warnings; source digests and archived originals are checked; no changes to the live repository, no commit/push/merge. This does not authorize production use or automatic promotion of laboratory results to evidence.

## 6. Deferred and non-goals

The following defects remain open, **not** silently fixed:

- F15/F11 rule-version opt-out in M0; agent write-then-run composition; CI dependency pinning.
- TB-003/TB-004 mandatory cross-component consistency and full compromise-inventory recovery labeling.
- Trusted head retention, source authentication, real signing/revocation/time, independent custody and admission authority.
- Any entity or ontological continuity claim, or assertion that tests prove institutional safety.

**Owner-controlled next step:** Inspect the isolated results, obtain explicit approval before any GitHub branch/commit/PR, and keep the new v0.2 code separated from v0.1 even if published later.
