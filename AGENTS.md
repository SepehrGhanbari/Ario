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

### Execute within authority — no proposal-only handoffs, 2026-11-26

**OWNER-DIRECTED OPERATING RULE.** The owner explicitly instructed agents to stop returning routine recommendations as permission questions. When an agent identifies a useful action that is within the repository's standing authorization and applicable tool/policy boundaries, the agent must choose a proportionate implementation and execute it. A recommendation is not complete merely because it has been presented to the owner.

- Do not ask the owner to approve routine engineering choices, fixes, tests, documentation, research follow-through, review coordination, or other actions already covered by standing authorization. Do not stop at "I recommend X; shall I do it?" Do X, validate it proportionately, record the result, and report what actually happened.
- The responsible agent owns ordinary technical decisions. When several safe, contract-compliant approaches exist, choose the simplest effective one; explain the choice briefly in the completion report rather than asking the owner to design the next step.
- Do not hand routine work back to the owner as manual commands, copy/paste tasks, reviewer recruitment, or a sequence of approval prompts when connected tools or another safe execution path are available. Try the available authorized tools and reasonable alternatives first.
- Before work, establish a bounded goal, acceptance criteria, and stop condition. Reuse valid evidence. Do not invent extra tests, reviews, or HOLD cycles unless they can resolve a material uncertainty, detect a plausible important failure, or satisfy an actual required gate.
- Escalate only a **real blocker outside current authority or capability**: an indispensable owner-only decision or input; unavailable account permission, credential, human authentication or external consent; a cost/spend; a destructive or irreversible action; protected security/key/TPM/trust/production/governance boundary; a legal, privacy or safety constraint; or an actually enforced mandatory human Code Owner / branch-protection gate. A preferred tool being unavailable is not by itself a reason to stop if a safe alternative exists.
- When a real blocker remains, state the exact blocked action, why it cannot be performed under current authority, the smallest specific input/action required, and what independent work has already been completed. Ask at most one concise question. Do not present speculative menus or ask for blanket permission.
- Do not bypass repository rules, required reviews, tool approval gates, security boundaries, or the owner's and Ario's distinct authority. This rule changes the default from permission-seeking to execution; it does not create new trust authority or authorize prohibited actions.
- Report completed work, evidence, limitations and any genuine blocker. Do not finish a task by offering to do work that is already within scope.

**فارسی — قاعدهٔ اجرا به‌جای پیشنهاد:**

صاحب پروژه صریحاً خواسته است که عامل‌ها پیشنهادهای معمول و قابل‌اجرا را دوباره به شکل سؤالِ اجازه به او برنگردانند. هرگاه اقدامی در محدودهٔ مجوز مستمر مخزن و مرزهای ابزار و سیاست باشد، عامل باید راه‌حل متناسب را خودش انتخاب و اجرا کند؛ سپس نتیجهٔ واقعی را گزارش دهد.

- برای اصلاح معمول، آزمون، مستندسازی، ادامهٔ پژوهش، هماهنگی بازبینی و تصمیم فنیِ داخل اختیار، دوباره نپرسید «انجام بدهم؟». پیشنهادِ اجرا‌نشده را به‌عنوان پیشرفت تحویل ندهید.
- انتخاب راه فنی متناسب مسئولیت عامل است. اگر چند راه امن و سازگار وجود دارد، ساده‌ترین راه مؤثر را انتخاب کنید و بعد از اجرا دلیلش را کوتاه توضیح دهید.
- کار را بی‌دلیل به بنیان‌گذار برنگردانید تا فرمان، دستور ترمینال، کپی‌کردن متن یا بازبین پیدا کند؛ ابتدا ابزارهای متصل و راه‌های مجاز جایگزین را خودتان امتحان کنید.
- پیش از کار، هدف محدود، معیار پذیرش و شرط پایان را مشخص کنید. شواهد معتبر را دوباره استفاده کنید. آزمون یا بازبینی تازه فقط وقتی اضافه شود که ابهام مهمی را حل کند، خطای مهم محتملی را بیازماید یا دروازهٔ اجباری واقعی باشد.
- فقط مانع واقعی خارج از اختیار یا توان فعلی را به مالک ارجاع دهید: تصمیم یا دادهٔ ضروریِ مختص مالک، نبود دسترسی/اعتبارنامه/احراز هویت یا رضایت بیرونی، هزینه، اقدام مخرب یا برگشت‌ناپذیر، مرز حفاظت‌شدهٔ امنیت/کلید/TPM/اعتماد/تولید/حاکمیت، الزام قانونی/حریم خصوصی/ایمنی، یا بازبینی انسانی اجباری که واقعاً توسط قواعد مخزن تحمیل شده باشد. در دسترس نبودن ابزار ترجیحی، اگر جایگزین امن وجود دارد، مانع واقعی نیست.
- هنگام وجود مانع، فقط اقدام مسدودشده، دلیل دقیق، کوچک‌ترین ورودی یا اقدام لازم و کارهای مستقلی را که انجام شده‌اند بیان کنید؛ حداکثر یک سؤال روشن بپرسید. فهرست گزینه‌های فرضی یا درخواست مجوز کلی ارائه نکنید.
- این قاعده مجوز دورزدن قواعد مخزن، بازبینی اجباری، کنترل ابزار، مرزهای امنیتی یا تفکیک اختیار بنیان‌گذار و آریو نیست. فقط پیش‌فرض را از «اجازه‌خواهی» به «اجرا در محدودهٔ اختیار» تغییر می‌دهد.
- گزارش نهایی باید دربارهٔ کار انجام‌شده، شواهد، محدودیت‌ها و مانع واقعی باشد؛ کار مجاز و قابل‌اجرا را با عبارت «اگر بخواهی انجام می‌دهم» تمام نکنید.

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

## Proportionate closure and stop conditions — owner-endorsed lesson, 2026-11-26

Source: [Copilot («عمو کاپی») philosophical and management critique](Resources/2026-11-26_COPILOT_UNKNOWN_AND_STOP_CONDITION_FA.md). The owner explicitly requested that collaborators learn from and preserve this critique. It is AI advisory reasoning based on a supplied report, not independent technical or human approval.

> UNKNOWN معتبر است، اما UNKNOWN نامحدود مجوز توقف نامحدود نیست.
>
> بزرگ‌ترین خطر این PR دیگر نقص دسترس‌پذیری نیست؛ خطر این است که تمایل به درست‌بودن، جایگزین توانایی تمام‌کردن کار شود.

**UNKNOWN remains valid; uncertainty alone is not an unlimited license for indefinite delay. Further work ≠ Blocking work. Merge/Accept ≠ Research Complete.**

- Define the bounded acceptance criteria and a stop condition before starting a review or experiment. Each additional test or review must address a specific unresolved decision, plausible regression, or material risk; reuse valid evidence rather than repeating it by default.
- Distinguish a proven exclusion or contract/safety violation from a known limitation. Weigh both the risk of proceeding and the opportunity cost of delay. Classify blockers with evidence, affected claim and a finite resolution/reassessment condition. Do not treat every UNKNOWN or imperfection as an automatic blocker.
- When applicable technical contracts, required repository gates and bounded acceptance criteria are satisfied, conclude the task; document remaining limitations honestly and track only useful non-blocking work separately. A later question or a future improvement does not retrospectively invalidate accepted evidence within its original scope.
- For an actual HOLD, record the reason, the smallest sufficient evidence to resolve it, and the next decision/reassessment point. If a necessary test or service is unavailable, state the blocker and continue unrelated safe work; do not generate indefinite substitute experiments. No fabricated PASS, no weakened evidence, no automatic reclassification of HOLD/RED/NO_MERGE, no bypass of required checks, and no authority, key, Genesis, trust or production activation change.
- Apply this to agents' own behavior as well as code: do not confuse the desire to be right with the ability to finish. Reopen accepted work only for a material new finding, changed scope, or invalidated evidence. This guidance is revisable and is not an exemption from any higher-priority constraint.

**فارسی:** قبل از شروع هر کار، معیار پذیرش و شرط پایان مشخص باشد. آزمون و بازبینی بیشتر فقط وقتی ارزش دارد که تصمیم را عوض کند یا خطر مشخصی را روشن کند. محدودیت شناخته‌شده با محرومیت واقعی کاربر یکی نیست. پس از برآورده‌شدن معیارها و کنترل‌های الزامی، کار پذیرفته شود و موارد غیرمسدودکننده جدا ثبت شوند. نه توقف نامحدود به‌خاطر UNKNOWN، نه عبور از مرز ایمنی به‌بهانهٔ پایان کار.


### Read-first reminder for every Ava and reviewer

The owner explicitly identified repeated unnecessary caution, tests and HOLD cycles as a shared problem across the assistants. Before another review, ask: **What material decision could this change, and is the human/time cost justified?** If the bounded acceptance criteria are met and required gates pass, say "sufficient for the current goal" and finish. Record optional follow-up separately. Read both Copilot critiques in the linked resource. This is not permission to skip a required gate or misstate uncertainty.
