# Guard V2 × Ario Self-Audit: read-only predecision probe

RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_CHECK_PUBLISH / NO_RULESET_CHANGE / NO_SIGNER / NO_TRUST.

## What is connected

The new research/guard_v2_live_link.py connects two non-authoritative research implementations:

- ario_repo_self_audit.observe() (#295): live GitHub PR/check/PR-linked Actions metadata through a narrow GET-only API. Its top-level output remains UNKNOWN, merge_authorized=false, execution_attestation=NOT_ESTABLISHED.
- research.guard_v2_pr_scope.assess() (#306): offline verification of caller-supplied synthetic PR/check/review records bound to a pinned repository ID, PR numeric database ID and number, HEAD, BASE and review digest. A coherent record yields only REVIEWABLE_ONLY; never merge or Check-write authority.

The bridge reads the GitHub PR before self-observation and again after it, comparing exact PR ID, number, numeric base repository ID, HEAD, BASE, body digest, state/draft and updated_at. Differences cause HOLD. It has no merge endpoint, no Check POST, no signer and no Ario memory mutation.

The existing advisory-only workflow on #295 executes live observations under a read-only GitHub Actions token and real PR context from the event. It supplies no authenticated reviews, issue comments or thread snapshots. Therefore live mode returns HOLD, even when linked PR CI is successfully reported. A green advisory job is neither a security status nor governance permission.

## Adversarial negative scenarios

Synthetic tests mutate the HEAD, BASE, database ID, PR body and updated_at between self-observation and a hypothetical decision; all return HOLD. A separately supplied comment changes between review captures and also returns HOLD. For historical R1i, a real App Check for PR #14 at a shared SHA had been accepted natively on sandbox PRs #15/#16; #306 correctly rejects the PR mismatch.

**Important retained UNKNOWN:** two equally forged supplied review captures can still give REVIEWABLE_ONLY. This is marked review_freshness=NOT_ATTESTED_BY_LIVE_GITHUB_READ; it is not a claim that the GitHub reviews were actually verified.

## Boundary and next falsifiers

1. Only PR metadata is reread live. updated_at may change with discussion activity but does not guarantee that edited/deleted reviews or threads were captured. Read the full review/issue-comment/inline-thread graph from authenticated source, with pagination and failure handling, before any enforcement.
2. The App 5747504 belongs to the historical disposable R1i lab, not the official Ario repository. Its external_id is publisher-controlled metadata; neither independent credential custody nor source authenticity is established.
3. These reads are not atomic with a future merge. A change after the last GET remains possible; no broker or CAS merge has been installed.
4. A future trusted PR-specific broker must retain exact repo/PR/HEAD/BASE + full evidence, independently verify provider and job logs, protect publisher authority and durable receipts, reject ambiguous POST outcomes, and repeat a fresh observation immediately before founder-authorized action. Test shared-SHA PR reuse, comment deletion, pending/skipped CI, base drift, concurrent merges and crashes in a disposable repository first.

**Outcome: diagnostic only.** Existing #295 and #306 histories, RED/GREEN evidence and prior original blobs are preserved; no auto-merge, trust, ruleset, key, or production activation.

## Reviewer follow-up — exact-check reachability and checkout token hardening (2026-11-21)

The original combined test called a PR15 identity on a FakeReader hard-coded to PR14 and allowed any earlier HOLD reason. Therefore its integration coverage did **not** prove the check matched at all. The new RED commit intentionally pinned the expected precise error `GUARD_CHECK_PR_ID_MISMATCH` for **two** destination PRs (15 and 16). GitHub Actions RED run 44944120546 confirmed both tests failed on `unexpected URL /pulls/15` and `unexpected URL /pulls/16` while 55 other tests passed. This was a test fixture limitation, not evidence of an active bypass.

In the GREEN fixture the PR target number and numeric PR database ID are consistent in the PR GET route, every returned PR identity, the linked pull_request workflow-run association, the caller pin, and the supplied review snapshots. A spy asserts that `guard.assess` is actually reached. Both PR15 and PR16 must reach and return exact `GUARD_CHECK_PR_ID_MISMATCH` for the old PR14 App Check, with four PR GET samples. Two additional legitimate synthetic PR15/16 App-check fixtures preserve `REVIEWABLE_ONLY` and all authority flags false. Original RED commit and run are preserved.

The advisory checkout now explicitly has `persist-credentials: false`. This prevents the checkout action from saving GitHub credentials into the repository's Git configuration; it does **not** hide the read-only `github.token` passed in the environment to PR-controlled Python. Complete isolation requires executing the GitHub reader from a trusted, source-pinned evaluator, outside the untrusted PR checkout. No credential permissions were expanded, and the workflow remains advisory/non-required.

Review/comment/thread freshness remains **UNKNOWN**: a PR metadata `updated_at` comparison alone does not authenticate edits and deletions. A successful synthetic test is not independent evidence custody or merge-time atomicity.

## 2026-11-21 — Review-graph freshness WIP: GraphQL two-pass observational falsifier

**Research-only, no enforcement.** This extension specifically addresses the missing live
review/issue-comment/inline-thread *data path*. GitHub GraphQL exposes PR
\`comments\`, \`reviews\` and \`reviewThreads { isResolved, comments }\`. The new
\`guard_v2_review_graph.py\` implements exactly three fixed GraphQL query
templates; HTTPS POST transports a **query**, not a mutation. Explicit query
templates, TLS verification, disabled HTTP redirect/proxies, bearer read token,
bounded response sizes and strict JSON protect the reader's request shape.
**It must not be run with a privileged GitHub App issuer or merge credential.**

For each collection the collector:
- Binds GitHub repository and PR \`fullDatabaseId\` (64-bit safe), PR number,
  exact HEAD and BASE on **every page**; validates cursor progress, totalCount,
  item identities, and complete pages.
- Reads issue conversation comments with body/timestamps, submitted reviews
  with state/body/timestamps, inline review threads with resolution/outdated
  state and reply bodies/timestamps. **More than 100 replies in one thread
  currently yields HOLD/INCOMPLETE_THREAD_REPLIES**, not a fabricated complete
  snapshot.
- Takes **two entire bounded passes**, hashes canonical content and returns
  \`REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES\` on an edited/deleted comment, review,
  thread, or reply—even when the PR's own \`updated_at\` is unchanged.
- Treats missing authorization, HTTP 403/timeout, GraphQL \`errors\`,
  inconsistent pagination, duplicates, cursor loops, stale HEAD/BASE and
  malformed IDs as \`HOLD\` / \`UNKNOWN\`.

\`guard_v2_live_link.examine\` accepts an **optional injected review_graph_reader**
to test this in an integrated synthetic environment. A changed graph causes
\`GRAPH_FRESHNESS_REVIEW_GRAPH_CHANGED_BETWEEN_SAMPLES\` and HOLD before a
hypothetical merge. A stable graph gives only
\`review_freshness=SAMPLED_STABLE_UNATTESTED\`: **it is not a trusted admission
of the caller-supplied review digest and never turns merge_authorized on**.

**Execution boundary:** The repository's existing #295 advisory workflow runs
the new **synthetic tests only**. It does not pass its PR-checkout token to
the GraphQL collector or execute live GraphQL against actual PR discussions.
That restraint is intentional: this workflow checks out PR-controlled code.
\`persist-credentials:false\` prevents checkout's Git config storage but is
not separate trust custody. A later truly trusted source-pinned process must
operate the live reader before its data can be considered operational
attestation.

**Remaining uncertainty:** Matching repeated GraphQL responses do not prove
that a comment was absent before the first read, that the provider or token
is independently controlled, or that no edit can occur after the final read.
Parallel writes while paginating remain an inescapable race; a two-pass
digest catches changes it observes but does not make GitHub's multirequest
snapshot atomic. Full read-back and separately retained baseline/checkpoint
plus authorized merge broker are still required for enforcement.
