# ARIO_RERE_01_RECURSIVE_MEMORY_REVISION_REPORT

**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO  
**Decision:** HOLD, with expected structural/epistemic RED probes; final empirical verdict pending exact-branch CI.  
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

These are source-inspected findings; empirically confirmed test statuses must come from CI, not this inspection.

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
| P01 | Explicit `RECORDED` mode | PASS | PENDING CI |
| N01 | Untrusted T1 must not default to `ACCEPTED` | FAIL | PENDING CI |
| N02 | Plain T1/T2 contradiction handled | FAIL | PENDING CI |
| P02 | Explicit `negates` conflict positive control | PASS | PENDING CI |
| N03 | Caller-supplied T3 `SUPPORTED` cannot promote | FAIL | PENDING CI |
| N04 | Recover prior assessment status at T4 | NOT_IMPLEMENTED | PENDING CI |
| N05 | Exact event replay idempotent | FAIL | PENDING CI |
| N06 | Fabricated digest cannot prove complete receipt | FAIL | PENDING CI |
| P03 | Malformed digest rejected | PASS | PENDING CI |
| N07 | Forward negation order invariant | FAIL | PENDING CI |
| N08 | `REVISED` requires reason and predecessor | FAIL | PENDING CI |
| P04 | M0 forbids prior audit-result as evidence | PASS | PENDING CI |
| P05 | M0 flags declared historical overwrite | PASS | PENDING CI |
| N09 | Independently authenticated source-root semantics | NOT_IMPLEMENTED | PENDING CI |
| N10 | Typed second-order assessment adjudication API | NOT_IMPLEMENTED | PENDING CI |

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

## 8. Unknowns and decision boundary

- Real source A/B/C identity, custody, clock calibration, revocation and root independence: **UNKNOWN**.
- Real append-only durability and deletion protection for memory assessment revisions: **NOT ESTABLISHED**.
- Live production event delivery and RERE-01 current runtime integration: **NOT IMPLEMENTED / NOT TESTED**.
- Independence of synthetic oracle from the test author: **NOT ESTABLISHED**.
- Claim truth, actual world status, independence of witnesses and consciousness: **NOT PROVEN**.
- User/owner authorization to adopt a new `#216` protected memory contract: **NOT GRANTED**.

**Decision: HOLD / REVISE candidate.** No merge, production use, trust activation, signer access or automatic admission. Independent review is absent; CI may assess test execution, but not epistemic authority. Add exact CI observations and link any issue/PR before calling this report complete.
