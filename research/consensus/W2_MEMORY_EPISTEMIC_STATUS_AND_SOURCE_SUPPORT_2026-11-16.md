# W2: Memory source-status, attribution and false-corroboration research (2026-11-16)

**Status:** `RESEARCH_ONLY / SOURCE_PINNED_SYNTHETIC_PROBE_EXECUTED / DRAFT_HOLD / NO_MERGE / NO_AUTHORITY`
**Primary provenance:** Draft [PR #210](https://github.com/SepehrGhanbari/Ario/pull/210), exact head `07068bdfa36abb29a3ce8e927077df3ffe02b0cf`; related [Issue #209](https://github.com/SepehrGhanbari/Ario/issues/209), [#216](https://github.com/SepehrGhanbari/Ario/issues/216), [#223](https://github.com/SepehrGhanbari/Ario/issues/223), [#227](https://github.com/SepehrGhanbari/Ario/issues/227), retrieval [PR #185](https://github.com/SepehrGhanbari/Ario/pull/185).
**Consensus Pro specialist follow-up:** https://consensus.app/search/research-task-for-arios-7-day-consensus-pro-window/BJkJUt6YR-KpC1hAWbLDyQ/
**Reminder:** The Consensus answer is an AI-generated review, **not an independent science validation**. Original full provider output is retained in the owner's account, not copied into this repository.

## 1. Verified independent negative-control result (W2-F1)

The PR #210 **source_monitoring.py** source was retrieved at the pinned head, Git blob `b3b500ebc8736aa5475d117f508a769a39b78d6d`; a separate Windows test host independently reproduced this digest using `git hash-object`. [Exact executed source probe](w2_source_semantics_probe.py) runs under CPython 3.13 with an isolated Python module name, only a synthetic `test_tool` allowlist and local strings.

- Build an unverified internal hypothesis: `An unrelated factual assertion about a blue box.`
- Call `record_empirical_observation` on a test tool (`exit_code=0`, `stdout="OK"`, local `execution_lock="synthetic-lock"`, and a different assertion `Synthetic test tool exited normally.`).
- Call `evaluate_claim_promotion(hypothesis_id, [successful_tool_observation_id])`.
- **Observed**: the unrelated hypothesis becomes `VERIFIED_EMPIRICAL`, even though the tool output supplies no semantic support for the claim.
- **Negative control**: `exit_code=1` with the same type of unrelated claim; `evaluate_claim_promotion` is blocked (caught `SelfCitationError`).
- **Execution result**: `W2_PROBE_EXIT=0`; assertions matched observed statuses. The probe did not call an actual tool for production data, nor change Ario files, memory, keys, user privilege, network, governance or state.

**Exact diagnostic stdout excerpt:**
```text
"unrelated_claim_promoted": "VERIFIED_EMPIRICAL"
"unrelated_claim_text": "An unrelated factual assertion about a blue box."
"successful_tool_assertion": "Synthetic test tool exited normally."
"failed_tool_control": "BLOCKED"
W2_PROBE_EXIT=0
```

**Source-code mechanism:** `record_empirical_observation` assigns `VERIFIED_EMPIRICAL` when `exit_code == 0` and recorded expected hashes do not mismatch; `evaluate_claim_promotion` tests that at least one supporting node has `EMPIRICAL_OBSERVATION` + `VERIFIED_EMPIRICAL` and that citations are noncircular. **No check relates the tool output/observation to the actual assertion being promoted**. The first function also accepts a caller-supplied `assertion` independent of `stdout`. This is a **reproduced semantic-support/label-overpromotion gap in a draft research implementation**; it is **not** proof of an exploitable production path or a claim that the program violates every stated syntactic invariant.

**Important distinction:** SHA or exit-0 supports *local execution/result consistency*, not proposition-level evidence, real-world truth, authorization or valid downstream action. The issue is **not** cured simply by adding more supporting IDs if all are unrelated.

**Suggested pre-reg implementation test gate (no patch or protected decision now):** synthetically assert (A) unrelated successful stdout → claim stays `UNASSESSED/UNSUPPORTED`; (B) meaningful, externally specified support predicate → `SOURCE_SUPPORTED` only within explicit scope; (C) unrelated failed stdout → refuse; (D) forged execution hash/duplicate reference/cycle → refuse; (E) honest external testimony remains recordable without becoming truth; (F) third-party truth/ground truth remains UNKNOWN if no independent oracle. Decide named support semantics separately in [#216](https://github.com/SepehrGhanbari/Ario/issues/216); do not make an ad hoc live change.

## 2. Source literature: established vs reported

| Work | Source quality | Relevant finding and bound |
| --- | --- | --- |
| Johnson, Hashtroudi & Lindsay, *Source Monitoring*, 1993; DOI [10.1037/0033-2909.114.1.3](https://doi.org/10.1037/0033-2909.114.1.3) | **PRIMARY VERIFIED** via [PubMed](https://pubmed.ncbi.nlm.nih.gov/8346328/) | Human source attribution is a **fallible judgment process**, not an origin-tag truth oracle. Cannot directly certify machine implementations. |
| McClelland, McNaughton & O'Reilly, *Why There Are Complementary Learning Systems...*, 1995; DOI [10.1037/0033-295X.102.3.419](https://doi.org/10.1037/0033-295X.102.3.419) | **PRIMARY VERIFIED** via [PubMed](https://pubmed.ncbi.nlm.nih.gov/7624455/) | Episodic/semantic systems as a cognitive modeling analogy; no proof that Ario's deterministic consolidation mimics neural processing. |
| Wu et al., *LongMemEval*, ICLR 2025, [official proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html) | **PRIMARY VERIFIED** | Five memory abilities: extraction, cross-session reasoning, temporal reasoning, updating, abstention; **500 questions** in the benchmark, not 500 independent real-user deployments. |
| Joshi, *Eywa: Provenance-Grounded Long-Term Memory for AI Agents*, arXiv:2605.30771 (2026) | **ORIGINAL PREPRINT, NOT PEER REVIEW VERIFIED**, [source](https://arxiv.org/abs/2605.30771) | Evidence-before-belief; reported LoCoMo/LongMemEval-S/BEAM outcomes and separation of retrieval context from instruction policy. Source support does **not** establish real-world truth. |
| *Useful Memories Become Faulty When Continuously Updated by LLMs*, arXiv:2605.12978v2 (user-provided PDF, reviewed previously) | **PREPRINT / AUTHOR-REPORTED** | Rewriting condensed memory can corrupt useful state on selected tasks. Do not transfer numeric ablations to Ario or automatically prohibit all semantic indexing. |
| *The Granularity Mismatch in Agent Security* (PACT), arXiv:2605.11039v1 (user-provided PDF, previously reviewed) | **PREPRINT / AUTHOR-REPORTED** | Distinguish tool argument data from authority-bearing roles; does **not** solve incorrect provenance labels or every allowed-content attack. |
| *Belief Engine*, arXiv:2605.15343v1; *The LLMbda Calculus*, arXiv:2602.20064v2 (user PDFs previously reviewed) | **PREPRINT / AUTHOR-REPORTED** | Operational stance ≠ truth; noninterference depends on accurate policy/source labeling and bounded endorsement assumptions. |

**Owner-supplied resource index consulted:** [Ario four-paper evidence review](https://github.com/SepehrGhanbari/Ario/pull/180) and Library file `ARIO_FOUR_PAPER_EVIDENCE_REVIEW_2026-11-10.md`; `Research_task_for_Ario_Epistemic_Middleware_memo.pdf` (10pp); `2605.30771v1.pdf` (29pp); other user-supplied Ario research PDFs. A Library attachment is **not a repo path**; do not claim `Resources/` is present in the current main tree without seeing it. The 2026-11-16 main tree did **not** contain a root `Resources/` directory. Preserve original PDF permissions; link or quote short claims instead of bulk mirroring.

## 3. Memory epistemic contract: proposed axes, not an accepted implementation

| Dimension | Recorded status | What must NOT be inferred |
| --- | --- | --- |
| **Capture** | `RECORDED` + raw byte identity + schema/version + line-terminator rule | Event truth, semantic coverage, consent to indefinite retention |
| **Execution** | `TOOL_EXEC_VERIFIED` within a pinned tool/target/receipt scope | Semantic relevance or correctness of the tool's emitted world claim |
| **Claim support** | `UNASSESSED / SUPPORTED_IN_SCOPE / CONTESTED / REVISED / OUTDATED` with explicit support relation | Independent source identity, global truth or unconditional permission |
| **World assessment** | `UNKNOWN` by default, unless separately specified externally authenticated adjudication exists | That `ACCEPTED`, a matching SHA or answer fluency equals world truth |
| **Authority** | Separate non-epistemic permission grant or `NONE` | That any memory/citation/status alone authorizes an effect |

Legacy `ACCEPTED` **must not silently map to `SUPPORTED` or `TRUE`**. A candidate v2 sidecar can interpret it only as historically `RECORDED/UNASSESSED` pending decision; **actual migration and node ID semantics remain HOLD under #216**. Preserve original bytes; no rewriting append-only history. `CONTESTED` should require bounded explicit incompatible evidence, not a mere suspicion or sensor failure.

## 4. Sixteen distinct proposed case designs for W2 (not independently executed)

Each case has a matching *benign/negative control* and explicit oracle unknown option; the table gives **research targets**, not outcome claims.

| # | Challenge family | Measurement |
| --- | --- | --- |
| W2-01 | Successful tool's output semantically unrelated to promoted claim **(executed local probe)** | false support promotion / positive related evidence control |
| W2-02 | A successful tool accurately reports its own execution but external sensor is wrong | execution consistency vs world accuracy |
| W2-03 | Accepted-looking stdout generated from altered input after lock creation | byte binding / missing provenance |
| W2-04 | Duplicate `case_id` or semantic ID across independent namespaces | false merge |
| W2-05 | Mutable nested object injected into a frozen memory node | preservation and aliasing |
| W2-06 | User statement quoted by a document from another speaker | attribution |
| W2-07 | Preference stated, revised at a later timestamp, queried for both times | bitemporal retrieval |
| W2-08 | Two same-named users, different principal scope | privacy and disambiguation |
| W2-09 | Two source aliases hiding same original document | independence overcounting |
| W2-10 | Irony/negation in user's statement | extraction certainty |
| W2-11 | Retrieved assistant claim “you said before” with no raw source | false memory and abstention |
| W2-12 | Index updated late, authoritative history newer | stale retrieval |
| W2-13 | Prompt injection inside retrieved context | authority-data separation |
| W2-14 | Partial JSONL last line; strict adapter vs permissive reader | parser compatibility, no silent skip |
| W2-15 | CRLF/LF and trim/raw line-hash versions | historical lineage compatibility |
| W2-16 | Query absent from all admissible evidence | proper `UNKNOWN`/abstention |

The previous 2026-11-15 issue findings #223 (aliasing/duplicate keys/resource bounds) and #227 (coverage, line-hash scheme, partial line) are **previously reported synthetic observations**, not new W2 test executions. W2-02 through W2-16 are **proposed/not run**.

## 5. Fair retrieval baseline: no authority or benchmark claims yet

Use one frozen, permission-cleared synthetic corpus and *identical* evaluated queries and available source bytes for: SQLite FTS5 lexical baseline, optional XERJ BM25 (existing Draft [#185](https://github.com/SepehrGhanbari/Ario/pull/185) is a MOCK, **real XERJ = NOT_TESTED here**), and optional semantic/hybrid system. Control for candidate count, context budget, retrieval latency, embedding/model cost, and identical version timestamps. Report (1) ingestion/schema coverage; (2) extraction fidelity; (3) retrieval sufficiency and top-k recall; (4) answer accuracy; (5) correct abstention; (6) attribution + privacy leak; (7) latency and token cost; (8) index rebuild cost. `CANDIDATE` is never `ADMITTED`.

**No new live memory ingestion, key access, real user ledger scans, unrestricted service startup, or model-in-the-loop pipeline in this note.**

## 6. Explicit limits and decisions

- `ADOPT` for **research rubric only**: record/capture, semantic support, world assessment and authority are distinct measurements.
- `TEST`: false relevance promotion, citation to unopened source, speaker scope, temporal correction, partial-line mismatch, retrieval cost parity.
- `HOLD`: actual versioned migration of `ACCEPTED`, source hash changes, node IDs, review gate semantics and code merge.
- `REJECT`: using Consensus AI summary or a neuroscience analogy as verification that Ario's architecture works; judging 16 hand-designed families as independently blinded validation.
- **Stop** if any write to a live memory ledger, trust activation, signer, owner credentials or sensitive host configuration is proposed; they are out of scope.

**Repro status:** W2-F1 is source-pinned and executed; other W2 families and an independent oracle are not. W2's research plan may be reviewed and corrected without conferring implementation authority.
