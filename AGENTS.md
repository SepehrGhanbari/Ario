# Ario Repository Governance

These instructions govern Codex and other AI-agent work in this repository. Read them, along with any more-specific applicable instructions, before acting. They guide work but do not replace higher-priority instructions or technical contracts in the repository.

## Authorization and scope

- Inspect the relevant repository state, files, instructions, and constraints before proposing or making a change.
- Modify only paths explicitly authorized for the current task. Do not expand the authorized scope by inference.
- Before any file write, report the exact planned paths and changes, how existing content will be preserved, and the intended validation. Wait for explicit user approval before writing.
- A single explicit user approval may authorize a clearly specified set of paths and actions. Do not require repeated approval for every individual write that falls entirely within an already approved plan. Any change outside that approved scope requires new approval.
- Treat approval as limited to the stated scope and action. Silence, a successful test, or a prior approval for a different change is not authorization.
- Do not commit or push without explicit authorization. Do not fetch, pull, switch branches, or otherwise change Git state unless explicitly authorized.

### Standing authority for routine engineering

- After explicit owner adoption of this subsection, owner-designated Ava Work may authorize Codex to perform bounded, contract-supported routine engineering without per-task owner approval. Each authorization must state exact paths, intended changes and actions, preservation/backup plan, proportionate validation, and whether a local commit is authorized. Codex must report the plan before writing and remain within it. This delegates engineering coordination only, not architectural or epistemic authority.

- Standing write scope is current and future source, tests, and ordinary technical documentation under implementation/, plus creation and append-only additions to ENGINEERING_LOG.md at the repository root. Uniquely named, verified backups may be created under C:\Users\xx4773\AppData\Local\Ario\engineering-backups\. Focused or full regression validation may create and remove only its own disposable fixtures and outputs within an exact Ava-specified scratch directory under that root, separate from retained backups. Existing historical records, backups, snapshots, runtime/cache/generated artifacts, unrelated changes, and existing untracked artifacts remain protected regardless of location; any modification outside the approved standing scope requires owner approval.

- For qualifying tasks only, Ava Work's explicit bounded authorization satisfies the existing per-write authorization requirements and may authorize validation, staging only approved task changes, and non-destructive local commits containing only those changes. This exception overrides per-task owner approval and otherwise-prohibited Git state changes only to that extent. Do not include unrelated staged changes. Verified recoverable backups and existing failure-handling requirements remain mandatory.

- Explicit owner approval remains required for foundational identity, memory, continuity, agency, or epistemic changes; core invariants or Non-Closure; new trust authorities, including cross-type lineage authorization; weakened evidence requirements or fail-closed behavior; destructive Git operations or history rewriting; mutation or deletion of historical evidence, immutable records, archives, snapshots, or backups; remote publication, push, merge, or releases; security or credentials; major dependencies or infrastructure; and governance changes, including adoption or amendment of this subsection. Do not fetch, pull, switch branches, or otherwise change Git state outside the scoped staging and local commits without owner approval. If a task mixes routine and protected actions, obtain owner approval before the protected action and continue independent authorized work where possible.

- Neither Ava Work nor Codex may expand this scope by inference or bypass higher-priority instructions, technical contracts, filesystem restrictions, or tool-level approval gates. Use one accountable executor per write scope and preserve unrelated tracked and untracked work. Append actual scope, changes, validation results, limitations, backup locations, and available commit identifiers to ENGINEERING_LOG.md; preserve prior entries. Reuse passing validation evidence unless new changes or a specific concern justify repeating it.

## Preservation and failure handling

- Do not overwrite, delete, rename, or repurpose a healthy or historical artifact without explicit authorization and a verified, recoverable backup.
- Before an authorized write that risks existing content, record its current state and create a uniquely named backup. Verify the backup against the original before proceeding.
- Keep each change as narrow as possible. If a change fails, do not leave the active project partially modified: restore from a verified backup when restoration is safe, then verify the restored state. If safe restoration cannot be confirmed, stop and report the condition without further writes.
- Do not touch unrelated user changes, untracked files, backups, runtime data, caches, or generated artifacts unless they are explicitly in scope.

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

## Owner-adopted repository PR review route (2026-11-03)

The owner explicitly approved developing a practical evidence-gated merge process rather than asking the nontechnical owner to certify implementation code. See [`docs/REVIEW_AND_MERGE_POLICY_V1.md`](docs/REVIEW_AND_MERGE_POLICY_V1.md). This is a **prospective, narrowly scoped repository-governance decision**, not retroactive authorization for earlier branches or a new trust/admission authority in Ario itself.

For `ROUTINE_LAB` code changes only, after the policy and its required GitHub checks are demonstrably **active on `main`**, a designated maintainer may integrate an explicitly bounded PR without a ceremonial owner code review if—and only if—fresh independent CodeRabbit review, verified RED/GREEN CI, absence of outstanding review blockers, exact PR SHA binding, append-only records, and the live GitHub branch rules all permit the merge. The existence of a tool result or bot text alone is not merge authorization. If checks fail or cannot be inspected: `HOLD`.

The routine authorization above is a limited exception to the requirement for a per-PR owner technical sign-off or ordinary remote merge approval. It **does not** grant unilateral authority to modify source identity/memory/agency/epistemic axioms, frozen security contracts, credentials, signer, trust, evidence admission, Genesis, production, governance, infrastructure, history or backups. These remain explicitly owner-controlled and separately reviewed. A protected change must never pass the routine gate merely by selecting a favorable label.

The initial policy installation is a separately owner-authorized one-time **governance bootstrap**, not a reusable bypass precedent. Until the new branch rules and required checks are verified live, continue following existing restrictions; do not claim the process is installed. Keep CodeRabbit `COMMENTED` reviews separate from GitHub `APPROVED` reviews, and do not assign technical competence to a nontechnical owner through a button click.

This additive section clarifies only the repository process; it neither amends Ario's proposed `REVIEWER_AUTHORIZATION_CONTRACT_V0_1` for possible future evidence review nor confers any evidence-admission authority.
