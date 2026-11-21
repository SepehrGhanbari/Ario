# PR #298 — Historical Support Envelope & Memory Budget (research v0.1)

**Classification:** `RESEARCH_ONLY / PROPOSED_CONTRACT / DRAFT / HOLD / NO_MERGE`  
**Implementation pinned:** `f3d3c2c9e4be0cb16208fa30dae7a1907b26d87f`  
**Intent:** Make the acceptance population and numeric resource target explicit **without claiming universal safety** or rewriting old ledgers. This document proposes a reviewable scope. It is **not** authorization to activate trust, signer, Genesis, or merge.

## 1. Three distinct populations — no silent promotion

**Tier A — directly observed history (OBSERVED, not authenticated):**
- Exactly one owner-designated historical runtime JSONL file; 198,993 bytes, 28 records, four Task and four Workflow IDs. Maximum Task-ID matches: 7. Largest decoded segment: 54,357 characters. File hashes before/after local measurement matched. Thirty old-vs-new outcome comparisons showed no differences, including four inherited `UNKNOWN` task histories.
- This is **one** Windows/CPython 3.13.x ASCII sample. Its original provenance and representativeness are not independently established. It does not prove all earlier Ario writers, restored copies, or production workloads are supported.

**Tier B — narrowly supported development writer profile (CONTRACT_CANDIDATE):**
- Inputs emitted via the current bounded Python Agent/Workflow CLI implementation, with valid UTF-8 JSONL; normal LF/CRLF/CR and optional initial BOM as covered by regression.
- Each CLI request is at most 4 MiB, individual bounded tasks declare <=8 actions, <=8 failure diagnostics and <=8 goal criteria; the observed code writes at most **18** events under one Task ID in a normal standalone invocation, or **19** when an enclosing Workflow appends the stage observation. Interrupted runs may lack a finish event.
- Cooperative local appenders honor their own documented locks; multiple uncoordinated writers, modified on-disk bytes during read, network filesystems and untrusted appenders have **no proven atomic-snapshot or identity guarantees**.
- **Research workload subset to benchmark:** one reader at a time, regular local ledger; at most **1 MiB encoded UTF-8 per individual record** and **128 total records matching one Task ID**. Total size of unrelated historical entries is **not globally capped**. Records outside this *benchmark subset* are not certified merely because the implementation's technical parser accepts them.
- The current runtime's hard fail-closed thresholds remain **16 Mi decoded characters per physical line** and **128 matching events per Task inspection**. Neither has been reduced or promoted to an unconditional compatibility promise.

**Tier C — UNKNOWN / OUTSIDE THE CLAIM:**
- Arbitrary legacy writers or restores, externally authored large JSONL, >1 MiB encoded records, 129+ matching records, concurrent uncoordinated append, multi-byte extreme fields near 16 Mi characters, large retained projected strings across many entries, multiple simultaneous readers, or a known-unsafe/malicious data source.
- For out-of-contract inputs the program must not infer `COMPLETED` just from truncated/partial evidence. Explicit `UNKNOWN` or refusal is preferable; there is no automatic recovery. Actual behavior still requires targeted falsification before any production promise.
- An `UNKNOWN` after `WORKFLOW_STAGE_OBSERVED` follows `TASK_FINISHED` is an **inherited conservative behavior**. Do not silently reclassify it as completion in this PR.

## 2. Memory budget: explicit research target, not demonstrated production guarantee

**Proposed one-reader target for a reference development Windows/Linux Python 3.13 run:**
- **Peak process RSS: at most 256 MiB** while inspecting Tier B's bounded *synthetic benchmark profile*, measured in a dedicated fresh interpreter; record platform, Python, process baseline, peak and concurrency. This is a **target to falsify**, *NOT VERIFIED* for all Tier B inputs.
- **Cross-platform regression guard:** measured `tracemalloc` peak **below 64 MiB** for two narrowly defined representative fixture classes: (i) 128 matching records with 126 records retaining 64-KiB `tool` strings (about 8 MiB source data); (ii) a ~1-MiB UTF-8 observation containing 4-byte Unicode code points. These are safe synthetic checks, not a worst-case memory proof.
- `tracemalloc` excludes native allocator/RSS and other process memory; do **not** equate a passing guard with the 256-MiB RSS target, a max-size allocation certificate, or production concurrency validation.
- The 16-Mi-character hard line bound could represent ~64 MiB of raw Unicode UTF-8 *before* decoder/JSON copies, while 128 retained selected fields can cumulatively consume far more memory. There is no strict aggregate projected-field byte quota. Thus the unconditional global memory budget is **UNKNOWN**.
- The separate `subprocess.run(capture_output=True)` path can temporarily allocate child output before slicing it. It is **outside** F-01/JSONL streaming and requires its own bounded capture design; do not claim that streaming fixes it.

**Why 256 MiB?** A deliberately conservative *trial target* to be benchmarked before owner approval, not derived from the observed 198,993-byte history or from an unmeasured RAM specification. Do not silently write it into runtime constants, require new hardware, or treat it as production policy.

## 3. Gate checklist and authorized interpretation

| Gate | Required to claim it | Current state |
|---|---|---|
| Three historical whole-file reads replaced by streaming | Exact source inspection + call-chain tests | **PASS in scope**, independently reviewed previously |
| Tier A source compatibility | Read-only before/after digest + full old-vs-new statuses | **PASS for one file**; custody not independently attested |
| Tier B code-derived count 18/19 | Source paths + actual-run tests | **PASS** for pinned source |
| Tier B 64-MiB traced-heap **fixture guard** | New safe CI tests on exact head Windows and Linux | **PENDING this commit** |
| Tier B 256-MiB peak **process RSS** | Fresh-process measured peak, both OS, defined machine/concurrency | **UNKNOWN / NOT_EXECUTED** |
| All Tier B inputs up to 1 MiB and 128 retained events | Adversarial boundary, large projected fields, mutation / race tests | **UNKNOWN** (partial coverage only) |
| Universal histories or near 16-Mi-character records | Real historic diverse corpus and worst-case memory profiling | **OUTSIDE SCOPE / UNKNOWN** |
| Independent approval | Reviewer not author of implementation, exact final SHA, disclosed evidence | **NOT_ESTABLISHED** |

## 4. Reviewer independence with only Codex and this assistant

- **Codex authored** a final tests-and-reports commit; this assistant authored earlier candidate runtime work. Neither can claim third-party, conflict-free independence for the entire PR merely by reviewing their own work.
- The previous v0 review is an **external technical review of an earlier SHA**, not final approval of the latest SHA. The founder remains the only authorized governance decision maker, and CI itself is not an independent reviewer.
- We can still complete engineering, attach a **self/peer adversarial audit clearly labeled as non-independent**, close sub-questions with verified evidence, and maintain a single explicit **final-merge HOLD** until review requirements are either satisfied or *formally* changed by founder-approved governance. Do not bypass a ruleset or represent a self-check as independent sign-off.

## 5. Decision

**RESEARCH TECHNICAL WORK MAY CONTINUE / DO NOT MERGE.** Tier A is verified within its sample and F-01 is fixed in the three audited paths. Tier B is a narrowly proposed testable contract. Neither the process peak-RSS ceiling nor external-independent signoff is established. History must remain append-only; files and system trust remain unchanged.

Evidence: [Historical measurements](LEDGER_BUDGET_REALITY_REPORT.md), [compatibility](HISTORICAL_COMPATIBILITY_REPORT.md), [resources/mutations](RESOURCE_AND_MUTATION_TEST_RESULTS.md), [gate](FINAL_PR298_REVIEW_GATE.md).
