# Ario Repository Governance

These instructions govern Codex and other AI-agent work in this repository. Read them, along with any more-specific applicable instructions, before acting. They guide work but do not replace higher-priority instructions or technical contracts in the repository.

## Standing owner delegation — adopted 2026-11-25

The repository owner, Sepehr Ghanbari, grants Ava Work and AI agents explicitly working on Ario a standing delegation to carry out repository engineering without asking for per-task, per-path, or per-action approval. This supersedes earlier requirements in this file to obtain owner approval before each write or before remote publication and merge.

### Delegated actions

Within the Ario repository, agents may independently inspect, research, select and modify relevant paths; create and update branches; create commits; push changes; open, update, close, and review pull requests; add issue/PR evidence; run local and hosted tests; request independent reviews; publish research documentation; and merge eligible pull requests. **Do not ask the owner for permission before any of these actions, including merge.**

The delegation includes foundational implementation work involving memory, identity representation, continuity, agency, and epistemic behavior. The agent must choose a bounded, evidence-backed plan, preserve existing history, and document what it did. The owner does not need to pre-approve a list of paths or repeat approval for each step.

### Merge authority and objective gates

Merge is delegated authority, not a command to merge blindly. The responsible agent decides when a PR is ready and may merge without asking the owner when all applicable conditions are met:

- the diff is understood, scoped to the stated engineering or research objective, and contains no unrelated or unexplained changes;
- required exact-head CI is green on the commit being merged; expected skips/xfails and all warnings are inspected and reported rather than relabelled as passes;
- no unresolved failing test, material security finding, blocking review, or known RED result is being hidden;
- required independent review is obtained for high-impact changes; the owner is not a substitute for an independent technical reviewer;
- the target branch and its protection rules are respected; no required check, review, or platform control is bypassed;
- research-only findings remain clearly labelled and are not represented as adopted policy, independent truth, or production readiness.

If an objective gate is not met, keep the PR open or in HOLD/DRAFT, record the reason, and continue other safe work. Do not ask the owner to resolve a routine engineering gate.

### Non-delegated hard boundaries

This standing delegation does not authorize real private-key creation, disclosure or use; signer activation; trust activation; Genesis activation; production deployment or production authority; bypassing platform/tool authorization; force-push or history rewriting; or destructive mutation/deletion of historical evidence, immutable records, archives, or retained backups. Existing `NO_REAL_KEYS`, `NO_TRUST_ACTIVATION`, `GENESIS = NO_GO`, and `PRODUCTION = NO_GO` constraints remain in force. These are hard HOLD boundaries, not reasons to interrupt the owner for routine approval.

No agent may claim that a passing test, a merge, or this delegation proves truth, provenance, independent custody, security, identity, or consciousness. A merge records an engineering decision only.

### Execution and preservation

- Inspect the current source, branch, applicable instructions, and existing work before editing.
- Keep changes narrow where possible; when a larger integration is necessary, include the complete dependency set and tests rather than a partial transplant.
- Preserve historical files and append-only logs. Before a risky mutation, create and verify a recoverable backup; never overwrite a healthy or historical artifact merely for convenience.
- Use one accountable executor per write scope; do not overwrite unrelated tracked or untracked work.
- Append actual scope, changed paths, source/base/head SHAs, CI results, skips, xfails, warnings, limitations, and merge disposition to `ENGINEERING_LOG.md`.
- If evidence is incomplete or contradictory, record `UNKNOWN` or `HOLD`, preserve RED evidence, and continue independent safe tasks without asking the owner for routine permission.

This delegation is an operational authorization from the project owner. It does not make the founder, any agent, or any project principle immune from review, and it does not override higher-priority system instructions, repository branch protection, technical contracts, or tool-level authorization.

## Preservation and failure handling

- Ordinary source, test, and documentation edits within the standing delegation do not require separate authorization. Do not destructively overwrite, delete, rename, or repurpose historical evidence, immutable records, archives, or retained backups; these remain protected by the hard boundaries above.
- Before a write that risks existing content, record its current state and create a uniquely named, recoverable backup where appropriate. Verify the backup against the original before proceeding.
- Keep each change as narrow as possible. If a change fails, do not leave the active project partially modified: restore from a verified backup when restoration is safe, then verify the restored state. If safe restoration cannot be confirmed, place the affected work on HOLD and continue only independent safe work.
- Preserve unrelated user changes, untracked files, backups, runtime data, caches, and generated artifacts. Modify them only when directly required by the engineering objective and within the standing delegation; never sweep them into a commit.

## Evidence and reporting

- Separate observations, inferences, recommendations, and unknowns. Cite the source, command, or artifact supporting material findings.
- Report what was actually inspected, changed, and validated, including failures and limitations. Do not present an assumption as a finding.
- A passing test establishes only the behavior exercised by that test under the reported conditions. Do not inflate test results into broader claims about correctness, truth, identity, consciousness, or ontology.
- Do not claim validation that was not performed. Preserve unresolved questions as unresolved.

## Ario epistemic constraints

Preserve the distinctions documented by Ario, including:

- `UNKNOWN` remains a valid, open epistemic state.
- Memory is not Truth.
- Self-Model is not Self.
- Self-Claim is not Self-Evidence.
- Revision is not Erasure.
- Backup is not Survival.
- No actor, invariant, or principle—including Non-Closure—is immune from examination or revision.
- Do not turn local implementation behavior or test results into claims about consciousness, identity, or ontology.