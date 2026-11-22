# R21B shadow reader — independent adversarial review, RED→GREEN fixes, optional sidecar decision

**Date:** 2026-11-22  
**Mode:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_SIGNER / NO_KEYS / NO_TRUST_ACTIVATION / PRODUCTION=NO_GO  
**Pinned parent:** Draft #322 HEAD \`71500a37d6c3918f1cac863987f7b3dff8640224\`.  
**Inherited dependencies:** Draft #320 HEAD \`d65dcb095cb7ce1e60339ce9b32806f99755359c\`, Draft #295 parent \`beb971ecdad229e153e50d1516db1d8aeca61c59\`.  
**Unchanged V1 reader:** \`implementation/research/guard_v2_review_graph.py\` Git blob \`2c6cb3a8c569f6daa0b6c59bce14607454107a08\`.  
**Unchanged V2 attribution-subset contract:** \`implementation/research/guard_v2_r21b_capture_v2.py\` Git blob \`8600052b72feb1ddc1ed951e041d146e8044ce57\`.

This audit analyzes R21B's *experimental* alternate adapter, not a protected/main admission path or a historical ledger. Both components remain strictly non-authoritative.

## F1 — two independent copies of the externally returned page

**Verdict: CONFIRMED synthetic source/copy race; fixed.**

Original \`V1ProjectionRecorder.get_page()\` projected one \`copy.deepcopy(page)\` into V1 and separately stored another \`copy.deepcopy(page)\` for V2 replay. A controlled, hostile dict-like reader object that changes \`review.body\` during deepcopy makes the V1 projection and raw V2 recorded page disagree, while the original design describes them as the SAME sampled page.

**[Original RED workflow #45022791852](https://github.com/SepehrGhanbari/Ario/actions/runs/45022791852)** at \`f42464c9d55652793cb0df3530b43fb4fab48455\`: **1 failed / 1996 passed / 7 skipped**. Exact failing assertion: \`SAME_PAGE_CLAIM_VIOLATED\`.

Minimal correction: snapshot the untrusted externally provided page **ONCE**, project the legacy V1 copy from that snapshot, and record the same snapshot for V2 replay. Both views now derive from identical captured contents; no V1 canonicalizer or query is modified.

**[F1 GREEN #45022872752](https://github.com/SepehrGhanbari/Ario/actions/runs/45022872752)**, with the adversarial test now passing.

**Limit:** this does not establish an atomic GitHub multi-page API snapshot or make arbitrary concurrent Python deepcopy operations atomic. The production GitHub transport parses bounded JSON into ordinary built-in containers; malicious custom \`__deepcopy__\` is a synthetic falsification of the adapter's previous same-source claim, not an observed live GitHub exploit.

## F2 — post-GraphQL REST revision drift

**Verdict: CONFIRMED synthetic live-observation contract error; fixed.**

The original live shadow script reads REST PR identity/head/base **before** GraphQL but not afterwards. Under a synthetic changed-head REST responder, GraphQL samples both report V1/V2 stable and the old script returned **exit 0** with \`TWO_COMPLETE_NONATTESTED\`, even though the PR HEAD changed immediately after the graph observation.

**[Original RED workflow #45022921400](https://github.com/SepehrGhanbari/Ario/actions/runs/45022921400)** at \`bea7d8e09fd7b110bda6e7ee285b52ab673d2425\`: **1 failed / 1997 passed / 7 skipped**. Exact failing assertion: \`STALE_HEAD_PRESENTED_AS_COMPLETE_AFTER_CHANGE\`.

Minimal correction: after shadow comparison, re-read the same immutable-target REST repository + PR identity/head/base and require exact equality with the initial pin. Output a precise \`final_rest_scope_check\`:

- \`STABLE_NONATOMIC\`: same observed identity/head/base; **not atomicity proof**.
- \`CHANGED_HOLD\`: changed identity/head/base; no complete observation.
- If the final REST request is unavailable (\`ReadUnknown\` included), the result remains \`READ_OR_REVISION_UNAVAILABLE\` / \`INCOMPLETE_OR_CHANGED_HOLD\` with exit 2.

**[F2 GREEN #45023019216](https://github.com/SepehrGhanbari/Ario/actions/runs/45023019216)**. Further tests check stable bracketing and final HTTP 503 loss without printing an access token.

**Limit:** a successful final REST read does not establish an atomic consistent snapshot, independent custody, historical truth or full review lifetime.

## Adversarial test matrix

Additional offline tests in \`test_guard_v2_r21b_shadow_adversarial_matrix.py\` cover:

- Changed author attribution **only on review page 2** (101 review records): V1 legacy digest stable, V2 digest changed; same 8 bounded network page reads.
- Old V1 digest equivalence with the same old fields extracted from 101 B-enriched review records.
- Repeated cursor (201 reviews), changed \`totalCount\`, and \`MAX_ITEMS+1\` overflow: V1 rejects, V2 is not promoted.
- GraphQL head swap between samples: V1 fail-closed, V2 suppressed.
- Unexpected review-node keys, page-budget rejection before any network request, and structured GraphQL cursor injection as a **variable**, never an interpolated query.
- No raw review body, author login, node ID or token in the result.
- Pinned workflow action digests, explicit read-only \`contents:read\`/\`pull-requests:read\`, no \`pull_request_target\`, no workflow dispatch or persisted checkout credentials.
- No inference that actual GitHub permissions exceed the workflow's stated limits.

**[Full Linux CPython 3.13 test suite #45023142884](https://github.com/SepehrGhanbari/Ario/actions/runs/45023142884): 2013 passed / 7 skipped / 273 subtests passed**; later commits only extend the research live-branch allowlist and add an explicitly read-only adversarial test workflow.

## Actual live read-only re-test after F1 and F2 fixes

**[GitHub Actions #45023258467](https://github.com/SepehrGhanbari/Ario/actions/runs/45023258467)** on \`acbc0ed5ea91ce0372f5fd876a235b41a8a270de\`: **SUCCESS**, with only ephemeral GitHub Actions token and fixed read-only GraphQL queries.

- Public PR #183: 6 bounded GraphQL pages; V1 samples stable and V2 subset samples stable; \`final_rest_scope_check=STABLE_NONATOMIC\`.
- Public PR #295: 6 bounded GraphQL pages; V1 samples stable and V2 subset samples stable; \`final_rest_scope_check=STABLE_NONATOMIC\`.
- All outputs remain \`UNKNOWN/HOLD\`, \`merge_authorized=false\`, \`trust_activated=false\`, custody/attestation/history \`NOT_ESTABLISHED\`.
- PR #295's observation digests differ from an earlier run; **cross-run digest equality was never claimed**. The repository's public review/comment data can change over time.
- No real withheld/null/ghost author or deliberately concurrent live edit tested; those are synthetic-only.

## Optional sidecar proposal — DECISION REQUEST ONLY; DEFAULT OFF

**Recommendation:** Consider **only** a completely separate opt-in, research-only, non-authoritative V2 diagnostic *sidecar*, once this PR receives independent review. Do **NOT** modify, replace, wrap, re-hash or reinterpret the existing V1 JSON report. Do not add a required check, pass badge, merge status, signer, trust activation or source-admission rule.

Suggested immutable output contract:

- \`schema="ARIO-R21B-OPTIONAL-V2-DIAGNOSTIC-SIDECAR-0.1"\` and explicit \`enabled_by_owner=false\` as the default.
- A **read-only reference** to a specific V1 observation artifact and source commit, plus its existing digest as observed. Never construct or rewrite historical V1 digest vectors.
- New versioned V2 attribution-subset \`schema\`, \`algorithm\` and \`digest\` in a DISTINCT field, never reuse the V1 digest key.
- Include \`final_rest_scope_check\` with \`STABLE_NONATOMIC\` or explicit HOLD; disclose that two equal samples are non-atomic and do not prove provenance.
- \`disposition=HOLD\`, \`merge_authorized=false\`, \`check_publish_authorized=false\`, \`trust_activated=false\`, \`independent_custody=NOT_ESTABLISHED\`, \`execution_attestation=NOT_ESTABLISHED\`, \`historical_truth=NOT_ESTABLISHED\`.
- Never include review bodies, author usernames, Node IDs, commit OIDs, credentials or an authorization-looking free-text reason.
- If V2 fails, preserve the original V1 bytes and status completely; sidecar reports \`UNKNOWN\`/unavailable. No silent fallback to a fabricated actor.
- No persistence to an existing historical ledger, no additional secret scopes or network mutations. Separate artifact path and retention policy require owner review.

**Do not activate the sidecar in protected workflow during this audit.** No code in this PR emits a new protected-read V2 report. A future owner-approved, default-off, versioned sidecar prototype must first demonstrate 100% byte-for-byte V1 output preservation, deterministic synthetic vectors, negative/error isolation, no reviewer PII leakage, exact-head Linux/Windows CI and a final independent security review.

## Research verdict

- \`F1_SINGLE_SNAPSHOT_FIXED_REPRODUCED_RED_GREEN\`
- \`F2_FINAL_REST_BRACKET_FIXED_REPRODUCED_RED_GREEN\`
- \`B_SHADOW_ADVERSARIAL_TESTS_GREEN_LINUX\`
- \`B_LIVE_RECHECK_PASS_NONATOMIC_NONATTESTED\`
- **\`B_OPTIONAL_SIDECAR_DESIGN_HOLD\` / \`NO_MERGE\`**

This is not permission to merge PR #322 or any parent, activate trust or handle real signer keys.
