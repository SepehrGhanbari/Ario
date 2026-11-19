# W1 second-pass review (Claude), with the November 17 extension visible

Reviewer: Claude (AI model, Sonnet 5.5). Date: 2026-11-17 (local 2026-11-18 early). Status: `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE`.
**AI review. Not independent human peer review. Not blind:** I had already seen the preprint and its results, and I had written the first report; this pass is a reassessment, not a fresh test. No GitHub merge, no publication action, no live signer.

Tags: **VERIFIED** (I ran it or recomputed it here), **READ** (from reading only), **HYPOTHESIS**, **UNKNOWN**, **NOT_RUN**.

## 0. Scope and provenance of what I used

Read and run: the offline packet `Ario_W1_Claude_Second_Pass_Offline_Packet_2026-11-17.zip` (extension supplement draft, harness, 15 tests, results JSON, replay recipe, CI receipt, pinned evaluator, 58-test provenance suite, my first report verbatim); Trae's report, patch and summary; the reference-model script `r5_counterexamples.py`.

- **VERIFIED:** `sha256sum -c SHA256SUMS.txt` passes for all 9 packet files. The evaluator is 26,726 bytes, SHA-256 `71912958...f567`, Git blob `4faf010d73219af63c254097e9c135da68d60078` (recomputed by me; same as Trae reports).
- **Discrepancy (VERIFIED):** Trae lists `W1_CI_RED_GREEN_RECEIPT_2026-11-17.md` as sha256 `f591a0bd...fed`; the packet's copy is `6ea6e4ae...b12c`. The two reviewers read different versions of the receipt. UNKNOWN which is current; the packet is not the branch HEAD Trae read (`48574e63`). Please reconcile before the register is recorded.
- **NOT_RUN / not available to me:** the GitHub Actions run URLs, PR #242, Trae's `evidence/*.txt` and `tools/*.py`, the brief (`W1_CLAUDE_TRAE_SEPARATE_REVIEW_BRIEFS`, not in the packet), the workflow file (not in the packet). Consequently I could apply only two of the three files in Trae's patch.
- My interpreter is CPython 3.13.18 only. Trae's 3.10 to 3.14 matrix is not re-run by me.

## 1. Direct verification of the artifact

| Check | Result |
|---|---|
| 15 W1 tests | VERIFIED: 15 passed (3.13.18) |
| CLI aggregate | VERIFIED: `designed_trials 16, development_expectation_matches 16, hidden_dependency_conditional 3 of 3, permutation_checks 192` |
| 58-test provenance suite (`pytest`) | VERIFIED: 58 passed |
| Trae F1 (ambiguous custody accepted passes both suites) | **VERIFIED** with my own mutation (`len(options) != 1` -> `< 1`): 58/58 pass; all 14 behavioral W1 tests pass |
| Trae F2 (capture-order gate removed) | **VERIFIED** (`elif any(c >= mutation_sequence)` -> `elif False`): both suites pass |
| **New: off-by-one at the order boundary** (`>=` -> `>`) | **VERIFIED, not in Trae's report:** both suites pass (58 passed; 14 behavioral W1 tests pass). Trae's patch test also does not catch it (see N1) |
| Trae F3 (shared holder across both witnesses stays CONDITIONAL) | VERIFIED: the patch's `expectedFailure` test fails as expected on the unmodified engine (`OK (expected failures=1)`) |
| Trae patch controls on the original engine | VERIFIED: 3 tests, OK, expected failures 1. Gap1 control catches M1; gap2 control catches M7 (VERIFIED under a re-pinned harness copy) |

Method note for the mutation runs: the byte pin rejects any edited engine, so each mutant ran in a temp copy with the harness's three pin constants re-computed for the mutant; the only W1 test that fails is the literal-pin test (`test_exact_source_pin`), which I did not count as detection.

## 2. Reassessment of my first-pass findings (F1-F11) with the extension visible

| # | First-pass finding | Status now | Why |
|---|---|---|---|
| F1 | Baseline's 4/16 is entailed by design | **Open for the extension, retained as history** | The extension drops the baseline (it tests only the pinned engine plus a wrapper) and keeps 4/16 vs 16/16 as "bounded historical observation" (supplement §1, §6.5). That is honest, but the entailment is never stated and no replacement comparator exists |
| F2 | Gate's 16/16 circular and largely duplicates existing tests | **Partly addressed** | Supplement §6.1-6.2 and the harness `scientific_status` say fixtures and oracle are author-built and not independent. Still open: the 16 trials are new but re-express `tp01..tp26`-type cases; and see N2 (the 16/16 now includes known failures) |
| F3 | Completeness/origin are declared inputs; hidden dependencies invisible | **Addressed in substance, framed too narrowly** | The extension adds exactly the hidden-dependency trials and states the limit plainly (supplement §3, §5; abstract). Open: it calls the result "non-identifiability counterexample" while counting the three false endorsements as development "matches" (N2); and the verdict name `CONDITIONAL` still reads as a positive (N5) |
| F4 | Baseline loses to a constant UNKNOWN classifier | **Open; quantified in N3** | No comparator in the extension. On the extension's own 16 trials a constant-UNKNOWN rule agrees with 7/16 and makes 0 false endorsements; the pinned gate makes 3 |
| F5 | "independently matched" in abstract contradicts §4.1 | **Mostly addressed** | The extension says the branch blob "was separately read via GitHub and matched" (§4), and does not call it independent. Reproduction is by the same project; the packet itself says so |
| F6 | Draft residue and availability inconsistency | **Open / changed** | The extension is clearly labelled "author-review draft". The record-hygiene items (titles, SSRN vs Zenodo, supplement deposition) now involve two public records (SSRN 10.2139/ssrn.7686572 in the supplement; Zenodo 10.5281/zenodo.24041161 in the repository). UNKNOWN which is canonical |
| F7 | Passing tests' mutation sensitivity unknown | **Upgraded to VERIFIED, adverse** | Three behavioral mutants (ambiguity, order gate, order boundary) survive both suites (section 1). Trae's patch closes two of three |
| F8 | Pinned-commit drift | **Partly addressed** | The extension pins the exact blob and the 58-test source and says tests are not "today's authority". UNKNOWN: whether the blob at the paper's `f562e14` equals `4faf010d` (the 41 vs 58 test difference suggests the evaluator or tests changed after the pin). Cheap to check with `git hash-object` at that commit |
| F9 | Novelty/literature | **Partly addressed** | The extension adds R1-R4 (existence of all four titled records confirmed in search results today; I did not verify author lists or read the full texts) and says it does not claim to invent the failure mode. Still missing classical dependability literature (N-version independence, common-cause failure), see section 7 |
| F10 | Arithmetic | n/a | Re-checked for the extension: expected classes are CONDITIONAL 5 (`honest-separate`, three `hidden-*-false-complete`, `untrusted-self-certification`), DEPENDENT 4, UNKNOWN 7, total 16; consistent with the aggregate I reproduced. Note that 3 of the 5 expected CONDITIONAL cases are the known non-detections (N2) |
| F11 | "pre-registered" terminology | **Open (low)** | The test docstring still says "Pre-registered TP-01..TP-26"; the extension says nothing is preregistered |

## 3. New findings

### N1 (medium, VERIFIED): order-boundary off-by-one escapes both suites and Trae's patch
`elif any(c >= case.mutation_sequence ...)` -> `>` is accepted by the 58-test suite, by the 14 behavioral W1 tests, and by Trae's `test_gap2` (it uses `mutation_sequence=1` with captures 1 and 2; capture 2 is already `>` 1, so the mutant still returns NOT_BEFORE_MUTATION). A test that places a capture **equal to** the mutation sequence catches it and also catches M7. Test code is in the Appendix (2 tests, passes on the original engine, fails on M7 and M9).

### N2 (major, VERIFIED): the 16/16 metric now encodes known failures as passes
In `w1_adversarial_input_sensitivity_v1.py` the three false-completeness trials are given `expected_report = "CONDITIONAL"` (lines 155, 158, 164), and `evaluate_trials` raises on any mismatch. So the engine's known non-detection of the hidden dependency is built into the oracle; "16/16 development matches" therefore cannot go down when the engine endorses a case whose latent truth is dependent. The supplement says this carefully in prose (§5 "What these denominators are not"), but `aggregate.development_expectation_matches` remains a quotable score.

### N3 (major, VERIFIED): scored against latent truth, with matched information
I scored five rules on the extension's 16 trials. All rules see the same `ProvenanceCase` (matched information). "False endorsement" = CONDITIONAL when the author-declared latent relation is not `SEPARATE_MODELED`. "Missed positive" = non-CONDITIONAL on the two disclosed-complete separate cases (`honest-separate`, `untrusted-self-certification`).

| Rule | Agrees with development oracle | False endorsements | Missed positives | UNKNOWN outputs |
|---|---|---|---|---|
| Pinned gate | 16/16 | **3** | 0 | 7 |
| Storage-only (my re-implementation of paper §4.3; HYPOTHESIS that it matches the authors') | 6/16 | 11 | 0 | 1 |
| Never-promote (same information as the gate, policy: DEPENDENT if detected, else UNKNOWN) | 11/16 | **0** | 2 | 12 |
| Constant UNKNOWN | 7/16 | 0 | 2 | 16 |
| Constant DEPENDENT | 4/16 | 0 | 2 | 0 |

Also VERIFIED: the trial set contains **observation-identical groups**: {`honest-separate`, `hidden-source-false-complete`, `hidden-admin-false-complete`, `hidden-source-admin-false-complete`} (4 trials, one serialized input) and two pairs ({`hidden-source-incomplete`, `separate-incomplete-source`}, {`hidden-admin-incomplete`, `separate-incomplete-control`}). Any deterministic function of the input must give one verdict per group. So no comparator that sees only the reported graph can separate the latent states; comparators differ only by **policy**: endorse the group (3 false endorsements out of 4 here) or abstain (1 missed positive out of 4). The 3-to-1 ratio is the author's choice and says nothing about prevalence. The fair question the study can ask is therefore not "which rule is more accurate" but "what policy does the verdict name imply, and what prevalence of hidden dependencies makes endorsement acceptable". That is a decision-theoretic statement the paper can make without any new data.

### N4 (medium, VERIFIED): same denominator, different cases
The extension's 16 trials are new, but the headline "16/16" repeats the 5 November paper's "16/16". Without care, readers will treat them as the same result. Say "16 new development trials" in the abstract and keep the two sets labelled R5NOV-16 and W1-DEV-16. (My storage-only re-implementation gives 6/16 on the new set, not 4/16, confirming they differ.)

### N5 (medium, HYPOTHESIS + VERIFIED behavior): the name `CONDITIONAL` invites promotion
The engine and wrapper return `CONDITIONAL` for graphs whose independence rests on a self-declared, unauthenticated completeness flag (VERIFIED: trials `hidden-*-false-complete`). The word reads as a weak positive. A neutral name that states the premise ("NO_DEPENDENCY_IN_DECLARED_GRAPH") would stop the label doing work the evidence cannot do. This is a naming/policy recommendation, not a defect claim.

### N6 (low, VERIFIED): the 192 permutation checks
They verify order invariance of classification only; `classify` does not hash the full report, so reasons or support lists could vary by order unseen. Trae says he checked full-report permutation stability (192, 0 mismatches); I did not re-run that. NOT_RUN by me.

## 4. Assessment of Trae's report

Verified by me: R1-R3 and R5 reproduce on 3.13; F1 and F2 (and my extra M9) reproduce with independent mutations; F3's `expectedFailure` behaves as described; the patch controls catch M1 and M7. Not re-run by me: the 3.10-3.14 matrix; M2-M6 (M3 inert, M6 caught by the 58-test suite only); the Windows CRLF emulation; his evidence files; the `.gitattributes` and workflow parts of the patch (the workflow file is not in the packet; the diff is plausible on reading). His disclosure that he read the harness before the results JSON, so separation was impossible, is accurate: the harness hard-codes the expected labels.

Points I would change:
- **F7 ("tautology")**: right that observation identity is by construction, but it is more than a tautology: it fixes the pinned artifact as a regression test and supports N3. I would call it "an observation-equivalence demonstration; it carries no information about the engine's discrimination".
- **F3 (shared custodian) and the `expectedFailure` test**: asserting `DEPENDENT` as the desired behavior is a specification decision, not a verified requirement. A single custodian holding both witnesses is a common-control path in a looser sense; it may deserve `UNKNOWN` or a separate axis rather than `DEPENDENT`. Decide in the spec first, then pin it.
- His patch's gap2 test misses the boundary (N1).
- A note on his claim "evaluator never falsely asserts independence": that is accurate only for the word as defined ("conditional"). N2/N3/N5 show the verdict can still be an endorsement in effect.

## 5. The reference-model script (`r5_counterexamples.py`)

I ran it (VERIFIED, `cryptography` 50.0.1): output matches its labels (10 VERIFIED, 4 HYPOTHESIS, 1 HAZARD). Assessment:
- It is a model of the **design contract as described** for PR #269 (receipt inspector) and PR #271 (history comparator); the author says he did not read their source, and I have not seen the PRs. So its results say what such a design permits, not what the code does. UNKNOWN for the real code.
- The substance is sound and standard: caller-supplied policy, pin, nonce set and clock cannot establish independence (T1-T3, T6); a stale independent pin proves only prefix consistency, a fresh floor catches suffix omission (T4, T4c); a floor needs sequence and hash (T5b); a single view cannot detect a fork (T9). These are the same limits that Certificate Transparency addresses with consistency proofs and gossip. I recommend citing them.
- The label **VERIFIED** is too strong: it means "demonstrated on the author's own model". Use `DEMONSTRATED_ON_REFERENCE_MODEL`. Several results are consequences of how the model was written (T1 follows from "all trust inputs are caller-supplied").
- T7, T8, T10 correctly remain hypotheses; they are checklist items to test against the real PR code. T11 (a one-line consumer adapter mapping `REVIEWABLE_ONLY` to success) is the most actionable: see recommendation R4.

## 6. Recommendations

### R1. Independent challenge oracle (what to build, and how to keep it honest)
1. A separate author (not the evaluator's author) writes a **graph-family generator**: start from a latent full graph G*, and produce the observed graph O by an explicit operator (hide edge, relabel completeness origin, alias a node, delete a log entry). Truth is G* by construction, and the generator is committed with seeds withheld until after the evaluator is frozen.
2. For each G*, emit matched variants: honest disclosure, declared-incomplete disclosure, undisclosed omission. Score every rule on all three, reporting false endorsements, missed positives and UNKNOWN rate **by variant**, with raw counts.
3. Report the **observation-identical groups** and state, per group, the policy each rule implies (N3).
4. Add baselines: constant UNKNOWN, never-promote, storage-only, and a "trusting" variant that ignores completeness flags.
5. Freeze evaluator hash, generator hash and metric definitions before generating test outputs; publish failures.
What this cannot show: that the model of the world is right. It can show what the rules do with information that is, by construction, missing.

### R2. No auto-promotion from laboratory verdict to trust (make it testable)
- A downstream-adapter test: scan the repository for code that maps a verdict (`CONDITIONAL`, `REVIEWABLE_ONLY`, `LAB_*`) to an exit code 0, to a string containing `VERIFIED`, or to an evidence-admission record; the test fails on any match without a recorded human admission record. (T11 shows the hazard; a test is the cheapest control.)
- Keep the verdict type distinct from any admission type so the two cannot be assigned from one another without an explicit conversion function that requires a human-authorization record.
- Rename the labels (N5).

### R3. Test additions (research-only, additive)
- Add the boundary tests (Appendix) to Trae's `test_w1_oracle_gap_controls.py`.
- Decide the shared-custodian rule in the spec, then replace `expectedFailure` with a real assertion.
- Run a mutation sweep (all comparisons and boundaries in `evaluate_provenance` and `_custody_for`) over both suites and record survivors; that is a cheap, systematic generalization of M1/M7/M9.

### R4. Paper text
- Abstract: say "sixteen new development trials"; say that the engine's verdict is a function of declared inputs and that three of the sixteen trials are known non-detections counted as development matches; give N3's table or a sentence from it.
- Replace "non-identifiability counterexample" with "observation-equivalence demonstration" unless a formal statement is added (the supplement §3 argument is correct and short; keep it).
- State the policy trade-off of N3 as the substantive result.
- Add the classical literature (section 7) and the CT/gossip references for the history-comparator line.

## 7. References (verification status)
- Confirmed to exist today in search results (titles, not full texts): Pan, Stakhanova, Ray (2023), ACM Computing Surveys (dblp record found); Sang et al., arXiv 2508.10639 (MirGuard); Bara, arXiv 2609.01873 (*Epistemic Sybil Resistance*; author name not confirmed by me); Li, Fan, Zhuang, arXiv 2607.02586 (*Auditing the Audit*); also Knight and Leveson (1986), Douceur (2002), Haeberlen et al. (2007) from the first report.
- To add and check before citing: Pearl (1988) on double counting; Ladha (1992) on correlated voters; common-cause failure/diversity in dependability standards; Certificate Transparency consistency/gossip papers for the history-comparator design.

## 8. What would change my assessment
A frozen, independently authored challenge generator with scores by variant (R1); a mutation sweep with survivors listed (R3); the receipt hash reconciled and the two public records (SSRN/Zenodo) declared canonical or merged; real PR #269/#271 code tested with the reference-model cases (section 5).

## Limits of this review
AI review; same model family as earlier Ario tooling; one pass; packet not equal to branch HEAD (receipt hash differs); CPython 3.13 only; CI URLs and PR pages unread; only 2 of 3 patch files applied; scoring in N3 uses the authors' own latent labels, which are metadata and not independently adjudicated.

## Appendix: boundary tests (additive, research-only)

```python
import unittest
import w1_adversarial_input_sensitivity_v1 as w

class TestCaptureOrderBoundary(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.e = w.load_pinned_engine(); cls.sep = w.build_case(cls.e)

    def test_capture_equal_to_mutation_is_not_before(self):
        c = w.replace(self.sep, mutation_sequence=2)   # captures are 1 and 2
        self.assertEqual(w.classify(self.e, c)["classification"], "UNKNOWN")
        self.assertEqual(self.e.evaluate_provenance(c).capture_order.status, "NOT_BEFORE_MUTATION")

    def test_capture_just_before_mutation_is_ok(self):
        c = w.replace(self.sep, mutation_sequence=3)
        self.assertEqual(w.classify(self.e, c)["classification"], "CONDITIONAL")
```

Results on engine variants (VERIFIED): original passes both; M7 (gate removed) fails the first; M9 (`>`) fails the first; M1 (ambiguity) is caught only by Trae's gap1 control.