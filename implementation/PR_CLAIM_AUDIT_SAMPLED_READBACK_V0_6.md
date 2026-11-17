# Ario audits Ario — scoped readback vocabulary v0.6

**RESEARCH_ONLY / STACKED_DRAFT / READ_ONLY / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO.**

**Lineage:** [#251](https://github.com/SepehrGhanbari/Ario/issues/251), Draft [#255](https://github.com/SepehrGhanbari/Ario/pull/255) v0.1, Draft [#256](https://github.com/SepehrGhanbari/Ario/pull/256) v0.2, and Draft [#257](https://github.com/SepehrGhanbari/Ario/pull/257) v0.3–0.5. v0.6 is an **additive three-file sidecar to Draft #257**; all prior source/tests/docs remain unchanged. No write operations to GitHub from the tool, no credentials, no reviewer approval, no trust/merge authority.

## Source of the challenge and scope

External AI reviewer *Hallaaj* analyzed the limited source excerpts supplied in chat and explicitly marked direct GitHub fetch and independent Python execution **NOT_RUN**. The reviewer raised four risks: confusing pinned HEAD with current HEAD; declaring an inaccessible/partial read stable; overclaiming TLS-source verification; and final PR readbacks themselves failing or racing. Reviewer also distinguished a changing `run.conclusion` from actual evidence inconsistency: a job/log correspondence can remain historically correct even as overall workflow conclusion changes between sampled reads.

The historical v0.5 returned diagnostic `MATCH` for a stable mock run, and its final PR recheck rejected a changed HEAD or body. This sidecar improves **claim language and explicit failure states**, not independent authentication. Do not mark source authenticity or test execution as VERIFIED because this module used a Python TLS client or because its CI is green.

## v0.6 output contract

| Field | Meaning |
| --- | --- |
| `status` | Always `UNKNOWN` (no execution attestation / permission to approve) |
| `claim_correspondence` / `correspondence_status` | Diagnostic from pinned job/log, `MATCH`, `MISMATCH`, or `UNKNOWN`, never proof of tests running |
| `pinned_pr_head_sha` | HEAD from first complete PR response; **historical binding**, not necessarily current |
| `last_pr_head_sha_observed` | HEAD from **last complete PR GET**; null after failed or partial last read; no `current_head_sha` claim |
| `final_pr_readback_status` | `OK`, `CHANGED`, `FAILED`, `PARTIAL`, `NOT_REACHED`, or `UNRESOLVED` based on bounded local observations |
| `pr_read_samples` | Ordered pairs of *local* request/completion UTC timestamps and outcome; no PR text, token, or log bytes emitted |
| `state_consistency` | v0.5's `WORKFLOW_CONCLUSION_CHANGED` / `STABLE_AT_SAMPLED_READS` / failure states; only sampled, never atomic |
| `source_delivery` | `READER_RESPONSE_UNATTESTED` — intentionally avoids a misleading `GITHUB_API_TLS_ROUTE=VERIFIED` meaning |
| `transport_configuration` | `PUBLIC_READER_CONFIGURED` vs `CALLER_INJECTED_READER`, describing a **code path**, not authenticated traffic |
| `tls_route_verification` | Always `NOT_INDEPENDENTLY_VERIFIED`; no independent network trace or TLS attestation collected |
| `execution_attestation` | Always `NOT_ESTABLISHED` (independent runner/source hash proving pytest execution is out of scope) |

A changed overall workflow conclusion does **not** by itself negate job/log correspondence. If initial/final workflow conclusion is not comparable, the earlier v0.5 treats it as unresolved, never `STABLE_AT_SAMPLED_READS`. No additional independent time server or signed receipt is pretended here.

The recorder wraps the existing read-only v0.5 reader. Every request for the target PR is timestamped before and after the operation, and outcomes are classified as `OK` only when `id`, `number`, `head.sha`, and `body` are present and type-valid. The recorder retains only the SHA-256 of the body, not the body itself. If the **last** PR read raises, `final_pr_readback_status=FAILED`, no last head is supplied, diagnostic claim is `UNKNOWN`. If fields are missing, `PARTIAL` is reported instead. If the last complete PR differs from the first in PR ID, number, head or body hash, `CHANGED` is reported; the last observed head may be displayed alongside the pinned historical head, **neither described as current at the time of response**.

**Limit:** even an `OK` last response describes only the last sampled instant, not an atomic state or perpetual current head. Cache controls cannot independently demonstrate a fresh origin without additional evidence. The underlying transport disables proxy forwarding and restricts HTTPS hosts, but this code does not collect a separate TLS proof. The debug tests use injected readers that are not independent proof of GitHub delivery.

## Exact reproducible local checks

From `implementation/`, with CPython 3.13 or later, without network or access tokens:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests python -B -m unittest -q \
  test_pr_claim_audit_origin_v0_2 \
  test_pr_claim_audit_github_v0_3 \
  test_pr_claim_audit_log_boundary_v0_4 \
  test_pr_claim_audit_state_v0_5 \
  test_pr_claim_audit_readback_v0_6
```

**Author-side observation:** 77/77 passed (10 v0.2 + 26 v0.3 + 13 v0.4 + 15 v0.5 + 13 v0.6) on disposable local files. Tests cover final HEAD shift, body-only shift, failed GET, partial GET, absence of run conclusion, injected reader, mocked internal constructor and local timestamps. This does **not** establish a live standalone Python fetch or full-repository correctness. Mutation controls and GitHub exact-HEAD CI must be reported separately.

## Remaining research boundaries

1. Independent connected run of the standalone Python reader, actual GitHub log redirect handling and response code observations: **NOT_RUN** in this offline lab.
2. PR updates after final GET, proxy/caching and stale service responses, incomplete server-side provenance: **NOT_ESTABLISHED**; repeated reads are not atomic.
3. Correct execution of pytest or independent runner custody: **OUT_OF_SCOPE**, not a precondition for this bounded claim-vs-log audit. Do not add a signer, secrets, or trust gate under the guise of this research.
4. Do not interpret `MATCH` in any diagnostic field as a true GitHub attestation, test quality, or merge permission.

**Decision required before operationalization:** a reviewer independently inspect the exact code/head and confirm that labels describe only observed evidence and sampling scope. Keep Draft until then.
