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