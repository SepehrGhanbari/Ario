# Context-isolated Grok review — provenance and follow-up register

**Record status:** RESEARCH INTAKE / USER-SUPPLIED ACCOUNT / HUMAN-INDEPENDENT-REVIEW NOT ESTABLISHED / NO SECURITY APPROVAL / NO PATCH ADOPTION.

**Exercise dates:** 2026-11-15 to 2026-11-16 (Asia/Tehran).  
**Source record:** [ARIO_BLIND_REVIEW_RECORD_2026-11-15_EN.md](./ARIO_BLIND_REVIEW_RECORD_2026-11-15_EN.md).  
**Uploaded original:** 7,793 bytes; SHA-256 `9c4b0f7134fab34d23710d9ed995ff58ae916131d8ce03cda29f016e3e516dd6`; Git blob SHA-1 (including Git blob header) `3d79b39cd20cfcb53d5e5e1896ee0cb9f7427550`.  
**Repository intake:** this independent archival branch, based on `main` commit `b5455ecd869e9b37f17ebfc9e7bbfb5133797df6`. Original record is copied without filling or rewriting any TODO fields.

## Roles and independence classification

- **Seed author / patch author:** the source identifies Claude Sonnet 5.5. The exercise's adversarial defects and the subsequent patch came from that same source, so the experiment was not independent of all design decisions.
- **Reviewer:** Grok on a *new account*, reported by the user/source as having no previous Ario project context. Round 1 used a neutral prompt and an approximately 283 KB curated review archive; this is **reported context isolation, not independently provable model isolation or a blind human peer review**.
- **Rounds 2–3:** same reviewer model but **not blind** to earlier findings. Post-round-3 parser/test tightening was only mutation-tested by the patch author; no reviewer round 4 or independent review of final v3 was reported.
- **Recording assistant:** archival and source-fingerprint checks only. It did **not** run Grok, reproduce the seeded tests, execute v3, independently validate the 99-input exercise or independently verify the claim of 11 caught mutations.

## As-reported outcomes (not independently rerun in this intake)

| Stage | As-reported observation | What it does *not* prove |
| --- | --- | --- |
| Round 1, blinded to seeds | Grok found S1–S4, **4/5** planted defects; S5 (tautological tests) was missed | No population-level detection rate, no full test-suite coverage |
| Additional finding | Unresolved `TRANSFORMATION` derivation can be omitted from the ancestry graph while the label reads `TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT` | Reporting/contract ambiguity, not an established exploit or falsity |
| Round 2 | Exposed false claim that v1 added fields without changing verdict: the 65,536-byte report boundary could flip PASS to FAIL/UNKNOWN; also tests/parser and Python 3.10 CLI deficiencies | Not proof the candidate patch is ready to adopt |
| Round 3 | No observed difference over **99 supplied cases**, Python 3.10 CLI fix reported, additional mutation-resistant tests identified | Not exhaustive proof of verdict equivalence |
| Final v3 (author-side) | **1,179 passed, 6 skipped, 116 subtests** on CPython 3.13; **11/11 mutations** reportedly caught | Not independently checked by Grok on final v3; `patch --dry-run` is not application |

The record reports one reduced-archive false positive ("LICENSE missing"), one inaccurate Grok statement concerning `"bad\\nid"`, and the **41 vs 58** test-count difference as historical version drift. Keep these counterexamples visible.

## Missing provenance / unresolved fields

1. **UNKNOWN:** exact source repository commit and checksum of the modified ~283 KB seeded archive, and the complete five seeded changes.
2. **UNKNOWN:** Grok model identifier and version as run in round 1–3, and execution environment details sufficient to repeat the exercise.
3. **UNKNOWN:** original raw Grok prompt, complete unedited output/transcript for each round, and separate SHA-256 digests of each. Pasted or summarized claims are **not** independently authenticated raw output.
4. **UNKNOWN:** exact `PATCH_v3.diff` bytes/hash and commit at which the patch is *actually* applied, if any. No patch or test changes were imported by this archival PR.
5. **NOT_RERUN:** full `implementation/tests/` including S5, writer's 11 mutation runs, 99-case verdict comparison, and CPython 3.10/3.13 regressions.
6. **DESIGN HOLD:** whether unresolved `TRANSFORMATION` derivations are tolerated declarations with narrower reporting, or should force `UNKNOWN`; no semantic contract change authorized.

## Admission boundaries and next audit step

The source report is retained as a **dated, attributed account of a single context-isolated cross-model experiment** (`N=1`), not a numerical model benchmark, verified third-party security certification, human peer review, or validated final patch. This record is **append-only research evidence**, not a validator or trust authority.

To advance the claim, archive the exact seeded ZIP, neutral prompt, raw Grok rounds, final v3 patch, model/version, SHA-256 hashes and exact execution logs; then ask a separate reviewer to check the *actual committed* patch and re-run the entire test directory. A later update should link new evidence without silently editing this source record.

**RESEARCH_ONLY / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO / NO_MERGE_WITHOUT_REVIEW.**
