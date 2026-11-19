# Ario audits Ario — Origin HOLD sidecar v0.2 (context-isolated reviewer challenge)

**Status:** PROPOSED / DRAFT / RESEARCH_ONLY / NO_MERGE / NO_TRUST_ACTIVATION / NO_PRODUCTION_AUTHORITY.

**Origin:** Review by the user-relayed AI reviewer "Hallaaj" on 2026-11-17. Hallaaj read an excerpt of the PR #255 v0.1 implementation, recalculated the SHA-256 of a deliberately fabricated log, and correctly distinguished static analysis from executable testing. The reporter marked execution of the real Python program and the complete test file as `NOT_RUN`. This record **does not** retroactively call the AI review a blind human or independent security certification.

## 1. Failure mode, provenance and independent reproduction

- Original v0.1 under [Draft PR #255](https://github.com/SepehrGhanbari/Ario/pull/255), exact source commit `2cac153c3bca0a81609bddce90ff011037fc3bce`, source Git blob `0293a15b033986acc35e653e35e7b5341a7be43d`.
- Hallaaj's supplied evidence log has self-declared `run_id`, `run_attempt`, `job_id`, `head_sha`, `job_log_complete`, and a SHA-256 hash **calculated from the same fabricated log**: `0ff35668231cc9a8551c010154c00a41ebab48080cf45323fee62af4dd822734`.
- Ava independently reconstructed **the exact v0.1 source blob** (matching its Git blob SHA-1) and ran `pr_claim_audit.assess` on the supplied forged claim and forged evidence, in a disposable local copy. The result was **`MATCH`**, reason `COUNTS_MATCH_SUPPLIED_SNAPSHOT`, with no differences. Appending arbitrary extra text to the forged log and recalculating its hash still produced `MATCH`.
- **Interpretation:** this is an observed vulnerability *if* a consumer uses `MATCH` as independently verified GitHub provenance or a merge/trust credential. It is **not** a contradiction of v0.1's explicitly disclosed snapshot-correspondence-only contract. The code never fetched external GitHub state.
- The previous comment on PR #255 identifies the same risk, but had not yet independently executed the complete v0.1 script. This addendum records that execution separately, without rewriting historical claims.

## 2. Narrow v0.2 decision: fail closed on provenance, preserve correspondence

The new `implementation/pr_claim_audit_origin_v0_2.py` **imports** the existing v0.1 comparator; it does not modify or replace that version. It emits:

| Field | Meaning | Available outcomes |
| --- | --- | --- |
| `correspondence_status` | Agreement with caller-supplied, internally checked data | `MATCH`, `MISMATCH`, `UNKNOWN` |
| `origin_status` | Independent GitHub origin established? | `UNVERIFIED` **only** (no verifier yet) |
| `status` | Strict final result suitable for downstream display | `UNKNOWN` **only** until a separate trusted retrieval design is reviewed |
| `reason` | Why not promoted? | `EVIDENCE_ORIGIN_UNVERIFIED` or `SNAPSHOT_NOT_ASSESSABLE` |

A malicious `origin_verified:true`, fake signature or `origin_status:"VERIFIED_BY_GITHUB"` in the supplied JSON **cannot authorize a positive final result**. There is deliberately no caller-controlled positive-origin argument or trust override. A status of `UNKNOWN` is **not** a verified negative or refutation of the claim; it preserves uncertainty.

## 3. Tests and direct reproducibility

Run in a disposable, secret-free checkout from `implementation/`:

```
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest -v tests.test_pr_claim_audit_origin_v0_2
```

The author-side scratch execution used an exact-content copy of the pinned v0.1 source: **10 / 10 passed**. Tests include: original v0.1 `MATCH` from fabricated evidence; strict final `UNKNOWN`; modification of log and recalculated SHA-256; caller-injected false `origin_verified`; misleading matched/mismatched count; wrong run/job/attempt; altered log without rehashing; absent evidence; CLI parse failure; no-write/one-JSON CLI check. This local result does not establish independent reviewer approval, full-suite CI, or origin authenticity.

## 4. What is still missing

1. **Independent, read-only GitHub fetcher** to bind the PR's actual HEAD, run attempt, membership of the job in that attempt, raw job log and a provenance receipt created from those fetched bytes. The same caller cannot supply both the log and its trusted origin claim.
2. **Retrieval trust model:** API identity, TLS and response/caching risks, GitHub API permissions, job retries, deleted/unavailable logs, PR head changes, malicious workflow/test log output, and audit record retention must be assessed. GitHub remains an operational source, **not a guaranteed independent human or immutable external witness**.
3. A future, separately reviewed design may enable final `MATCH` or `MISMATCH` only when source verification is actually established. This experimental module **never** does so; no automatic approval/check publication/merge follows.
4. Exact-head CI and review of this stacked PR are pending. No requirement to create or use secrets is introduced here.

**Research boundary:** MEMORY != TRUTH; SELF_CLAIM != SELF_EVIDENCE; REVISION != ERASURE; UNKNOWN remains valid. No edits to M0, Rulesets, CODEOWNERS, signer, Genesis, or main.
