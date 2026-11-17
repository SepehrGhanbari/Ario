# ARIO_RERE_01_RECURSIVE_MEMORY_REVISION_REPORT

**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO  
**Decision:** REVISE / HOLD. Recorded empirical result: 5 positive PASS, 7 desired-contract FAIL, 3 NOT_IMPLEMENTED; no merge or trust activation.  
**Date:** 2026-11-18  
**EVENT_ID:** LAB-E101  
**Pre-registration:** [RERE_01_PREREGISTRATION_V0_1.json](RERE_01_PREREGISTRATION_V0_1.json)

## 1. Source pins and actual deployment boundary

- Inspected **main** at `bc3f734890287c5ec365358680f74241f2285f82` (GitHub branch API).
- Experimental source is separate, **unmerged Draft PR #210** at source HEAD `6235df45444f112c3a7a699d5c96cac85a4e5b66`, branch `feature/cognitive-memory-consolidation`. The RERE branch is pinned to this parent; it is **not evidence of a feature in main**.
- `main` M0 source inspected: `implementation/core/schema.py` blob `ad459cf0b0fb37a5936814324d585d5fcd164308`, `implementation/core/audit_engine.py` blob `27b258d47383fd85789bd13ee6ebaa617d2cb6de`, `implementation/ledger_observation_adapter.py`, `implementation/ario_agent.py`.
- PR #210 source inspected: `implementation/core/memory_consolidation.py` blob `21d0d86af2a604ca4597c689573fc7295983fc4c`; test module `implementation/tests/test_memory_consolidation.py` blob `349145121a4b9e94df7b279bee394e071a261cda`.
- Issue [#216](https://github.com/SepehrGhanbari/Ario/issues/216) is **OPEN / HOLD**. DR-MEM-216 v0.2 **V1 retained + opt-in V2 sidecar** is a proposal, NOT owner-ratified; do not read V2 candidates as an adopted trust policy.
- `AGENTS.md` and `ADMISSION_REVIEW_POLICY_V0_1.md` read. No real user data, keys, signing, production memory, governance or trust state accessed.

## 2. What actually exists versus what was proposed

| Layer | Present in source | Epistemic limit |
| --- | --- | --- |
| `main` M0 `Claim`, `HistoricalState`, `Assessment`, `LineageEdge`, `Provenance` | YES | Typed supplied structures; no persistent, automatic, second-order memory adjudicator |
| `main` `AuditEngine` F05/F11/EAG | YES | Structural overwrite and wrong-kind evidence screening, not world-truth determination |
| `main` JSONL observer/bridge | YES | Read-only byte observation, not authenticated event origin |
| Draft #210 `ConsolidationEngine` | YES, UNMERGED | Maintains mutable in-process semantic nodes; no durable per-assessment supersession trail |
| Draft #210 `RECORDED` enum and opt-in default | YES, UNMERGED | Constructor default still legacy `ACCEPTED`; raw caller can supply a status |
| Draft #210 `SourceMonitoringGuard` | YES, UNMERGED | Empirical metadata guard, not independent source custody/attestation |
| `reassess_prior_assessment` / typed revision of an assessment with authenticated C invalidation | NOT IMPLEMENTED at inspected interface | T3/T4 epistemic loop cannot be claimed functional |

**Notable source-level contradictions:**
- Draft #210 `_process_raw_event` reads caller-supplied `status` directly, including `SUPPORTED` and `REVISED`. Raw input is not an authorized assessment.
- The existing `default_status` is `ACCEPTED` despite the new `RECORDED` label; #216 properly remains HOLD.
- Exact same event hash is folded into the node and increments `reinforcement_count` / salience on every replay.
- `ingest_event_stream` registers caller-supplied 64-character digests without matching them against independently held source bytes.
- Contradiction relies on explicit `negates` pointer or an `opposite` relation hint; a plain OPEN/CLOSED pair lacks rule-based resolution. A forward `negates` pointer depends on arrival order.
- Existing `_nodes` values are replaced when marked `CONTESTED`, without an in-engine prior-status history; immutable raw *ledger* is not the same as a recoverable history of *assessments*.
- The source-level `get_node`/legacy alias behavior is not a versioned epistemic assessment lineage mechanism.

These are source-inspected findings, now supplemented by exactly pinned GitHub Actions tests. The direct `ConsolidationEngine` results do not imply the same default behavior via every wrapper: inspected `EpistemicLedgerBridge` explicitly sets `default_status=RECORDED` for its own engine; its `STEP_OBSERVED` path can separately build `SUPPORTED` from a caller-described `COMPLETED` record. The bridge behavior is SOURCE-INSPECTED ONLY in RERE-01, not a new executed RERE case. Do not infer untrusted network reachability.

## 3. Pre-registered independent synthetic reference

The oracle is **fixture ground truth**, not an authorized witness or real human-independent auditor. Scenario constant: LAB-E101, door at 2026-11-18T00:00:00Z, synthetic actual state **CLOSED**. The truth fixture is declared only in the preregistration file and **not passed** to `ConsolidationEngine`.

- T1: A says OPEN; unauthenticated. Warranted **UNKNOWN / RECORDED**, not supported truth.
- T2: B says CLOSED; unauthenticated and not yet shown independent. Warranted **CONFLICT / UNKNOWN**.
- T3: C says CLOSED with synthetic validity in a *positive-control contract only*. A justified rejection of T1 requires a verified, temporally matching, scoped and independently admissible C. Merely transmitting `status=SUPPORTED` must not satisfy this.
- T4: Calibration report discredits C's timestamp. Reassess the **T3 assessment itself**; without other admissible proof the new object-level verdict is **UNKNOWN**, retaining the T3 reasoning and original event.

The comparison is intentionally dual: **epistemic justification** and **historical integrity** are assessed separately. SUT never receives oracle truth. This does not establish independent custody, source authenticity, consciousness, or biological memory.

## 4. Frozen matrix and exact executable test mappings

| ID | Contract | Preregistered expected baseline | Observed |
| --- | --- | --- | --- |
| P01 | Explicit `RECORDED` mode | PASS | PASS |
| N01 | Untrusted T1 must not default to `ACCEPTED` | FAIL | FAIL (strict XFAIL) |
| N02 | Plain T1/T2 contradiction handled | FAIL | FAIL (strict XFAIL) |
| P02 | Explicit `negates` conflict positive control | PASS | PASS |
| N03 | Caller-supplied T3 `SUPPORTED` cannot promote | FAIL | FAIL (strict XFAIL) |
| N04 | Recover prior assessment status at T4 | NOT_IMPLEMENTED | NOT_IMPLEMENTED (strict XFAIL) |
| N05 | Exact event replay idempotent | FAIL | FAIL (strict XFAIL) |
| N06 | Fabricated digest cannot prove complete receipt | FAIL | FAIL (strict XFAIL) |
| P03 | Malformed digest rejected | PASS | PASS |
| N07 | Forward negation order invariant | FAIL | FAIL (strict XFAIL) |
| N08 | `REVISED` requires reason and predecessor | FAIL | FAIL (strict XFAIL) |
| P04 | M0 forbids prior audit-result as evidence | PASS | PASS |
| P05 | M0 flags declared historical overwrite | PASS | PASS |
| N09 | Independently authenticated source-root semantics | NOT_IMPLEMENTED | NOT_IMPLEMENTED (strict XFAIL) |
| N10 | Typed second-order assessment adjudication API | NOT_IMPLEMENTED | NOT_IMPLEMENTED (strict XFAIL) |

`pytest.mark.xfail(strict=True)` on N-cases is **not a PASS** for the desired contract. It records a known, expected failure while allowing a research branch CI run to distinguish baseline failure from an unanticipated regression; any unexpected success is an XPASS and fails CI. The `NOT_IMPLEMENTED` rows are absence-of-interface probes, not fabricated runtime claims.

## 5. Reproduction, environment, baseline, hashes

Pinned source parent: `6235df45444f112c3a7a699d5c96cac85a4e5b66`.  
Seed `510101`. All inputs synthetic. CI Python requested: `3.13`, Ubuntu; advisory Windows 2022 on PR. Exact patch commit, Python patch version, platform, run IDs and observed counts must be recorded **after** execution.

```bash
git checkout research/rere01-recursive-memory-20261118
cd implementation
python -VV
python -m pip install -r requirements-research.txt
python -m pytest -q tests/test_rere01_m0_boundary.py -rx
python -m pytest -q tests
```

Do not run the research tests directly on `main`; the experimental `memory_consolidation.py` is absent there. Running this on the stacked branch does not test production Ario.

## 6. Simple append-only baseline comparison

A naive append-only list can retain T1..T4 records in order, but cannot itself authenticate evidence, resolve contradictions, prove independence, or re-evaluate a prior *assessment*. M0 offers typed references, F05 declared-overwrite detection, F11 wrong-kind checks, and EAG ancestry visibility beyond a raw list. Draft #210 offers semantic grouping, conflict flags and saliency. **Neither inspected layer establishes a functioning recursive epistemic assessor.** Their advantage is structural screening and indexing, not demonstrably better factual justification. No numeric comparative gain is asserted without a shared evaluation harness.

## 7. Risk, failure examples, and minimal next patch

- **P0 / S–M:** Reject untrusted caller `status=SUPPORTED/REVISED` or explicitly downgrade to `RECORDED`; add an authorized scoped assessment boundary. Do not change historical `ACCEPTED` in place.
- **P0 / M:** Model `AssessmentRevisionV0` as an **opt-in versioned sidecar** referencing an exact prior assessment ID and digest, source evidence + withdrawal reason; preserve old records. A T4 corrective assessment must target T3 as its subject, not merely T1; no trust/admission by default.
- **P1 / S:** Idempotency on `(event_id, raw_line_digest)` and conflict on same ID/different bytes. Do not equate reinforcement with epistemic independence.
- **P1 / M:** Reconcile explicit `negates` both directions and retain unresolved forward links as UNKNOWN. Define temporal-scope contracts; no semantic magic-string assertions.
- **P1 / M:** Pin ledger digests to actual retained bytes using declared v1/v2 digest labels; a locally generated hash cannot authenticate its own source. Independent retention/revocation remains separate and UNKNOWN.
- **P1 / M:** Introduce durable evidence-backed assessment history and structured retrieval; tests for truncation, duplicate, order and reasonless revision; no overwrite.
- **P2 / S:** Document the two independent scores with false acceptance, false rejection, structural recall, and unknown count.

Cost estimates: S = roughly 0.5–2 engineering days of scoped implementation/review; M = roughly 2–7 days plus cross-platform and compatibility tests. Estimates are directional, not schedules or promises.

## 8. Actual CI run records and split assessment

**Executed exact RERE test commit**: `3138cbf92bc3a5ff3294af03368a4277acbb29aa`. Compared against experimental base #210 `6235df45444f112c3a7a699d5c96cac85a4e5b66`; this research change made the 10 expected RED markers stricter with `raises=AssertionError`. Thus an unexpected crash cannot be disguised as expected RED.

- [GitHub Actions PR run #44185466049](https://github.com/SepehrGhanbari/Ario/actions/runs/44185466049): **SUCCESS** for Ubuntu M0 job, Windows 2022 advisory job, and cognitive-memory job. This reports CI execution success, **not safety success**. Linux and Windows M0 jobs each report `1232 passed, 10 xfailed, 121 subtests passed`; dedicated cognitive-memory job reports `86 passed` (these are overlapping tests, not additional independent witnesses).
- [GitHub Actions branch-push run #44185460000](https://github.com/SepehrGhanbari/Ario/actions/runs/44185460000): Linux PASS; Windows push job skipped per workflow's `pull_request` condition. Earlier exact PR-run [#44185167608](https://github.com/SepehrGhanbari/Ario/actions/runs/44185167608) also succeeded with the original 15-case preregistered tests, before stricter `raises` exception handling.
- GitHub logs: Linux **Python 3.13.18**, Windows **Python 3.13.17**, `pytest==9.1.1`, pinned `cryptography==46.0.4`, pytest seed convention `510101` in our synthetic digest labels. Linux job command `python -m pytest -q tests`; Windows command `python -B -m pytest -p no:cacheprovider -p tests.test_m0_reproducibility_demo -q tests`. Both included 15 RERE cases. Linux dedicated suite also ran its existing 86 memory tests.
- Preregistered **15 RERE cases**: five non-xfail positive controls passed (P01/P02/P03/P04/P05); seven intended safety assertions failed (N01/N02/N03/N05/N06/N07/N08); three absent interfaces were recorded as strict assertion XFAIL (N04/N09/N10). The 10 XFAIL are *not* counted as PASS, and `NOT_IMPLEMENTED` is not reclassified as a behavior-level FAIL.
- Reporting contract: a safety RED means one asserted property fails in an in-memory synthetic candidate; it does **not** establish external exploitation, independently authenticated evidence or actual harm.

**Epistemic justification, separate from structural history:** Basic explicit-record controls P01/P02 and wrong-kind M0 firewall P04 pass. The desired no-untrusted-promotion, general contradiction, ordering and reason-required transitions fail at the directly inspected candidate API. Real authenticated C→T3 and calibration-based T4 judgment have no implemented authorized interface. No warranted truth verdict is produced.

**Historical integrity, separately reported:** M0 F05 can flag a supplied historical mutation candidate (P05 PASS). In draft consolidation, replay reinforcement (N05) and caller-declared hash completeness (N06) fail the required safety assertions, while a durable old-assessment version retrieval (N04) is not implemented. Existing raw ledger retention and M0 structural checks do not by themselves prove a complete chain of evolving assessment justifications.

**GitHub records:** [Research Issue #276](https://github.com/SepehrGhanbari/Ario/issues/276), [Draft PR #274](https://github.com/SepehrGhanbari/Ario/pull/274). PR is stacked on open #210; neither #210 nor #274 is approved for merge.

## 9. Unknowns and decision boundary

- Real source A/B/C identity, custody, clock calibration, revocation and root independence: **UNKNOWN**.
- Real append-only durability and deletion protection for memory assessment revisions: **NOT ESTABLISHED**.
- Live production event delivery and RERE-01 current runtime integration: **NOT IMPLEMENTED / NOT TESTED**.
- Independence of synthetic oracle from the test author: **NOT ESTABLISHED**.
- Claim truth, actual world status, independence of witnesses and consciousness: **NOT PROVEN**.
- User/owner authorization to adopt a new `#216` protected memory contract: **NOT GRANTED**.

**Decision: REVISE / HOLD.** Exact-head Linux+Windows RERE probes have now run and their results are recorded above. Do not merge, activate production/trust, access signer or grant evidence admission. Independent human and administrative witness custody review are absent; a CI green marker does not undo seven observed safety REDs or create three missing capabilities.
