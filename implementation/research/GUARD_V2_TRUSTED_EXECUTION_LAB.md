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
