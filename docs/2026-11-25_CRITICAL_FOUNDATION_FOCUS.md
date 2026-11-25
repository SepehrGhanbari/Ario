# Ario Critical Foundation Focus — 2026-11-25 to 2026-12-09

**Decision status:** OWNER-DIRECTED PROJECT PRIORITY  
**Window:** 2026-11-25 through 2026-12-09 (inclusive)  
**Scope:** Three existing foundational workstreams only  
**Project posture:** RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE

## 1. Decision

For this two-week period, Ario work is restricted to the following three foundational workstreams:

1. **Signature and authority independence** — independent custody, authorization boundaries, veto enforcement, replay/crash recovery, external recovery, and rollback resistance.
2. **Memory and epistemic safeguards** — prevent unverified input or self-selected labels from becoming evidentiary support; preserve provenance, versioning, UNKNOWN, and append-only revision semantics.
3. **Governance enforcement and merge protection** — test whether repository controls, CI, review pins, branch protections, and merge paths actually enforce the documented governance constraints and cannot be bypassed through alternate paths.

Work on unrelated features, demos, website changes, outreach, publications, cosmetic improvements, and new standalone research directions is paused during this window. Documentation, tests, integration, and archival work are in scope only when they directly support one of these three workstreams or preserve the ability to resume them.

This is a temporary prioritization decision. It does not declare any of the three workstreams complete, authorize their completion by a deadline, or lower the evidence required for a PASS.

## 2. Reason for the decision

The founder may be unable to renew paid AI-tool subscriptions in approximately two weeks because of financial constraints. Current access to AI coding and research tools may therefore become limited or unavailable.

The project must use the remaining period to strengthen its most consequential foundations and, just as importantly, make its work independently recoverable and continuable from the repository.

The purpose is not to maximize activity while subscriptions remain available. It is to reduce dependency on any particular assistant, provider, account, or paid tool by preserving source-pinned findings, reproducible tests, negative results, decision records, and clear continuation instructions in Ario's own repository.

This rationale records a possibility and a planning constraint; it does not assert that subscriptions will certainly end on a particular date.

## 3. Execution priorities

### A. Signature and authority independence

Prioritize the unresolved questions around actual key custody and authority separation, unauthorized signing, veto enforcement, nonce/replay protection, crash-window recovery, durable receipts, external witnesses, fresh-environment recovery, and rollback by a common administrator.

Synthetic or same-administrator experiments must remain explicitly limited. They must not be described as proof of independent custody or real-world authority.

### B. Memory and epistemic safeguards

Audit ingestion, consolidation, import, snapshot/restore, replay, retrieval, revision, and downstream consumption. A record being stored, hashed, signed, or locally labeled must not by itself imply truth or evidentiary support.

Preserve the distinctions:

- MEMORY != TRUTH
- CLAIM != PROOF
- REVISION != ERASURE
- SELF-MODEL != SELF
- UNKNOWN is a valid state.

Do not silently rewrite historical records or identifiers. Any protected semantic or migration decision remains subject to its required owner approval.

### C. Governance enforcement and merge protection

Test the executable enforcement of existing governance rules, including alternate write and merge paths, exact reviewed-HEAD binding, CI evidence boundaries, unauthorized policy changes, and attempts by one actor to supply and approve their own evidence.

A green CI result or a successful merge must not be treated as proof of properties the tests did not exercise.

## 4. Operating rules

- Fix and consolidate before adding features or opening new research directions.
- Reuse existing issues, PRs, experiments, and evidence; inspect their exact current heads before relying on historical summaries.
- Preserve all positive, negative, failed, inconclusive, and UNKNOWN results.
- Bind material claims to exact source commits, test commands, artifacts, and hashes where available.
- Keep work reproducible without paid services wherever feasible.
- Keep the repository as the durable source of continuation context; do not leave essential decisions only in chat, a subscription-bound tool, or an external workspace.
- Do not create parallel PRs for the same finding when a focused update to an existing workstream is safer.
- Do not represent a plan, local test, synthetic actor, same-host process, or AI-generated review as independent external validation.

## 5. Non-negotiable safety and authority boundaries

This focus decision does not amend Ario's governance, security, identity, memory, or trust contracts. It grants no new authority.

The following remain in force:

- RESEARCH_ONLY
- NO_REAL_KEYS
- NO_TRUST_ACTIVATION
- NO_PRODUCTION
- NO_AUTOMATIC_MERGE
- NO_HISTORY_REWRITE
- No unauthorized governance or security changes
- GENESIS = NO_GO
- TRUST_ACTIVATION = NO_GO
- PRODUCTION = NO_GO

Do not access or alter protected R51 TPM state, permanent signer keys, production systems, or host security policy. Do not weaken fail-closed behavior or evidence requirements to meet the time window.

A deadline is not evidence. If a property cannot be established safely and independently, preserve it as HOLD, UNKNOWN, NOT_ESTABLISHED, or the appropriate negative result, with the exact reason and next reproducible step.

## 6. End-of-window handoff

By the end of the focus window, produce a repository-grounded handoff for each of the three workstreams:

- exact current source/PR/issue references and pinned heads;
- what was actually changed and tested;
- positive and negative results, including unresolved counterexamples;
- known trust and independence limitations;
- reproducible commands and required environment;
- the smallest next step that can be continued without relying on this conversation or a particular paid assistant.

The objective is a stronger, more recoverable foundation—not a declaration that all three hard problems have been solved.

---

# فارسی

## تصمیم تمرکز بنیادی آریو — از ۲۵ نوامبر تا ۹ دسامبر ۲۰۲۶

**وضعیت تصمیم:** اولویت‌گذاری به دستور بنیان‌گذار  
**بازه:** از ۲۵ نوامبر تا پایان ۹ دسامبر ۲۰۲۶  
**دامنه:** فقط سه محور بنیادی موجود  
**وضعیت پروژه:** پژوهشی؛ بدون کلید واقعی، فعال‌سازی اعتماد، تولید یا مرج خودکار

### ۱. تصمیم

در این بازه، فقط روی سه محور زیر کار می‌کنیم:

۱. **امضا و استقلال اختیار:** استقلال واقعی نگهداری کلید، مرزهای مجوز، حق وتو، جلوگیری از بازپخش، بازیابی پس از Crash، بازیابی بیرونی و مقاومت در برابر بازگردانی تاریخچه.

۲. **حافظه و حفاظت معرفتی:** جلوگیری از تبدیل ورودی تأییدنشده یا برچسب انتخابی نویسنده به شواهد معتبر؛ حفظ منشأ، نسخه‌بندی، وضعیت UNKNOWN و بازنگری بدون بازنویسی تاریخچه.

۳. **اجرای قوانین حاکمیتی و حفاظت از Merge:** آزمودن اینکه کنترل‌های مخزن، CI، بازبینی، اتصال به HEAD دقیق و مسیرهای Merge واقعاً قوانین موجود را اجرا می‌کنند و راه جایگزینی برای دورزدن آن‌ها وجود ندارد.

تمام فعالیت‌های نامرتبط، از جمله قابلیت‌های تازه، دمو، تغییرات سایت، ارتباطات بیرونی، انتشار مقاله، بهبودهای ظاهری و مسیرهای پژوهشی مستقل جدید، در این بازه متوقف‌اند. مستندسازی، آزمون، یکپارچه‌سازی و آرشیو فقط هنگامی مجاز به‌عنوان کار این دوره‌اند که مستقیماً به یکی از این سه محور کمک کنند یا امکان ادامهٔ آن را حفظ کنند.

این تصمیم موقت است؛ نه به معنای تکمیل قطعی سه محور تا ضرب‌الاجل و نه مجوز کاهش معیار شواهد برای اعلام موفقیت.

### ۲. علت تصمیم

بنیان‌گذار ممکن است به‌دلیل محدودیت مالی، حدود دو هفتهٔ دیگر نتواند اشتراک ابزارهای پولی هوش مصنوعی را تمدید کند. در نتیجه، دسترسی فعلی به ابزارهای کدنویسی و پژوهشی ممکن است محدود یا قطع شود.

بنابراین باید فرصت باقی‌مانده صرف تقویت بنیادی‌ترین اجزای آریو و مهم‌تر از آن، مستقل‌کردن امکان بازیابی و ادامهٔ کار از داخل خود مخزن شود.

هدف، افزایش حجم فعالیت در مدت باقی‌ماندن اشتراک نیست. هدف کاهش وابستگی به هر دستیار، شرکت، حساب یا ابزار پولی و نگهداری یافته‌های متصل به سورس، آزمون‌های بازتولیدپذیر، نتایج منفی، تصمیم‌ها و دستور ادامه در مخزن خود آریو است.

این سند یک احتمال و محدودیت برنامه‌ریزی را ثبت می‌کند؛ نه اینکه قطع اشتراک در تاریخ مشخصی را قطعی بداند.

### ۳. قواعد اجرا

- اصلاح و یکپارچه‌سازی بر افزودن قابلیت مقدم است.
- پیش از اتکا به گزارش‌های قدیمی، HEAD و وضعیت فعلی هر PR و Issue بررسی شود.
- نتایج موفق، ناموفق، منفی، نامعین و UNKNOWN حفظ شوند.
- ادعاهای مهم به SHA دقیق، دستور آزمون و شواهد قابل‌بازیابی متصل شوند.
- تا حد امکان امکان ادامه و آزمون بدون سرویس پولی فراهم شود.
- تصمیم‌ها و دانش ضروری فقط در چت یا ابزارهای اشتراکی باقی نمانند.
- یک آزمایش یا نقص واحد با چند PR موازی و تکراری پراکنده نشود.
- آزمایش مصنوعی، فرایند هم‌میزبان یا بازبینی تولیدشده توسط هوش مصنوعی، شاهد مستقل بیرونی معرفی نشود.

### ۴. مرزهای غیرقابل‌تغییر

این تصمیم هیچ قرارداد امنیتی، حاکمیتی، هویتی، حافظه‌ای یا اعتمادی را تغییر نمی‌دهد و اختیار تازه‌ای ایجاد نمی‌کند.

RESEARCH_ONLY، NO_REAL_KEYS، NO_TRUST_ACTIVATION، NO_PRODUCTION، NO_AUTOMATIC_MERGE و NO_HISTORY_REWRITE همچنان برقرارند.

به TPM محافظت‌شدهٔ R51، کلیدهای دائمی امضا، سامانه‌های تولیدی یا سیاست امنیتی میزبان دست زده نشود. برای رسیدن به ضرب‌الاجل، رفتار fail-closed یا معیارهای شواهد تضعیف نشوند.

اگر ویژگی‌ای به‌طور امن و مستقل اثبات نشد، همان HOLD، UNKNOWN یا NOT_ESTABLISHED باقی بماند و علت دقیق و قدم بعدی بازتولیدپذیر ثبت شود.

### ۵. خروجی مورد انتظار

برای هر سه محور، در پایان دوره یک گزارش ادامه‌پذیر در مخزن ثبت شود: وضعیت و SHA دقیق، تغییرات واقعی، آزمون‌های اجراشده، نتایج مثبت و منفی، محدودیت‌های استقلال، دستورهای بازتولید و کوچک‌ترین قدم بعدی.

هدف، بنیانی قوی‌تر و قابل‌بازیابی‌تر است؛ نه اعلام حل‌شدن سه مسئلهٔ دشوار بدون شواهد کافی.
