# W1 Trae focused adversarial third-pass review — 2026-11-18

```text
REVIEWER: Trae (AI agent). Underlying model disclosed by host as "DeepSeek-V4.1-Flash". AI-ASSISTED, not human.
RUN_DATE_UTC: 2026-11-17T20:4x Z (sandbox clock); reviewer-local date 2026-11-18 (Asia/Shanghai)
REVIEW_MODE: AI-ASSISTED_ADV_TRANSPARENT (NOT HUMAN PEER REVIEW) / FOCUSED_THIRD_PASS
BANNER: RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO

READ_ONLY_SOURCE_HEAD_SHA: dcac42fcb1409d3befdab5ab968d03a695769b5d
  (= PR #242 head, branch research/consensus-sprint-20261116, verified twice:
   git ls-remote 2026-11-17 this session, and GitHub API pulls/242 head.sha)
PRIOR_HEAD_UNDER_TEST_IN_FIRST_PASS: 48574e63f00bdb3d3212a09fc589b61df24b23c1 (superseded; NOT re-reviewed)
W1 FILES ARE BLOB-IDENTICAL between f179e71c8f1d99c55eda90231005f68a9c6e7aa9 (CI run 44170674792 head)
  and dcac42f: compare/f179e71...dcac42f -> ahead_by 6, changed files are W22 + brief + adjudication only;
  none of the W1 evaluator / harness / boundary tests / workflow appear in the delta.

PRIMARY_FILES_READ_AND_HASHED_AT_TIP dcac42f (sha256 | git-blob | bytes):
  implementation/witness_provenance_experiment.py
      71912958bad6db97218ac630cadee6c34c04b286aec99b3f7cda071f8d79f567 | 4faf010d73219af63c254097e9c135da68d60078 | 26726
  research/consensus/w1_adversarial_input_sensitivity_v1.py
      8e36b1f8daccde6f6866868eca803afe5874f50f56f56c18c8d3cb98da9f9c15 | 0a98640c22e0bbea700d6bdf6772e66b311cc99c | 12829
  research/consensus/test_w1_adversarial_input_sensitivity_v1.py
      fc516da8b69e384241064a46cf2d1d73f3b323fba08cd78d108bfc0aa4c89d98 | 415bdd9f042480ca09a701af27e53e2aea1d6b09 | 5387
  research/consensus/test_w1_trae_boundary_controls_v1.py
      90d7c1e6257bc3a18d7c8c9a5c0e51135c011097a92dded990dc0a9bece47280 | 825689ba0045f85705a1f8dd6a47cd421920ddcb | 3894
  research/consensus/W1_SENSITIVITY_RESULTS_2026-11-17.json
      24f98917ae1ca741f4cde4608d76761d44aa502721b1245687375d1d39bd7459 | f1a4a7eb24d013acd2d586b268d524f8b75b533e | 17931
  research/consensus/W1_CLAUDE_SECOND_PASS_REPORT_2026-11-17_VERBATIM.md
      474a03e478e97f465bda19061f5532d4487d193d978df314fef807d4a7923ada | 9131f6a619b5359fd6c6cbbfbbed011ce3444066 | 19646
  research/consensus/W1_CI_RED_GREEN_RECEIPT_2026-11-17.md (branch edition)
      f591a0bd21ec7afcb0a61b9bf534aef36cf1fd13983af0e979f13cb88fa37fed | 6b449ebc2adc780f3756fac3be7af99c13525df6 | 1522
  research/consensus/W1_CI_RED_GREEN_RECEIPT_OFFLINE_PACKET_VARIANT_2026-11-17.md (offline-packet edition)
      6ea6e4aedd8bef4836b715237846727f6d396d64b00e61c9698d6c1b51f1b12c | 4b088282d966a5c3d69194daf105518692e2eaf9 | 2161
  .github/workflows/w1-provenance-research.yml
      5fd39c05a691c5213f8aa3d8307d967d2b62b8d26fedc8f08b6e47e6922d0d3a | 198e9d50dd91840c3f2b1807156c9bb284737330 | 1536
  .gitattributes
      d3d15441c79c35302a1e5755b6730e0cfbb962c033936a5fc91745ddba9d8741 | 5ff82401dc2a3eb06b92c8a38ce5c9c0c963a7a9 | 219
  HISTORIC evaluator at paper pin f562e14cd8ca7f8723ad0b94eec005025f07a9a6
      (extracted) sha256 3c1f7019342319546d945de5a6cb4d46c7e7382e61b06b84e7577caa12f48ea1 | blob b49b5fa6489a97a31a7056bf2fd8b1c6f2c03139 | 23876
  => historic blob != current blob; these are NOT the same engine (confirms brief §18 and resolves Claude F8: the answer is NO).

TOOLS_AND_EXECUTION: sha256sum / git hash-object / stat / git ls-remote / curl (proxy 127.0.0.1:18080) / python3 CPython 3.14.8 / pytest 9.1.1.
  No evaluator, signer, trust, main, manuscript or author-rights file was modified. All mutants ran in isolated in-memory copies.
WHAT_REVIEWER_KNEW_BEFORE_DESIGN: third pass. I had already read the frozen evaluator, the harness (hard-coded expectations) and both test files in the first pass,
  and Claude's second-pass report before designing the battery. Separation from the oracle was NOT achievable and is not claimed.
CLAIMS_INDEPENDENTLY_VERIFIED: M9 killed by exactly one test; five-policy table (4 of 5 rows reproduce, storage-only does not); observation-identical groups;
  F3 shared-custodian non-separation; cross-engine classification identity; CI run conclusions via API.
WHAT_REMAINS_UNKNOWN / NOT_RUN: GitHub raw job-log CONTENT (HTTP 403 "Must have admin rights"); author external ground-truth adjudication for latent labels;
  the 58-test implementation suite; the historic R5NOV-16 scenario set (not re-run here); the reference-model r5_counterexamples.py.
VERDICT: REVISE (research-scaffolding only). M9 boundary control accepted with one hardening. Storage-only row of Claude N3 must be corrected.
  Never production GO.
```

---

## 1. Executive summary

This third pass is **focused**, not a repeat. I re-verified only the new boundary claims and the disputed numbers against the **current** branch HEAD that Claude and the brief both referenced.

Findings, ordered by materiality for the research record:

- **T1 — M9 off-by-one: CONFIRMED, but guarded by a single test.** Mutating `elif any(c >= case.mutation_sequence ...)` → `>` (M9) is killed by **exactly one** named test: `test_gap2_capture_equal_mutation_is_unknown`. Nothing else in the W1 set or the boundary set catches it. The two newly added boundary tests are genuine (not tautological) and mutation-sensitive, but the equality case rests on **one** guard and on hard-coded capture sequences, so the guard is fragile in a way the file does not declare.
- **T2 — Five-policy table: 4 of 5 rows reproduce exactly; the storage-only row does not.** Pinned gate 16/16 / 3 false-end / 0 missed-positive / 7 UNKNOWN, never-promote 11/16 / 0 / 2 / 12, constant-UNKNOWN 7/16 / 0 / 2 / 16, constant-DEPENDENT 4/16 / 0 / 2 / 0 all reproduce. Claude's **storage-only row (6/16, 11, 0, 1) does not reproduce under any rule that depends only on the storage axis** (exhaustive check: none of the 3²=9 storage-axis-only mappings match; three natural re-implementations give 5/16–7/16). The storage axis is in fact **degenerate on this set** (14/16 `LAB_DISTINCT_OBJECTS`, 2/16 `UNKNOWN`), so "storage-only" carries almost no discriminative information here.
- **T3 — Observation-identical groups: CONFIRMED exactly.** The four-trial group {`honest-separate`, `hidden-source-false-complete`, `hidden-admin-false-complete`, `hidden-source-admin-false-complete`} plus the two pairs all serialise to identical bytes; a deterministic function of the input cannot separate them. This is a **policy** result, not an accuracy result.
- **T4 — Shared-custodian F3: CONFIRMED non-separated.** Shared initial, middle and final custodian all stay `CONDITIONAL`; only a *scenario compromise* flag flips to `UNKNOWN`, and it does so even for a non-shared custodian. Do **not** silently redefine `DEPENDENT`; the correct minimal move is a **separate custody-correlation axis** (proposed, research-only).
- **T5 — Historic vs W1 engine: NOT the same engine, and the W1 cases are engine-agnostic.** All 16 W1-DEV trials classify identically under historic blob `b49b5fa6` and current `4faf010d`. Both carry the `>=` boundary; the historic engine lacks `MAX_CUSTODY_WALK_VISITS`. I did **not** pool R5NOV-16 with W1-DEV-16.
- **T6 — CI: verified by API (not logs).** Run `44170674792` = completed/success, head `f179e71`, four jobs success (windows/ubuntu × 3.11/3.13), each running both W1 steps to success. Latest tip run `44171922201` (head `dcac42f`) also success with four W1 jobs. **Raw log CONTENT is NOT_RUN** (HTTP 403, admin-only).
- **T7 — Receipt reconciliation: two genuinely different editions, not a collision.** `f591a0bd…` (1522 B) and `6ea6e4ae…` (2161 B) are distinct files with distinct text; retain both.
- **T8 — Latent-graph challenge scaffold (research-only, proposed).** A latent `G*` + masking operator `O` generator, scored by variant. It demonstrates that the pinned rule produces 3 false endorsements on an *undisclosed-omission* variant that is byte-identical to an honest case where it produces 0 — i.e. no input-only rule can be credited with separating these. **Precisely what remains unproven:** the latent truth is still author-declared; there is no independently adjudicated oracle.

No defect in the frozen evaluator was found that breaks its declared semantics. The issues are in what the *evidence scaffolding* is allowed to claim.

---

## 2. What was actually executed (commands, and status)

All commands below were run this session. Evidence captured verbatim in `./evidence/`.

| # | Command | Result | Status |
|---|---|---|---|
| R1 | `python3 -m pytest research/consensus/test_w1_adversarial_input_sensitivity_v1.py -q` (tip) | `15 passed, 13 subtests passed` | PASS (run) |
| R2 | `python3 -m pytest research/consensus/test_w1_trae_boundary_controls_v1.py -q` (tip) | `4 passed, 1 xfailed` | PASS (run) |
| R3 | `python3 research/consensus/w1_adversarial_input_sensitivity_v1.py` (tip) | `{"designed_trials":16,"development_expectation_matches":16,"hidden_dependency_conditional":3,"hidden_dependency_trials":3,"permutation_checks":192}` | PASS (run) |
| R4 | `python3 tools/mutation_battery.py` (pin-bypassed exec) | baseline 20 tests / 1 xfail; M1–M11 matrix | RUN (see §3) |
| R5 | `python3 tools/policies.py` | five-policy table + identical-groups | RUN (see §4) |
| R6 | `python3 tools/f3.py` | shared-custodian probe | RUN (see §5) |
| R7 | `python3 tools/cross_engine.py` | historic vs current on W1-DEV-16 | RUN (see §6) |
| R8 | `python3 -m pytest tools/w1_custody_correlation_probe.py -v` | `5 passed, 1 xfailed` | PASS (run) |
| R9 | `python3 -m pytest tools/w1_latent_graph_challenge_v0_1.py -v` | `4 passed` | PASS (run) |
| R10 | `curl api.github.com/.../actions/runs/44170674792` + `/jobs` | 200; success; 4 jobs success | RUN (§7) |
| R11 | `curl api.github.com/.../actions/jobs/<id>/logs` | 403 "Must have admin rights" | **NOT_RUN** (content) |
| R12 | `sha256sum` / `git hash-object` / `stat` on 10 W1 files + historic | all recorded above | RUN |
| R13 | `git ls-remote` + compare `f179e71...dcac42f` | tip `dcac42f`; ahead_by 6; only W22/brief files changed | RUN |

The `test_w1_*` suites and harness were executed from the tip export (`/tmp/w1_tip`). Notably, `tools/` scripts intentionally import `/tmp/w1_p3/research/consensus` (first-pass export at `3459ebd`) because the W1 files are blob-identical at that ancestor; this is stated so the path is auditable, not hidden.

---

## 3. T1 — M9 boundary verification (priority A)

**Mutation method.** The frozen evaluator is byte-pinned (`load_pinned_engine` re-verifies size + SHA-256 + Git blob, then `exec(compile(...))` on the same bytes). To separate **byte-pin rejection** from **oracle sensitivity**, each mutant is compiled from mutated source into an isolated module object and injected via monkeypatch of `w.load_pinned_engine`, so the pin never sees the muted bytes. `test_ids()` counts only `failures + errors`; the designed `@expectedFailure` (gap-3) is excluded from kills and reported separately.

**Baseline (unmutated, pin-bypassed):** `testsRun=20 failures=0 errors=0 expectedFailures=1`.

**Mutation matrix (kills = named tests that FAIL under the mutant):**

| Mutant | Change | PIN_REJ | behavioral kills |
|---|---|---|---|
| M1 accept ambiguous custody | `len(options) != 1` → `< 1` | SIZE_MISMATCH | `test_gap1_ambiguous_custody_transfer_remains_unknown` (1) |
| M2 invert storage | storage verdict inverted | SHA256_MISMATCH | 15 tests |
| M3 drop source-origin filter | — | SIZE_MISMATCH | **NONE (survives)** |
| M4 drop completeness gate | — | SIZE_MISMATCH | 3 |
| M5 remove common-control | — | SIZE_MISMATCH | 2 |
| M6 accept multiple holders | `len(holders) != 1` → `< 1` | SIZE_MISMATCH | **NONE (survives)** |
| M7 remove capture gate | `elif any(c >= ...)` → `elif False` | SIZE_MISMATCH | `test_gap2_capture_after_mutation_remains_unknown`, `test_gap2_capture_equal_mutation_is_unknown` (2) |
| **M9 order off-by-one** | `>=` → `>` | SIZE_MISMATCH | **`test_gap2_capture_equal_mutation_is_unknown` (1, the ONLY killer)** |
| M10 order inverted | `>=` → `<=` | SHA256_MISMATCH | 7 |
| M11 order equality-only | `>=` → `==` | SHA256_MISMATCH | `test_gap2_capture_after_mutation_remains_unknown` (1) |

**Drift demonstration on crafted cases (equality boundary), original vs mutants:**

```
original equality(ms=2): order=NOT_BEFORE_MUTATION  class=UNKNOWN      | after(ms=10,cap=11): order=NOT_BEFORE_MUTATION  class=UNKNOWN
M9       equality(ms=2): order=LAB_BEFORE_MUTATION  class=CONDITIONAL  | after(ms=10,cap=11): order=NOT_BEFORE_MUTATION  class=UNKNOWN
M7       equality(ms=2): order=LAB_BEFORE_MUTATION  class=CONDITIONAL  | after(ms=10,cap=11): order=LAB_BEFORE_MUTATION  class=CONDITIONAL
```

This confirms Claude N1 in both directions: M9 silently upgrades `UNKNOWN`→`CONDITIONAL` at capture == mutation, and the *equal* test is what detects it.

**Review of the two newly added tests (challenging their mutation sensitivity).** Source: `research/consensus/test_w1_trae_boundary_controls_v1.py` L47–L62 (blob `825689ba…`, sha256 `90d7c1e6…`).

1. `test_gap2_capture_equal_mutation_is_unknown` (L47-54) sets `mutation_sequence=2`; `build_case` fixes `capture-a=1`, `capture-b=2` (L58-59, default `mutation_sequence=10` at L86). It asserts both `capture_order.status == "NOT_BEFORE_MUTATION"` and `classification == "UNKNOWN"`. It is **not tautological** — it exercises a real comparison boundary — and it **does** kill M9.
2. `test_gap2_capture_just_before_mutation_is_conditional` (L56-62) sets `mutation_sequence=3` and asserts the *positive* neighbour (`LAB_BEFORE_MUTATION` / `CONDITIONAL`). It does **not** kill M9; it kills M10 (`<=`) and others. It is a correct anti-over-abstention control, complementary to #1.

**Fragility I flag (not a Claude error, a hardening point):**

- **Single-guard risk.** M9 has exactly one killer. If that single test is edited, renamed, skipped, or relaxed, M9 again escapes *both* W1 suites and the 58-test suite (Claude VERIFIED that survival). The file does not declare that it is the *sole* guard.
- **Vacuous-balance risk.** Neither test asserts its own **precondition** — that at least one capture sequence actually *equals* `mutation_sequence`. Both depend on the builder's hard-coded sequences (1, 2). If `build_case`'s capture sequences ever change, `mutation_sequence=2` would silently stop being the equality boundary and the test would keep passing while testing nothing. A one-line precondition assertion closes this (proposed in §8-R3).

Net: Claude's M9 finding is **accepted and independently reproduced**; the boundary tests correctly isolate the behaviour; I recommend one minimal hardening.

---

## 4. T2/T3 — Five-policy recomputation and the observation groups (priority B)

**Method.** Every policy receives the **same** `ProvenanceCase` bytes (`w.build_trials`). The evaluator never sees `latent_relation`/`expected_report`/`mechanism`. Latent labels are **author-declared metadata**, explicitly **not** externally adjudicated ground truth. Definitions: *false endorsement* = `CONDITIONAL` when declared latent relation ≠ `SEPARATE_MODELED`; *missed positive* = non-`CONDITIONAL` on a disclosed-complete separate case.

**Per-trial truth (pinned verdict vs development expectation, all 16 `match=True`):** reproduced in full in `./evidence/policies.log`. Confirms Claude F10 accounting: expected `CONDITIONAL` = 5, `DEPENDENT` = 4, `UNKNOWN` = 7.

**Five-policy table (mine, at tip):**

| Policy | agree/16 | falseEnd | missPos | UNKNOWN |
|---|---|---|---|---|
| Pinned gate | **16/16** | **3** | 0 | 7 |
| Storage-only (else UNKNOWN) | 7/16 | 0 | 2 | 16 |
| Never-promote (detect→DEPENDENT else UNKNOWN) | **11/16** | **0** | 2 | 12 |
| Constant UNKNOWN | 7/16 | 0 | 2 | 16 |
| Constant DEPENDENT | 4/16 | 0 | 2 | 0 |

Extra disclosed variants (transparency): storage-only→CONDITIONAL else = 5/16, 12, 0, 0; storage-only tri-state = 7/16, 10, 0, 2.

**Deviation from Claude N3 table.** Four rows match Claude **exactly**. The **storage-only row does not**: Claude reports `6/16, 11 false-end, 0 missed, 1 UNKNOWN`; I cannot obtain it. Evidence:

- I brute-forced **all** rules that depend only on the storage axis (3²=9 mappings over the two observed statuses `LAB_DISTINCT_OBJECTS`, `UNKNOWN`): **none** yields (6,11,0,1).
- My three natural storage-only variants yield (7,0,2,16), (5,12,0,0), (7,10,0,2). The closest to Claude's *shape* (low agreement, ~high false-end) is the "else CONDITIONAL" variant, but it gives 5/16 and 12 false-end, not 6/16 and 11.
- **Root cause candidate:** the storage axis is **degenerate on this set** (14/16 `LAB_DISTINCT_OBJECTS`, only 2/16 `UNKNOWN`; see `./evidence/policies.log`). A rule that can only read storage therefore has almost no discriminative power, and small definitional choices shift the counts. Claude's HYPOTHESIS caveat ("that it matches the authors'") is well-taken; but the specific numbers should not enter the record as reproduced. **Recommendation: drop the storage-only row unless the exact rule is published, or restate it qualitatively ("a storage-only comparator cannot detect the hidden dependencies on this set").**

**Observation-identical groups (confirmed exactly):**

```
fbc9a0267c03 : honest-separate, hidden-source-false-complete, hidden-admin-false-complete, hidden-source-admin-false-complete   (4)
2d2d10fa3a4d : hidden-source-incomplete, separate-incomplete-source                                                              (2)
86294751c29b : hidden-admin-incomplete, separate-incomplete-control                                                              (2)
```

Consequence (agrees with Claude N3): any deterministic function of the *reported* input must emit **one** verdict per group. On the four-trial group the pinned gate emits `CONDITIONAL` (3 of those 4 have a hidden dependency ⇒ **3 false endorsements**), while a never-promote/abstain rule emits `UNKNOWN` (⇒ **1 missed positive**, on `honest-separate`). The 3-to-1 ratio is a **design choice**, not a prevalence. The honest scientific statement is decision-theoretic: *what policy does the verdict name imply, and what hidden-dependency prevalence makes endorsement acceptable* — statable without new data. I concur with Claude N2/N4 that `development_expectation_matches = 16/16` **encodes three known non-detections as matches** and must never be read as detection accuracy.

---

## 5. T4 — Shared-custodian F3 (priority C)

**Probe (frozen engine, read-only), `./evidence/f3_shared_custodian.log`:**

| Configuration | storage | admin | custody | classify |
|---|---|---|---|---|
| baseline separate | LAB_DISTINCT_OBJECTS | LAB_CONDITIONALLY_SEPARATE | (CHAIN, CHAIN) | **CONDITIONAL** |
| shared **initial** custodian (`origin-a` holds both) | LAB_DISTINCT_OBJECTS | LAB_CONDITIONALLY_SEPARATE | (CHAIN, CHAIN) | **CONDITIONAL** |
| shared **middle** custodian (`relay-m`) | LAB_DISTINCT_OBJECTS | LAB_CONDITIONALLY_SEPARATE | (CHAIN, CHAIN) | **CONDITIONAL** |
| shared **final** custodian (`holder-a`) | LAB_DISTINCT_OBJECTS | LAB_CONDITIONALLY_SEPARATE | (CHAIN, CHAIN) | **CONDITIONAL** |
| shared final + scenario compromise | LAB_DISTINCT_OBJECTS | **COMPROMISED_BY_SCENARIO** | (CHAIN, CHAIN) | **UNKNOWN** |
| control: compromise of a **NON-shared** custodian (`holder-b`) | LAB_DISTINCT_OBJECTS | **COMPROMISED_BY_SCENARIO** | (CHAIN, CHAIN) | **UNKNOWN** |

**Conclusion.** Custody is evaluated **per witness**; a single custodian common to both witnesses is **never cross-compared**, so all shared-custodian shapes remain `CONDITIONAL`. The only path to `UNKNOWN` is the separate *compromise* flag, and it fires even when the compromised custodian is **not shared** — i.e. the mechanism that *does* catch custody risk is unrelated to sharing. This mirrors Claude §4 and my first-pass F3.

**Semantics recommendation (do NOT silently redefine `DEPENDENT`).** A shared custodian is a **common-control path** and is not the same object as a shared source or shared admin. Redefining `DEPENDENT` would silently change the meaning of an already-claimed verdict. Minimal, reviewable option, implemented as an **additive research-only axis** (see §8-R2 and the patch): report `COMMON_CUSTODY_DETECTED` / `NO_COMMON_CUSTODY_IN_DECLARED_GRAPH` as a **separate correlation result**, leaving the frozen evaluator and its `DEPENDENT` semantics untouched. The existing `@expectedFailure` in `research/consensus/test_w1_trae_boundary_controls_v1.py` (L64–L74) should be **preserved** as the documented gap until the policy is agreed — it asserts `UNKNOWN`, which is itself only one of the candidate policies (UNKNOWN vs separate-axis vs DEPENDENT). My probe fixture `./tools/w1_custody_correlation_probe.py` demonstrates the separate axis and keeps the frozen engine as a regression guard.

---

## 6. T5 — Historic vs W1 evaluator; version/evidence reconciliation (priority D)

**Two engines, distinct, confirmed by Git blob:**

- historic (paper pin `f562e14`): blob `b49b5fa6489a97a31a7056bf2fd8b1c6f2c03139`, **23,876 B**;
- current W1 (`dcac42f`): blob `4faf010d73219af63c254097e9c135da68d60078`, **26,726 B**.

They are **not** the same engine (resolves Claude F8: the blob at `f562e14` is **not** `4faf010d`).

**Cross-engine on the W1-DEV-16 cases (`./evidence/cross_engine.log`):** all **16/16** classify **identically** under both engines; differing = 0. Both engines carry the line `elif any(c >= case.mutation_sequence for c in captures):`. The historic engine **lacks** `MAX_CUSTODY_WALK_VISITS` (current: 4096; historic: ABSENT). So on this case set the engines agree, but they are **not interchangeable** in general (the bounded custody walk is a current-only guard).

**I did NOT pool the sets.** This run applies **both engines to the 16 W1 development cases**; it does **not** combine the 5-Nov paper's R5NOV-16 with W1-DEV-16. The paper's R5NOV-16 (CONDITIONAL 2 / DEPENDENT 7 / UNKNOWN 7; storage-only 4/16; bounded gate 16/16) is a **different** case set, read from the extracted paper text, and is **NOT_RUN** here. Any "16/16" must be labelled **W1-DEV-16** to avoid the conflation Claude warns about in N4.

**Receipt reconciliation (T7).** The two `W1_CI_RED_GREEN_RECEIPT` editions are genuinely different files: branch `f591a0bd…` (1,522 B) vs offline-packet `6ea6e4ae…` (2,161 B), with different byte-lengths and content. This is **not** an unexplained hash mismatch or collision; it is a versioned duplicate. **Retain both**, and record which was seen by which reviewer. The brief's account is confirmed.

---

## 7. T6 — CI verification (priority E, remote)

Verified via GitHub REST API through the sandbox egress proxy (`HTTP_PROXY=http://127.0.0.1:18080`); raw JSON saved (`run_44170674792.json`, `jobs_44170674792.json`, `jobs_44171922201.json`, `runs_branch.json`, `pr242.json`, `compare_f179_dcac.json`).

- **`44170674792`** ("W1 synthetic provenance research only"): `status=completed`, `conclusion=success`, `head_sha=f179e71c8f1d99c55eda90231005f68a9c6e7aa9`, run #35. Four jobs, **all `success`**: `(windows-2022, py3.11)`, `(ubuntu-latest, py3.13)`, `(ubuntu-latest, py3.11)`, `(windows-2022, py3.13)`. Each job ran both W1 steps to success: *"Verify source pin and execute stdlib synthetic tests"* and *"Exercise Trae-reported custody and capture decision boundaries (synthetic only)"* — plus a byte-exactness step *"Keep source checkout byte-exact on Windows and Linux"*.
- **`44171922201`** (branch tip `dcac42f`): completed/success, four W1 jobs all `success`.
- **PR #242:** `state=open`, `draft=true`, `base=main`, `head.sha=dcac42fcb1409d3befdab5ab968d03a695769b5d`.
- **Ancestry:** `compare f179e71...dcac42f` → `ahead_by=6`, `behind_by=0`; changed files are W22 artefacts + the third-pass brief + adjudication + the offline receipt variant only. **No W1 file changed**, so the `44170674792` result also certifies the W1 files at tip.

**NOT_RUN:** the **raw job-log content** (the four-job pass/fail *statements* are verified from the API, but the exact stdout lines, e.g. "4 passed, 1 xfailed", were **not** downloaded). `actions/jobs/{id}/logs` returns **HTTP 403 "Must have admin rights to Repository."** I therefore verify job **conclusions** and **step names**, and mark per-test log text **NOT_RUN**. Locally (R2) the same boundary file yields exactly `4 passed, 1 xfailed`, consistent with the brief's "5 focused tests: 4 PASS, 1 expected failure", but that is a local run, not a CI-log read.

---

## 8. T8 — Stronger latent-graph challenge protocol, and what stays unproven (priority E)

**Proposal (research-only scaffold, `./tools/w1_latent_graph_challenge_v0_1.py`, 4 tests passing):**

1. Define a **latent complete graph `G*`** carrying the true relation by construction.
2. Apply a **documented masking operator `O`** that removes/relabels information to produce the observed graph `O`. Generate **matched variants** from the *same* `G*`: `HONEST`, `DECLARED_INCOMPLETE`, `UNDISCLOSED_OMISSION`.
3. Score every rule **by variant**, reporting raw counts of false endorsements / missed positives / abstentions, not an aggregate "matches".
4. A **future frozen oracle** authored separately from the evaluator, with generator seeds withheld until after the evaluator is hashed.
5. Emit the **observation-identical groups** and the policy each rule implies.

**Demonstrated result of the scaffold:**

```
== pinned ==
  HONEST               n=4 dev=4 falseEnd=0 missPos=0 abstain=0
  DECLARED_INCOMPLETE  n=4 dev=1 falseEnd=0 missPos=0 abstain=1
  UNDISCLOSED_OMISSION n=4 dev=4 falseEnd=3 missPos=0 abstain=0
== never-promote ==
  HONEST               n=4 dev=3 falseEnd=0 missPos=1 abstain=1
  DECLARED_INCOMPLETE  n=4 dev=1 falseEnd=0 missPos=0 abstain=1
  UNDISCLOSED_OMISSION n=4 dev=0 falseEnd=0 missPos=1 abstain=4
```

The pinned rule reports **0 false endorsements** on the honest variant but **3** on an undisclosed-omission variant that is **byte-identical** to an honest case — the exact hazard. The never-promote rule trades this for a missed positive. The scaffold's tests assert: no latent label leaks into the observed input; the omission variant is observation-identical to honest-separate; and the summary is matched per variant.

**Precisely what remains unproven.** (a) The **latent truth is still author-declared** — there is no independently adjudicated `G*` oracle, so scores remain policy demonstrations, not accuracy measurements. (b) Because the variants are observation-identical, **no input-only rule can be credited with separating them**; the result is decision-theoretic. (c) The world-model itself (that the graph schema captures the relevant independence structure) is unverified. A separately-authored generator with withheld seeds (Claude R1) is the only thing that would move this from "demonstrated on the author's model" to external evidence.

---

## 9. Deviations from Claude's second pass

| Item | Claude | This pass |
|---|---|---|
| M9 kills | equal-mutation test kills M9 and also M7 | Confirmed; M9 has **exactly one** killer (equal test); M7 killed by two |
| Storage-only row (N3) | 6/16, 11, 0, 1 | **Does not reproduce**; storage axis degenerate (14/16 distinct); natural variants 5/16–7/16 |
| Other four policy rows | 16/3/0/7, 11/0/2/12, 7/0/2/16, 4/0/2/0 | Reproduce **exactly** |
| F8 (blob at `f562e14` == `4faf010d`?) | UNKNOWN | **No** — `b49b5fa6` (23,876 B) ≠ `4faf010d` (26,726 B) |
| F3 shared custodian | a spec decision; UNKNOWN or separate axis | Agreed; **separate axis recommended**, do not redefine `DEPENDENT` |
| CI | not read | Verified via API: `44170674792` success, 4 jobs; raw logs NOT_RUN (403) |
| Boundary tests | correct and killing | Agreed, **plus** single-guard and vacuous-balance fragility |

Claude's N2, N3 (policy framing), N4, N5 and N6 are, on my evidence, **sound in substance**. The one number I must correct is the storage-only row. N6's 192-permutation caveat stands: my harness run confirms `permutation_checks=192` with classification order-invariance; full-report (reasons/support) order stability was **NOT_RUN** here.

---

## 10. Remaining failures and unknowns

- **M3 and M6 survive both W1 suites** (drop source-origin filter; accept multiple holders). M6 is caught only by the separate 58-test implementation suite (Claude READ/VERIFIED); M3 is inert on these inputs. These are **open coverage gaps** in the W1 set, not engine defects.
- **F3 shared-custodian non-separation** remains an unfixed, documented gap.
- **Raw CI log content** and **external ground-truth adjudication** remain unavailable/unproven.
- **R5NOV-16** (historic paper set) not re-run; only the W1-DEV-16 set was exercised here.
- The **external latent-label authority question** (are `latent_relation` values independent of the evaluator author?) is unanswered; all scores inherit author-declared truth.

---

## 11. Prioritized recommendations

**FIX (research scaffolding):**

- **R-F1.** Add a **precondition assertion** to `test_gap2_capture_equal_mutation_is_unknown` (and the just-before test) that a capture sequence **equals** `mutation_sequence`, so the equality boundary cannot silently become vacuous if `build_case` changes.
- **R-F2.** Correct the record: **drop or qualify Claude's storage-only row**; state that the storage axis is degenerate on W1-DEV-16 and that storage-only cannot detect the hidden dependencies here.
- **R-F3.** Relabel the headline as **"16 new development trials (W1-DEV-16)"** and append: three of the sixteen are **known non-detections counted as development matches** (Claude N2/N4 carried into the report).

**REVISE (semantics, reviewed before pinning):**

- **R-R1.** Add a **separate custody-correlation axis** (`COMMON_CUSTODY_DETECTED` / `NO_COMMON_CUSTODY_IN_DECLARED_GRAPH`) — additive only; **do not** redefine `DEPENDENT`; keep the existing `@expectedFailure` as the recorded gap. (Implemented research-only in the patch; frozen engine untouched.)
- **R-R2.** Consider Claude N5 renaming (`CONDITIONAL` → a neutral premise-stating label) as a **spec change**, decided and reviewed before any pin.
- **R-R3.** Run a **systematic mutation sweep** over all comparisons/boundaries in `evaluate_provenance` and `_custody_for` on both suites, and record survivors (generalises M1/M3/M6/M7/M9).

**HOLD (do not act without independent evidence):**

- **R-H1.** Do **not** treat any W1 verdict as detection accuracy, admission, or trust; keep `PRODUCTION=NO_GO`.
- **R-H2.** Do **not** merge or pin the new verdict semantics until the separate-axis policy and any renaming are reviewed.
- **R-H3.** Await an independently authored, seed-withheld challenge generator (Claude R1) and real PR #269/#271 code tests before any "independently matched" claim.

---

## 12. Research-only patch (separate; not merged)

`w1_trae_third_pass_research_only.patch` — additive, research-only, against baseline `981ce5ea2e605c91553950d627437dbd9e083731`, **2 files, +287 lines, 0 deletions**, no production/evaluator/workflow change:

- `research/consensus/w1_custody_correlation_probe.py` — separate `custody_axis(case, engine)` returning `COMMON_CUSTODY_DETECTED` / `NO_COMMON_CUSTODY_IN_DECLARED_GRAPH`; tests for shared final/initial/middle custodian; one `@expectedFailure` documenting the frozen-engine gap; a compromise regression guard. Local: `5 passed, 1 xfailed`.
- `research/consensus/w1_latent_graph_challenge_v0_1.py` — the latent-graph protocol scaffold described in §8. Local: `4 passed`.

Both were executed this session (R8, R9). The patch is intended to be **reviewed and, if agreed, applied on the research branch only**, never `main`.

---

## 13. Attached evidence (`./evidence/`)

| File | Content |
|---|---|
| `mutation_battery.log` | baseline + M1–M11 kill matrix + equality-drift demo |
| `policies.log` | per-trial truth, identical groups, five-policy table, variants, equality-axis detail |
| `f3_shared_custodian.log` | shared initial/middle/final + compromise probes |
| `cross_engine.log` | historic vs current on W1-DEV-16; boundary lines; walk-visit guard |
| `fixture_15.log`, `boundary_5.log`, `boundary_5_verbose.log`, `harness_aggregate.log` | W1 suite and harness runs |
| `run_44170674792.json`, `jobs_44170674792.json`, `jobs_44171922201.json`, `runs_branch.json`, `pr242.json`, `compare_f179_dcac.json` | GitHub API receipts |
| `joblog_403.txt` | HTTP 403 evidence that raw job logs are not accessible |

Tools used: `./tools/{mutation_battery,policies,f3,cross_engine}.py` and the two patched research files. Reproducibility notes: `mutation_battery.py`, `policies.py` import the pinned harness from the first-pass export path (blob-identical to tip); `cross_engine.py` uses `/tmp/w1_tip/historic_eval.py` (blob `b49b5fa6`). All scripts are offline and touch no keys.

---

```text
RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO
No modifications were made to main, operational signing, trust settings, author rights, or the manuscript under journal review.
This review is AI-assisted, not human, and not blinded. Latent truth referenced here is author-declared metadata, not independently adjudicated ground truth.
```