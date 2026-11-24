# Ario R21B — read-only live GraphQL evidence and isolated V2 attribution contract

**Date:** 2026-11-22  
**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_TRUST_ACTIVATION / NO_KEYS / PRODUCTION=NO_GO  
**Parent:** Guard V2 PR #295 at exact SHA `beb971ecdad229e153e50d1516db1d8aeca61c59`.  
**Patch A:** PR #318 remains independent and unchanged by this branch.

## Purpose and scope

Verify the **exact proposed Patch B query selection** on live GitHub GraphQL using a short-lived **GitHub Actions GITHUB_TOKEN** with read-only `contents: read` and `pull-requests: read` permissions. Then define a separate, versioned V2 attribution **subset** commitment. Do not grant authority or rewrite historical ledger/digests.

The live query selects `author { __typename login ... on Node { id } }`, `authorAssociation`, `commit { oid }`, `lastEditedAt`, and the original review fields. The **direct** `Actor.id` query is not what the original B patch proposed. The Node fragment is schema-compatible.

## Live evidence — actual GitHub Actions / GraphQL

**[Read-only successful probe run #45020637294](https://github.com/SepehrGhanbari/Ario/actions/runs/45020637294)**, Python 3.13 hosted runner, request schema `ARIO-R21B-LIVE-GRAPHQL-PROBE-0.1`, status `SCHEMA_AND_QUERY_VERIFIED_NON_AUTHORITATIVE`.

- Exact review query SHA-256: `1437876edb7fb39d4388c0f25eafbb38fc42c042171a0ddb42ead970ae3d8f6b`
- Live GraphQL: `PullRequestReview.author: Actor` (nullable).
- `PullRequestReview.authorAssociation: CommentAuthorAssociation!` (non-null).
- `PullRequestReview.commit: Commit` (nullable).
- `PullRequestReview.lastEditedAt: DateTime` (nullable).
- `PullRequestReview.updatedAt: DateTime!` (non-null).
- `Actor` has no directly selectable `id` field. `Node` has `id`.
- Actor possible types returned: Bot, EnterpriseUserAccount, Mannequin, Organization, User.
- PR #295 query was syntactically valid, but currently returned **zero** review nodes (no live null-actor conclusion from this PR).
- Additional **read-only** PR #183 query returned one public Bot-authored review node; its author and commit were present and the Node fragment included `id`. No login, author node ID, commit OID or review body was written to job logs.
- Both queries are queries (GraphQL POST transport), not mutations. No keys or secrets were transmitted beyond the ephemeral Actions token via GitHub API transport.
- The first attempts returned a GraphQL introspection-limit error and then a local parsing error. The final run corrects both. Do not cite failed attempts as successful observations.
- These are platform-reported observations only, NOT independently attested execution, trusted identity or historical truth.

## Versioned contract / no historical rewrite

New `implementation/research/guard_v2_r21b_capture_v2.py` is **not integrated with the legacy Guard V2 reader or validator**. V2 schema: `ARIO-GUARD-V2-R21B-ATTRIBUTION-SUBSET-LAB-v2`. Digest algorithm: `SHA256_DOMAIN_SEPARATED_CANONICAL_JSON_V2`; domain prefix `ARIO-GUARD-V2-R21B-ATTRIBUTION-SUBSET-v2\0`.

- The V2 hash is *only* an attribution-subset commitment, NOT a replacement for the original full review-graph digest.
- It binds the fixed PR identity pin, ordered review IDs, pre-existing review content hashes/timestamps, and normalized proposed B fields.
- Distinguishes field **ABSENT**, **EXPLICIT_NULL**, and **OBSERVED_VALUE**; Node fragment `id` absent is representable without guessing an identity.
- Unknown actor types, null author/commit, missing fields, malformed responses and duplicate review IDs remain `UNKNOWN/HOLD` (not merge authorization).
- Equal completed samples yield only `B_SAMPLES_EQUAL_NONATTESTED` and remain HOLD; equal incomplete/null data never become a completed attribution capture.
- Attribution changes change the V2 hash. Historical fixtures, ledgers and previous digests are **not updated or reinterpreted**.

## Automated tests

**[Linux exact-branch implementation regression #45020637283](https://github.com/SepehrGhanbari/Ario/actions/runs/45020637283)** PASS: **1960 passed, 7 skipped, 273 subtests passed** on hosted CPython 3.13.18.

- Existing synthetic B lab: 35 new tests vs initial 1879-test parent.
- New capture V2 contract: 46 further tests, including null-vs-missing, unknown actors, duplicate IDs, pin mismatch, deterministic domain hashing, known modifications and two-sample HOLD.
- Existing baseline and other R17/R19 tests remain unmodified.
- **[Draft PR #320 exact-code platform CI #45020767846](https://github.com/SepehrGhanbari/Ario/actions/runs/45020767846)**: ALL 3/3 jobs SUCCESS. Linux Python **3.13.18: 1960 passed, 7 skipped**, Linux Python **3.14.10: 1960 passed, 7 skipped**, Windows Python **3.13.17: 1940 passed, 27 skipped**. Every job reports **273 subtests passed** and 2 unrelated diagnostic warnings.
- **[Restore security #45020768319](https://github.com/SepehrGhanbari/Ario/actions/runs/45020768319)**: 10/10 jobs successful; **[advisory self-audit #45020767797](https://github.com/SepehrGhanbari/Ario/actions/runs/45020767797)** successful (not independent provenance).

## Remaining open questions

1. The live examples exercised a Bot reviewer, not real null author/commit or a deleted identity. Those remain **synthetic** only.
2. Node fragment field presence across every Actor concrete type is not established from one Bot observation; schema possible-types are not sampled completeness.
3. Last-edited and updated timestamps cannot prove revisions/deletions before the first sample.
4. Schema-v2 capture is a separate research contract, not a proven migration of historical V1 digests.
5. Existing PR-specific governance, external custody and provenance remain NOT_ESTABLISHED.
6. Integration into the actual GraphQL reader + validator requires a separate, reviewed migration plan and independent test gate; the supplied original Patch B is NOT applied.

**Verdict:** `B_SCHEMA_QUERY_VERIFIED_READ_ONLY` and `B_V2_CONTRACT_RESEARCH_GREEN_LINUX`; **`B_INTEGRATION_DESIGN_HOLD`**.

No merge, signer/Genesis, rule change, token disclosure or trust activation performed.
