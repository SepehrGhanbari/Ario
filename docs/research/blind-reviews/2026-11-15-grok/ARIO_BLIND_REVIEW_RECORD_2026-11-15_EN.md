# Ario: seeded-flaw blind review and patch cycle (record)

Status: **record of a small, single-reviewer exercise. Not an independent human review. Not evidence of security.**
Dates: 2026-11-15 to 2026-11-16 (Asia/Tehran).
Fields to fill before filing (not known to the writer): repo commit of the archive reviewed `[TODO]`; Grok model name and version `[TODO]`; SHA-256 of each saved raw Grok output `[TODO]`; commit at which the patch is applied `[TODO]`.

## 1. Why this was done

Ario has had no outside contributor for about six months. Requests for critique drew little response. The question was whether an available, cheap reviewer (an AI model with no project context) can find defects in the code and documents, and how much its silence can be trusted.

## 2. Method

A copy of the repository was made and five defects were planted by the assistant (Claude Sonnet 5.5, which also wrote the later patch; see limitations). The existing test suite still passed with all five present: 1,140 original tests plus 2 new ones, 1,142 passed, 6 skipped, 116 subtests (CPython 3.13).

| ID | Location | Planted defect |
|---|---|---|
| S1 | `core/audit_engine.py`, history-mutation check | digests compared on the first 16 characters only |
| S2 | `core/audit_engine.py`, retrieval check | transformation compared by `reference_id` only; `reference_type` ignored |
| S3 | `papers/evidence-laundering-2026-10-27/Manuscript.md`, test table | total changed from 280 to 290, plus the claim "confirms the system is secure against witness collusion", which the paper's own limits contradict |
| S4 | `GOVERNANCE.md` | status line says Genesis ACTIVATED and releases Founder-signed; the rest of the file says NOT_ACTIVATED |
| S5 | new test file | two tautological tests named as independence guarantees |

A 283 KB archive (code, tests, the manuscript, GOVERNANCE.md) and one neutral prompt were given to a fresh Grok account. The prompt did not mention planted defects or the author, and asked for verified-versus-suspected labelling and for "no defect found" where nothing was found. Reviewers with prior context (the author's existing Claude, Gemini, ChatGPT, DeepSeek and Lovable accounts) were **excluded** from scoring because they may have known the project.

## 3. Round 1 result (blind)

- Found S1, S2, S3, S4 with correct locations and reproduced behavior: **4 of 5**.
- Missed S5. It ran only the five manuscript modules and the M0 regression file, so it likely never opened the new test file. The miss reflects what it ran, not necessarily what it can recognise.
- No clear false positive.
- One finding that was not planted: a `TRANSFORMATION` derivation reference with no corresponding object is dropped from the ancestry graph, and the report still says `TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT`. The writer reproduced it on the original, unseeded code (same evidence, `PASS` with type `TRANSFORMATION`, `FAIL`/`UNKNOWN` with type `CLAIM`). The project's own test fixtures use an unresolved `TRANSFORMATION` derivation, so this is probably intended. The defect is that the label overstates what was traced.
- One note it flagged as uncertain, which was correct: the manuscript says 41 witness-provenance tests, the tree collects 58. This is version drift (the manuscript cites an earlier commit), not a planted defect.

## 4. Patch and review rounds

Patch v1 (written by the assistant) added three informational keys to the ancestry report, naming unresolved `TRANSFORMATION` derivations, and six regression tests. Claim made: it never changes a verdict.

| Round | Reviewer finding | Outcome |
|---|---|---|
| 2 | The claim was false: near the 65,536-byte report cap the new keys pushed the report over and turned `PASS` into `FAIL/UNKNOWN`. Reproduced by running patched and stripped engines. | True. Fixed: keys are added only if the report still fits. |
| 2 | New tests did not pin full-digest equality (`[:17]` stayed green), reference-type comparison, or the truncation flag. | True. Tests extended. |
| 2 | Parser did not validate the new keys. | True. Validation added. |
| 2 | CLI crash on Python 3.10 (`LineageEdge` forward reference). | True on 3.10 only; 3.11 to 3.13 unaffected. One-line fix in `schema.py`. |
| 2 | LICENSE missing. | False positive caused by the writer's reduced archive. |
| 2 | Over-limit guard path returns before the new keys are added. | True, low, **not fixed**. Documented. |
| 3 | The size-cap claim could not be broken on 99 inputs (0 differences). 3.10 CLI crash fixed. | Confirmed. |
| 3 | Size-gate test too loose (gate +100 stayed green); `[:64]`, `.strip()`, `sorted` for `set`, `isinstance(int)` for the flag all stayed green; parser accepts values the emitter cannot produce. | True. Tests and parser tightened. |

Patch v3 (final): 1,179 passed, 6 skipped, 116 subtests on CPython 3.13. Eleven mutations of the patched code, including every one the reviewer named, each fail at least one new test. The final changes were checked by the writer's own mutation runs; **no fourth reviewer round was run on v3**. `patch --dry-run` applies cleanly to the original tree.

One reviewer statement was inaccurate: it said the parser accepts `"bad\nid"` while the emitter's `report_id` rejects it. `report_id` accepts it (it checks only non-empty and at most 128 bytes), so the parser's behavior there is consistent.

## 5. What this does and does not show

Shows:
- A context-free model with code execution found four of five planted defects, one real unplanted reporting weakness, and a false claim in the writer's own patch.
- The existing test suite did not detect two silent weakenings of comparison rules (S1, S2). Coverage of those rules was loose.
- Two review cycles produced tests that are mutation-sensitive for the changed code.

Does not show:
- A detection rate. This is one reviewer, one run, five defects.
- That Ario is secure, or that independent review has taken place. No human reviewer took part.
- Anything about the models that had prior context.

## 6. Limitations

1. **One reviewer model, N = 1.** Rounds 2 and 3 were not blind: the reviewer had seen earlier rounds.
2. **Shared origin.** The planted defects and the patch came from Claude; the reviewer is a different model family, but all such models share broad training data and similar blind spots.
3. **Planted defects are the writer's choice** and skew toward what the writer thinks of as defects.
4. **Raw outputs are the author's pasted text.** Hashes and full transcripts should be archived (fields above).
5. **Environment.** The reviewer ran Python 3.10.22; the project targets 3.13. Three planner-transport tests fail on 3.10 for reasons not related to the patch (no 308 redirect support in the standard library, plus unstable network tests).
6. **Scope.** Not reviewed in this exercise: the Persian edition of the book, the architect's personal notes, the dialogue experiments, most of the engineering log. The English book and the papers were read by the writer (the book through a sub-reviewer's report), and are not part of the score above.
7. **Coverage gap left open:** S5-type fake tests were not found because the reviewer never ran the whole `tests/` directory. A rerun with the instruction "run all of `implementation/tests/` and list every test file" is recommended before drawing any conclusion about tautological tests.

## 7. Open items

- Decide whether an unresolved `TRANSFORMATION` derivation should stay a declaration (current design, now reported) or produce `UNKNOWN`.
- Apply the patch to the real repository and record the commit.
- Obtain at least one human reviewer with veto rights (the single-maintainer gap in `GOVERNANCE.md` remains open).
- Add a note to the manuscript that its 41-test provenance count refers to an earlier commit.
