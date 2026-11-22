# RECALL-FIRST-02 — GitHub public-record read-only recall spike

**2026-11-22 / RESEARCH_ONLY / HOLD / NO_MERGE / NO_TRUST_ACTIVATION / NO_PRODUCTION**

## Falsifiable engineering goal

Recover a previously recorded answer/decision from its existing *authorized source record*, detect when a question asks for a fresh assessment, and never promote a repeated memory to verified truth.

This addendum is **not** a new primary memory system. It extends the existing [RECALL-FIRST-01 branch](https://github.com/SepehrGhanbari/Ario/tree/research/recall-first-01-20261122/research/recall_first_01) with a source-grounded, **off-repo executable** test report. The full locally executed research package has not yet been pushed into GitHub; do not mistake this note or its hashes for committed executable source.

### Public source records actually inspected by connected GitHub readback

1. [#209 comment 7078883522](https://github.com/SepehrGhanbari/Ario/issues/209#issuecomment-7078883522): founder asked for recall on repeated questions rather than re-derivation.
2. [#216 comment 6899388206](https://github.com/SepehrGhanbari/Ario/issues/216#issuecomment-6899388206): **option B is PROPOSED, NOT ADOPTED**.
3. [#216 comment 7078780381](https://github.com/SepehrGhanbari/Ario/issues/216#issuecomment-7078780381): read-only snapshot status interpretation is **a RESEARCH PROPOSAL, not a ratified policy**.

These are **public Github issue comments**, NOT the full Ario private conversation corpus, NOT a live Ario runtime ledger, and NOT authenticated external-world truth.

### Research code executed locally, with exact SHA-256

- `readonly_record_adapter.py`: `a8a92e91c0f491867846d61936afb2f9e134e5e29d31d70d248e5c51d7867fd3` — bounded read-only export, captured source references, explicit question/alias index, fail closed for ambiguity/source tamper; no writes.
- `github_comment_readonly_provider.py`: `f965dc1022cef2a8f4424a714c08ada4fe6639f0f599ad3c24c401f00b67ed49` — optional GitHub public GET validation and in-process readback cache; live HTTP branch **NOT_EXECUTED** in offline test environment.
- `public_ario_comment_excerpts.json`: `fc0f070ad37294e84794f4df23897f6f6ed18f6a2b743dce7f208935f629f7a9` — 3 public comment excerpts, 6 explicit query bindings; is not a complete transcript.
- `test_readonly_record_adapter.py`: `9340fe753895d9666c72f13b27ec8b9dacc1d2a283da9f7672fb5db210db17fd`.
- `test_github_comment_readonly_provider.py`: `53faee46b9f00ec62b5b862ccaaa147fdd988714bcdcc2d373c13fd587735676`.
- `README.md`: `b204f701330bb606fc32eeaf0882ac55481dad26355377f223583d2d3ecb73ef`.

**Run command (local package):**

```bash
python -B -m unittest -v test_readonly_record_adapter test_github_comment_readonly_provider
```

**Observed:** **36/36 PASS** on local synthetic+captured-public-excerpt harness. A targeted mutation `effective_assessment: NOT_EVALUATED -> SUPPORTED` returned **exit 1, test failure**; the negative control isn't a permanently green test. Historical recall returns the same source record for an explicitly bound paraphrase, cross-session source-file reload survives, 100 repeats remain `RECORDED/NOT_EVALUATED`. Asking `CURRENT_POLICY` for an unadopted #216 proposal refuses with `HOLD_NOT_ADOPTED`. A missing or changed source returns `UNKNOWN/HOLD`.

**NOT ESTABLISHED:** Python provider live network execution; native Ario conversation history source; automated free-form semantic paraphrase resolution; real authorized V1→V2 status migration; autonomously recognizing changed real-world facts; any independent source custody or trust admission.

### Gap in actual source; why this spike is not a runtime fix

Research head `3af6349d1c9dd128d7e1aa908b5f52320b1b3bb6`, `implementation/core/memory_consolidation.py::retrieve_active_context` retrieves salience-qualified nodes by concept substring, not a past question-answer receipt. In main `9dd4dda2784fe90e8dda0bb5142ea81167a64869`, `implementation/ledger_observation_adapter.py` provides event/task/hash metadata for *execution* JSONL, not prior dialog answers. An arbitrary new writer or self-declared `ANSWER_RECORDED` type must **not** be smuggled into either interface.

**Next bounded engineering gate:** locate and obtain explicit source/consent/scope for an existing Ario persisted chat/decision ledger, then adapt its real read-only event IDs to this source-reference interface, with both negative and legitimate positive tests. No new mutable parallel journal. Maintain `REMEMBERED_ANSWER != VERIFIED_TRUTH`.
