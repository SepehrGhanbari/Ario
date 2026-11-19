# W1 Trae boundary controls — GitHub-hosted CI readback receipt (2026-11-17)

**Status:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`  
**Source commit checked:** `c0468171c652a5035ee3e1bd41cffd84fc1dee6d`  
**Actual workflow run:** [44167277581](https://github.com/SepehrGhanbari/Ario/actions/runs/44167277581) (*W1 synthetic provenance research only*).  
**Separate project regression run:** [44167277587](https://github.com/SepehrGhanbari/Ario/actions/runs/44167277587) (*Implementation Regression*) — conclusion success, different coverage; do not confuse it with W1.

## Actual GitHub Actions jobs, read from API and selected logs

| OS / Python | Job ID | GitHub conclusion | New control results |
| --- | --- | --- | --- |
| Ubuntu latest / 3.11 | 134336578770 | success | 15 original tests ran; three new tests ran (2 ordinary PASS, 1 expectedFailure) |
| Ubuntu latest / 3.13 | 134336579252 | success | New-control step explicitly marked success; inspect full job log if per-case audit needed |
| Windows 2022 / 3.11 | 134336579282 | success | New-control step explicitly marked success; inspect full job log if per-case audit needed |
| Windows 2022 / 3.13 | 134336579115 | success | 15 original tests ran; three new tests ran (2 ordinary PASS, 1 expectedFailure) |

In both **directly retrieved Windows 3.13 and Ubuntu 3.11 job logs**, the exact new test names were displayed:
- `test_gap1_ambiguous_custody_transfer_remains_unknown`: **ok**
- `test_gap2_capture_after_mutation_remains_unknown`: **ok**
- `test_known_gap3_shared_custodian_across_witnesses_not_separated`: **expected failure**
- `Ran 3 tests` and `OK (expected failures=1)`.
Both job logs show `Ran 15 tests` for the original suite. No implication that `expectedFailure` is a passing protection assertion.

The workflow now watches changes to pinned `implementation/witness_provenance_experiment.py`, root `.gitattributes`, the original and new W1 research test files, and the workflow file itself. It performs Git checkout with `core.autocrlf=false`, the exact-byte source pin, the original fifteen tests and the three additional tests.

## Local supplementary evidence, distinct from GitHub execution

The independently reconstructed three-test file was run locally against the original evaluator Git blob `4faf010d73219af63c254097e9c135da68d60078` / SHA256 `71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567`, with CPython in the research sandbox: **3 runs, 2 PASS, 1 expectedFailure**.

A transient in-memory variant of M1 (accept multiple custody paths) caused the F1 control to fail; an M7 variant (ignore capture-after-mutation) caused the F2 control to fail. Neither mutant was persisted in GitHub or used for official CI. This is **not** direct execution of Trae's original absent patch/evidence attachments; see [review adjudication](W1_TRAE_FINDINGS_AND_RESEARCH_ONLY_REPAIR_2026-11-17.md).

## Gate
`CI_SCOPE_PASS`: exactly four successful named W1 test jobs on the specified commit, with **one deliberately documented expected failure** per job. No operational witness independence, human peer review, true blind oracle, production readiness, or trust activation is established. **HOLD / NO_MERGE**.
