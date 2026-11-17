# Claim–Receipt Read-only Support View — Research Contract v0.1

**Status: PROPOSED / NOT ADOPTED / RESEARCH-ONLY / DRAFT / HOLD.**  
**Source:** Ario cognitive-memory Draft #210 (current head 409613b433c86aea4fbed641dc9fed58ee852fe1); related failing characterization Draft #258, exact last head af9ad2b4b86522c3979dde9d3164111625b4fb39. **Issues:** #216, #81, #128.

## Reason for this experiment

On the source-pinned #258 negative test branch, Linux and Windows GitHub Actions both reproduced CE-01 (successful but irrelevant tool receipt promotes a claim), CE-03 (contradicting receipt/claim still promotes), and CE-04 (same receipt ID yields two lineage edges). Those are **failures of current research-module behavior**; they do not establish actual production compromise. Neither checksum equality nor allowlisted command exit code proves semantic support for an unrelated proposition.

Existing **EA-0.1** (`implementation/EVIDENCE_ADMISSION_CONTRACT_V0_1.md`), **ARP-0.1** and **RAC-0.1** explicitly separate observation, review, authorization and truth. Their positive admission authority is **NOT implemented**. This view reuses the same distinctions; it does not invent an authority, alter Module 2, or relabel old `VERIFIED_EMPIRICAL`, `ACCEPTED`, `OBSERVED` or semantic IDs.

## Exact boundary

`inspect_claim_support(registry, claim_id, supporting_ids, proposed_relations)` takes an already materialized in-memory **snapshot** of the pre-existing `SourceAttribution` registry. It never opens files, sends requests, calls `evaluate_claim_promotion`, writes to original guard/memory, mutates proof bytes, constructs M0 evidence, signs data or activates trust.

- `legacy VERIFIED_EMPIRICAL`: only a **reported tool-receipt state**, not an authenticated witness or a claim-entailment verdict.
- `proposed_relations`: untrusted proposer-declared `SUPPORTS | CONTRADICTS | UNRELATED | UNKNOWN`, not a model-verifier conclusion. Even `SUPPORTS` on a semantically irrelevant claim yields only `REVIEWABLE_ONLY`; this **is not** evidence that the claim is supported.
- `review_status=REVIEWABLE_ONLY`: a bounded well-typed **candidate for future review**, no epistemic promotion. It preserves positive same-topic receipts so reviewers can inspect them when real authorization and source custody exist.
- `review_status=UNKNOWN`: missing/contradictory/unrelated/invalid/duplicated supporting evidence, shared recorded ancestry, graph cycle, missing source or cap violation. A declared `CONTRADICTS` does **not** prove the claim false.
- `independent_support_count=0` in all results: distinct receipt IDs or distinct local lock hashes do not establish independently authenticated real-world sources.
- `source_authenticity=UNKNOWN`, `semantic_support=NOT_ASSESSED`, `claim_assessment=NOT_ASSESSED`, `admission_decision=NOT_EVALUATED`, `reviewer_authorization=NOT_ESTABLISHED`, `memory_mutation=NONE`, `history_mutation=NONE`, `contract_adoption=NOT_ADOPTED` on every path.

## Synthetic evaluation

Negative cases: unrelated claim; contradicting evidence claim; duplicate receipt ID; missing relation; unverified or testimony-only receipt; common-ancestor derived sources; missing ancestry; cycle; malicious SUPPORTS annotation; malformed and oversized inputs. Positive candidate cases: same-topic successful receipt and two disjointly declared receipts **remain REVIEWABLE_ONLY** with zero authenticated independent witness count. Historical V1 verified claim is left byte/value-for-value unchanged. No source text/IDs/hashes are returned, only fixed reason strings and small counts.

Tests **must not** imply that candidate review success proves truth; untrusted `SUPPORTS` is not validated by keyword overlap or NLI. No direct sidecar-to-core integration is authorized; do **not** fix #258 by marking RED assertions as xfail. A future versioned, independently authorized claim/receipt binding would need exact source locator, authenticated reader, bounded claim scope, independent reviewer role, real passage-based support assessment, cross-version compatibility and privacy review. Any uncertainty must continue to be representable as UNKNOWN.

## Unestablished / falsifiers

- The input registry is caller-owned and pre-materialized: no upstream byte, CPU or memory budget is proven.
- A Python object with malicious methods is not a trusted input; the strict type gates are not process isolation.
- An arbitrary proposer can lie about SOURCE origins, SUPPORTS and graph ancestry. Hashes/different IDs cannot establish independence or external custody; provenance graph describes **recorded** edges only.
- This is not a general natural-language inference engine, scorer, production access control or signer.
- Re-run exact-head tests under Linux and Windows; request independent code review. Keep #210/#216/#258 and this contract DRAFT/HOLD, no automatic merge or activation.

**Memory != Truth. Claim != Proof. Revision != Erasure. UNKNOWN is valid. PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO.**
