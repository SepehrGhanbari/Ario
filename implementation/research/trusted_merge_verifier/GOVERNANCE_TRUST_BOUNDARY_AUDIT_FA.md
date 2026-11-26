# ممیزی مرز اعتماد در گارد ادغام — مرحلهٔ ۲ (پژوهشی)

- تاریخ: 2026-11-25
- شاخهٔ پژوهشی: `research/governance-merge-protection-20261125`
- مبنای مرحلهٔ ۱: `f0bd5672b291c5bdb5c99748477f0680e0d631b6` (والد `5ce5d4fb69a1e0fb97fd8dc4db9ea4267d377b14`)
- دامنه: `RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_HISTORY_REWRITE / NO LIVE RULESET CHANGES`

## ۱. پرسش

مرحلهٔ ۱ نشان داد که یک ارزیابِ مبتنی بر JSON عرضه‌شده توسط مدعی، حتی وقتی منطقش درست است، «موفقیت» را از خودِ مدعی می‌گیرد: مدعی می‌تواند policy، فهرست فایل‌ها، هش لاگ، هویت بازبین و شاهد CI را در همان JSON جعل کند. پرسش مرحلهٔ ۲ این است:

> اگر مدعی بتواند checker، policy، workflow و شاهد خودش را آزادانه تغییر دهد، آیا یک verifier جداگانه و pinned می‌تواند ادعای موفقیت را رد کند و صرفاً با اشیای واقعی Git تصمیم بگیرد؟

پاسخ آزمایش‌شده: **بله، در محدودهٔ یک آزمایشگاه دو‌نقشی روی همان ماشین.** verifier با policy و سورسِ پین‌شدهٔ بیرون از درخت مدعی اجرا می‌شود، diff/rename/حذف/هش بلاب/والدهای merge/بایت‌های لاگ را از اشیای Git استخراج می‌کند، و هر ادعای ناسازگار را HOLD می‌کند. این موفقیت هرگز مجوز ادغام نیست.

## ۲. نقش‌ها

| نقش | اعتماد | محل |
|---|---|---|
| candidate / evidence supplier | صفر | مخزن Git موقت؛ می‌تواند هر فایل خودش را عوض کند |
| pinned verifier | مرجعِ بررسی | کپی جداگانهٔ `trusted_merge_verifier/` بیرون از درخت مدعی |
| trust root | پین اپراتور | فایل JSON بیرون از درخت مدعی؛ هش بایت‌های verifier و policy |
| evidence claim | ورودی غیرقابل‌اعتماد | JSON عرضه‌شده؛ فقط «ادعا» است |

نکتهٔ حیاتی: verifier سورس خودش را از داخل HEAD مدعی import نمی‌کند. حتی اگر مدعی فایل `implementation/research/trusted_merge_verifier/policy.json` با `required_approvals: 0` اضافه کند، policy پین‌شدهٔ بیرونی اعمال می‌شود.

## ۳. ریشهٔ اعتماد (trust root)

فایل pin با ابزار `pin.py` و بیرون از مخزن مدعی ساخته می‌شود:

```powershell
cd implementation
python -m research.trusted_merge_verifier.pin `
  --verifier-dir C:\path\outside\candidate\verifier `
  --out C:\path\outside\candidate\trust_root.json
```

ساختار:

```json
{
  "schema": "ARIO-TRUST-ROOT-RESEARCH-0.1",
  "policy_file": "policy.json",
  "policy_sha256": "<64 hex>",
  "verifier_sha256": {"verifier.py": "<64 hex>", "...": "<64 hex>"},
  "pinned_at": "2026-11-25T00:00:00Z"
}
```

`verify_trust` مجموعهٔ دقیق فایل‌های `.py` را با pin مقایسه می‌کند: فایل اضافه، فایل حذف‌شده، symlink، تغییر یک بایت، یا تغییر policy 모두 `TRUST_BOUNDARY_INVALID` می‌دهد. مسیر trust root یا verifier داخل مخزن مدعی، `TRUST_ROOT_INSIDE_CANDIDATE` / `VERIFIER_INSIDE_CANDIDATE` می‌دهد.

## ۴. آنچه از اشیای Git استخراج می‌شود

`git_objects.py` فقط‌خواندنی است و اجرای کد مدعی، hook، replace object، external diff و textconv را خاموش می‌کند:

- `rev-list --parents` و `rev-parse <sha>^{tree}` برای هویت commit/tree و والدها؛
- `diff-tree -r -z -M --raw --no-abbrev` برای A/M/D/R/T و blobهای قبل/بعد؛
- `ls-tree -z --full-tree <commit> -- :(literal)<path>` برای blob در یک مسیر دقیق (بدون تفسیر مسیر به‌عنوان revision)؛
- `cat-file blob` برای بایت واقعی لاگ و workflow (با سقف ۸ MiB)؛
- `merge-base --is-ancestor` و `merge-base` برای رابطهٔ base و head؛
- خواندن دوبارهٔ refها قبل و بعد از استخراج برای تشخیص جابه‌جایی HEAD/base.

بنابراین «افزودن شدن، تغییر، rename، حذف و محتوای blob» از خود Git می‌آید، نه از فهرست مدعی.

## ۵. گاردها

| گارد | کد HOLD | چه چیزی را از Git/pin می‌سنجد |
|---|---|---|
| `repository_identity` | `REPOSITORY_IDENTITY_MISMATCH` | repo id/name ادعا برابر policy پین‌شده |
| `refs_match_claim` | `HEAD_REF_SHA_MISMATCH`, `BASE_REF_SHA_MISMATCH` | ref واقعی شاخه‌ها برابر claim |
| `head_tree` | `HEAD_TREE_MISMATCH` | tree واقعی HEAD برابر claim |
| `base_ancestor` | `BASE_NOT_ANCESTOR` | base جدّ head است |
| `merge_base` | `MERGE_BASE_MISMATCH` | merge-base برابر base اعلام‌شده |
| `diff_declaration` | `DIFF_DECLARATION_MISMATCH` | مجموعهٔ دقیق (status, path, old_path, old_blob, new_blob) |
| `protected_paths` | `PROTECTED_PATH_TOUCHED`, `PROTECTED_PATH_RENAMED`, `WORKFLOW_SOURCE_MODIFIED` | مسیرهای حاکمیتی و فایل workflow |
| `log_prefix` | `LOG_PREFIX_BROKEN`, `LOG_MISSING`, `LOG_NOT_APPENDED` | بایت‌های لاگ در base و head؛ prefix دقیق |
| `log_declaration` | `LOG_PATH_MISMATCH`, `LOG_DECLARATION_MISMATCH`, `LOG_APPEND_HASH_MISMATCH` | هش/طول delta ادعاشده برابر بایت‌های Git |
| `reviewer_identity` | `SELF_APPROVAL`, `REVIEW_NOT_ON_HEAD`, `DUPLICATE_REVIEWER_IDENTITY`, `AMBIGUOUS_REVIEWER_LOGIN`, `AUTHOR_LOGIN_COLLISION`, `CHANGES_REQUESTED_PRESENT`, `DUPLICATE_REVIEW_ID` | هویت عددی/لاگین و اتصال review به HEAD |
| `required_approvals` | `INSUFFICIENT_APPROVALS` | شمارش **مجموعهٔ یکتای author_id**، نه تعداد ردیف review |
| `ci_identity` | `CI_REPOSITORY_MISMATCH`, `CI_EVENT_NOT_PULL_REQUEST`, `CI_NOT_GREEN`, `CI_HEAD_MISMATCH`, `CI_BRANCH_MISMATCH`, `CI_WORKFLOW_MISMATCH`, `CI_CHECK_IDENTITY_MISMATCH` | repo/event/head/branch/workflow/app/check |
| `ci_pr_association` | `PR_ASSOCIATION_UNPROVEN` | فقط `explicit_link` با pr_id و pr_number برابر؛ در غیر این صورت HOLD |
| `workflow_binding` | `WORKFLOW_MISSING`, `WORKFLOW_SOURCE_SHA_MISMATCH` | blob واقعی workflow در HEAD برابر `workflow_source_sha` |
| `merge_method` | `MERGE_METHOD_CONFLICT`, `MERGE_METHOD_UNSUPPORTED` | روش merge ادعا و policy |
| `premerge_shape` | `PRE_MERGE_PR_NOT_OPEN`, `DRAFT_PR_NOT_MERGEABLE`, `PRE_MERGE_HAS_MERGE_METADATA` | ارزیابی پیش از merge |
| `postmerge_shape` | `POST_MERGE_STATE_INVALID`, `MERGE_COMMIT_MISSING`, `MERGE_COMMIT_NOT_TWO_PARENT`, `MERGE_BASE_PARENT_MISMATCH`, `MERGE_HEAD_PARENT_MISMATCH`, `MERGE_PARENTS_DECLARATION_MISMATCH` | ممیزی پس از merge؛ squash/rebase تک‌والد رد می‌شود |
| `bypass_actor` | `BYPASS_ACTOR_MERGE` | actor بای‌پس policy در merge پس‌از‌وقوع |
| `mode_consistency` | `MODE_CONFLICT` | حالت درخواستی برابر حالت claim |
| `refs_stable` | `HEAD_OR_BASE_MOVED`, `REF_MOVED_AFTER_VERIFICATION` | جابه‌جایی ref بین دو خواندن |

## ۶. ماتریس حمله (آزمون‌های اجراشده)

هر ردیف یک مخزن Git موقت و یک verifier پین‌شدهٔ جدا دارد.

| حملهٔ مدعی | نتیجه |
|---|---|
| افزودن policy/checker خودش با `required_approvals: 0` | `INSUFFICIENT_APPROVALS` |
| گذاشتن trust root جعلی داخل درخت | نادیده گرفته می‌شود؛ نتیجهٔ claim سالم `PASS_PROCESS` |
| بازنویسی تاریخچهٔ لاگ (نه append) | `LOG_PREFIX_BROKEN` |
| کوتاه‌کردن لاگ | `LOG_PREFIX_BROKEN` + `LOG_DECLARATION_MISMATCH` |
| حذف لاگ | `LOG_MISSING` |
| لاگ بدون تغییر | `LOG_NOT_APPENDED` |
| هش اشتباه برای delta | `LOG_APPEND_HASH_MISMATCH` |
| تغییر نام سند حاکمیتی به مسیر آزاد | `PROTECTED_PATH_RENAMED` |
| تغییر `implementation/AGENTS.md` | `PROTECTED_PATH_TOUCHED` |
| تغییر `docs/*_POLICY_*.md` | `PROTECTED_PATH_TOUCHED` |
| تغییر workflow الزامی (با به‌روزکردن ادعای blob) | `WORKFLOW_SOURCE_MODIFIED` |
| حذف workflow | `WORKFLOW_MISSING` |
| self-approval با id نویسنده و لاگین دیگر | `SELF_APPROVAL` |
| self-approval با لاگین نویسنده و id دیگر | `SELF_APPROVAL` + `AUTHOR_LOGIN_COLLISION` |
| دو تأیید با یک author_id | `DUPLICATE_REVIEWER_IDENTITY` + `INSUFFICIENT_APPROVALS` |
| تأیید روی commit قدیمی | `REVIEW_NOT_ON_HEAD` + `INSUFFICIENT_APPROVALS` |
| تأیید dismissed | `INSUFFICIENT_APPROVALS` |
| CHANGES_REQUESTED | `CHANGES_REQUESTED_PRESENT` |
| review id تکراری | `DUPLICATE_REVIEW_ID` |
| چک از event=push | `CI_EVENT_NOT_PULL_REQUEST` |
| CI قرمز | `CI_NOT_GREEN` |
| CI روی HEAD دیگر | `CI_HEAD_MISMATCH` |
| CI روی branch دیگر | `CI_BRANCH_MISMATCH` |
| workflow/app جعلی | `CI_WORKFLOW_MISMATCH` / `CI_CHECK_IDENTITY_MISMATCH` |
| repo اشتباه در CI | `CI_REPOSITORY_MISMATCH` |
| اتصال PR با `name_and_sha` | `PR_ASSOCIATION_UNPROVEN` |
| اتصال به PR دیگر | `PR_ASSOCIATION_UNPROVEN` |
| workflow_source_sha جعلی | `WORKFLOW_SOURCE_SHA_MISMATCH` |
| فایل شبح/جاافتاده/blob اشتباه/rename به‌صورت add | `DIFF_DECLARATION_MISMATCH` |
| tree جعلی | `HEAD_TREE_MISMATCH` |
| base غیرمرتبط | `BASE_NOT_ANCESTOR` |
| HEAD جابه‌جا پیش از بررسی | `HEAD_REF_SHA_MISMATCH` |
| base جابه‌جا پیش از بررسی | `BASE_REF_SHA_MISMATCH` |
| جابه‌جایی HEAD در حین بررسی | `HEAD_OR_BASE_MOVED` + `REF_MOVED_AFTER_VERIFICATION` |
| squash (تک‌والد) در حالت POST_MERGE | `MERGE_COMMIT_NOT_TWO_PARENT` |
| ترتیب والدهای merge معکوس | `MERGE_BASE_PARENT_MISMATCH` |
| merge توسط actor بای‌پس | `BYPASS_ACTOR_MERGE` |
| claim دارای merge metadata در PRE_MERGE | `PRE_MERGE_HAS_MERGE_METADATA` |
| PR draft | `DRAFT_PR_NOT_MERGEABLE` |
| mode درخواستی مغایر claim | `MODE_CONFLICT` |
| policy یا سورس verifier تغییرکرده | `TRUST_BOUNDARY_INVALID` |
| فایل اضافه در پوشهٔ verifier | `TRUST_BOUNDARY_INVALID` |

## ۷. آزمون جهش (mutation testing)

برای هر گارد حیاتی، همان حمله ابتدا HOLD می‌دهد و سپس با حذف **فقط همان گارد** (در همان بایت‌های پین‌شده) به `PASS_PROCESS` می‌رسد. این نشان می‌دهد رگرسیون‌ها واقعاً به گارد وابسته‌اند، نه به تصادف.

| گارد حذف‌شده | حمله | قبل | بعد |
|---|---|---|---|
| `log_prefix` | بازنویسی لاگ | `LOG_PREFIX_BROKEN` | `PASS_PROCESS` |
| `protected_paths` | rename سند حاکمیتی | `PROTECTED_PATH_RENAMED` | `PASS_PROCESS` |
| `protected_paths` | تغییر workflow | `WORKFLOW_SOURCE_MODIFIED` | `PASS_PROCESS` |
| `reviewer_identity` | دو تأیید با یک id | `DUPLICATE_REVIEWER_IDENTITY` | `PASS_PROCESS` |
| `required_approvals` | صفر تأیید | `INSUFFICIENT_APPROVALS` | `PASS_PROCESS` |
| `ci_identity` | چک push | `CI_EVENT_NOT_PULL_REQUEST` | `PASS_PROCESS` |
| `ci_pr_association` | اتصال name+sha | `PR_ASSOCIATION_UNPROVEN` | `PASS_PROCESS` |
| `workflow_binding` | source sha جعلی | `WORKFLOW_SOURCE_SHA_MISMATCH` | `PASS_PROCESS` |
| `diff_declaration` | فایل شبح | `DIFF_DECLARATION_MISMATCH` | `PASS_PROCESS` |
| `head_tree` | tree جعلی | `HEAD_TREE_MISMATCH` | `PASS_PROCESS` |
| `mode_consistency` | mode مغایر | `MODE_CONFLICT` | `PASS_PROCESS` |
| `repository_identity` | repo اشتباه | `REPOSITORY_IDENTITY_MISMATCH` | `PASS_PROCESS` |
| `bypass_actor` | merge بای‌پس | `BYPASS_ACTOR_MERGE` | `PASS_PROCESS` |
| `postmerge_shape` | squash | `MERGE_COMMIT_NOT_TWO_PARENT` | `PASS_PROCESS` |
| `refs_stable` | جابه‌جایی HEAD در حین بررسی | `HEAD_OR_BASE_MOVED` | `PASS_PROCESS` |

در همهٔ موارد، حتی `PASS_PROCESS` بعد از حذف گارد نیز `merge_authorized=false` و `trust_activated=false` دارد.

## ۸. نگاشت به محدودیت‌های مرحلهٔ ۱

ده فرضِ «اعتماد به دادهٔ فراخوان» در مرحلهٔ ۱ که اکنون از Git/pin مشتق می‌شوند:

1. policy الزامی از JSON مدعی → policy پین‌شدهٔ بیرونی.
2. فهرست فایل‌های تغییرکرده از claim → diff واقعی Git.
3. append-only با «حضور نام فایل» → مقایسهٔ بایت‌به‌بایت prefix.
4. شمارش تأیید با تعداد ردیف review → مجموعهٔ یکتای `author_id`.
5. اتصال review به HEAD اعلام‌شده → همان HEAD از Git.
6. چک سبز بدون `event=pull_request` → event اجباری.
7. اتصال چک به PR با heuristic → `explicit_link` یا HOLD.
8. هویت workflow از فیلد claim → blob واقعی workflow در HEAD.
9. squash/rebase با فرض حفظ HEAD → والدهای واقعی merge commit.
10. بی‌توجهی به TOCTOU ref → دو خواندن و مقایسه.

کنترل‌های مثبت کاذب مرحلهٔ ۱ (موارد سالمی که نباید رد شوند) در تاریخ حفظ شده‌اند و در این مرحله نیز baselineهای سالم (`PASS_PROCESS`) وجود دارند؛ هیچ‌کدام به «شاهد تأیید ادغام» ارتقا داده نشده‌اند.

## ۹. نتایج اجرا

محیط: Windows، Python `3.15.0`، pytest `9.1.1`، git `2.56.0.windows.4`.

```text
python -m pytest -q tests/test_trusted_merge_verifier.py
80 passed
```

```text
python -m unittest tests.test_trusted_merge_verifier
Ran 80 tests
OK
```

هر ۸۰ آزمون روی مخزن‌های موقت و verifier پین‌شده اجرا می‌شوند؛ هیچ شبکه، credential، GitHub API، ruleset، merge یا trust activation در آن‌ها نیست.

## ۱۰. محدودیت‌ها (آنچه اثبات نشده)

- **مرز مدیر مشترک:** candidate و verifier هر دو زیر یک کاربر ویندوز و یک مخزن اجرا می‌شوند. جداسازی، منطقی/فرآیندی است، نه custody مستقل. همان مدیر می‌تواند هم verifier و هم trust root را بازنویسی کند. pin فقط «تغییر بایت» را نسبت به یک لحظهٔ پین‌شده نشان می‌دهد.
- verifier کد candidate را اجرا نمی‌کند، اما مخزن candidate و ابزار `git` روی همان ماشین مشترک‌اند؛ نفوذ به سطح سیستم‌عامل یا git خارج از دامنه است.
- claim همچنان توسط مدعی نوشته می‌شود. verifier فقط ناسازگاری claim با Git/pin را می‌بیند؛ اگر مدعی دربارهٔ GitHub دروغ بگوید و Git محلی هم آن را تأیید نکند، HOLD می‌شود، اما صحت خود GitHub تأیید نمی‌شود.
- هویت واقعی بازبین، امضای تأیید، استقلال سازمانی، و trusted executor اثبات نمی‌شود.
- هیچ بازخوانی زندهٔ GitHub API انجام نشد؛ `pull_requests` خالی در API واقعی همچنان مسئله است.
- `PASS_PROCESS` فقط سازگاری فرآیندی است. `merge_authorized` همیشه `false` است و CLI همیشه با کد ۱ خارج می‌شود؛ این ابزار عمداً نمی‌تواند required check سبز شود.
- squash در حالت PRE_MERGE قابل ارزیابی نیست؛ در POST_MERGE باید HOLD شود.
- این ممیزی امنیت عمومی، صحت کد، یا آمادگی انتشار را اثبات نمی‌کند.

## ۱۱. بازتولید

```powershell
cd implementation

# آزمون متمرکز
python -m pytest -q tests/test_trusted_merge_verifier.py

# آزمون جایگزین
python -m unittest tests.test_trusted_merge_verifier

# اجرای دستی روی یک claim (همیشه exit code = 1)
python -m research.trusted_merge_verifier.cli `
  --candidate C:\path\to\candidate `
  --claim C:\path\to\claim.json `
  --trust-root C:\path\to\trust_root.json `
  --verifier-dir C:\path\to\verifier `
  --mode PRE_MERGE
```

## ۱۲. نسبت به PR #133 و Guard V2

- از `guard_v2_pr_scope.py` ایدهٔ PR-scoped HEAD/check و از `guard_v2_review_graph.py` ایدهٔ اتصال review به commit بازاستفاده شد؛ اما این پیاده‌سازی policy و سورس را از مرز پین‌شده می‌گیرد.
- گیت `review_evidence_gate.py` (PR #133) فقط نام فایل را می‌دید، append-only را با حضور فایل می‌سنجید، و `event=pull_request` را الزام نمی‌کرد. گارد جدید این سه شکاف را می‌بندد و علاوه بر آن blob/rename/حذف و والدهای merge را از Git می‌خواند.
- هیچ‌کدام از این دو مسیر merge یا فعال‌سازی ruleset نشدند.

## ۱۳. آنچه انجام نشد

- هیچ push/merge/تغییر ruleset/تغییر policy روی `main`/فعال‌سازی trust/کلید واقعی/history rewrite انجام نشد.
- هیچ ادعای «تأیید ادغام» از شواهد مصنوعی ساخته نشد.
- PR #133، #381، #385 و rulesetهای `24782645`/`27201221` دست‌نخورده ماندند.

**پایان مرحلهٔ ۲.**
