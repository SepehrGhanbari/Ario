# W7 — Ario research claim/evidence ledger and next falsification gates

**Date:** 2026-11-16. **Status:** `EVIDENCE_RECONCILIATION / SOURCE_CHECK / NO_NEW_OPERATIONAL_RUN / RESEARCH_ONLY / HOLD`.
**Purpose:** prevent the results of W1–W6, historical research PRs, and first-party manuscript claims from being inflated into scientific validation or runtime permission. This is the requested [Issue #195](https://github.com/SepehrGhanbari/Ario/issues/195) “failure archive + falsifiers” discipline, not a competing research roadmap or a new core implementation.

**Methodological primary anchors (independently verified with publisher/PubMed):**
- Nosek, Ebersole, DeHaven & Mellor, *The preregistration revolution* (PNAS 2018), [DOI 10.1073/pnas.1708274114](https://doi.org/10.1073/pnas.1708274114): hypothesis development from seen evidence and genuinely prospective testing on new data must not be collapsed.
- Munafò et al., *A manifesto for reproducible science* (Nature Human Behaviour 2017), [DOI 10.1038/s41562-016-0021](https://doi.org/10.1038/s41562-016-0021): research should retain transparent methods/reporting and reproducibility/verification boundaries, not just selected success outcomes.
- [W3C PROV-DM](https://www.w3.org/TR/prov-dm/): origin/derivation records do not by themselves certify proposition truth or a statistical causal effect.
- [LongMemEval, ICLR 2025](https://proceedings.iclr.cc/paper_files/paper/2025/hash/d813d324dbf0598bbdc9c8e79740ed01-Abstract-Conference.html): retrieval, knowledge updates, temporal queries and abstention are different abilities. **None of these sources evaluated the Ario project**; they motivate the proposed methodology only.

## Evidence grades (must be explicit for every claim)

- `REPRODUCED_LOCAL_SYNTHETIC`: actual source-pinned code and outcome executed again in the audit environment, but authored fixture/oracle may remain non-independent.
- `RECOMPUTED_FROM_ARCHIVE`: old raw result/labels were checked by new independent code; underlying ground truth and engine execution remain inherited assumptions.
- `AUTHOR_REPORTED_EXECUTION`: source contains a dated primary investigator's run/hashes; this researcher read it but **did not** repeat it.
- `PRIMARY_THEORETICAL_ANALYSIS`: mathematical/source-contract conclusion, not a test of a running Ario engine.
- `DESIGN_ONLY / NOT_EXECUTED`: scoped proposal, scenario list, or preregistration.
- `NOT_ESTABLISHED`: objective requires additional sources, independent custody, or a new experiment; not a negative verdict on the entire project.

## Claim-to-evidence and falsifier table — findings as of this cutoff

| Claim or potential overclaim | Best actual evidence / level | Falsifier / one narrow next gate | Current decision |
| --- | --- | --- | --- |
| **W1 TB-003 source graph handles hidden dependencies** | 80 deterministic variants of **8 logical families**, pinned local execution; 30 intentionally false-premise latent mismatches. **REPRODUCED_LOCAL_SYNTHETIC** | Independent author creates latent-world sources and separately frozen masked graph; blinded adjudication after pre-reveal predictions. The 80 variants are **not** 80 independent worlds | `DEVELOPMENT_ONLY`, W1-B blind holdout has **0 verified independent worlds** |
| **Hash + witness count proves independent source truth** | Prior 16/16 first-party co-designed cases, W1 30 latent mismatches, CT/source-copy methods. **PRIMARY_THEORETICAL + SYNTHETIC** | Distinct but secretly common-owner/log-root controls; independently verified inventory with named scope. Preserve `UNKNOWN` | `NOT_ESTABLISHED`; no admission/trust |
| **A successful tool observation semantically supports arbitrary memory claims** | W2 actual source-pinned CPython 3.13 negative probe: unrelated hypothesis became `VERIFIED_EMPIRICAL`; failed-tool control refused. **REPRODUCED_LOCAL_SYNTHETIC** | For new implementation, unrelated stdout + successful tool should remain unassessed; truly related, separately scoped support should not be falsely rejected | `VERIFIED_DRAFT_SEMANTIC_GAP`, linked to #216 / PR #210 |
| **Legacy `ACCEPTED` means historical empirical truth** | Draft #210 uses `ACCEPTED` by default, #216 identifies semantic migration risk. **SOURCE_READ / DESIGN** | A v2 sidecar preserves original bytes/IDs while keeping `RECORDED` apart from `SUPPORTED`, and explicit negative tests show no silent promotion | `HOLD`, no status/ID migration |
| **Causal DAG of evidence proves `do(X)`** | W3 two observationally identical SCMs with different interventions; W3C provenance vs causal-model theory. **PRIMARY_THEORETICAL_ANALYSIS** | An explicit SCM, identification assumptions, measured variables and intervention oracle; until then UI should say `Remove premise: recompute support` | `REJECT_AS_CURRENT_CLAIM`, #208 research only |
| **Archived XERJ Semantic finds the right memory and the newest version** | W4 re-audit of owner 75-query JSON: Hit@5 71/75, update record in top five 15/15, but latest-first 2/15. **RECOMPUTED_FROM_ARCHIVE** | Same-host/snapshot new blind semantic vs lexical with time-validity and `UNKNOWN` controls; independently adjudicated episodes | `QUALITY_TRADEOFF`, retrieval candidate ≠ current memory |
| **Real XERJ engine was never executed in #185** | Historical README/R03 say no live; newer R06 reports isolated Linux-musl `rc.102` two ×75 HTTP pages. **AUTHOR_REPORTED_EXECUTION** | Repeat R06 from exact asset/hashes and test same-source ranking separately. Note wire consistency ≠ answer accuracy | `OLDER_STAGE_STATEMENT_SUPERSEDED` |
| **R9-A/B/C passing tests establishes exactly-once external effects** | Prior author-reported 17/17, later R9-B 19/19/20/20, R9-C 25/25 *synthetic*; successful rollback/stale-epoch attack traces. **AUTHOR_REPORTED_EXECUTION** | Use truly external destination-side idempotent conditional commit and independently operated checkpoint; exercise ACK-loss and same-root full rollback separately | `NOT_ESTABLISHED`, #212/#213/#236 DRAFT/HOLD |
| **Research release Git tree SHA is accurately recorded** | W6 actual GitHub commit+tree and 264-path/blob/size readback; **2 mistyped tree fields**; 6 RAM-only RED/GREEN controls. **REPRODUCED_LOCAL_SYNTHETIC (for verification logic)** | Versioned corrected sidecar matches Git `commit.tree.sha` and fails when commit SHA is passed as tree. Don't rewrite published package | `VERIFIED_METADATA_DEFECT`, correction in research PR #242; source release #202 notified |
| **14 Nov full research ZIP contains all historical/private work** | Exact commit source file accounting **264/264**, including 24 deliberate index-only exclusions; unpublished PR/private files excluded. **REPRODUCED_SOURCE_TREE_INVENTORY** | Demonstrate missing tracked file in pinned tree inventory or claim broader coverage than pinned source; verify full ZIP/TXT bytes separately | `SCOPED_COMPLETENESS_ONLY` |
| **Zenodo book Version 6 PDF contains sixth-edition content** | Publication record V6 label conflicts with published PDF V5 cover/file names, documented in source audit/README. **FIRST_PARTY_AUTHOR_AUDIT, NOT NEWLY REPLICATED** | Authenticated publisher-deposited edition with unambiguous cover/page identity and independent original-byte comparison | `UNRESOLVED_LABEL_CONFLICT`, preserve originals |
| **Ario independently governed signer/keys and main runtime are proven** | Distinct signer R62/R63 labs and owner's separate conversational runner work are **outside this research window**; sources expressly say separate root/authority NOT ESTABLISHED. **NOT_ESTABLISHED** | Strictly separate custodian/operator domains and scoped signer governance tests before any operational claim; conversational runtime has its own evidence protocol | `NO_GO` for trust/production; no interference with builder |

## Hall of Failure — preserve the uncomfortable evidence

Negative results must be registered with the **predicate that failed**, not buried under “PASS”:

- `HOF-W1`: hidden common-admin/source roots: 30/80 latent synthetic disagreement **given falsely declared graph completeness**. Fails **unqualified independence promotion**; does not necessarily violate TB-003 conditional contract.
- `HOF-W2`: unrelated successful tool evidence promotes an unrelated memory hypothesis to `VERIFIED_EMPIRICAL`. Fails **semantic claim-to-evidence relevance**; not an external exploit.
- `HOF-W4`: high Semantic Hit@5 accompanies latest-first 2/15; global recency boosts 14/15 but loses 20 more top-five hits overall versus Semantic (21 Semantic-only, 1 recency-only). Fails **assumption that raw rank supplies temporal truth**.
- `HOF-R9-A`: T09 local full rollback, T17 remote-epoch race are **successful adversarial attacks**, although their test assertions are green.
- `HOF-R9-B/C`: local shared-root rollback allows consumed epoch reuse; unresolved provider-effect ambiguity under lost ACK.
- `HOF-W6`: actual Git tree ID misbound to commit SHA in two historical release JSON files; all 264 path/blob/size records nevertheless correct. Fails **typed source identity**, not complete source inventory.
- `HOF-BOOK`: publisher record edition label and PDF cover disagree. Neither invent revision content nor replace original.
- `HOF-CI`: Implementation Regression passing is **not** evidence that all standalone Linux experimental suites were executed; current Vercel platform build-rate failure is not itself a source-code regression.

These are separately falsifiable results. None should be added to automatic live memory or signer authority.

## Three highest-value research gates after this checkpoint

1. **P0 research: claim-to-source relevance + safe v2 status** (#216 / #210). Already have an actual negative fixture; independent adversarial scrutiny should clarify what positive `SUPPORTED_IN_SCOPE` requires. This directly matters to a future conversational Ario but **does not modify it now**.
2. **P0 research: W1-B truly independent masked evidence** (PR #242). Tests must separate **graph contract consistency** from **unknown real-world omitted dependency**. No invented oracle or second AI role as fake independent reviewer.
3. **P1 research: independent custody / external effect reconciliation** (R9). A common-admin two-process lab and local conditional SQLite simulation cannot establish real external exactly-once; prioritize explicit **UNKNOWN** failure modes, not extra pseudothreshold witnesses.

**Lower immediate value:** more renamed synthetic cases, repeatedly comparing 75 exposed questions, adding a fourth restatement of the same literature synthesis, or opening yet another PR just for a research note. Real engine/real operator tests remain out of this research window.

## Publishing/readiness controls

**Scientific communication:** a paper's math/protocol, author's local run, independently repeated run, and authenticated real-world deployment are *different evidence levels*. Report “successful attack” and “non-authorizing field remained blank” by their own denominators. Do not use `peer reviewed` for the first-party Zenodo and SSRN preprints. Keep negative cases, source hashes, issue/PR links, versioned amendments, abstentions and incomplete status.

**Methodological basis only:** Nosek et al. and Munafò et al. are original scientific publications about transparent research practices, not independent reviews of Ario. Their practical lesson here is to preserve *prediction-before-observation* and avoid using the same author-designed scenarios as generalization proof.

**Current subscription limitation:** Consensus Pro successfully returned W1–W4 studies but a later W5 new-thread request was explicitly rejected for exhausted included usage. User reports about seven days remain until trial end (~23 November); that does **not** imply further free queries. No paid usage is authorized.

**Disposition:** `RESEARCH_ONLY / DRAFT_HOLD / MAIN_UNCHANGED / NO_MERGE / TRUST_ACTIVATION=NO_GO / GENESIS=NO_GO / PRODUCTION=NO_GO`.
