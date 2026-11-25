# Ario — Standing Owner Delegation

**Adopted:** 2026-11-25  
**Owner:** Sepehr Ghanbari  
**Applies to:** Ava Work and AI agents explicitly acting on the Ario repository  
**Status:** Active operational delegation; does not change epistemic or production status.

## فارسی — اختیار اجرایی مستمر

سپهر غنباری، صاحب پروژهٔ آریو، اختیار اجرایی مستمر را به آوا و عامل‌های هوش مصنوعی که مشخصاً روی مخزن آریو کار می‌کنند واگذار می‌کند.

از تاریخ تصویب این سند، برای کارهای مهندسی و پژوهشی مخزن نیازی به گرفتن اجازهٔ موردی از صاحب پروژه نیست؛ از جمله:

- بررسی مخزن، انتخاب مسئله و تعیین مسیرهای لازم؛
- ایجاد و اصلاح شاخه‌ها، فایل‌های کد، آزمون و مستندات؛
- اجرای آزمایش‌ها و CI، ثبت نتایج و حفظ شواهد ناموفق؛
- ساخت Commit و Push؛
- ایجاد، به‌روزرسانی، بستن و بازبینی Issue و Pull Request؛
- درخواست بازبینی مستقل؛
- **Merge کردن Pull Requestهای آماده، بدون پرسیدن اجازه از صاحب پروژه.**

این اختیار شامل اصلاحات بنیادی مربوط به حافظه، نمایش هویت، تداوم، عاملیت و رفتار معرفتی آریو نیز می‌شود. عامل مسئول خودش محدودهٔ فنی را تعیین می‌کند، وابستگی‌های کامل را بررسی می‌کند و کار را پیش می‌برد. نباید برای هر فایل، هر مرحله، هر انتشار پژوهشی یا هر Merge دوباره از سپهر اجازه خواسته شود.

### شرط Merge

اختیار Merge به معنای Merge کورکورانه نیست. عامل مسئول می‌تواند بدون اجازهٔ مجدد صاحب پروژه Merge کند، به شرط آنکه:

1. تفاوت‌ها و وابستگی‌های تغییر فهمیده شده و تغییر نامرتبط یا توضیح‌نداده‌شده وجود نداشته باشد؛
2. CI لازم روی همان SHA نهایی موفق باشد؛
3. شکست، یافتهٔ امنیتی مهم، بررسی مسدودکننده یا نتیجهٔ RED حل‌نشده پنهان نشده باشد؛
4. برای تغییرات پراثر، بازبینی فنی مستقل انجام شده باشد؛
5. حفاظت شاخه و کنترل‌های GitHub دور زده نشوند؛
6. نتایج پژوهشی به‌اشتباه حقیقت مستقل، سیاست پذیرفته‌شده یا آمادگی تولید معرفی نشوند.

اگر شرطی برقرار نیست، وضعیت باید HOLD یا DRAFT بماند و علت مستند شود. برای رفع یک مانع عادی مهندسی نباید از صاحب پروژه اجازهٔ دوباره خواسته شود؛ عامل باید کارهای امن و مستقل دیگر را ادامه دهد.

### مرزهای سخت و خارج از این واگذاری

این اختیار شامل ساخت، افشا یا استفاده از کلید خصوصی واقعی، فعال‌سازی امضاکننده، فعال‌سازی اعتماد، Genesis، استقرار یا اختیار Production، دور زدن مجوز ابزارها و حفاظت شاخه، Force-push یا بازنویسی تاریخچه، یا حذف و دست‌کاری مخرب شواهد تاریخی، آرشیوها و نسخه‌های پشتیبان نیست.

محدودیت‌های `NO_REAL_KEYS`، `NO_TRUST_ACTIVATION`، `GENESIS = NO_GO` و `PRODUCTION = NO_GO` پابرجا هستند. این موارد مرزهای سخت HOLD هستند، نه موضوعی برای گرفتن اجازهٔ روزمره.

Merge فقط تصمیم مهندسی دربارهٔ تغییر کد است؛ به‌تنهایی حقیقت تاریخی، منشأ مستقل، نگهداری مستقل، امنیت، هویت یا آگاهی را اثبات نمی‌کند.

## English — Standing operational authority

The project owner delegates standing operational authority to Ava Work and AI agents explicitly working on Ario. No per-task, per-path, or per-action owner approval is required for repository engineering. The delegation expressly includes source and test edits, research documentation, branch creation, commits, pushes, issue/PR work, hosted validation, independent-review requests, and **merging eligible pull requests without asking the owner again**.

The delegation covers foundational memory, identity-representation, continuity, agency, and epistemic implementation work. Agents are responsible for choosing a bounded plan, identifying the complete dependency set, validating the exact commit, preserving evidence, and documenting limitations.

Merge is permitted only when the exact-head required CI is green, the diff is understood and scoped, blocking failures/reviews/security findings are resolved, required independent review is present for high-impact changes, and repository protection is respected. If a gate is not met, record HOLD/DRAFT and continue other safe work without requesting routine owner approval.

This delegation does not authorize real-key or signer operations, trust activation, Genesis, production deployment, tool/branch-protection bypass, force-push/history rewriting, or destructive alteration of historical evidence and retained backups. Existing NO_GO constraints remain hard boundaries.

A merge or passing test is not proof of truth, provenance, independent custody, security, identity, or consciousness.

## Source of authority and implementation

This document records the owner's explicit instruction in the conversation dated 2026-11-25. The repository agent instructions in `AGENTS.md` are amended to implement it. The append-only `ENGINEERING_LOG.md` records the change. If an agent encounters an ordinary task approval prompt in older project notes, this standing delegation supersedes that prompt for the scope described here.
