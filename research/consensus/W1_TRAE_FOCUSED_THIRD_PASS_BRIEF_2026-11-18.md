# W1 focused technical third-pass assignment for Trae — 18 November 2026

**Status:** `PREPARED_NOT_SENT / RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`. This is a copyable assignment, not a claim the review happened. Reviewer remains AI-assisted, not blinded or human.

Hi Trae ❤️

This is a **focused follow-up**, NOT a repeat of your first W1 review. Claude Sonnet 5.5 completed its second pass and independently reported a new capture-order off-by-one survivor (M9). Your own first F1/F2 findings have already resulted in additive **research-only** tests; the question now is whether the new boundary, the data-scoring policy and the shared-custodian interpretation are correct.

**Repository:** https://github.com/SepehrGhanbari/Ario  
**Draft PR:** https://github.com/SepehrGhanbari/Ario/pull/242  
**Research branch:** `research/consensus-sprint-20261116`. **Read the current commit SHA; do not assume your old `48574e63` remains HEAD.**

Start here:
1. [Claude's **verbatim second-pass report**](W1_CLAUDE_SECOND_PASS_REPORT_2026-11-17_VERBATIM.md) — especially N1–N6 and its two Python tests.
2. [Our reviewed discrepancies and task ledger](W1_CLAUDE_SECOND_PASS_ADJUDICATION_AND_TRAE_HANDOFF_2026-11-18.md).
3. [Your original verbatim report](W1_TRAE_REPORT_2026-11-18_VERBATIM.md) and [original patch, preserved but **not** blindly applied](W1_TRAE_ORIGINAL_PATCH_2026-11-18.patch).
4. [Current focused W1 test file](test_w1_trae_boundary_controls_v1.py), pinned evaluator `implementation/witness_provenance_experiment.py`, W1 harness and its older 16-case JSON, and `.github/workflows/w1-provenance-research.yml`.
5. The **historic** 5-Nov paper and historic 25-Oct source pin. Important: the old evaluator file is Git blob `b49b5fa6489a97a31a7056bf2fd8b1c6f2c03139` (23,876 bytes), while the extension's evaluator blob is `4faf010d73219af63c254097e9c135da68d60078` (26,726 bytes). These are **not the same engine**.

**Scope of your review:**

A. **M9 boundary verification.** On the current pinned evaluator, independently check the correct semantics for `capture_sequence == mutation_sequence`, `<`, and `>`. Mutate only in a **temporary isolated copy**: `elif any(c >= case.mutation_sequence ...)` → `>` (M9), and separately M7 (remove capture gate), M1 (accept multiple custody transfer paths). Record which named tests kill each mutant. The current W1 research test file now contains `test_gap2_capture_equal_mutation_is_unknown` and `test_gap2_capture_just_before_mutation_is_conditional`; independently examine whether they correctly isolate the target behavior, with no tautological test. **Separate source-byte pin rejection from mutation-oracle sensitivity.** Never alter the frozen evaluator or real signing/production logic.

B. **Score claims against declared latent truth and oracle.** Verify or falsify Claude N2/N3: three falsely-complete rows are recorded as development `CONDITIONAL` matches; the "16/16" development score must not be interpreted as real-world detection accuracy. Independently reproduce the five-policy table (pinned gate, storage only, never-promote, constant UNKNOWN, constant DEPENDENT), reporting per-class counts, false endorsements, missed positives and UNKNOWN/abstention. Use **the exact same observed case inputs** and distinguish developer-provided latent metadata from externally authenticated ground truth. Verify the four-case byte-identical observation group; explain the trade-off rather than present it as a realistic frequency.

C. **Shared custodian F3.** Independently test shared starting, middle and final custodian. Decide whether the design needs **UNKNOWN, a separate custody-correlation result, or DEPENDENT**; do not silently redefine `DEPENDENT` without a reviewed specification. Preserve existing expectedFailure as a known gap until the policy is agreed.

D. **Version and evidence reconciliation.** Claude saw the offline ZIP `W1_CI_RED_GREEN_RECEIPT` SHA-256 `6ea6e4aedd8bef4836b715237846727f6d396d64b00e61c9698d6c1b51f1b12c`, now archived separately [offline-packet variant](W1_CI_RED_GREEN_RECEIPT_OFFLINE_PACKET_VARIANT_2026-11-17.md). Your GitHub branch saw `f591a0bd21ec7afcb0a61b9bf534aef36cf1fd13983af0e979f13cb88fa37fed`, [branch edition](W1_CI_RED_GREEN_RECEIPT_2026-11-17.md). Verify they are different editions, not an unexplained hash mismatch; retain both. **Do not pool** the historic paper's 16 cases and W1's new 16 development trials. Current experimental CI [run 44170674792](https://github.com/SepehrGhanbari/Ario/actions/runs/44170674792) has four completed successful W1 jobs (Windows/Linux Python 3.11/3.13), with **5 focused tests: 4 normal PASS and 1 documented expected failure** per job. You must inspect the jobs yourself or mark remote CI `NOT_RUN`.

E. **Better research design, no false blinding.** Propose a new graph-family challenge generator using latent complete graph `G*`, a documented masking operator `O`, and matched honest/incomplete/undisclosed omission variants, with a future frozen oracle separate from the evaluator. Nothing in the old public development data is blinded. If suggesting CI changes, isolate them from production and show an exact minimal patch plus offline test output.

**Return** one English `W1_TRAE_THIRD_PASS_REPORT_2026-11-18.md` with source HEAD SHA, what you actually read, rerun commands/stdout/exit codes, precise mutations/test kills, reproducible cases, deviations from Claude, score table, source revision/hash reconciliation, remaining UNKNOWNs, and prioritized `FIX / REVISE / HOLD` recommendations. If needed attach a **separate research-only patch** and raw evidence; do not auto-merge. Do not assert human peer review, independently sealed ground truth, live custody or authorization.

**Forbidden:** modifications to `main`, actual keys, signer, rulesets, trust activation, production admission, persistent memory, old journal history, original journal-facing manuscript, SSRN/Zenodo or editorial correspondence.

`RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`
