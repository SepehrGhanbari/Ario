# R06 — Exact lexical first-page wire, live XERJ rc.102 and regression (2026-11-14)

**Status: RESEARCH ONLY / PR #185 DRAFT-HOLD / NOT MERGED / NOT ACTIVATED.**

## Authorization and preservation

Continued under the owner's explicit instruction to continue bounded research and previous consent to scoped experimental PR edits. Before any R06 PR file changes, created and **verified** `backup/xerj-pr185-pre-r6-20261114` at old HEAD `6afdd1c474f1113673c4f1cef4749209bc1956c4`. The original adapter and three existing test files were re-read from the PR branch and backup; their Git blob hashes matched exactly. No force-push, rebase, merge, historical result rewriting, signer/trust activation, real Ario ledger, or private project data.

Five changed paths, all under `experiments/xerj-readonly-r0-2026-11-12/`:

1. `ario_xerj_readonly.py`: `search()` now explicitly requests `track_total_hits=true`; strict parsing accepts only the frozen **single-index, single-shard, lexical match, first page, no filter/pagination modifier** response with a nonnegative exact object `{"value":n,"relation":"eq"}`. A response having `len(hits) != min(n,k)` (including zero hits with n>0) is `RETRIEVAL_INCOMPLETE` and emits zero candidates/root labels. `skipped` metadata must be present in this experimental wire. A missing, `gte`, integer or malformed total is **unsupported/inexact in this specific strict profile**, not a universal XERJ defect. Legacy direct-fixture parsing without `require_completion_metadata` remains available but is not the live contract.
2. `test_r4_strict_completion.py`: positive and negative short-page pairs, lower-bound/absent totals, invalid total shapes and skipped field, all nonauthorizing.
3. `test_ario_xerj_readonly.py`: existing direct-fixture helper and randomized strict fixtures now provide correct exact totals so real positive acceptance is still exercised; 1,500 test iterations remain one deterministic randomized test, not 1,500 independent runs.
4. `test_wire_contract.py`: mocked normal HTTP response supplies the exact total and verifies `track_total_hits=true` in outbound request.
5. This **new append-only R06 report**. Earlier R0–R5 notes and historical failures have not been overwritten.

## Real engine observation before R06 patch — two isolated runs

Official Linux-musl XERJ v1.0.0-rc.102 asset SHA-256 `990532c0ceeef58c2ffb8756c928b99b38641c6c12d2d025124236a8955aef94`, checked against user-provided sha256 sidecar. Ran inside disposable chroot in unprivileged user/mount/network namespaces: host nobody mapping, loopback only, no outbound routes, bounded CPU/memory, isolated synthetic-only index, no actual Ario records or keys. Temporary API credentials were never exported. Engine stopped at the end of each run.

Both runs used the **same 85 synthetic agent-memory records and 75 questions**, dataset SHA-256 `bac616fb74bafeccff94c5b990b343c9a972ceed87b91dbf7346fa15ca7d4cb4`.

- **Run A:** existing PR185 lexical match body `{"size":5,"_source":false,"query":{"match":{"text":"..."}}}`. All **75/75** HTTP 200, `hits.total` `eq` object, one healthy shard `(1,1,0,0)`, `timed_out=false`, and **0** exact first-page length discrepancies. One legitimate zero-hit/zero-total result. `match_all` positive control on the 85-record index with sizes 1, 3, 5, 10 gave 85 `eq` and exactly the requested number of hits.
- **Run B:** identical search, but with **explicit `track_total_hits:true`**. Again all **75/75** HTTP 200, `eq`, healthy shard and **0** short-page inconsistencies. This directly verifies the option now frozen in `search()`.
- Additional **36 variant probes** (6 queries × 6 variants): default and `track_total_hits:true` returned `eq`; `track_total_hits:false` omitted `hits.total`; integer tracking caps 1 and 2 returned `gte`. An attempted `rest_total_hits_as_int:true` in the JSON *body* produced HTTP 400 and is **not** a valid test of that query parameter's supported semantics.
- Auth controls: no key **401**, scoped read-only key write **403**, foreign-index search **403** in both runs.

**Limit:** these are bounded observations of a small, healthy corpus, not a guarantee that all XERJ paths, deployments, malicious providers, larger corpus/timeout conditions or ranking are correct. Exact `eq` plus matching page length only tests *internal consistency of a claimed first page*. It neither proves completeness/recall nor establishes the bytes internally searched.

## Post-commit reproducibility

- Exact new adapter Git blob SHA-1 should be `05087917880f345f522f88e82da8efef759483a9`, SHA-256 `ab9bcbf017496a2682c9f42f7849b826c2a07f73a1ab9bd313b9e0eed52c5ce9`.
- On a separate connected Windows test host, downloaded the **exact updated GitHub commit** `2862d49468af216b75d75b44cc528eea967d460e` and ran `python -B -m unittest -q test_ario_xerj_readonly test_wire_contract test_r4_strict_completion`: **51 tests, exit code 0, PASS**. The downloaded adapter SHA-256 matched the local prototype.
- Independent deterministic exhaustive constructed oracle: **140/140** exact-`eq` lexical first-page shapes agree with the patched parser under the declared contract; zero mismatches (30 candidate responses, 5 honest empty responses, 105 incomplete). The **previous** R5 code mismatched the same oracle on 70/140 constructed cases. Neither count is an observed real-XERJ failure rate.

The conversation research package contains two per-query live raw-metadata JSON outputs, a separate 140-case oracle JSON, harness code and hashes. The raw package is **not committed into GitHub**; reviewers should distinguish author reports from an independently executed check.

## Trust, unknowns and post-review disposition

XERJ remains a replaceable *candidate* retriever. All search results retain `answer_authorized=false`, `trust_activated=false`, `source_independence=NOT_ESTABLISHED`. The code still resolves returned IDs through a supplied local mapping and **does not independently attest that XERJ searched those bytes**. A stale indexed document, poisoned-but-valid-ID index, altered rank, forged same-provider `_source`, false truthful-looking hit total, omitted matches, or an attacker changing the indexed corpus between runs can bypass purely internal metadata checks.

R2/R3 version binding, signed/offline canonical build manifest, epoch fencing including untracked ABA, independently anchored provenance, quarantine result type and real epistemic admission checks remain **separate research/HOLD**, not silently incorporated here. No actual Ario evidence ledger connected; no merge into `main`; no deployment, credentials, signer or governance change.

`_shards=(1,1,0,0)` is an experimental supported configuration, not a universal XERJ security claim. Similarly, `gte` and omitted totals can be legitimate **for other request options**; this frozen strict profile chooses to reject them as **unverified completion**, not as proof of malicious truncation. Unknown and failure remain non-authorizing.

**Action:** review R06 diff, tests, observed wire and limitations. New HEAD CI and CodeRabbit results must be checked and documented separately; do not label this report an independent security certification.
