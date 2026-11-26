# W4 — Retrieval hits ≠ current memory: archived benchmark re-audit and new evaluation gate

**Date:** 2026-11-16. **Status:** `ARCHIVE_BYTES_HASH_VERIFIED / SIX_ARMS_REAUDITED / HISTORICAL_XERJ_OUTPUTS / PRO_REVIEW_COMPLETE / LIVE_SAME_HOST_HEAD_TO_HEAD_NOT_RUN / HOLD`.

**Owner's exact historical study:** `ARIO_XERJ_SQLITE_R1_AUDIT_2026-11-14_FA.md` plus `ARIO_XERJ_SQLITE_R1_RESULTS_2026-11-14.json` from owner ChatGPT Library. The original JSON was materialized read-only into isolated analysis scratch; SHA-256 verified `20a0dba360de42d8a7659496728cbdcad2e0a48fb728eb5e04eca2f8cbbb21de` (329,767 original bytes). The JSON **reports** its source corpus `XERJ-research/benchmarks/agent-memory/dataset.json` with SHA-256 `bac616fb74bafeccff94c5b990b343c9a972ceed87b91dbf7346fa15ca7d4cb4`. The underlying 85-record corpus was **not independently opened or hashed in this new re-audit**.

**Actual code execution in this turn:** standard-library Python [w4_archive_reaudit.py](w4_archive_reaudit.py) executed locally against the original 329,767-byte source; strict source hash; 75 distinct query IDs and aligned category labels checked across six methods, bounded top-5 ID lists; [aggregate results JSON](W4_ARCHIVE_REAUDIT_AGGREGATE_2026-11-16.json) published without private raw texts. Both published files were independently Git-blob checked against the tested local exact bytes: script `7f5dc6fe2af6b91bd4df73095224e0465630ba41`, aggregate `a5bd03b07694e1ebce77b6ebf8e7d30ffb1ec6cb`. The script trusts the archived original correctness booleans; **it is not an independently rebuilt gold-label oracle**.

**Consensus Pro source:** [W4 Retrieval Quality vs Memory Update Correctness](https://consensus.app/search/ario-research-sprint-user-says-consensus-pro-free-/VuDCwb2IQpWmsnS4iXRJGA/), completed as `mode=pro`. Only this Ario-authored critique is retained here; the full provider report and its paper corpus are not mirrored or claimed to be independent peer review.

## 1. What the archived results *actually* say

The prior owner-run study consists of a **live SQLite FTS5** run on an 85-record synthetic corpus, and **re-scoring archived XERJ rc.100 outputs collected on another host**. The report does **not** constitute live same-machine comparison of the engines. Question distribution is 25 exact, 25 paraphrase, 15 knowledge update and 10 distractor queries.

| Retention/candidate ranker | Hit@5 overall | Paraphrase Hit@5 | Updated record in top five | Latest/correct replacement ranked first |
| --- | ---: | ---: | ---: | ---: |
| SQLite FTS5 all-terms | 56/75 | 7/25 | 14/15 | 3/15 |
| SQLite FTS5 stop-terms | 56/75 | 7/25 | 14/15 | 3/15 |
| Archived XERJ BM25 | 55/75 | 6/25 | 14/15 | 2/15 |
| Archived XERJ Semantic | 71/75 | 21/25 | 15/15 | 2/15 |
| Archived XERJ Hybrid | 70/75 | 21/25 | 14/15 | 2/15 |
| Archived XERJ Hybrid + Recency | 51/75 | 9/25 | 14/15 | 14/15 |

**Core measured discrepancy:** Semantic retrieves the designated updated record somewhere in its top-five for all **15/15** update queries, but puts that new version first in only **2/15**. If a downstream reader assumes rank-one = current truth, a good retrieval result can still be a bad memory update. **This record does not measure actual answer-model correctness or verified source truth**.

**Ablation tradeoff, same archived labels:** `Hybrid+Recency` lifts top-one update correctness from 2/15 (plain semantic or hybrid) to **14/15**, but falls from 25/25 to **18/25** on exact Hit@5 and from 21/25 to **9/25** on paraphrase Hit@5 versus Semantic. A single global recency weight is a poor substitute for a separately validated *time/identity/scope-aware* resolution step, although this observation alone cannot establish that a resolver would succeed.

**New per-query recomputed discrepancies (not just aggregate percentages):**
- Semantic versus FTS5 all-terms: **16** queries where Semantic alone has a correct top-five hit, **1** where FTS5 alone has it. The net 15-query advantage is mostly paraphrase (+14/25).
- Hybrid+Recency versus Semantic: **1** query exclusively covered by recency, **21** exclusively covered by Semantic at Hit@5.
- Exactly **3 query IDs** `p04`, `p20`, `p21` have `hit5=false` in **all six archived arms**. All three belong to paraphrase. They warrant independent source-text/gold audit; the archived flags alone cannot diagnose why.
- These are fixed synthetic questions with shared underlying episodes. Do not treat them as 75 independent real-world studies or claim significant superiority of one vendor.

## 2. The other, separate live-XERJ record in #185

The original [PR #185 R0 README](https://github.com/SepehrGhanbari/Ario/blob/research/xerj-readonly-candidate-r0-20261112/experiments/xerj-readonly-r0-2026-11-12/README.md) and earlier `RESULTS_R03.json` correctly say `LIVE_XERJ_EXECUTED=false` for their *historical stage*. **Do not carry that older status forward as the current status of the entire PR.**

[Later R06 report (14 Nov)](https://github.com/SepehrGhanbari/Ario/blob/research/xerj-readonly-candidate-r0-20261112/experiments/xerj-readonly-r0-2026-11-12/R06_EXACT_FIRST_PAGE_LIVE_2026-11-14.md) reports official Linux-musl `v1.0.0-rc.102` in an isolated container/chroot with two runs of 75 HTTP queries on 85 synthetic records, consistent exact first-page totals, authentication/foreign-index controls, and additional 36 query-option variants. The report's raw wire payload is not in this GitHub PR and was **not re-executed or independently matched here**.

R06 addresses **API-wire consistency**, not ranking correctness, semantic equivalence, truth, source completeness or error-free indexing. No contradiction with the archived October `rc.100` quality study: they are different questions, versions and runs.

**Official upstream [XERJ releases](https://github.com/xerj-org/xerj/releases):** at check, `releases/latest` yielded `rc.101`, with a Windows binary; `rc.102` was explicitly described as Linux-only in its dated release note. `rc.101` notes distinguish the Apache-2.0 public engine from **optional proprietary XERJ-Query inference crates/model assets**. A search benchmark must distinguish lexical/semantic retrieval from an optional question-answering/inference model; licenses and permitted redistribution are separate.

## 3. Why a current-memory oracle is needed

Three requirements are not equivalent:

1. `candidate_recall@5`: designated historical record appears somewhere in top-five.
2. `current_valid_record@1`: highest answer candidate has the right subject/scope and *valid-time* version, with any superseded records retained for historical queries.
3. `answer_supported_in_scope`: the final answer accurately quotes/derives from specific opened canonical sources, resolves corrections and abstains if evidence insufficient.

Even a canonical SHA-256 on the retrieved record only addresses byte identity. It does not establish who said it, the correct time period, the record's underlying truth, or a permission for actions.

**Primary supporting research:** [LongMemEval, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html) explicitly separates knowledge updates, temporal reasoning and abstention from ordinary retrieval across 500 questions. [LoCoMo, ACL 2024, DOI 10.18653/v1/2024.acl-long.747](https://aclanthology.org/2024.acl-long.747/) tests multi-session long conversations. [SQLite FTS5](https://www.sqlite.org/fts5.html) documents its lexical tokenizer and lower-is-better BM25; it makes **no** real-world source-authentication guarantee. BEIR and newer 2025/2026 RAG papers mentioned in Consensus are methodological leads, not independently verified comparative results for Ario. The user-provided [Eywa 2026 preprint](https://arxiv.org/abs/2605.30771) separates retrieved evidence from answer-policy instructions; its performance claims are author-reported, not Ario replications.

## 4. Preregisterable, matched W4-B lab — **not yet executed**

**Do not retrain or tune on the exposed original 75 questions and claim a blind holdout.** New corpus/query author must be independent of evaluator tuning, with private time-scoped gold and reproducible release after frozen predictions.

**Matched arms:** deterministic SQLite FTS5 lexical; **live pinned XERJ rc.102** lexical; optional XERJ semantic and hybrid only if the same reproducible engine/config supports them; one cheap dense baseline only if predeclared and affordable. Every arm sees the exact same **authorized, synthetic, fixed dataset bytes and query scope**. Freeze original record IDs, subject principals, source provenance, recorded-at time versus valid-from/valid-to time, supersession edges, tombstones/deletion/privacy constraints and versioned hash scheme. Record exact engine asset SHA-256, index-build hash/options, host, Python/SQLite versions, tokenizer, embeddings, query transformations, top-k, storage cost, cold/warm latency and server/network overhead.

**No false test equivalence:** don't compare a fresh rc.102 semantic model with old rc.100 archived predictions as a head-to-head. Don't compare in-process SQLite microseconds with remote XERJ HTTP times. Don't treat `gte` or omitted total as a malicious attack when requested options legitimately allow them; R06's exact-shard/total acceptance is intentionally a narrow first-page profile.

**Primary endpoint proposed before any gold release:** time- and principal-scoped *correct current answer*, with `UNKNOWN` when no admissible source exists. Report `false-current-answer` numerator/denominator and valid abstention; then secondary Hit@1/5, latest-valid@1, evidence cited to original raw record, privacy leakage, source-identity confusion, false rejection of valid unusual records, and p50/p95 latency in separate warm/cold dimensions. Use matched query IDs; for inferential intervals resample at the genuinely independent episode/author cluster, **not simply 75 correlated questions**. The archive's old paired bootstrap CI [0,4] percentage points for FTS5–BM25 is descriptive within this crafted dataset, not proof of general superiority.

**Twenty future challenge families** (proposed, not executed; each has a clean positive/negative control): corrected preference; multi-turn changing validity; two same-named principals; adversarial retriever snippet; third-party quote; copied source alias; misspelled query; compound query; swapped time range; stale index; deletion/retention conflict; recorded claim versus verified fact; ambiguous origin; absent reply; repeated stale fact in old sessions; malicious authority-bearing tool argument; valid abstention; fabricated rank/score; apparent source diversity under one controller; large-corpus/timeout/partial-first-page behavior.

Schema: `{query_id,scenario_family,corpus_sha256,index_snapshot,engine,engine_version,query_transform,scope,k,retrieved:[{doc_id,record_sha256,recorded_at,valid_from,valid_to,supersedes,principal_id,score,score_trusted:false}],candidate_hit5,current_version_top1,source_authority:"NOT_ESTABLISHED",abstained,answer_supported_in_scope,latency_cold_ms,latency_warm_ms}`. Raw texts stay in permitted owner-private custody until distribution rights are settled.

## 5. Decisions and falsifiers

- **ADOPT / research:** always distinguish retrieval from temporal adjudication, source support and authorization; `UNKNOWN` is valid. Freeze the corpus, query set and origin; preserve the question- and episode-level error ledger.
- **TEST:** first reproduce XERJ rc.102 and FTS5 under equal resource/host/index constraints using *new blind* time-corrected episodes. Measure whether metadata-aware post-retrieval selection improves correctness without destroying recall, and separately measure absence of false promotions.
- **TEST:** investigate `p04,p20,p21` as difficult paraphrase cases in the *exposed archive*; **never** move them into the unseen test set after viewing their IDs.
- **HOLD:** adoption of XERJ, promotion of retrieved records into evidentiary truth, reading of real user ledger, changing memory status `ACCEPTED`, signer/keys/Ruleset, trust activation, production deployment and merges.
- **REJECT:** treating 75/75 HTTP success in R06 as 75/75 answer accuracy; treating 94.67% Hit@5 as “94.67% true memory”; declaring one engine winner across unmatched hosts/versions or redistributing the owner archive and provider PDF without permission.

**Timeline:** user clarified on 2026-11-16 that the Consensus Pro trial has about seven days remaining. An existing scheduled research automation was **updated successfully** (ID `6afb4b7b845881918826b270ef1da81b`) to run daily 17–23 November 2026, flexible 15:00 Europe/Copenhagen, seven runs. This is an execution schedule, **not** verification of the subscription's actual expiry minute or a promise of access on each future run. **Neither W4 nor the schedule purchased additional credits or used Deep mode.**
