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
