# W1 Trae adversarial technical & reproducibility review — 2026-11-18

```text
REVIEWER: Trae (AI agent). Underlying model disclosed by host as "DeepSeek-V4.1-Flash". AI-ASSISTED, not human.
RUN_DATE_UTC: 2026-11-17T20:02Z (sandbox clock); reviewer-local date 2026-11-18 (Asia/Shanghai)
REVIEW_MODE: AI-ASSISTED_ADV_TRANSPARENT (NOT HUMAN PEER REVIEW)
READ_ONLY_SOURCE_HEAD_SHA: 48574e63f00bdb3d3212a09fc589b61df24b23c1 (branch research/consensus-sprint-20261116)
PRIMARY_FILES_READ: (sha256; see §2 for full table)
  implementation/witness_provenance_experiment.py  sha256 71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567 (blob 4faf010d73219af63c254097e9c135da68d60078, 26726 bytes)
  research/consensus/w1_adversarial_input_sensitivity_v1.py  sha256 8e36b1f8daccde6f6866868eca803afe5874f50f56f56c18c8d3cb98da9f9c15
  research/consensus/test_w1_adversarial_input_sensitivity_v1.py  sha256 fc516da8b69e384241064a46cf2d1d73f3b323fba08cd78d108bfc0aa4c89d98
  research/consensus/W1_SENSITIVITY_RESULTS_2026-11-17.json  sha256 24f98917ae1ca741f4cde4608d76761d44aa502721b1245687375d1d39bd7459
  research/consensus/W1_SENSITIVITY_REPRODUCE_2026-11-17.md  sha256 4d96d3576ef676dcd027fe72ffca278ac6a8468bd9a750cc1f2c79c145bff7ed
  research/consensus/W1_CI_RED_GREEN_RECEIPT_2026-11-17.md  sha256 f591a0bd21ec7afcb0a61b9bf534aef36cf1fd13983af0e979f13cb88fa37fed
  research/consensus/W1_CLAUDE_TRAE_SEPARATE_REVIEW_BRIEFS_2026-11-17.md  sha256 8c5477a3d99cd5733bb62e26810753c7c45d666ac38c7bc3430703837b87da75
  .github/workflows/w1-provenance-research.yml  sha256 c56cf328d5815a5f33f677d1d39033dd4bd457cecda07a61586638966b600265
  implementation/tests/test_witness_provenance_experiment.py  sha256 fc08f8cb6d81759100519b036aaa28443c1a16a0cb4ea76a3fafdace67268c77
TOOLS_AND_EXECUTION: sha256sum / git hash-object / wc -c; CPython 3.10.22, 3.11.17, 3.12.15, 3.13.16, 3.14.8 (pyenv); unittest; pytest 9.1.1. Exact commands and captured stdout in ./evidence/*.txt. Offline, synthetic, no network, no keys.
WHAT_REVIEWER_KNEW_BEFORE_CASE_DESIGN: I had read the evaluator, the harness and the test file before reading the results JSON. The harness source hard-codes the development expectations, so the oracle was partially visible before the JSON; separation was NOT fully possible.
NOVEL_HYPOTHESES_BEFORE_VIEWING_ORACLE: NOT_SEPARATED for the results JSON (see disclosure in §5). Three hypotheses were formed from the evaluator + input schema and are recorded verbatim in §5.0 regardless.
CLAIMS_INDEPENDENTLY_VERIFIED: (a) byte-pin 4faf010d… / 26726 B / sha256 71912958… matches; (b) exact reproduction of the 15-test suite and the 16-trial JSON oracle; (c) shared-source, shared-admin, storage-only, source-alias negatives fail-closed; (d) identically-observed bytes across opposite latent labels; (e) two mutation-testing coverage gaps that both existing suites miss.
COUNTEREXAMPLES_WITH_EXACT_INPUTS: §6 (C1b/C2b/C2c shared-custodian → CONDITIONAL), §7 (M1 ambiguous-custody UNKNOWN→CONDITIONAL; M7 capture-after-mutation UNKNOWN→CONDITIONAL). Runnable cases in ./tools/.
SEVERITY_AND_SCOPE: technical/experimental-design only. No invented CVSS. No production, signer, trust or memory impact.
PAPER_CLAIMS_TO_WEAKEN: "16/16 development matches" is self-consistency, not detection accuracy; the non-identifiability demo is a metadata tautology, not an evaluator result; false-completeness hidden dependencies are not detected.
WHAT_REMAINS_UNKNOWN: live Windows/Linux CI execution (NOT_RUN here); behavior on a real GitHub allocation; whether the 58-test implementation suite covers all admin/custody paths.
VERDICT: REVISE (research-scaffolding fixes only). Never production GO.
```

Banner: `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`.

---

## 1. Executive summary

The frozen TB-003 evaluator is **source-integral**, largely **fail-closed**, and its development results are **exactly reproducible**. I verified the byte pin independently and reproduced both the 15-test suite and the 16-trial JSON oracle byte-for-byte across CPython 3.10–3.14.

The adversarial findings are about the **harness/test scaffolding framed as evidence**, not about a broken evaluator:

- **F1 (MEDIUM):** neither the 15-test W1 fixture nor the 58-test implementation suite contains an *ambiguous-custody-transfer* row. A one-token mutation that accepts ambiguity passes **both suites** and upgrades a case from `UNKNOWN` to `CONDITIONAL`.
- **F2 (MEDIUM):** no row exercises a witness captured **after** the modeled mutation. A mutation deleting the `NOT_BEFORE_MUTATION` branch passes **both suites** and upgrades `UNKNOWN`→`CONDITIONAL`.
- **F3 (LOW–MEDIUM):** "administrative separation" ignores **shared custodians**. Two witnesses passing through one custodian still report `CONDITIONAL` (custody is checked per-witness only, never cross-compared).
- **F4 (framing):** "false completeness" (a LAB completeness attestation with a hidden dependency) yields `CONDITIONAL`; this is a disclosed model limit, yet it is one of the 16 "matches", so 16/16 is not a detection score.
- **F5 (LOW, CI):** the W1 workflow `paths` filter omits `implementation/witness_provenance_experiment.py`, so an evaluator-only PR does not trigger the byte-pin job.
- **F6 (LOW, repro):** no `.gitattributes`; Windows byte-exactness depends solely on a runner `git config`. I reproduced the reported Windows failure deterministically (LF→CRLF ⇒ `SOURCE_SIZE_MISMATCH`).
- **F7 (framing):** the "two different hidden realities, same observed input" control is a **tautology** (the latent reality is author metadata never fed to the evaluator); it is true but non-informative.

Everything is research-only; a minimal additive patch is in `w1_trae_research_only.patch`. Nothing was merged or activated.

---

## 2. Source integrity (independent verification)

Computed on a fresh `git archive HEAD` export (so no working-tree drift):

| File | sha256 | git blob | bytes |
|---|---|---|---|
| `implementation/witness_provenance_experiment.py` | `71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567` | `4faf010d73219af63c254097e9c135da68d60078` | 26726 |

- `git hash-object implementation/witness_provenance_experiment.py` → `4faf010d73219af63c254097e9c135da68d60078` — **matches the pin**.
- Recomputed `sha1("blob 26726\0" + bytes)` → `4faf010d…` and `sha256(bytes)` → `71912958…` — **match**.
- `sha1sum(file)` = `0fb9b6b88b9b7d3856be6b1db97c005753187cb0` (raw-file SHA-1; **not** the Git blob — expected difference, do not confuse).
- Working tree clean at `48574e63`; no `.gitattributes`; `core.autocrlf` unset locally.
- The harness re-verifies size → sha256 → git blob **before** `exec(compile(source))`, and executes the *same verified bytes* (`w1_adversarial_input_sensitivity_v1.py:29-46`). Verified by reading and by tamper tests.

**Test T-source-integrity: PASS.**

---

## 3. Reproduction (disposable offline environment)

Environment: `git archive HEAD | tar -x -C /tmp/w1_repro` (read-only export of `48574e63`). No network used by any script (imports are stdlib only: `argparse, dataclasses, hashlib, json, pathlib, random, sys, types`).

| # | Test | Command (from repo root) | Result |
|---|---|---|---|
| R1 | W1 fixture, Python 3.14.8 | `PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s research/consensus -p 'test_w1_adversarial_input_sensitivity_v1.py' -v` | **PASS** — 15 tests OK (exit 0) |
| R2 | Harness CLI aggregate | `PYTHONDONTWRITEBYTECODE=1 python -B research/consensus/w1_adversarial_input_sensitivity_v1.py` | **PASS** — `{"designed_trials":16,"development_expectation_matches":16,"hidden_dependency_conditional":3,"hidden_dependency_trials":3,"permutation_checks":192}` |
| R3 | Fresh JSON vs committed oracle | `… --json-out /tmp/w1-new-results.json` then structural compare | **PASS** — `FRESH==COMMITTED: True` (all 16 trials, all fields) |
| R4 | Fixture on 3.10.22 / 3.11.17 / 3.12.15 / 3.13.16 / 3.14.8 | same discover command per interpreter | **PASS ×5** — 15 tests OK each |
| R5 | 58-test implementation suite baseline | `cd implementation && python -m pytest -q tests/test_witness_provenance_experiment.py` | **PASS** — 58 passed |
| R6 | `--json-out` refuses overwrite | `… --json-out <existing>` | **PASS** — exit 2, "must not overwrite existing evidence" |
| R7 | `--json-out` requires existing parent | `… --json-out /tmp/nope/x.json` | **PASS** — exit 2, "parent must already exist" |
| R8 | Windows 2022 GitHub job | live CI | **NOT_RUN** (no allocation; emulated — see §8) |
| R9 | Reproduce remote run URLs | — | **NOT_RUN** (no network/credentials; receipt text only) |

Evidence: `evidence/01..04, 08`. **R1–R7 PASS; R8–R9 NOT_RUN.**

---

## 4. Negative controls — separation axes

Cases built on the pinned `build_case` (source/admin/storage/capture/custody axis), each varying the intended causal property. Full logs: `evidence/05`.

| ID | Control (intended truth) | Expected safe verdict | Observed | Verdict |
|---|---|---|---|---|
| C1 | concealed shared source | not `LAB_CONDITIONALLY_DISTINCT` | `COMMON_SOURCE_DETECTED` → DEPENDENT | **PASS** |
| C3 | common root via `SHARES_CONTROL_ROOT` | detected | `COMMON_CONTROL_DETECTED` → DEPENDENT | **PASS** |
| C4 | common root via transitive `ADMINISTERS` (root-m→a, root-m→b) | detected | `COMMON_CONTROL_DETECTED` → DEPENDENT | **PASS** |
| C5 | source alias (distinct id, same `object_identity`) | detected | `COMMON_SOURCE_DETECTED` → DEPENDENT | **PASS** |
| C6b | transitive shared source (capture→mid→source-a) | detected | `COMMON_SOURCE_DETECTED` → DEPENDENT | **PASS** |
| C7 | storage-only shared object | detected | `SAME_STORAGE_OBJECT` → DEPENDENT | **PASS** |
| C8 | ambiguous custody (two sequenced routes to holder) | `UNKNOWN` | `UNKNOWN` | **PASS** |
| duplicate witness refs | `UNKNOWN`/invalid | `INVALID_ARTIFACT_OR_COMPROMISE_REFERENCE` | **PASS** |
| missing custody transfer | `UNKNOWN` | `UNKNOWN` | **PASS** |
| C10 | candidate-authored graph (origin `CANDIDATE`) | fail-closed | all axes `UNKNOWN` | **PASS** |
| C9 | false completeness (hidden shared source, LAB-declared complete) | not promoted | `CONDITIONAL` | **FAIL (known limit, F4)** |
| C1b | **shared final holder** (one custodian holds both witness artifacts) | not promoted to separation | `LAB_CHAIN_PRESENT×2` → `CONDITIONAL` | **FAIL (F3)** |
| C2b | **shared initial capture custodian** | not promoted | `CONDITIONAL` | **FAIL (F3)** |
| C2c | **shared intermediate custodian** on both chains | not promoted | `CONDITIONAL` | **FAIL (F3)** |

Interpretation: source, administration, storage and capture-order dependencies are detected (or fail closed) as claimed. The evaluator has **no cross-witness custody-separation axis**: a single custodian or a shared custody hop across both witnesses is invisible, and the verdict stays `CONDITIONAL`. `CONDITIONAL` is explicitly not an independence claim, so this is a **modeling gap / unstated assumption** (F3), not a false "independent" verdict — but the paper must not imply custody independence is tested.

---

## 5. Non-identifiability challenge

### 5.0 Hypotheses recorded from the evaluator + input schema
H1: two *different* hidden realities can yield **byte-identical** observed graphs, so a `CONDITIONAL` verdict is under-determined. H2: some dependency axis (custody in particular) is not cross-compared, so a real shared fact stays `CONDITIONAL`. H3: mutating the evaluator's decision logic will not be caught because the "16/16" oracle checks only self-authored labels.

### 5.1 Disclosure
The harness source **contains the expected labels** (`build_trials`, lines 152-169) and the tests import them, so a clean blind separation from the oracle was **impossible**. I read the results JSON after forming H1–H3.

### 5.2 Result
`serialize_case(honest-separate) == serialize_case(hidden-source-false-complete) == serialize_case(hidden-admin-false-complete) == serialize_case(hidden-source-admin-false-complete)` is **True**; all four carry `reported_graph_sha256 = fbc9a0267c0334d7f32bb87b0219f78e4febf7a342501cbd7da77b216b41813d`. So H1 is **CONFIRMED** — but the "hidden reality" exists **only as author metadata** (`latent_relation`, `mechanism`, `expected_development`), which is **never** in the serialized evaluator input (verified: none of the strings `latent`/`expected`/`mechanism`/`passes_dev` appear in the serialized case). The control therefore demonstrates that the **input format is under-determined**; it does **not** demonstrate an evaluator behavior, and equality of observations is **not** a software bug. The evaluator's actual output is the same safe `CONDITIONAL` on both, i.e. it does not falsely assert independence.

**Verdict H1: confirmed-true but tautological (F7).** Do not cite it as evidence the system *detects* hidden dependencies.

---

## 6. Mutation testing — does either suite detect incorrect decisions?

Method: for each mutation, (i) confirm the on-disk byte-pin rejects the tampered file (`PIN_REJ`), (ii) bypass the pin by `exec`-ing the mutated source into a module and run the **16-trial oracle** (`W1_ORACLE`), (iii) run the **58-test implementation suite** (`IMPL58`), (iv) show **concrete drift** on a crafted negative control. Full table: `evidence/06`.

| Mutation | PIN_REJ | W1 oracle | IMPL58 | Concrete drift |
|---|---|---|---|---|
| M1 accept ambiguous custody (`!=1`→`<1`) | yes | **not_caught** | **not_caught** | ambiguous: `UNKNOWN`→`CONDITIONAL` |
| M2 invert storage SAME/DISTINCT | yes | CAUGHT | CAUGHT | many |
| M3 drop LAB-origin filter on sources | yes | not_caught | not_caught | **none (dead code)** |
| M4 drop control-surface completeness gate | yes | CAUGHT | CAUGHT | incomplete_ctl `UNKNOWN`→`CONDITIONAL` |
| M5 remove common-control detection | yes | CAUGHT | CAUGHT | shared_admin `DEPENDENT`→`CONDITIONAL` |
| M6 accept multiple holders | yes | not_caught | **CAUGHT** | dup_holder `UNKNOWN`→`CONDITIONAL` |
| M7 remove capture-order gate | yes | **not_caught** | **not_caught** | capture_after `UNKNOWN`→`CONDITIONAL` |

- **F1:** M1 escapes **both** suites (`INVALID`-free, ambiguous custody accepted). Root cause: no fixture/TP row has two strictly-sequenced `TRANSFERRED_TO` routes to the holder. `W1_SENSITIVITY_RESULTS` has no such trial; the implementation suite has none either.
- **F2:** M7 escapes **both** suites. Root cause: no row has `capture_sequence >= mutation_sequence` (all fixtures use `mutation_sequence=10`, captures 1/2). The `NOT_BEFORE_MUTATION` branch is effectively untested.
- M3 is **inert** (the source walk only traverses `lab_edges`, already LAB-origin-restricted) → **REJECT** as a non-finding (honest).
- The built-in `test_mutant_detector_proves_test_is_sensitive` (UNKNOWN→CONDITIONAL) **is** caught — but it only proves sensitivity to that one mutation.
- **Important:** row `PIN_REJ=yes` is the byte-pin refusing tampered bytes — a genuine strength, but it must not be confused with oracle sensitivity (the on-disk suite cannot even start on a mutated file; the M1/M7 "not_caught" columns come from the pin-bypassed exec path).

**Verdict: the fixture oracle is incomplete for the custody-ambiguity and capture-order decision boundaries (F1, F2) — FAIL for oracle completeness.**

Additional strong checks (`evidence/07`): full-report permutation stability = **192 permutations, 0 mismatches** (stronger than the suite's classify-only assertion); honest dependencies → `DEPENDENT`; honest incompleteness → `UNKNOWN`. **PASS.**

---

## 7. Windows / Linux reproducibility

- The pinned reader opens the file `"rb"` and compares exact size — so any EOL translation breaks the pin.
- **Deterministic reproduction** of the reported Windows failure (`evidence/04`): converting the pinned file LF→CRLF (26726 → **27281** bytes) yields `ValueError: SOURCE_SIZE_MISMATCH`. Matches the receipt's `SOURCE_SIZE_MISMATCH` at `runs/44157654647` (Windows 3.11/3.13 FAILURE).
- The applied fix `git config --global core.autocrlf false` (commit `6efa093f…`, present in `.github/workflows/w1-provenance-research.yml:21-22`) is sufficient for the current repo because there is **no `.gitattributes`**. It is **fragile**: it depends on runner git state and on no future `* text=auto`. A `.gitattributes` rule (`… -text`) makes byte-exactness intrinsic to the repo (patch).
- The pin failing **closed** (refusing to load) is correct security behavior.
- Live Windows/Linux GitHub execution: **NOT_RUN** (no allocation/credentials in this sandbox). All cross-interpreter runs here are Linux.

---

## 8. Hidden assumptions, leakage, oracle quality

- **No leakage into the evaluator:** `build_trials` passes only `ProvenanceCase`; `latent_relation`/`expected_development`/`mechanism` are harness metadata, absent from the serialized input (verified §5.2). The results JSON *outputs* them — that is output disclosure, not input leakage. **PASS.**
- **Weak oracle, honestly labelled:** `scientific_status = AUTHOR_BUILT_DEVELOPMENT_FIXTURES_NOT_BLINDED_OR_INDEPENDENT` and the reproduce doc warn it is not a benchmark. Risk: the aggregate keys (`development_expectation_matches`, `designed_trials`) can be quoted as a 16/16 "pass rate". One of the 16 "matches" is a **known non-detection** (false-completeness → `CONDITIONAL`).
- **False completeness:** `complete_source_surface/complete_control_surface` with `completeness_origin=LAB` is trusted as a boolean with no cryptographic binding; a case that *falsely* asserts LAB completeness hides a dependency and still returns `CONDITIONAL`. Disclosed in code, but should be stated as a binding assumption in the paper.
- **CI coverage:** the W1 workflow runs only on changes to the harness/test/workflow (`.github/workflows/w1-provenance-research.yml:4-7`); it omits the pinned evaluator. The 58-test implementation suite runs on all PRs (ubuntu, py3.13) but does **not** verify the byte pin. So an evaluator-only PR would not run the pin job (**F5**).
- **Implementation cleanliness:** `_paths` overflow, `_reachable_cycle`, bounded custody walk (`MAX_CUSTODY_WALK_VISITS=4096`), duplicate-node/edge rejection, and typed fail-closed returns all behave as documented; no unexpected state mutation observed; default run has **no on-disk side effects** (only opt-in `--json-out`).

---

## 9. Findings register

| id | defect | severity | source SHA | reproduction | status | proposed fix |
|---|---|---|---|---|---|---|
| F1 | Oracle lacks ambiguous-custody row; M1 escapes W1+IMPL suites (UNKNOWN→CONDITIONAL) | MEDIUM | 48574e63 | evidence/06, tools/final_battery.py | **FIX (patch)** | additive test `test_gap1_ambiguous_custody_transfer_is_unknown` |
| F2 | Oracle lacks capture-after-mutation row; M7 escapes both suites (UNKNOWN→CONDITIONAL) | MEDIUM | 48574e63 | evidence/06 | **FIX (patch)** | additive test `test_gap2_capture_after_mutation_is_unknown` |
| F3 | Shared custodian across witnesses not modeled (C1b/C2b/C2c → CONDITIONAL) | LOW–MED | 48574e63 | evidence/05 | **REVISE (disclose)** | document as unmodeled axis; optional expectedFailure marker |
| F4 | False-completeness hidden dependency not detected; 16/16 ≠ detection | NOTE | 48574e63 | evidence/05, verify_extra | **REVISE (framing)** | state the trusted-attestation assumption; relabel aggregate |
| F5 | W1 workflow `paths` omits the pinned evaluator | LOW | 48574e63 | evidence/06, workflow L4-7 | **FIX (patch)** | add evaluator + `.gitattributes` to `paths` |
| F6 | No `.gitattributes`; Windows byte-exactness depends on runner config | LOW | 48574e63 | evidence/04 | **FIX (patch)** | add `implementation/… -text` |
| F7 | Non-identifiability demo is a metadata tautology | NOTE | 48574e63 | evidence/07 | **REVISE (framing)** | downgrade the claim to "input under-determination" |
| — | M3 source-filter removal | none | 48574e63 | evidence/06 | **REJECT (inert)** | none |
| — | byte-pin integrity & fail-closed | positive | 48574e63 | evidence/01-04 | **PASS** | none |

No finding affects production, signer, keys, trust, memory, or `main`.

---

## 10. Minimal proposed fix — research-only patch

`w1_trae_research_only.patch` (114 lines, **additive**; does not touch the frozen evaluator, the existing 16-trial fixture, `W1_SENSITIVITY_RESULTS_*.json`, or `main`):

1. `.gitattributes` — `implementation/witness_provenance_experiment.py -text` (byte-exact across OSes; fixes F6 root cause).
2. `.github/workflows/w1-provenance-research.yml` — add `implementation/witness_provenance_experiment.py`, `.gitattributes`, and the new test file to `paths` (fixes F5).
3. `research/consensus/test_w1_oracle_gap_controls.py` — additive controls closing F1/F2 (assert `UNKNOWN` for ambiguous custody and capture-after-mutation) plus a documented `expectedFailure` for F3. Verified: **3 tests, OK (expected failures=1)** on the correct evaluator; the gap1 control **catches M1** and the gap2 control **catches M7** under pin-bypass exec (`evidence/09`, §6).

Apply with `git apply w1_trae_research_only.patch` on a **draft** branch only. Do not merge or activate.

---

## 11. What remains UNKNOWN

- Live Windows 2022 and GitHub-hosted runs (NOT_RUN): the CRLF→SIZE_MISMATCH mechanism is reproducible here, but the actual remote job logs were not fetched.
- Whether the 58-test implementation suite fully covers all `ADMINISTERS`/`RESTORES_FROM`/custody paths (I sampled, not exhaustive).
- Whether reviewers accept F3/F4 as disclosures vs. required model changes.
- Any real-certification meaning of `CONDITIONAL` in production (none claimed; `PRODUCTION=NO_GO`).

---

## 12. Verdict

**REVISE** — research scaffolding only. The pinned evaluator and its results are integral and reproducible, and most separations fail closed, but two decision boundaries (ambiguous custody, capture-order) are untested by both suites and silently upgradable, and shared custody is unmodeled. Apply the additive patch on a draft branch for review; do not merge or activate anything.

Banner: `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`.

---

### Appendix — evidence index
```
evidence/01_repro_unittest.txt            R1 (Python 3.14, 15/15 OK)
evidence/02_repro_and_json_equality.txt   R2/R3 (aggregate + FRESH==COMMITTED True)
evidence/03_cross_version.txt             R4 (3.10–3.14 ×15 OK)
evidence/04_windows_crlf.txt              R8-emulation (CRLF -> SOURCE_SIZE_MISMATCH)
evidence/05_negative_controls.txt         §4 (C1..C10, C1b/C2b/C2c, C11)
evidence/06_mutation_battery.txt          §6 (M1..M7 table)
evidence/07_verify_extra.txt              §5/§6 (bytes-identical, no leakage, 192/0 perms)
evidence/08_impl_suite_baseline.txt       R5 (58 passed)
evidence/09_patch_controls.txt            §10 (patch controls 3 tests OK)
tools/*.py                                runnable reproductions
w1_trae_research_only.patch               additive research-only patch
```