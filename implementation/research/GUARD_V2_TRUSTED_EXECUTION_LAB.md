# Guard V2 — two execution boundaries, protected-main manual research

**RESEARCH_ONLY / DRAFT / NO_MERGE / NO_REQUIRED_CHECK / NO_APP_KEYS / NO_TRUST / PRODUCTION=NO_GO**

## Finding, reproducible RED

At #295 HEAD \`f092407cf7762e55d665d6a10f97a8d62a8bbe65\`, the \`pull_request\` advisory job still directly injected the GitHub Actions \`github.token\` into PR-checkout Python through \`ARIO_GITHUB_READ_TOKEN\`, notwithstanding \`persist-credentials:false\`. It additionally requested \`actions:read\`, \`checks:read\`, and \`pull-requests:read\`. A new focused workflow-security test proved **2 failures** on the exact old workflow in GitHub Actions [push run 44946891381](https://github.com/SepehrGhanbari/Ario/actions/runs/44946891381), alongside 1,806 passing tests; the original commit and run must be preserved.

This is a credential-boundary issue **even though the token was read-only**. The PR source, its test harness, requirements files and dependencies are under less-trusted control.

## First correction: PR workflow is synthetic-only

At follow-up #295 commit \`85ae37321f716d161d042291359d302bb3231135\` the original advisory workflow removed both token-bearing live Python steps and narrowed job permissions to **contents:read only**. It retains \`persist-credentials:false\` and synthetic self-audit, Guard PR-scope and GraphQL review-graph tests. It does not read a live GitHub PR itself anymore. The old successful self-audit readbacks are historical observations, **not** evidence of a currently installed trusted live observer.

Static tests on this PR branch check these properties but **cannot themselves enforce branch protection**: an untrusted PR can edit its own workflow/tests. Enforcement requires source from a separately protected authority.

## Second correction staged: protected-main manual observer

Two new components are staged **only in Draft PR #295**, with no active installation:

- \`.github/workflows/ario-guard-v2-trusted-read-manual.yml\`: triggers exclusively on \`workflow_dispatch\`, restricts to \`refs/heads/main\`, checks out the exact immutable **\`github.sha\` from protected main**, uses \`persist-credentials:false\`, no PR checkout or artifact execution, no dependency installation from the PR, and scopes GitHub token to **contents:read, pull-requests:read, issues:read**. Only this main-sourced workflow supplies its read token to Python.
- \`implementation/research/guard_v2_trusted_manual.py\`: fixed repo REST PR identity and 64-bit database ID, exact HEAD, protected base, then **two full, bounded GraphQL review samples** from source pinned to the workflow's checked-out main commit. Final REST PR reread must match. It prints only digests, identifiers and HOLD reasons—never review bodies or tokens—and it has no Check POST or merge endpoint.
- \`implementation/tests/test_guard_v2_trusted_manual.py\`: synthetic positive-HOLD, edit/delete/thread resolution, 403/pagination, changed HEAD/base/PR and source-hash negatives. Test the manual-workflow source pin and absence of PR code checkout.

**CRITICAL:** \`workflow_dispatch\` is not installed in default \`main\` by creating this Draft PR. It cannot be invoked as a trusted active observer before a separately approved research merge; do not present it as live executed. The workflow and token-scope boundaries require independent line-by-line source review before any founder-approved install. Merging a research workflow is not Trust/Genesis/signer/production activation.

## Future lab falsifiers and limits

- Execute the manual workflow against a disposable PR from protected main after review, with the precise PR number and expected HEAD, and inspect the **real GraphQL schema**. A schema field/permission error must yield HOLD; synthetic fake-page tests do not prove live schema compatibility.
- Modify and delete a real sandbox comment/review/thread between samples. Record responses, digest changes and time windows. Build a separately held prior digest/floor to investigate deletion before the first read and rollback.
- A protected main workflow is isolated from **unmerged PR source**, but main and its GitHub Actions token remain under founder/repository administrative control: **independent custodian NOT ESTABLISHED**.
- Even complete two-pass GitHub observations do **not** create an atomic observation-and-merge transaction. Post-last-read edit, replay, race, provider omission and credential compromise remain. An operational PR-bound merge broker with exact issuer custody, durable observations and CAS-like action handling is **not installed**.
- No new human reviewer is a required security primitive. Automated checks are useful evidence, not a substitute for the founder's authorized governance decision.

**Final disposition must remain \`GUARD_V2_OPERATIONAL_HOLD\`** until live trusted execution and the remaining falsifiers pass.

## 2026-11-21 — Reviewer REVISE: REST exact root blocked before HTTP (RED→GREEN)

Independent review of #295 at \`a8a7c733da8d7d9dced67f7ddf0b4dfacf53351e\` found \`guard_v2_trusted_manual.observe\` requests \`https://api.github.com/repos/SepehrGhanbari/Ario\` before the first PR GET, but the shared \`GitHubReadOnly.get_json\` rejected the **exact repository root** as \`FORBIDDEN_HOST\`. Existing \`FakeRest\` erroneously accepted the root. Manual CLI returned exit 0 for any HOLD, allowing an entirely empty read to appear green.

A new **RED-only parent commit \`2d14aa04e809d4f3ba3cb77e6612273ec61ed425\`** added tests using the **actual \`GitHubReadOnly\` class** with only its \`urllib\` opener replaced by a deterministic fake HTTPS transport. Tested:
- exact repository root GET and syntactically restricted original PR/Check/Actions routes;
- complete REST→GraphQL two-pass diagnostic with a real REST parser, 3 fake HTTP GETs and 6 GraphQL fake pages;
- no-data manual CLI must exit nonzero;
- exact-root trailing slash, query string, sibling repo and unrecognized path all fail before transport.

The **GREEN** change allows **only** \`url == API\` as an extra REST GET, preserving original path/host restrictions and strict bounded JSON parsing. CLI now returns **2** whenever the graph was not completely sampled and the final live PR identity was not obtained. A fully sampled advisory still returns \`HOLD\` with all authority bits false; its exit **0 denotes read completion, NOT merge safety**. No check publication, mutation or trusted source activation.

Test evidence must be pinned to exact HEAD; the staged manual workflow still exists **only in Draft #295**, not on \`main\`, and is not live. The GraphQL client itself was not provided a privileged token. The later test against GitHub with main-sourced code and a read-scoped token remains separately required.


## 2026-11-21 — Malformed nonempty report: no false-green manual job

Even after report-printing fixes, Bash's \`test -s\` checked only file size.
The manual research step could exit **0** with a nonempty string, whitespace,
JSON array, wrong schema, duplicate authority keys, or \`merge_authorized=true\`,
with the job appearing green despite no valid diagnostic. This was reproduced
in six separate RED tests on the original full Bash step and historical
RED commit; the raw diagnostic was under repo control, not an authorization.

The correction introduces a small **offline shape validator**
\`research/guard_v2_manual_report.py\`, invoked by **python3 from the
protected-main checkout** after CLI output is saved, before displaying its
content. It parses strict bounded UTF-8 JSON as one object and rejects duplicate
keys, nonfinite/floating numeric tokens, invalid schema/status/disposition,
missing/non-boolean-false authority fields, and incorrect non-attestation
boundaries. If reader exit is zero, it additionally requires the expected PR
number, exact HEAD and source commit, two equal SHA-256 sample digests,
a complete sampled graph and final REST PR identity. This check validates
*report structure only*: it cannot attest the underlying GitHub history
or make the observation atomic.

For malformed or incomplete output, the Bash step replaces it with a
non-authorizing \`INVALID_DIAGNOSTIC_JSON\` record, prints it, adds it to
\`GITHUB_STEP_SUMMARY\`, and forces exit **2** if the reader claimed zero.
A preexisting nonzero reader exit (for example 17 or 2) is always preserved.
Empty output retains \`NO_DIAGNOSTIC_JSON\`; valid error HOLD reports preserve
their original reason in log/summary. A valid completed observation still
has \`disposition=HOLD\`, \`merge_authorized=false\` and no power to publish
Check results, issue an approval, activate trust or merge.

Test scope: the actual workflow Bash block is run under \`-e -o pipefail\`
against a mocked CLI but the **real Python validator**, without any network or
GitHub token. This is a staged Draft-only workflow; no actual protected-main
manual run has taken place. Status remains \`GUARD_V2_OPERATIONAL_HOLD\`.


## 2026-11-22 — R17 independent-review input whitelist (research-only)

Independent R17 review provided by Perplexity on source HEAD
\`bfb24113af2f0c43072c9f254983f3d1e4424ce7\` found a **format/meaning
ambiguity**, not a demonstrated merge-authority escalation. The validator
rejected malformed JSON, duplicates, float/non-finite constants and non-bool
authority flags, but admitted unrecognized top-level authority-looking keys
(\`guard_decision=PASS\`, \`merge_ready=true\`), Unicode look-alike field
names, and nested \`live_identity.merge_authorized=true\`. Python CLI \`int()\`
also admitted \`2_95\`, \` 295\` and \`+295\` instead of canonical decimal
arguments. These additions could mislead people or downstream consumers
about whether a report was *validated*, even though the actual Guard
decision remained HOLD and no Check or merge capability was granted.

**Evidence:** the exact twelve reviewer-supplied tests are preserved in
\`implementation/tests/test_guard_v2_manual_report_r17.py\`, Git blob
\`cf2dc9f174dbb6cffd84d5dd2a964a27ea9eded9\`. A test-only
append-only RED commit \`9200eb5a8fc090da749227c6ceb5d5464424ec43\`
was run in GitHub Actions
[44956804464](https://github.com/SepehrGhanbari/Ario/actions/runs/44956804464):
**9 failed / 1,853 passed / 7 skipped / 273 subtests passed**. The
R17 3 positive reader-shaped baselines were not rejected by the old code.
This preserves an actual hosted negative result before repair, independent
of the reviewer's earlier Python 3.14 sandbox report.

**Bounded correction:** apply the *verbatim supplied R17 patch* solely to
\`implementation/research/guard_v2_manual_report.py\`. Git blob changes
from \`09dd41d5f2b878a82f731068b9a9dc2d12b11ff1\` to
\`1956f99275e7da94fed234e2c418f43f4088f7c3\`. Allow only known
real-reader top-level keys, require exactly five native PR identity keys,
require ASCII-only serialized bytes (consistent with \`ensure_ascii=True\`),
and require canonical ASCII decimal arguments. Keep success semantics
\`disposition=HOLD\`, all authority flags **false**, and all attestation
claims **NOT_ESTABLISHED**.

**Deliberate non-claim:** the validator checks whether two SHA-256-looking
hex strings are equal; it does **not** recompute SHA-256 from complete
source-backed GitHub observations. Two fabricated equal digest strings can
pass. Do not describe this as canonical digest attestation. Nor does a
\`workflow_dispatch\` YAML \`github.ref == main\` check alone prove protected
source custody: selecting other run refs is possible, and actual provider/
token/branch-protection behavior remains **UNKNOWN** pending an explicitly
approved, trusted-main lab. An external consumer must check actual run
branch, workflow path and commit lineage, not the green Actions icon.

**Scope & status:** Draft #295 only, no force push, merge, Check issue,
ruleset, secret, real key, signer, trust, Genesis or production mutation.
All #306 source history remains intact. Exact-head GREEN hosted tests are
reported in the PR review handoff; this log entry is limited to the
RED-falsifier and implemented patch provenance, not a claim of live GraphQL
or atomic historical review evidence.

## 2026-11-22 — Independent R19 typed-values review (Draft #295 only)

Source basis: independent Perplexity R19 document, `R19 proposed patch.patch`,
and `R19 RED tests.py` supplied by the founder. Starting PR HEAD
`7577b7c8440d31d6934a98b1d7e0bb99292e30af` (Draft/HOLD). Its R17
validator closed the *key set* but did not constrain every allowed key's
*value*, particularly on nonzero-exit reports. An apparent authority claim
could be embedded as `review_graph_reason: {"merge_authorized": true}`,
`review_graph_reason: "APPROVED_BY_FOUNDER"`, or `error_type: ["MERGE_OK"]`.
Error-HOLD records also admitted mismatched source SHA/PR identity, malformed
digest types, and control/bidi characters in the reason. These are report-
format failures, **not evidence of authorized merges**.

A test-only commit `a5dec0890f8d4b178be848b0f9e6c492ecb0f03b`
preserves the exact 17 original R19 tests (8 negative and 9 positive,
Git blob `0c7e3476143fefa4b9e6f35363271933e527787e`). Actual
[GitHub Actions RED 44958673546](https://github.com/SepehrGhanbari/Ario/actions/runs/44958673546):
**8 failed, 1871 passed, 7 skipped, 273 subtests passed**. All eight
new adversarial counterexamples failed as expected, while the original
unmodified reader outputs stayed acceptable.

The authorized patch modifies only
`research/guard_v2_manual_report.py` plus the single erroneous R17
positive-fixture string: `review_graph_reason="STABLE"` replaced with
actual `"TWO_COMPLETE_GRAPH_SAMPLES_MATCH"`. The reviewer patch fixes:
token-only `reason`/graph metadata, typed optional digests/errors on *both*
exit paths, fixed freshness, source and live-identity binding even for
failed reads, and exclusion of `error_type` on success. Success still
means a well-formed **HOLD**, never a merge or Check authorization.
As in R19, a missing success graph-reason key remains tolerated for the
legacy workflow fixture; changing that requires a separately reviewed
contract update.

Limitations preserved: reason vocabulary remains open even when token-shaped
(`MERGE_APPROVED` is syntactically possible on a failed report); equal
digest strings are not independently recomputed; a workflow_dispatch
branch selector and workflow run color are not independently verified custody;
the protected-main manual workflow has not been deployed/exercised live.
Real GraphQL token scope, historic review truth, atomicity, independent
custody and merge authority remain **UNKNOWN / NOT_ESTABLISHED**.
No workflow, ruleset, trust, credential, signer, history deletion, merge
or production change was authorized.

