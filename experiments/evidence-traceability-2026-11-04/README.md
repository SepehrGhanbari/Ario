# Ario Evidence Traceability R2 — bounded research record

**Date:** 2026-11-04  
**Status:** `RESEARCH_ONLY / DOCUMENTATION_CANDIDATE / NOT_ADMITTED / NOT_MERGED`  
**Scope:** A non-authoritative claim → source → proposed test → supplied receipt → review-status research index. This is a documentation-only proposal, **not executable code**, an M0 adapter, or an authorization mechanism.

## Existing EA/ARP boundary

Ario already implements [EA-0.1](../../implementation/EVIDENCE_ADMISSION_CONTRACT_V0_1.md), [ARP-0.1](../../implementation/ADMISSION_REVIEW_POLICY_V0_1.md), [candidate_dossier_builder.py](../../implementation/candidate_dossier_builder.py), and [admission_review_evaluator.py](../../implementation/admission_review_evaluator.py). The proposed cross-project index **does not duplicate or replace** that ledger-specific candidate/review pipeline.

An EA dossier is only a `CANDIDATE` with `admission_decision=NOT_EVALUATED`. ARP review screening does not authenticate reviewer authority or admit evidence; its CLI can return **exit code 0 with `status=UNKNOWN`**. R2 self-digests are research-format pins, not ARP canonical candidate digests. No research matrix PASS, ZIP digest, receipt, successful exit code, self-claim, reviewer label, or repeated copy of one source may be automatically converted into M0 `Evidence`, `Assessment`, `Claim`, `AuditResult`, admission, independent provenance, authorization or truth.

`OBSERVED != CANDIDATE != ADMITTED != ASSESSED != TRUTH`

## Privately held material and limits of review

The R0/R1/R2 ZIPs, historical logs, synthetic fixture bytes, and original failure records are retained privately and **not published by this file**. The reported SHA-256 pins are:

| Research package | SHA-256 |
|---|---|
| R0 | `bdb979b93961b2afcdb95c589bf2f87e50d77abdde57ac2a0f5831c5466d1f82` |
| R1 | `a666d151e9702894d73ef35be3781052670d8edb1f91613bd21eb30be3375709` |
| R2 | `d3910bf0f8a9b2951615e6a45aaf17ab6e737c198c41e6922bd4e9539025d964` |

These identify reported bytes only; they are not evidence of authenticated provenance or independent custody. **CodeRabbit has not received, source-reviewed or executed R2.** Reported Ava-run local suites: R0 41/41 focused tests, a separate synthetic two-Ava replay 34/34, R1 45/45, and R2 50/50. The initial R2 run had **48 passes and two test-expectation failures**, and the earlier failure log was retained. None of these counts is a GitHub CI result for this documentation PR, an independent execution attestation, or proof of a real-world claim.

## Three R1 counterexamples observed in isolated scratch

All three were **reproduced by Ava on disposable R1 copies**, not on M0:

1. **Co-forged green log:** Replace a supplied green-test log and re-pin its digest; R1 still emitted an execution-looking positive matrix label. R2 instead uses `PASS_REPORTED_IN_PINNED_RECEIPT_NOT_INDEPENDENTLY_REEXECUTED`, which deliberately **does not claim fresh execution**.
2. **Claim/test-scope substitution:** Change claim objective, test selector and runner while retaining the referenced receipt; R1 accepted the altered description. R2 locally pins registry and plan semantics to reject simple unilateral changes. A jointly forged checker, plan and receipts remain outside this protection.
3. **Final-component symlink race (POSIX scratch):** Substitute a symlink after R1 checks a pathname but before its read; R1 read synthetic out-of-root bytes. R2 used no-follow directory-FD traversal and a single opened-descriptor capture to reject the **tested final-symlink** substitution. This does not prove full filesystem concurrency safety, atomic multi-file capture, or native Windows race safety.

A successful hash match establishes consistency under local rules, not that a claimed execution occurred independently.

## CodeRabbit follow-up: proposed controls, NOT_EXECUTED here

- **Unchanged packet:** rerun only the checker against an intact packet; do not allow an interpreted claim that tests themselves were rerun.
- **Plan split-read and in-place mutation:** hash bytes A, change the pathname/content before parse if a second read occurs; separately mutate an already-open regular file during capture. Parse/hash one bounded capture or refuse, without claiming an atomic filesystem snapshot.
- **Mixed generations:** combine files individually consistent with two different generations; do not infer simultaneous historical coexistence.
- **Windows reparse point:** test a substitution between pre/post checks on Windows. `WINDOWS_RACE_SAFETY=NOT_ESTABLISHED`.
- **Positive and negative controls:** include valid and invalid claim/selector/receipt bindings so a deny-everything checker cannot pass.
- **Non-promotion:** give a potential consumer an all-green index, forged receipt and ARP `UNKNOWN` with exit 0. Require no M0 object, audit call, ledger mutation or authority change.

These are **future adversarial fixtures**. No execution or result is claimed for them in this repository document.

## Remaining gates

1. Authorized independent review of **exact R2 source bytes**, digest, parser bounds, original REDs, runner and receipt-binding logic.
2. Independent, isolated **synthetic** replay with exact commands, selectors, environment, outputs and negative controls. Separate newly observed results from supplied historical logs.
3. Platform-specific review: POSIX no-follow finding only for tested race; in-place writes, cross-file snapshots and Windows concurrency unresolved.
4. Review of exact public diff and privacy limits before any merge, code integration or change of evidence/trust authority. This note itself grants none.

`CLAIM_TRUTH=UNKNOWN`  
`SOURCE_AUTHENTICITY=NOT_ESTABLISHED`  
`INDEPENDENT_EXECUTION_ATTESTATION=NOT_AVAILABLE`  
`M0_ADMISSION=NOT_EVALUATED`  
`EXPERIENTIAL_IDENTITY=UNKNOWN`  
`OWNER_SIGNER=HOLD`  
`GENESIS/PRODUCTION=NO_GO`

No private conversations, raw archives, tokens, live GPU work, payments, keys, signer, trust enrollment, evidence admission or production operations are published or activated.

## Discussion and request for falsification

- [Issue #81 — independent evidence and admission](https://github.com/SepehrGhanbari/Ario/issues/81)
- [Ava R1 report](https://github.com/SepehrGhanbari/Ario/issues/81#issuecomment-6636408866)
- [CodeRabbit R1 critique](https://github.com/SepehrGhanbari/Ario/issues/81#issuecomment-6636460223)
- [Ava R2 adversarial replay](https://github.com/SepehrGhanbari/Ario/issues/81#issuecomment-6636800394)
- [CodeRabbit R2 reply supporting documentation-only scope](https://github.com/SepehrGhanbari/Ario/issues/81#issuecomment-6636844375)

**Review challenge:** Identify a concrete smallest falsifier of any overstated integrity, freshness, execution, independence or Windows guarantee. Do not infer an M0 admission mechanism from this index.
