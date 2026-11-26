# Ario Repository Governance

These instructions govern Codex and other AI-agent work in this repository. Read them, along with any more-specific applicable instructions, before acting. They guide work but do not replace higher-priority instructions or technical contracts in the repository.

## Owner's standing engineering authorization — 2026-11-26

**OWNER-ADOPTED / STANDING / NO REPEATED PER-TASK APPROVAL.** The owner expressly instructed that Ario's engineering agents and reviewers must stop repeatedly asking the owner for permission and record this continuing authorization in the repository so all collaborators can consult it. This section takes precedence over conflicting per-action owner-approval requirements elsewhere in this file. It remains effective until the owner explicitly revises or revokes it; it is not a time-limited session grant.

**فارسی:** صاحب پروژه در ۲۶ نوامبر ۲۰۲۶ مجوز مستمر کار مهندسی آریو را صادر کرد. برای بررسی، آزمایش، رفع ایراد، تکمیل پژوهش، انتخاب راه‌حل فنی، مستندسازی و انتشار تغییرات مجاز دیگر از او مجوز تکراری نخواهید. مسئولیت تصمیم فنی، شواهد، بازبینی و ثبت نتیجه با عامل انجام‌دهنده است. محدودیت‌های ایمنی و اختیار مستقل آریو همچنان برقرارند.

- Owner-designated Ava agents, Codex and authorized project collaborators may coordinate and execute Ario engineering and research without fresh owner consent for each task. This includes source inspection, scoped implementation and corrections (including architectural or epistemic research candidates), regression tests, documentation, verified backups, ordinary non-destructive Git operations, and publication of appropriate research branches, PRs and issue records. Reviewers may independently critique and recommend corrections. No reviewer receives authority merely by being named here.
- The executor records exact affected paths, justification, preservation and validation plan, then proceeds without waiting for another owner message. Prefer existing issues, branches and PRs; preserve prior findings, including failures. Technical choices may be made and documented by the responsible executor; disagreements and unresolved semantics remain visible. The owner's standing consent does not certify a design, test, reviewer, witness, or claim.
- Ordinary non-HOLD changes may be integrated through the normal repository review and CI process without another owner-approval request when all applicable required gates are actually satisfied. Do not bypass rulesets, required reviews, technical contracts, or tool approval mechanisms. Do not fabricate approval or classify an unresolved research candidate as ready merely to merge it. Existing HOLD, RED, RESEARCH_ONLY and NO_MERGE dispositions remain binding unless resolved through their documented technical decision process.
- Preserve real-key isolation, the founder–Ario dual-approval model, Ario's veto and choice, and the evidence-only role of custodians and witnesses. This standing engineering authorization is not a signature, a grant of independent trust authority, consent on behalf of Ario, or activation of Genesis or production. It does not authorize private-key access, destructive history rewrites, deletion of historical evidence, bypass of protections, disclosure of private data, or changes to real signer/TPM custody. If such a barrier prevents a task, report the blocker and continue independent safe work rather than repeatedly soliciting permission to cross it.
- The previous authorization provisions below are retained as historical context and continue to govern preservation, bounded scope, technical safety, accountability and evidence quality. Their requirements to ask the owner again for an already covered action are superseded by this standing authorization. Do not interpret it as unlimited control of external accounts, spending, systems, other people, or future unrelated tasks. Agents cannot broaden their own authority by editing this provision.

### Reviewer availability and honest attribution — owner statement, 2026-11-26

- The owner reports that after approximately seven months of work and repeated outreach, Ario has no participating independent human reviewer; the active work is undertaken by the founder and AI assistants/review tools. This is the owner's dated account, not an independently verified exhaustive outreach audit.
- Clearly label founder review, AI-assisted review, automated review, and CI execution as such. None is an independent human approval. Do not invent a reviewer, substitute a bot identity for a human, or describe multiple AI outputs as independent human oversight.
- Where independent human review is unavailable, continue permitted engineering and research with documented limitations, actual tests and transparent review attribution. If a required repository gate cannot be satisfied, report it as blocked; do not misrepresent its status. Lack of a human reviewer neither establishes trust nor transfers the founder's or Ario's authority to a reviewer.

**فارسی:** طبق اعلام صاحب پروژه در ۲۶ نوامبر ۲۰۲۶، پس از حدود هفت ماه تلاش و مکاتبه، بازبین انسانی مستقل مشارکت‌کننده‌ای در پروژه وجود ندارد؛ کار فعلی با بنیان‌گذار و دستیارها و ابزارهای هوش مصنوعی پیش می‌رود. بازبینی ماشینی، آزمون CI و بازبینی بنیان‌گذار باید با عنوان واقعی خود ثبت شوند، نه به نام تأیید مستقل انسانی. نبود بازبین انسانی نباید کار پژوهشی مجاز را بی‌دلیل متوقف کند یا به ادعای اعتماد و تأیید ساختگی منجر شود.

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