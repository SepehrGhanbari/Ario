# W8 — Claim-to-evidence relevance across the #210 memory prototype

**Date:** 2026-11-16. **Status:** `SOURCE_PINNED_SYNTHETIC_FALSIFIERS_EXECUTED / NOT_PRODUCTION / MEMORY_V2_NOT_ADOPTED / HOLD`.
**Targets:** [Draft PR #210](https://github.com/SepehrGhanbari/Ario/pull/210), [Issue #216](https://github.com/SepehrGhanbari/Ario/issues/216), prior [W2 observation](W2_MEMORY_EPISTEMIC_STATUS_AND_SOURCE_SUPPORT_2026-11-16.md); review dependencies [#229](https://github.com/SepehrGhanbari/Ario/pull/229), [#232](https://github.com/SepehrGhanbari/Ario/pull/232) (historically closed, proposals remain readable), [#238](https://github.com/SepehrGhanbari/Ario/pull/238) (independent parser-comparator scope, not a replacement for #210), [#209](https://github.com/SepehrGhanbari/Ario/issues/209).

## 1. Reproduction material and exact limits

**Actual branch source inspected/tested:** [`feature/cognitive-memory-consolidation`](https://github.com/SepehrGhanbari/Ario/tree/feature/cognitive-memory-consolidation), exact PR head `07068bdfa36abb29a3ce8e927077df3ffe02b0cf`. Three source Git Blob objects independently compared by `git hash-object` on an isolated Windows test PC:

| Source file | Git Blob SHA-1 |
| --- | --- |
| `implementation/core/source_monitoring.py` | `b3b500ebc8736aa5475d117f508a769a39b78d6d` |
| `implementation/core/memory_consolidation.py` | `b131bab9047d0c579e6a0dda6c0ee26861ef0100` |
| `implementation/core/prospective_memory.py` | `3991f38f4d6ed1b51c0753bec54dd66c446d9e25` |

Test machine: **Windows / CPython 3.13**, separately loaded modules with no Ario service, network, user data, disk ledger, live LLM, signer or independent witness.

Published execution artifacts:
- [14-case experimental probe](w8_source_claim_matrix.py) + [per-case JSON result](W8_SOURCE_CLAIM_MATRIX_RESULTS_2026-11-16.json): **14 expected outcomes matched, process exit `0`**; 1 known prior reproduction, **6 distinct new code falsifiers**, 1 schema/deserializer issue, 5 positive controls, 1 type control. They are *one author-authored synthetic test matrix*, **not 14 independently adjudicated worlds**.
- [Three-module contrary-stdout trace](w8_three_module_false_support_trace.py) + [raw synthetic result JSON](W8_THREE_MODULE_RESULTS_2026-11-16.json): source-pinned cross-module execution, one failing-meaning (but syntactically successful) tool example and one rejected nonzero-exit control, process exit `0`. The legacy [integration test in #210](https://github.com/SepehrGhanbari/Ario/blob/07068bdfa36abb29a3ce8e927077df3ffe02b0cf/implementation/tests/test_cognitive_memory_integration.py) uses the same general guard → filter → ledger → accepted semantic node → prospective cue path with **non-adversarial** test text; our trace supplies an explicitly contradictory message.

## 2. Observed 14-case source guard matrix

All tests use only caller-supplied synthetic strings. `PROMOTED` is **an actual V1 enum result**, not proof of empirical truth.

| ID | Stimulus (bounded) | Actual output | Scientific interpretation |
| --- | --- | --- | --- |
| B01 | unrelated successful tool → unconnected hypothesis | `PROMOTED` | Repeats W2 baseline |
| B02 | tool stdout `NOT_FOUND` contradicts claim `Target A exists` | `PROMOTED_AND_FILTER_ADMITTED` | **New downstream gate failure:** `require_verified=True` does not check semantic support |
| B03 | hash/status for Target A cited by claim about Target B | `PROMOTED` | No checked target/scope equality |
| B04 | completely empty stdout, exit 0 | `PROMOTED` | No meaningful evidence bytes required |
| B05 | no expected hashes, caller supplies success and asserted result | `PROMOTED` | Current API computes hashes of *supplied* data; no external receipt/tool-execution proof |
| B06 | hypothesis has dangling `GHOST-SOURCE-ID` parent | `PROMOTED_WITH_DANGLING_PARENT` | Cycle check does not imply graph closure |
| B07 | `SourceAttribution.from_dict` with `VERIFIED_EMPIRICAL` + fake parent ID | `DESERIALIZED_AS_VERIFIED` | Schema constructor accepts claimed status **without registry validation**; **not** proof this forged object entered guard registry |
| B08 | explicit attribution ID reused for unrelated assertion | `PRIOR_ATTRIBUTION_OVERWRITTEN` | Registry dictionary overwrites earlier mapping; no append-only audit trail in this local in-memory registry |
| B09 | Python `True` passed as exit code (subclass of int) | `UNSUPPORTED` | Correctly **not** a zero-exit promotion but type accepts bool; separate bounded type question |
| B10 | nonallowlisted tool | `BLOCKED` | Existing allowlist functions |
| B11 | wrong expected stdout hash | `BLOCKED` | Existing mismatch guard functions when a conflicting expected digest is supplied |
| B12 | nonzero exit tool parent | `BLOCKED` | Existing anti-promotion condition functions |
| B13 | external testimony without empirical parent | `BLOCKED` | Existing anti-self-citation condition functions |
| B14 | matching synthetic claim text / evidence text, successful tool | `PROMOTED` | Non-vacuous positive; **text match + exit0 is not independent truth** |

**Mechanism in original code:** `record_empirical_observation` computes SHA-256 of its **caller-supplied** `execution_lock` and `stdout`; expected digests are optional. With `exit_code == 0`, the *caller-provided assertion* becomes `VERIFIED_EMPIRICAL`. `evaluate_claim_promotion` checks that a parent has type `EMPIRICAL_OBSERVATION` and `VERIFIED_EMPIRICAL`, rejects self/circular cases, but never binds claim proposition, real tool target and actual stdout to a **named semantic evidence predicate**. `filter_working_memory_candidates(... require_verified=True)` then trusts that tag.

This demonstrates a bounded *API semantics/evidence-relevance* defect relative to the stronger claims in `COGNITIVE_MEMORY_SOURCE_MONITORING_V0_1.md`, **not** evidence that a production model has already made a false-world statement or that malicious external input can reach these methods unauthenticated. Validating checksums of self-supplied bytes is not independent tool attestation.

## 3. The actual multi-module status propagation — not just a label dispute

In the pinned three-module trace, a fabricated success `exit_code=0` with **stdout `NOT_FOUND: Target A`** and hypothesis **`Target A exists`** yields:

```text
claim.veracity                    VERIFIED_EMPIRICAL
guard.require_verified           1 accepted working-memory candidate
ConsolidationEngine              1 node, status=ACCEPTED
ProspectiveMemoryRegistry        status=TRIGGERED for a synthetic cue predicate based on ACCEPTED
External task execution          FALSE
```

The matched nonzero-exit control yields:

```text
claim.veracity                    UNSUPPORTED
guard.require_verified           0 candidates
ConsolidationEngine              0 nodes
ProspectiveMemoryRegistry        PENDING, 0 triggers
External task execution          FALSE
```

The `prospective` module merely emits a **local TRIGGERED status and synthetic action-payload record**, not an actual task runner/command; `main`, host user memory, keys, real signing and production authority are untouched. This trace proves the **cross-component propagation of V1 labels in the local prototype**, not real downstream effects.

**Critical design gap in #216:** Fixing only the `SemanticNode.ACCEPTED` name would leave `SourceAttributionV1.VERIFIED_EMPIRICAL`, `require_verified=True`, and historical prospective predicates such as `status == "ACCEPTED"` still capable of overpromotion. Any v2 view/adoption must cover **all three interfaces and consumer policies**, not just one enum or hash scheme. Conversely, blindly changing `ACCEPTED` to `RECORDED` can alter an existing historical cue without versioned migration: this is another reason for a sidecar rather than in-place rewrite.

## 4. Evidence and literature boundary

[Johnson, Hashtroudi & Lindsay, *Source Monitoring*, 1993](https://pubmed.ncbi.nlm.nih.gov/8346328/) explains that attribution to a source is an inferential and fallible process, **not** cryptographic proof of world truth. The user-supplied *Eywa* 2026 preprint and [ICLR 2025 LongMemEval](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html) motivate evidence-backed update/abstention tests; neither independently benchmarks Ario. Source locks and append-only references establish scoped byte/record identity if their root and custody are trusted; they cannot prove that the proposition is entailed by those bytes.

## 5. Falsifiable V2 support contract proposal (not ratified)

**Preserve Option B already recommended in [#216](https://github.com/SepehrGhanbari/Ario/issues/216) and historic [#232 decision matrix](https://github.com/SepehrGhanbari/Ario/blob/c456f9886fdebe0aee0d529f554603dcf4c04384/implementation/MEMORY_V2_MIGRATION_DECISION_MATRIX_V0_1.md):** immutable V1 records + opt-in V2 *read-only sidecar*, no silent `ACCEPTED` rewrite.

Separate **four non-interchangeable axes** in any proposed v2 view:

1. `capture_state`: `RECORDED`, `NOT_CAPTURED` or `UNKNOWN` with a version-tagged raw source reference. No `SUPPORTED` inference.
2. `execution_state`: `CALLER_REPORTED_SUCCESS`, `RECEIPT_VERIFIED_IN_SCOPE`, `FAILED` or `UNKNOWN`. Exit0 and same-origin hashes alone cannot reach the second state.
3. `claim_support_state`: `NOT_ASSESSED` / `SUPPORTED_IN_SCOPE` / `CONTESTED` / `UNKNOWN`. For `SUPPORTED_IN_SCOPE`, require a typed, exact proposition-to-evidence relationship with authenticated subject/target/time, independently reviewable raw evidence span (or test predicate/effect with exact output contract), full dependency reachability and a **separately authorized assessment event**; semantic entailment is **not** established automatically by a string match, embedding similarity or model vote.
4. `action_authority`: `NONE` unless a distinct approved policy/permission/effect gate grants action. Neither `VERIFIED_EMPIRICAL`, `ACCEPTED`, nor `SUPPORTED_IN_SCOPE` alone can grant a prospective action.

**Legacy projection:** `V1 ACCEPTED` and `V1 VERIFIED_EMPIRICAL` remain bitwise preserved and visible with origin `legacy`; in a V2 consumer their best **epistemic** import is `RECORDED/NOT_ASSESSED` (and `execution_state=CALLER_REPORTED_SUCCESS` when appropriate). Maintain historical IDs and a versioned ambiguity-preserving crosswalk: `("a:b","c")` versus `("a","b:c")` remains `UNKNOWN` for V1 ID resolution; legacy `negates` references must not guess the v2 target. No covert resurrection of older trimmed line hashes under raw-line scheme. Treat external approval, privacy and actual retention rights as **separate**.

**Prospective cue control:** existing `status=="ACCEPTED"` is a *legacy structural status*; prospective V2 consumers must never mistake it for `assessment_state=SUPPORTED_IN_SCOPE` or actual permission. Any modified cue policy must be versioned, backwards-compatibility-tested and reviewed by #216 owners. A read-only lab demonstrating safer interpretation is not a governance adoption.

### Required negative/positive tests for a candidate V2 gate

- `B02` contradictory stdout and `B03` cross-target evidence must **not** yield `SUPPORTED_IN_SCOPE`; working-memory may still show clearly labeled unassessed data when policy allows.
- `B04` empty evidence and `B05` self-supplied hashes must not be interpreted as independent verified execution.
- `B06` unresolved parent must produce incomplete dependency/`UNKNOWN`; `B07` deserialized claimed states must not self-verify.
- `B08` attribution IDs cannot silently replace prior records in a future append-only relation; conflict becomes explicit or refused.
- Positive control: a separately authenticated, exact-target, specified test contract with demonstrable raw evidence can yield `SUPPORTED_IN_SCOPE` **only after review and approval of that contract**; still not world-level truth or action authority.
- Historical V1 bytes and IDs remain identical after V2 projection, ambiguous source/crosswalk/Unicode/line-ending scheme tagged; old `negates` stays unresolved when ambiguous.
- Cross-module counterexample must stop **before** any assessed-positive cue or action authorization while retaining explainable recorded history. Avoid the vacuous solution of dropping all legitimate evidence.

## 6. Explicit decisions

- `VERIFIED_DRAFT_RELEVANCE_GAP`: B02/B03/B04/B05/B06/B08 and schema-only B07 are observed under the pinned code.
- `RESEARCH_ADOPT`: add `SourceAttributionV1` and `ProspectiveMemoryRegistry` to the scope of issue #216's versioning/authority proposal, not just `SemanticNode`.
- `RECOMMEND_OPTION_B_FOR_REVIEW`: historical V1 + opt-in V2 sidecar remains the least-destructive architecture **but is not an adopted owner decision**.
- `HOLD`: code patch, V1 semantic reinterpretation, source-ID algorithm, source hash scheme, CI/ruleset changes, memory recording, auto-authorization, live task dispatch, PR merge.
- `UNKNOWN`: outside-world truth of synthetic claims, whether any production Ario caller invokes this path, independent semantic evaluator accuracy, user privacy/retention implementation.

**Next review unit:** an independently reviewed evidence-binding schema, a versioned consumer migration contract and one *new* adversarial case authored by someone other than the evaluator designer. Reusing the same 14 synthetic fixtures for final blind scoring is not valid. No external reviewer/witness or sealed oracle was established here.
