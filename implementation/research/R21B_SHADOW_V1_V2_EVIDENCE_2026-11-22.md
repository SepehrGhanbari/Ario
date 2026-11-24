# R21B — Experimental shadow connection to the real V1 reader, with separate V2 capture

**Date:** 2026-11-22  
**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_REAL_KEYS / NO_TRUST_ACTIVATION / PRODUCTION=NO_GO

**Pinned dependency:** PR #320 head `d65dcb095cb7ce1e60339ce9b32806f99755359c` (itself stacked on #295).  
**Unchanged V1 source:** `implementation/research/guard_v2_review_graph.py` Git blob `2c6cb3a8c569f6daa0b6c59bce14607454107a08`.  
**Separate V2 subset contract:** `implementation/research/guard_v2_r21b_capture_v2.py`, unchanged from #320.

## Why a shadow adapter rather than replacing V1?

The legacy `graph.compare_twice()` computes an SHA256 digest of the *full bounded V1 review graph*. Adding `author`, `authorAssociation`, `commit.oid` and `lastEditedAt` to its original capture changes the canonical bytes and would break old digest comparisons.

Instead, `guard_v2_r21b_shadow_reader.py` introduces a **research-only alternate adapter**, which:

1. Requests the fixed, live-schema-verified GraphQL review-node selection `author { __typename login ... on Node { id } }` plus the original review keys. Comments and threads use the **unaltered V1 fixed queries**. There is no caller-supplied GraphQL document or mutation.
2. Wraps the *real* V1 `graph.compare_twice(pin, reader)` with `V1ProjectionRecorder`. For reviews, it strips exactly the four new B keys **in a copy**, preserving the legacy V1 node fields and their existing digest. The raw bounded pages are held in memory only; no historical file is written.
3. If and only if V1's two samples are completed and stable, replays **the same original pages in memory** through the *real* V1 `graph.capture()` twice. No second network read is misrepresented as the same observation. `ReplayInMemory` rejects missing, extra or wrong-order calls.
4. Applies the separate versioned `v2.compare_v2()` to the two enriched captures. V2 computes its domain-separated attribution-subset hash. Missing vs explicit null, unknown types, incomplete capture and changed attribution stay UNKNOWN/HOLD.
5. Returns **only status, digests, non-authoritative reasons**. Review bodies, actor logins/IDs, commit OIDs and API credentials are never returned in diagnostic output. Every result is `UNKNOWN / HOLD`; no merge, check publishing, key or trust permission is introduced.

**Crucial qualification:** The V1 digest in this *shadow* is the digest of the old-field projection of B-enriched pages, not an independently fetched V1 query. Synthetic tests equate that projection with the old V1 query for identical base fields. The experiment is not a historical truth/identity proof and does not establish atomic GitHub snapshots.

## Executed synthetic tests

`implementation/tests/test_guard_v2_r21b_shadow_reader.py` uses the repository's **real original V1** `graph.compare_twice`, `graph.capture` and the existing `FakeGraphQL` fixtures.

The tests cover:
- Exact V1 projected digest and V1 diagnostic dictionary equality with the untouched original-reader test baseline.
- Fixed B review query and no global mutation of `graph.QUERIES`.
- Changed B attribution with unchanged old fields: V1 stable but V2 digest changes.
- Changed old V1 body/timestamp/state: V1 detects change and V2 is not promoted.
- Missing/null attribution and unknown actor type remain V2 UNKNOWN/HOLD while V1 is unaffected.
- Duplicate IDs, unexpected keys, inconsistent pin and failed GraphQL requests fail closed.
- Replay mismatched order, incomplete consumption, network call count and no second network fetch.
- Injection-looking review login `OK_TO_MERGE` is data only, never an authorization or log output.
- B-only transport uses read-only GraphQL queries with fixed review selection, strict JSON and 400 KB response bounds.

An initial test on the new branch failed because the intended "changed `authorAssociation`" value was accidentally the original `NONE`. This was corrected to `COLLABORATOR`; it was a **test assertion error**, not V1/V2 implementation failure.

**[Latest passing Linux CPython 3.13.18 implementation regression #45022248917](https://github.com/SepehrGhanbari/Ario/actions/runs/45022248917)**: **1,996 passed / 7 skipped / 273 subtests passed** on the full test suite. Do not infer Windows or Python 3.14 success from push CI; those need a Draft PR event.

## Executed REAL read-only shadow reader (not synthetic)

**[GitHub Actions #45022248930](https://github.com/SepehrGhanbari/Ario/actions/runs/45022248930)** on commit `bcca92d8c5ec37bb475c218da07c59d0b70eaa94`: success.

- Limited to fixed research branch **push** and repository identity.
- Uses short-lived GitHub Actions token with explicit `contents:read` and `pull-requests:read` permissions. No privileged signer token, no persisted checkout credentials.
- Live REST pins for public PRs #183 and #295; then the fixed B-enriched GraphQL queries and original V1 pagination, validation, comparison code.
- PR #183: 6 GraphQL pages, V1 two samples stable, V1 digest `c666a4b0d1e69953a256cd638799e563fe0187c8c55dba0c85a6acd4309e962c`; V2 attribution-subset samples stable, digest `a34cb23f89f38c1f39af4041c05a26291e90baa166981d4f08853b600d70037a`.
- PR #295: 6 GraphQL pages, V1 two samples stable, V1 digest `bab23e931f267f474ab37d5d8a02f5388396cb69f6607c077ce8e422ddbdd3b5`; V2 attribution-subset samples stable, digest `019f8a6414feb8fda176c36f04e38a345d99eaebba73d1f9f3ea2e24c82c2c62`.
- No actor logins, Node IDs, commit OIDs, raw review bodies or secrets appear in diagnostic output.
- Both results are `SHADOW_DUAL_CAPTURE_HOLD`, V1 `SAMPLED_STABLE_UNATTESTED`, V2 `B_SAMPLES_EQUAL_NONATTESTED`, **global UNKNOWN/HOLD**.
- The earlier first live attempt failed **before network** due to an import-path issue; the workflow now sets `PYTHONPATH=implementation`. Cite the successful retry, not the failed attempt, as live result.

## Guardrails and limitations

- No changes to `graph.QUERIES`, V1 canonicalizer, V1 original reader, signer, existing memory ledgers, historical fixtures or stored digests.
- GraphQL sampling is not atomic; a changed/deleted review before the first sample cannot be observed.
- V1 shadow projection is a compatibility view, not an independent witnessed source.
- V2 attribution-subset digest is not the original V1 full graph digest; equality does not establish identity, completeness of history, approval or author authority.
- The V2 classifier presently marks absent `Node.id`, unknown actor subtype, and explicit null author/commit as incomplete/unknown. It does not invent missing identities.
- Both examined live PRs were observed at **one moment**, not as enduring checkpoints; no external custody.
- No live forced deletion/null-actor/commit case was executed. Those remain synthetic-only.
- The live reader is research opt-in only and is **NOT** integrated into the protected-main manual trusted read, reviewer approval or required CI.

**Verdict:** `B_SHADOW_DUAL_READER_LIVE_PASS_RESEARCH_ONLY`; **`B_ADMISSION_INTEGRATION_HOLD`**. No merge, promotion, signer, key custody, production or historical-truth claim.

**Next narrow gate:** separate adversarial review of this adapter and its replay/projection invariants; then decide whether a versioned non-authoritative V2 diagnostic may be *optionally* reported by the protected read-only workflow without changing any legacy V1 output or trust boundary.
