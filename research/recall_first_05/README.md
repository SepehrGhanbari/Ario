# RECALL-FIRST-05 — Traceable, revocable, versioned question-equivalence research

**Date:** 2026-11-22  
**State:** `RESEARCH_ONLY / SYNTHETIC_EXECUTED / HOLD_FOR_REVIEW / NO_CORE_CHANGE / NO_REAL_MEMORY / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`  
**Tracking:** [Ario PR #210](https://github.com/SepehrGhanbari/Ario/pull/210), [Issue #209](https://github.com/SepehrGhanbari/Ario/issues/209), blocked semantic admission policy [Issue #216](https://github.com/SepehrGhanbari/Ario/issues/216).

## The specific failure and the bounded experiment

RF04 correctly blocked unreviewed paraphrases but also refused all legitimate non-identical questions. RF05 tests whether a **separately reviewed, explicitly pinned, *one-pair-only* alias** can be retrieved without re-derivation, while preserving revocation, source/version linkage, and epistemic non-promotion. It **does not** claim general semantic understanding, model inference, verified reviewers, or independent source custody.

RF05 is one **read-only answer projection**, *not a new durable memory writer*. It opens a bounded immutable-in-process snapshot of the **existing RF01 synthetic answer journal** and passes the bytes to the **unchanged RF01 replay code** in a temporary directory. Review annotations are supplied as bounded in-memory events for the test and are **not** a second answer journal. No production `implementation/core/*` changed, no local Ario desktop path inspected, and no keys used.

## Three safeguards plus revision

1. **Do not confuse similarity with equivalence.** `propose_candidate(original, alternate)` returns `CANDIDATE_NEEDS_REVIEW` or a conservative contrast HOLD. An actual different-surface-form recall requires a synthetic `GRANT` referencing one original `ANSWER` ID, original question, scope, source journal SHA-256, exact answer version, `basis_ref`, reviewer label, rationale, digest, chain position, and supplied pinned head. This is a *lab consistency check*, **not independently authenticated reviewer authorization**. The only other eligible input is the exact original question under the RF01 normalization convention.
2. **Reject detectable meaning differences even if someone falsifies a review label.** The defensive, partial contrast detector checks question intent (why/what/when/who/how/yes-no), selected subject domains, explicit digit slots, obvious negation and exactly swapped token-order cases with the same word multiset (PAWS-style). These are safety-oriented **negative checks, not a proof of positive semantic entailment**. It may reject legitimate paraphrases; it cannot detect every wrong paraphrase, especially multilingual cases beyond the small lexicon.
3. **Historical recall is not present-time assessment.** `mode=CURRENT_FACT` / `CURRENT_POLICY` and conspicuous `now/still/latest/امروز/هنوز/الان` return `RECHECK_REQUIRED` without asserting a present truth, even if the stored answer is labeled `STABLE`. The current-intent detector does **not** cover unrestricted natural language or all languages.
4. **Versioned revocation without erasure.** A hashed `REVOKE` event references an exact `GRANT` digest. Its review ID and digest must match a caller-supplied policy pin, and replay must match a supplied `(seq, head)` floor. When revoked, alias recall stops; the original answer and all review/revoke events remain available in the input. A fresh new `GRANT` can restore a *new* reviewed link, with a new ID. If the source journal changes, previous source-digest pins fail. If a version changes, new review is required. Neither repeat retrieval nor multiple reviewers upgrade `RECORDED / NOT_EVALUATED` to `SUPPORTED` or `ACCEPTED`.

## Actual tests, negative controls, and reproducibility

The synthetic lab ran in the isolated research environment under Python **3.13.5**, stdlib only; `42/42` unit tests PASS. Tests include:

- Exact historical recall and bilingual *manually curated* paraphrase across restart-like reconstruction; 100 repeat lookups, zero recomputation/evidence promotion, no changes to original source bytes.
- Wrong topic, wrong question type, negation, number change, swapped entity roles despite high lexical overlap, unreviewed alias and failed scope separation → HOLD/UNKNOWN.
- Explicit current-intent checks, false current-as-historical labels → RECHECK, not a historical answer marketed as current.
- Missing/mismatched pinned review, omitted/replayed revocation, stale review floor, tampered/reordered review events, duplicate/multi-answer reviews, changed source journal, stale answer version, retention of previous answer versions.
- A deliberate residual counterexample: the same controller can supply a forged old review stream **and** an old matching floor; the result is still labelled `NOT_INDEPENDENTLY_ATTESTED` and does not establish historical rollback resistance.

Four **purposely corrupted copies** of RF05 were separately tested, each causing assertion failures as expected: disabling (a) semantic contrast, (b) current recheck, (c) pinned-floor gate, and (d) revocation. The original source was never edited by mutation runs. `4/4` mutants detected. Full stdout in `POSITIVE.log` and `MUTATION_NEGATIVE.log`; see `TEST_REPORT.json` for checksums and versions.

From repository root on a research checkout containing the existing RF01 lab:

```bash
PYTHONPATH=research/recall_first_01:research/recall_first_05 python -B -m unittest discover -s research/recall_first_05 -p 'test_*.py' -v
python -B research/recall_first_05/mutation_probe.py
```

In Windows PowerShell the path separator is `;`, or invoke from `research/recall_first_05` after adding `research/recall_first_01` to `PYTHONPATH`. **Neither Windows execution nor GitHub Actions execution is claimed here**; local tests ran in Linux. No live language-model paraphrase classifier was tested.

## Literature and research limits

- [PAWS, NAACL 2019](https://aclanthology.org/N19-1131/) shows why high lexical overlap is unreliable for positive paraphrase identity; negative swapped-role fixtures are relevant, not a substitute for PAWS benchmark evaluation.
- [XNLI, EMNLP 2018](https://aclanthology.org/D18-1269/) provides multilingual entailment examples to consider if adding an independent bidirectional-NLI candidate ranker in a **separate research-only** stage. English↔Persian equivalence here was manually pinned, not model-proven.
- [W3C PROV-O](https://www.w3.org/TR/prov-o/) models provenance and invalidation; our minimal lab event format is not a PROV-O implementation, nor does hashing confer source authenticity.

Unresolved: semantic-equivalence mistakes by the reviewer, issuer/reviewer authority, independent retained review floor, same-controller source+pin rollback, concurrent immutable reads, implicit current-intent classification, broad Persian idioms, transitive paraphrase reasoning, and the meaning of historical `ACCEPTED`/snapshot `SUPPORTED` in #216. None is silently treated as PASS.

**Disposition:** `LAB_REVIEWED_ONE_PAIR_RECALL_PASS / 42_LOCAL_TESTS_PASS / 4_MUTANTS_DETECTED / GENERAL_EQUIVALENCE_NOT_ESTABLISHED / #216_NOT_ADOPTED / MAIN_MERGE=NO_GO`.