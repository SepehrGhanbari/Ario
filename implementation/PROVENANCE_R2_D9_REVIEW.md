# Ario R2 D9 — External Custody Boundary: Review-Only Reference Lab

**Date:** 2026-11-18  
**Status:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`  
**Related:** [PR #270](https://github.com/SepehrGhanbari/Ario/pull/270), [Issue #251](https://github.com/SepehrGhanbari/Ario/issues/251), [Issue #81](https://github.com/SepehrGhanbari/Ario/issues/81).

## Evidence provenance

- **Design input:** Hallaaj's D9 text provided by the project owner, `DESIGN_REVIEW / CHAT_REPORTED`. Hallaaj could not fetch/execute D8 and is **not** an authenticated witness or code reviewer.
- **Previous experiment:** Local D8 archive `Ario_R2_D8_One_Custodian_Floor_Boundary_Lab_2026-11-18.zip`, SHA256 `14c8b888c365971a0e3e5dbf54d4ecdccbee00f4c5b5d7ac5a382c4306e5182f`, opened and ZIP integrity checked locally. D8's 261 tests replayed locally. The D2–D8 source archive itself is **not** added to this PR.
- **D9 scope:** Exactly two new standalone Python files (validator + 45 tests) and this documentation. No workflow, signer, real account/key, endpoint, production admission, `AGENTS.md`, or existing implementation changed.
- **External custodian / actual live read:** `NOT_ENROLLED / NOT_RUN`. All three ephemeral Ed25519 test keys, observations and the alleged protected floor are created **within one author's local test process**. Distinct keys do not imply distinct operators.

## The falsifiable question

Can an *offline consumer* check the internal mathematical consistency of a signed append-only history, a separately signed verifier floor, a nonce-bound signed head and a visible conflicting view **without** promoting any of these *caller-supplied* objects to genuinely externally sourced authority?

This code is intentionally **not** a live custodian client. It performs no network or filesystem I/O and does not maintain persistent verifier state. It is **not** C2SP, RFC 9162, Merkle log proof verification, GitHub Artifact Attestations, an authenticated time source, an independent execution observer, or M0 admission code.

## Source and minimal input contract

- `provenance_r2_d9_custody_lab.py`: `evaluate(tuple[Signed], signed_head, signed_floor, LabPins, optional_signed_alternative_head)`. Domain-separated Ed25519 signatures; canonical, strict bounded JSON; events `STATE`, `REVOKE`, `OBSERVER_ROTATE`, `ROOT_ROTATE` (explicitly held). Full linear chain from synthetic genesis, maximum 128 entries.
- `test_provenance_r2_d9_custody_lab.py`: 45 Python `unittest` tests, independently invoking the source under test with disposable, in-memory Ed25519 keypairs.
- `LabPins` is a *supplied lab input*, not an authenticated out-of-band enrollment. It deliberately allows **only** `source_basis=LAB_SUPPLIED` and forbids a caller from labeling the pin `OOB_AUTHENTICATED` and gaining authority.
- A mathematical signed floor checks only whether an observed history matches the **supplied** floor. It does **not** prove that the floor is retained on an independently administered, rollback-resistant device.
- A signed head with a matching 128-bit *lab-provided* nonce checks response binding. It does **not** demonstrate external liveness, unpredictability of a real nonce, a truthful latest head, a trusted clock or absence of concealed data.
- Observer rotation requires a separate *lab-pinned* rotation key and increments an epoch; custodian-root rotation requires **new out-of-band enrollment**, not a claimed event. Real rotation/recovery policies are unimplemented.
- A changed revocation tip must be carried by a typed `REVOKE` event; omission of a **known** revocation below the protected floor is rejected. A never-delivered revocation cannot be inferred.

## Local validation (not GitHub CI)

```shell
cd implementation
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_provenance_r2_d9_custody_lab.py -q
```

Recorded author-local outcome: **45/45 PASS** on CPython 3.13.5 with `cryptography` installed. An additional **9/9 targeted code mutations went RED** when guards were deliberately weakened in disposable copies; this checks negative-control sensitivity, not completeness or independence. Mutation runner and JSON output are included in the separate downloadable research ZIP, **not in this three-file PR scope**. Historical D2–D8 suite replayed separately: **261/261 PASS** from the original D8 ZIP. These are **not** 306 exact-PR-head CI tests; prior archived code isn't in the PR.

Targeted negative controls tested: invalid signatures, malformed/duplicate/noncanonical JSON, changed HEAD nonce, stale history below floor, old-sequence fork, visible equivocation, newer disclosed view, invalid key rotation, silent revocation/key change, and an omitted revocation already known to the floor. An all-`UNKNOWN` final classifier is **not** independently validated positive-control recall.

## What passes, what never passes

| Observation | Narrow conclusion |
|---|---|
| Valid signed chain + floor + nonce-bound head | `lab_diagnostic=LAB_CONSISTENT_ONLY`, `status=UNKNOWN` |
| Candidate HEAD behind protected floor | `ROLLBACK_BELOW_PROTECTED_FLOOR`, `status=UNKNOWN` |
| Conflicting signed view at any observed sequence | `VISIBLE_SIGNED_EQUIVOCATION`, `status=UNKNOWN` |
| Newer *observed* authenticated view | `NEWER_SIGNED_VIEW_WAS_WITHHELD`, `status=UNKNOWN` |
| Revocation / key rotation in the known floor omitted from candidate chain | Rejected; no rewriting prior receipts |
| Hidden revocation / fork that nobody reports | **Cannot be detected**; absence remains `NOT_ESTABLISHED` |
| Full rollback of keys, floor and history under one controller | **Indistinguishable from prior valid world** absent independent retained evidence |

**Every** D9 return has: `status=UNKNOWN`, `evidence_admission=NOT_EVALUATED`, `real_world_custody=NOT_ESTABLISHED`, `external_enrollment=NOT_ESTABLISHED`, `actual_remote_read=NOT_RUN`, `remote_freshness=NOT_ESTABLISHED`, `original_github_execution=NOT_ESTABLISHED`. `LAB_CONSISTENT_ONLY` is a deliberately non-authoritative diagnostic.

## Why the reviewer's D9 proposal was narrowed

1. `sequence >= floor` + local timestamp is **not** globally verifiable freshness. A custodian might replay or re-sign stale state. A user-supplied nonce isn't proof of independently performed challenge delivery or current head.
2. A hash-chained local floor is **not** protected from a common administrator who can rewrite the entire chain and its reference. Verifier-floor protection must be physically/administratively independent of both claimant and custodian.
3. Object-store versioning is **not automatically append-only**; an administrator can sometimes delete prior versions or change retention and IAM. Requirements include external retained history and enforceable append-only guarantees, not merely an API supporting versions.
4. A witnessed fork requires an independently delivered contradictory view. Two monitors that share an administrative/recovery or information source do not furnish independence by quantity alone.
5. A valid signature authenticates bytes against a pinned key; it does not prove external enrollment, underlying custody, that the original GitHub `pytest` ran, or claim truth.
6. Revocation completeness, root replacement and disaster recovery require independently authenticated policy, separately anchored history and observable rejection behavior. No such authority was added here.

## Next *real* D9 gate (NOT_RUN; no real custodian has been authorized/enrolled)

1. Select an actual custodian **not administered, backed up, recoverable or key-controlled by the claimant** and record its administrative-control threat model. A VPS controlled by the same account is **not** sufficient.
2. Establish a custodian key fingerprint by an authenticated, explicitly owner-approved, out-of-band channel; independently pin a verifier-floor root. Do not accept pins/`registered=true` inside the candidate's envelope.
3. Perform a fresh nonce challenge via a read-only endpoint, preserve exact response bytes and transport metadata; verify signatures and any available *real* log consistency proof. A single signed "latest" endpoint is not, by itself, globally current.
4. Retrieve at least one independently retained historical checkpoint and independently observed revocation/rotation event; test mismatch, network outage, replay, hidden fork and recovery against an external trace.
5. Preregister source-independent positive and negative cases. Measure false promotion **and positive recall**; do not score lab-only conditional positives as external independence.
6. Only with additional explicit owner security and governance decisions should any change to trust/admission/signers/workflows be considered. **No credentials or service provisioning performed.**

## Independent reviewer challenge — can be copied as plain text

> D9 local verifier (not a live custodian) verifies domain-separated Ed25519 checkpoint and floor signatures, full signed linear chain, revocation-tip and key-epoch transitions, nonce binding and supplied alternate signed heads. It returns `status=UNKNOWN` even for `LAB_CONSISTENT_ONLY`. Source and 45 tests are in this PR, but Hallaaj's input was chat-only and no external witness has been enrolled. Please inspect exact new source and try to produce a counterexample that causes a non-UNKNOWN global status, misses a **visible** old-sequence fork/known revocation, mistakes an observer-key rotation for custodian-root rotation, or accepts malformed/noncanonical signed input. Also explain whether a valid signature with nonce could prove *global freshness* when the custodian itself hides newer events. Report exact source SHA, commands run and limitations; do not grant production authority.

`RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / TRUST_ACTIVATION=NO_GO`
