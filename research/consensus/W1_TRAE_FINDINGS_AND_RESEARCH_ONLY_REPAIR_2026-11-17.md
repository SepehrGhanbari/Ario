# W1 — Trae AI-assisted technical review: F1–F7 adjudication and bounded repair
**Intake timestamp:** 2026-11-17 UTC (reviewer's local report date: 2026-11-18 Asia/Shanghai)  
**Status:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`  
**Origin:** owner-supplied Trae report, AI agent reported as DeepSeek-V4.1-Flash. This is **not human peer review, a blind independent holdout, nor a real-world independent witness.**

## Complete provenance and limitations
- **Verbatim uploaded review, archived & read back without a character change:** [W1_TRAE_REPORT_2026-11-18_VERBATIM.md](W1_TRAE_REPORT_2026-11-18_VERBATIM.md), Git blob `5db6920c695d1544bf17de697e8f402db63efb45`.
- Trae inspected HEAD `48574e63f00bdb3d3212a09fc589b61df24b23c1` (not the later PR #242 head) but its pinned TB-003 evaluator blob `4faf010d73219af63c254097e9c135da68d60078`, 26,726 bytes, SHA-256 `71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567` matches the source on this research branch.
- Trae's report states local Python 3.10–3.14 replays passed, a 58-test implementation replay passed, and F1/F2 mutation gaps were observed **in its sandbox**. R8/R9 live GitHub CI checks are marked `NOT_RUN` by Trae. Its results and paths in the report remain reviewer claims until exact supporting artifacts are received and checked.
- **Critical artifact limitation:** user supplied the full markdown report **only**. The named `w1_trae_research_only.patch`, `evidence/01..09*.txt` and `tools/*.py` were **not included in the upload**. Therefore this commit does **not** claim Trae's original patch has been received, byte-compared, or applied. The research controls below are separately reconstructed from the report and actual source, not a verbatim Trae patch.

## Source-grounded adjudication table

| ID | Trae report and source observation | Adjudication | Evidence/next condition |
| --- | --- | --- | --- |
| F1 | `_custody_for` requires exactly one strictly sequenced transfer path; mutation `len(options) != 1`→`< 1` would improperly accept two. | **ACCEPT / FIX_TEST_COVERAGE:** new independent additive ambiguous-custody case. No change to evaluator. | [new tests](test_w1_trae_boundary_controls_v1.py); local pinned source test PASS; deliberate in-memory M1 mutation causes exactly one new test FAIL. |
| F2 | For capture-after-mutation, `capture_order` should be `NOT_BEFORE_MUTATION`, and final class should be UNKNOWN. Existing 16 test inputs do not exercise this boundary. | **ACCEPT / FIX_TEST_COVERAGE:** new capture sequence 11, transfer sequence 12, mutation sequence 10 to keep custody valid and isolate capture timing. | Local pinned source test PASS; deliberate in-memory M7 branch-elimination causes exactly one new test FAIL. |
| F3 | Both witnesses can have separate valid custody chains but the **same custody node**; current report checks paths per-witness and does not cross-compare custodians. | **ACCEPT AS OPEN MODEL GAP:** only `@unittest.expectedFailure` documents that a stronger UNKNOWN policy is not currently implemented; this is **not** a fixed bug nor a passed cross-custody security property. | Cannot be a GO gate until model/policy design with independent reviewer and tests; no evaluator edit here. |
| F4 | False-completeness cases can still receive CONDITIONAL. | **ACCEPT AS INPUT TRUST BOUNDARY:** no graph supplied by an interested party authenticates its own completeness. | Existing Nov17 extension demonstrates the limitation; no claimed attack rate, no production corroboration. |
| F5 | Workflow path filter omitted `implementation/witness_provenance_experiment.py` so evaluator-only changes might skip pin job. | **PATCHED IN RESEARCH WORKFLOW** to add evaluator, new test, and `.gitattributes` to `on.pull_request.paths`, and to run the new test. | GitHub file read-back verified; remote CI outcome still requires actual completed job receipt. |
| F6 | Windows checkout EOL risk; no `.gitattributes` for pinned source. | **PATCHED ONLY THIS SOURCE FILE**: root `.gitattributes` entry `implementation/witness_provenance_experiment.py -text`; preserves committed byte image on Windows checkout. | Repo config replaces reliance on runner-only checkout configuration; need Windows CI readback, do not claim that yet. |
| F7 | Different latent labels, same observed serialized input is a tautological equality. | **ACCEPT SCIENTIFIC REFRAMING:** `input under-determination` is accurate; the controlled equality itself says nothing about successful detection of hidden dependencies. | Manuscript must not conflate developer metadata with independently authenticated latent truth. |

**Trae's M3** ("drop LAB-origin filter") was inert in the observed test route; **REJECT as a finding**, preserve reviewer analysis. All pin-rejection results protect bytes but must not be counted as mutation-test oracle kills.

## Actual follow-up carried out in this intake

- Read and verified the pinned original TB-003 source from the research copy (same SHA-256 and Git blob as GitHub); did **not** alter evaluator.
- New additive [test_w1_trae_boundary_controls_v1.py](test_w1_trae_boundary_controls_v1.py): local `unittest` **3 tests run, 2 normal PASS, 1 expectedFailure** (F3 still open).
- In disposable local in-memory mutation execution, an M1 `!= 1`→`< 1` change caused **the F1 test to FAIL**; an M7 removal of the capture-after branch caused **the F2 test to FAIL**. Each variant: 3 tests run, 1 failure, 1 expected failure. The mutations were executed from altered bytes in a transient module only, not saved into Ario's core or a repository branch. This is a **different patch/test implementation** from Trae's unseen original, not a literal reexecution of its `tools/` artifacts.
- Original 15 W1 local tests still pass separately; the 3-test extension passed with one **explicit expected failure**. That is 17 ordinary passing assertions/tests and one documented expected failure across these two suites, **not** 18/18 positives and not a security accuracy rate.
- Workflow now invokes both named suites in GitHub Actions matrix jobs and watches changed evaluator/attrs/test paths. When a new workflow run completes, inspect actual jobs and logs before claiming GitHub PASS.
- **No** new hidden/development trial rows or metrics silently inserted into the original sixteen-scenario JSON; `main`, signer, real keys, memory authority and journal remain unchanged.

## Combined Claude + Trae manuscript implications

- Claude's [major-revision report](W1_CLAUDE_REFEREE_REPORT_2026-11-17_VERBATIM.md) raises the circular original 4/16 versus 16/16 comparison and the constant-UNKNOWN baseline 7/16. Trae confirms the original W1 counterexamples are input-model limits and finds F1/F2 *test coverage* omissions; the two AI reports overlap in their central critique, but this is **not statistically independent or human peer review**.
- New paper wording should say *transparent decision-boundary demonstration with authenticated-input assumptions not fulfilled*, rather than comparative detection accuracy, and explicitly declare absent cross-witness custody checks and no accepted external oracle.
- The already-shared original manuscript remains untouched under its existing journal review; any future publication of these additions requires a clearly versioned separate article/addendum and human author review. No inference of journal endorsement.

## Next blocking tasks
1. Obtain reviewer original patch+tools+raw evidence if exact reproduction is required; archive them separately and hash before use.
2. CI: verify completed matrix run on the **current exact PR HEAD**, including new test output, and preserve Windows/Linux outcomes.
3. F3: design a **separate** explicit custody-independence policy and adversarial negative controls. Avoid treating a shared physical custodian as an authenticated fact from labels alone.
4. Scientific manuscript: add constant-UNKNOWN baseline and class-level coverage/abstention, run matching-baseline comparisons if making comparative empirical claims; preserve no-field-validation caveat.
5. Keep W1 PR DRAFT/HOLD; do **not** activate signer, grant authority, modify historical source or merge.
