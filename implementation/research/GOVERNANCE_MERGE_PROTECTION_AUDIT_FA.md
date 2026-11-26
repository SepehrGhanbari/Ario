# ممیزی حفاظت از ادغام و حاکمیت — Ario

**تاریخ:** 2026-11-25
**وضعیت:** `RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_HISTORY_REWRITE`
**مبنا:** `main` در `5ce5d4fb69a1e0fb97fd8dc4db9ea4267d377b14`
**شاخهٔ محلی پژوهش:** `research/governance-merge-protection-20261125`
**مخزن:** `C:\Users\xx4773\Documents\Default Project\ario-governance-audit`
**دامنه:** فقط خواندن GitHub API و Git محلی؛ بدون push، merge، تغییر ruleset، تغییر سیاست، یا بازنویسی تاریخچه.

> این سند یافتهٔ پژوهشی است، نه تأیید امنیتی، نه تصمیم حاکمیتی، و نه مجوز ادغام.
> هیچ ادعایی دربارهٔ هویت مستقل بازبین، صحت اجرای CI، یا امنیت تولید اثبات نشده است.

---

## ۱. خلاصهٔ اجرایی

حفاظت شاخهٔ `main` در GitHub به‌صورت **شکل‌گرا** وجود دارد، اما در عمل سه شکاف هم‌زمان آن را کم‌اثر می‌کند:

1. **بای‌پس مالک:** ruleset سخت‌گیر `24782645` یک actor بای‌پس دارد (`104393545`) با حالت `pull_request`. بنابراین الزام «۱ تأیید + CODEOWNERS» برای همان actor قابل دور زدن است. شاهد تجربی: **۲۵ از ۲۵** PR ادغام‌شدهٔ اخیر **صفر تأیید** داشتند.
2. **هویت چک‌ها فقط «نام job» است:** ruleset دوم `27201221` تنها context با نام `m0-regression` و `integration_id=15368` را الزام می‌کند؛ هیچ قیدی بر مسیر workflow، ref، یا event وجود ندارد. خود فایل workflow نیز توسط همان PR قابل تغییر است. نمونهٔ دقیق: PR #298 فایل `implementation-regression.yml` را تغییر داد (۱۱ افزودن، ۰ حذف) و با صفر تأیید merge شد.
3. **اتصال بازبینی به HEAD و اتصال CI به PR شکننده است:** `dismiss_stale_reviews_on_push=false` و `require_last_push_approval=false` هستند؛ merge از نوع squash/rebase مجاز است و در PR #345 هد بازبینی‌شده (`7c9a1250`) در تاریخچهٔ `main` حفظ نشده است. در HEAD یک PR، دو چک هم‌نام `m0-regression` (یکی از `push` و یکی از `pull_request`) روی یک SHA دیده شد و API استاندارد GitHub فیلد `pull_requests` را خالی برمی‌گرداند؛ لذا تطبیق «نام + SHA» ذاتاً مبهم است.

در پاسخ، یک ارزیاب پژوهشی fail-closed با ۴۱ آزمون سنتتیک ساخته شد که همین شکاف‌ها را تشخیص می‌دهد، اما همیشه `merge_authorized=false` و خروجی غیرصفر دارد تا هرگز به‌عنوان check سبز قابل استفاده نباشد.

---

## ۲. روش و منابع

- بازرسی فقط‌خواندنی با `gh api` و `git` محلی.
- استفادهٔ مجدد از پژوهش‌های موجود Guard V2 و review-evidence به‌جای بازسازی:
  - `origin/research/guard-v2-pr-scope-synthetic-20261121:implementation/research/guard_v2_pr_scope.py`
  - `origin/research/r22-guard-v2-current-run-and-report-completeness-20261122:implementation/research/guard_v2_review_graph.py`
  - `origin/governance/review-evidence-gate-v1-20261103:.github/scripts/review_evidence_gate.py`
  - `experiments/ava-bridge-governance-2026-11-03/RESEARCH_FINDINGS_FA.md`
  - `implementation/ADMISSION_REVIEW_POLICY_V0_1.md` و `implementation/REVIEWER_AUTHORIZATION_CONTRACT_V0_1.md`
- بازتولید با دادهٔ سنتتیک در `implementation/tests/test_governance_merge_guard.py`.
- هیچ دادهٔ واقعی، کلید، توکن، یا وضعیت production فعال نشد.

---

## ۳. یافته‌ها

### F1 — دو ruleset فعال با الزامات ناهم‌سطح

| ruleset | وضعیت | الزام PR | وضعیت‌چک | بای‌پس |
|---|---|---|---|---|
| `24782645` «Protect main» | active | ۱ تأیید، CODEOWNERS، `require_extra_approval_for_unattributed_changes=true` | ندارد | actor `104393545` (`User`, `pull_request`) |
| `27201221` «Protect main - no-bypass baseline PR and status» | active | **۰ تأیید**، بدون CODEOWNERS | `m0-regression` از `integration_id=15368`، strict | ندارد |

هر دو فعال‌اند و GitHub قواعد را تجمیع می‌کند؛ الزام ۱ تأیید از ruleset اول باقی می‌ماند، اما بای‌پس همان ruleset آن را برای actor مشخص بی‌اثر می‌کند. `current_user_can_bypass` مقدار `pull_requests_only` دارد.

تنظیمات دقیق ruleset اول:

```json
{"dismiss_stale_reviews_on_push":false,
 "require_code_owner_review":true,
 "require_extra_approval_for_unattributed_changes":true,
 "require_last_push_approval":false,
 "required_approving_review_count":1,
 "required_review_thread_resolution":false,
 "allowed_merge_methods":["merge","squash","rebase"]}
```

### F2 — شاهد تجربی صفر تأیید

برای ۲۵ PR ادغام‌شدهٔ اخیر، تعداد review با state برابر `APPROVED` صفر بود. نمونهٔ دقیق:

| PR | approvals | merged_at | merge commit | head |
|---|---:|---|---|---|
| #366 | 0 | 2026-11-24T18:32:48Z | `5ce5d4fb69a1e0fb97fd8dc4db9ea4267d377b14` | `c91300a3e4430ddbb4f60ab5fb23513be23d3b1e` |
| #357 | 0 | 2026-11-24T17:59:40Z | `89ef7ba466db2e7a267ee7780df348ee9e5920e6` | `f9ec4b4981789d04e2ba45b5eb479154d2763fa3` |
| #345 | 0 | 2026-11-23T22:10:15Z | `a98be4c06d06247e5f7fa56a3491287bc983e8cf` | `7c9a1250a51da235dcfeef6fa55415087174f669` |
| #341 | 0 | 2026-11-23T17:56:41Z | `18abe89598a56e7153ce984a9cd366313a07312f` | `732b36284e06c99f3f24aecf689bfd123e756924` |
| #340 | 0 | 2026-11-23T18:15:01Z | `70851e67f1bf206c54af0189e3ede98e75a6a96f` | `18abe89598a56e7153ce984a9cd366313a07312f` |
| #298 | 0 | 2026-11-21T12:46:02Z | `f2771f56345f76fa111f92c0edb64045464fa37f` | `850e17d0cb421701a6b87c03db6d62d054c20cfd` |

(فهرست کامل ۲۵ مورد در اجرای ممیزی ثبت شد: #366, #357, #345, #341, #340, #332, #329, #326, #323, #318, #317, #316, #315, #314, #313, #310, #309, #308, #307, #305, #303, #301, #300, #299, #298.)

**نتیجه:** «۱ تأیید الزامی است» یک ادعای کاغذی است؛ مسیر عملی ادغام آن را دور می‌زند.

### F3 — هویت چک لازم، فقط نام job است

- ruleset فقط `context="m0-regression"` و `integration_id=15368` را می‌خواهد.
- در GitHub، context یک status check همان نام job است؛ مسیر workflow و event جزو الزام نیست.
- `.github/workflows/implementation-regression.yml` روی شاخهٔ PR اجرا می‌شود؛ پس PR می‌تواند همان فایل را تغییر دهد و jobی با همان نام تولید کند.

شاهد دقیق: PR #298 فایل workflow الزامی را تغییر داد:

```diff
@@ -24,6 +24,10 @@ jobs:
       - name: Run M0 and runtime regression suites
         run: python -m pytest -q tests
+      - name: PR298 synthetic Linux CLI peak-RSS experiment (256 MiB trial)
+        if: github.event_name == 'pull_request' && github.event.pull_request.number == 298
+        timeout-minutes: 6
+        run: python -B research/pr298/linux_rss_probe.py
```

این PR با **۰ تأیید** merge شد (`f2771f56`). یعنی فایل تولیدکنندهٔ چک الزامی، در همان PRی تغییر کرد که با آن چک سبز شد.

### F4 — دو چک هم‌نام روی یک SHA و ابهام PR-scoping

روی `c91300a3e4430ddbb4f60ab5fb23513be23d3b1e` (HEAD PR #366) دو check run موفق با نام یکسان دیده شد:

| check run id | job id | run id | event | started |
|---|---|---|---|---|
| `138681144591` | `138681144591` | `45460415487` | `pull_request` | 2026-11-24T18:31:29Z |
| `138681081235` | `138681081235` | `45460397514` | `push` | 2026-11-24T18:31:18Z |

هر دو `app=github-actions`، `conclusion=success`، و روی همان SHA هستند. برای هر دو، هم REST check-runs و هم Actions runs API فیلد `pull_requests` را **خالی** برگرداند:

```json
{"id":45460415487,"event":"pull_request","head_sha":"c91300a3...","head_branch":"research/integrity-gate-v1-20261124","path":".github/workflows/implementation-regression.yml","pull_requests":[]}
```

**نتیجه:** گیتی که فقط «نام + SHA» را تطبیق دهد، می‌تواند چک `push` را به‌جای چک PR بپذیرد. تفکیک واقعی باید `event=pull_request`، `head_branch`، `workflow_id/path` و در صورت وجود، اتصال صریح PR را با هم ببیند. حتی در این حالت، اتصال «event + branch» یک مبنای جزئی است، نه اثبات کامل.

### F5 — squash/rebase اتصال HEAD بازبینی‌شده را از بین می‌برد

- PR #345: HEAD بازبینی‌شده `7c9a1250a51da235dcfeef6fa55415087174f669`; merge commit `a98be4c06d06247e5f7fa56a3491287bc983e8cf` **تک‌والد** با parent `67327dfdcbe786235e76c89b1ab03baef241bb1c` است.
- tree هر دو برابر است: `85529dab8985c91ddf23e41c3357f7732450aac5`. یعنی محتوا حفظ شده، اما commit بازبینی‌شده در تاریخچهٔ `main` نیست:

```text
git merge-base --is-ancestor 7c9a1250 HEAD   -> exit 1
git branch -r --contains 7c9a1250             -> origin/fix/cli-py310-forward-ref-authorization
```

- در مقابل، PR #366 با merge دووالدی `5ce5d4f` انجام شد و `c91300a` والد دوم آن است؛ پس HEAD حفظ شده است.

**نتیجه:** در squash، «محتوای مشابه» تنها با مقایسهٔ tree قابل حدس است؛ خود رکورد merge هیچ تعهدی به HEAD بازبینی‌شده ندارد. گارد باید squash/rebase را HOLD کند مگر اینکه نگاشت صریح reviewed-HEAD ارائه شود.

### F6 — تأیید کهنه و thread حل‌نشده مسدود نمی‌شوند

- `dismiss_stale_reviews_on_push=false`: با push جدید پس از تأیید، تأیید قبلی باطل نمی‌شود.
- `require_last_push_approval=false`: آخرین push نیاز به تأیید تازه ندارد.
- `required_review_thread_resolution=false`: thread حل‌نشده مانع merge نیست.

در ۲۵ merge اخیر اصلاً تأییدی وجود نداشت، بنابراین «تأیید کهنه» در عمل دیده نشد؛ اما کنترل فنی آن هم وجود ندارد.

### F7 — تفکیک وظایف تضمین نمی‌شود

- `.github/CODEOWNERS` فقط `@SepehrGhanbari` است.
- هیچ قاعده‌ای author ≠ approver را الزام نمی‌کند؛ actor بای‌پس نیز همان مالک است.
- در عمل چون تأییدی ثبت نمی‌شود، self-approval هم بی‌اثر است؛ اما در یک مدل «تأیید لازم»، self-approval مسدود نیست.

### F8 — شکاف‌های دقیق گیت قبلی `review_evidence_gate.py`

این فایل فقط روی شاخهٔ `governance/review-evidence-gate-v1-20261103` است، روی `main` نیست، و required check نیست. PR #133 از 2026-11-03 باز است، `mergeable=false` (`dirty`) و ۰ تأیید دارد. رفتار دقیق آن:

1. `protected_path()`: هر مسیر خارج از `implementation/` را protected می‌داند، اما داخل `implementation/` فقط زیررشته‌های `owner_signer`, `genesis`, `trust_anchor`, `authorization`, `admission`, `memory_engine`, `continuity`, `self_model`, `identity_contract`, `governance`, `secret`, `credential` را. بنابراین `implementation/AGENTS.md` protected نیست.
2. فقط **نام فایل‌ها** بررسی می‌شود؛ `patch`، `status`، `deletions` و محتوای diff بررسی نمی‌شود. policy smuggling در متن یک فایل مجاز، یا حذف محتوای یک فایل موجود، دیده نمی‌شود.
3. append-only فقط با `require("ENGINEERING_LOG.md" in actual, "APPEND_ONLY_LOG_MISSING")` بررسی می‌شود؛ هیچ بررسی‌ای برای حذف/کوتاه‌شدن/جابه‌جایی خطوط نیست.
4. بازبینی: فقط ربات‌های مشخص، stateهای `COMMENTED` یا `APPROVED`، `commit_id == head`، و «آخرین» بازبینی؛ صحت هویت ربات و استقلال واقعی اثبات نمی‌شود.
5. چک سبز: `name == "Implementation Regression"` و `head_sha == head` و `head_branch == PR head ref`؛ اما `event == pull_request` الزام نیست. بنابراین چک `push` روی همان شاخه می‌تواند پذیرفته شود.
6. PR باید `open`، غیرdraft، base=`main`، و `head == reviewed_head_sha` باشد و مجموعهٔ نام فایل‌ها دقیقاً با رکورد برابر باشد؛ این بخش خوب است، اما بدون بررسی patch/deletion ناقص می‌ماند.

### F9 — سطح حاکمیتی PRهای باز

در زمان ممیزی: **۶۷ PR باز**، ۶۰ draft و ۷ آماده.

- **#381** (draft، head `38204d103`) و **#385** (draft، base `research/foundation-recovery-20261125`، head `22f54103`) فایل `AGENTS.md` را تغییر می‌دهند.
- **#385** فایل `GOVERNANCE/OWNER_DELEGATION_2026-11-25.md` را اضافه می‌کند و در `AGENTS.md` زبان preservation را تضعیف می‌کند. نمونهٔ دقیق diff:

```diff
-- Do not overwrite, delete, rename, or repurpose a healthy or historical artifact without explicit authorization and a verified, recoverable backup.
+- Ordinary source, test, and documentation edits within the standing delegation do not require separate authorization. Do not destructively overwrite, delete, rename, or repurpose historical evidence, immutable records, archives, or retained backups; these remain protected by the hard boundaries above.
```

- سند پیشنهادی `OWNER_DELEGATION_2026-11-25.md` صریحاً می‌گوید merge بدون اجازهٔ مجدد مجاز است، اما در شرط ۵ خود می‌گوید «حفاظت شاخه و کنترل‌های GitHub دور زده نشوند». این با actor بای‌پس فعال `104393545` در تناقض مستقیم است.
- **#282** (آماده، `mergeable=false`/`dirty`، ۰ تأیید) و **#210** (draft) فایل workflow الزامی را تغییر می‌دهند؛ #282 همچنین `ario_cli.py` و حافظهٔ core را.
- **#133** گیت قبلی review-evidence است و هرگز merge نشد.
- **#376** (draft) سند تمرکز دوهفته‌ای را ثبت می‌کند و خودش هم تأیید نشده است.
- ده‌ها draft دیگر workflowهای جدید زیر `.github/workflows/` اضافه می‌کنند؛ هر کدام می‌تواند نام چک تولید کند، هرچند فقط `m0-regression` فعلاً الزامی است.

### F10 — append-only بودن `ENGINEERING_LOG.md` ماشینی نیست

در تاریخچهٔ فایل، ۵ commit هر کدام دقیقاً یک خط حذف کرده‌اند:

```text
53f1e85d810b8abece3e27b6ab658b64b95cf61c
6c85fcabf6968da1cc9d6cf21ff6617dada0b79f
4ecdedf5d7accb61992a8bad498eb6515eabfa15
bb2d482fb856ec03a1108e75c8684c0c68ebab5e
b94f2a0bb412ca4c0a9d749092ba26d5a3c6fb73
```

در هر پنج مورد، خط حذف‌شده **عیناً** در خطوط افزوده reappear می‌کند (اصلاح newline انتهای فایل). بنابراین شاهد حذف معنایی پیدا نشد. اما هیچ کنترل ماشینی وجود ندارد که حذف/کوتاه‌شدن واقعی را رد کند؛ گیت قبلی هم آن را بررسی نمی‌کند. این یک شکاف فرآیندی است، نه شاهد تخریب.

---

## ۴. گارد پژوهشی ساخته‌شده

فایل: `implementation/research/governance_merge_guard.py`
آزمون‌ها: `implementation/tests/test_governance_merge_guard.py`

ورودی یک JSON با دادهٔ عرضه‌شده توسط فراخوان است (بدون شبکه). خروجی همیشه:

```json
{"authority":"NON_AUTHORITATIVE_RESEARCH_ONLY",
 "merge_authorized":false,
 "trust_activated":false,
 "disposition":"HOLD|PASS_PROCESS"}
```

`PASS_PROCESS` فقط یعنی «دادهٔ عرضه‌شده با قواعد پژوهشی سازگار است»، نه تأیید ادغام.

### قواعد اعمال‌شده

| قاعده | کد HOLD | پوشش یافته |
|---|---|---|
| تطبیق pin با PR (number/id/head/base) | `PIN_IDENTITY_MISMATCH` | F5 |
| تأییدها باید روی HEAD فعلی باشند | `STALE_OR_UNBOUND_APPROVAL` | F6 |
| self-approval ممنوع | `SELF_APPROVAL` | F7 |
| حداقل تأیید مستقل | `INSUFFICIENT_APPROVALS` | F1/F2 |
| سیاست صفر تأیید رد می‌شود | `ZERO_APPROVAL_POLICY` | F1 |
| CHANGES_REQUESTED مسدود می‌کند | `CHANGES_REQUESTED_PRESENT` | F6 |
| چک الزامی باید از PR event باشد | `CHECK_NOT_FROM_PULL_REQUEST_EVENT` | F3/F4 |
| چک باید به همین PR متعلق باشد | `CROSS_PR_CHECK_REUSE` | F4 |
| app و workflow باید trusted باشند | `UNTRUSTED_CHECK_APP`, `UNTRUSTED_CHECK_SOURCE` | F3 |
| HEAD چک باید فعلی باشد | `STALE_CHECK_HEAD` | F6 |
| چند چک هم‌نام سبز = ابهام | `AMBIGUOUS_REQUIRED_CHECK` | F4 |
| تغییر workflow = HOLD | `WORKFLOW_SELF_MODIFIED` | F3 |
| تغییر مسیرهای حاکمیتی = HOLD | `PROTECTED_POLICY_CHANGE` | F8/F9 |
| لاگ باید فقط append باشد | `EVIDENCE_LOG_NOT_APPEND_ONLY` | F10 |
| حذف لاگ ممنوع | `EVIDENCE_LOG_DELETED` | F10 |
| squash/rebase بدون حفظ HEAD | `REVIEWED_HEAD_NOT_PRESERVED` | F5 |
| merge توسط actor بای‌پس | `BYPASS_ACTOR_MERGE` | F1/F2 |

مسیرهای حاکمیتی شامل: `AGENTS.md` در هر عمقی، `GOVERNANCE.md`، `REVIEWER_INSTRUCTIONS.md`، `SECURITY.md`، `CONTRIBUTING.md`، `CODEOWNERS`، هر مسیر زیر `.github/` و `GOVERNANCE/`، و اسناد دارای `POLICY|CONTRACT|GOVERNANCE|AUTHORIZATION|DELEGATION` در نام.

### نکتهٔ مهم دربارهٔ API واقعی

برای اجرای واقعی، فیلد `pull_requests` در REST و Actions runs خالی است. گارد به‌صورت پیش‌فرض `EXPLICIT_LINK` را الزام می‌کند و در این حالت روی دادهٔ واقعی HOLD می‌دهد. حالت صریح `association="EVENT_AND_BRANCH"` اجازه می‌دهد فقط با `event=pull_request` + `head_branch` + `head_sha` ارزیابی شود و در خروجی `pr_link_basis="EVENT_AND_BRANCH_ONLY"` و محدودیت را ثبت می‌کند. این یک مبنای جزئی است و نباید به‌عنوان اثبات کامل PR-scoping خوانده شود.

---

## ۵. نتایج آزمون

محیط محلی: Windows، Python `3.15.0`، pytest `9.1.1`، cryptography `46.0.4`.
(CI مخزن طبق `implementation/requirements-research.txt` روی Python 3.13.16 اجرا می‌شود؛ نتیجهٔ محلی جایگزین CI نیست.)

```text
python -m pytest -q tests/test_governance_merge_guard.py
41 passed, 8 subtests passed in 0.22s
```

```text
python -m unittest tests.test_governance_merge_guard
Ran 41 tests
OK
```

پوشش آزمون‌ها: baseline سازگار؛ pin/merge mismatch؛ تأیید کهنه/بدون commit؛ self-approval؛ changes-requested؛ سیاست صفر تأیید؛ دو تأیید مستقل؛ چک مشترک بین PRها؛ چک push؛ workflow/app جعلی؛ HEAD کهنه؛ capture ناقص؛ چک تکراری؛ تغییر workflow واقعی؛ `AGENTS.md` تودرتو؛ اسناد policy/contract؛ truncation/deletion/empty append لاگ؛ squash و rebase؛ bypass actor؛ ورودی خراب/ناقص؛ و CLI که هرگز ۰ برنمی‌گرداند.

اجرای کامل مجموعه:

```text
python -m pytest -q tests
1747 passed, 15 skipped, 2 errors, 367 subtests passed in 85.55s
```

دو error مربوط به `tests/w4c_lab/test_w4b_profile_lab.py` و محدودیت محیط Windows است (`ValueError: the environment variable is longer than 32767 characters`)، نه به تغییر این شاخه. این خطا در baseline هم با همین محیط رخ می‌دهد.

---

## ۶. محدودیت‌ها و آنچه اثبات نشده

- گارد دادهٔ عرضه‌شده را می‌خواند؛ GitHub را زنده بازخوانی نمی‌کند و TOCTOU را حذف نمی‌کند.
- هویت بازبین، امضای تأیید، استقلال واقعی و trusted executor اثبات نمی‌شود.
- `pull_requests` خالی در API واقعی، اتصال چک به PR را به heuristic فرو می‌کاهد.
- rulesetها در زمان ممیزی snapshot شده‌اند و ممکن است بعداً تغییر کنند.
- یافته‌های «۰ تأیید» از API خوانده شده‌اند؛ اگر تأییدی خارج از GitHub (مثلاً مکاتبه) وجود داشته باشد، در شواهد مخزن نیست.
- هیچ کلید واقعی، امضاکننده، trust anchor، production، یا تصمیم حاکمیتی فعال نشد.
- این ممیزی امنیت عمومی، صحت کد، یا آمادگی انتشار را اثبات نمی‌کند.

---

## ۷. توصیه‌های محدود (اجرا نشده‌اند)

این‌ها پیشنهاد پژوهشی‌اند و هیچ‌کدام در این شاخه اعمال نشده‌اند:

1. چک الزامی را از `m0-regression` (نام job) به یک Check Run اختصاصی با GitHub App مستقل و `external_id` حاوی `PR number + head SHA + run id` منتقل کنید؛ الزام context فعلی قابل جعل با نام job است.
2. `dismiss_stale_reviews_on_push=true` و `require_last_push_approval=true` و `required_review_thread_resolution=true` را فعال کنید.
3. merge method را به `merge` محدود کنید یا نگاشت صریح `reviewed_head_sha -> merge_commit` را در یک چک الزامی ثبت کنید؛ squash فعلی اتصال را از بین می‌برد.
4. actor بای‌پس `104393545` را حذف یا به یک مسیر دو‌نفره/owner-signer برای مسیرهای حاکمیتی محدود کنید. سند پیشنهادی خودش دور زدن branch protection را ممنوع می‌داند.
5. `.github/**`، `AGENTS.md` تودرتو، و اسناد policy/contract را با CODEOWNERS و یک چک path-based که fail-closed است پوشش دهید.
6. append-only بودن `ENGINEERING_LOG.md` را ماشینی کنید: برابری prefix با blob مبنا، به‌جای اتکا به عرف.
7. PRهای #381/#385 را بدون بازبینی صریح «تغییر حاکمیتی» merge نکنید؛ آن‌ها `AGENTS.md` و سند واگذاری را تغییر می‌دهند.
8. ادعاهای پژوهشی را از وضعیت production/trust جدا نگه دارید؛ `PASS_PROCESS` هرگز نباید به‌عنوان مجوز ادغام تفسیر شود.

---

## ۸. بازتولید

```powershell
# rulesets
gh api repos/SepehrGhanbari/Ario/rulesets --jq '.[] | {id,name,enforcement}'
gh api repos/SepehrGhanbari/Ario/rulesets/24782645
gh api repos/SepehrGhanbari/Ario/rulesets/27201221

# چک‌های هم‌نام روی HEAD یک PR
gh api repos/SepehrGhanbari/Ario/commits/c91300a3e4430ddbb4f60ab5fb23513be23d3b1e/check-runs

# حفظ نشدن HEAD در squash
git cat-file -p a98be4c06d06247e5f7fa56a3491287bc983e8cf
git merge-base --is-ancestor 7c9a1250a51da235dcfeef6fa55415087174f669 5ce5d4fb69a1e0fb97fd8dc4db9ea4267d377b14

# آزمون گارد
cd implementation
python -m pytest -q tests/test_governance_merge_guard.py
```

---

**پایان ممیزی.** هیچ push، merge، تغییر ruleset، تغییر سیاست `main`، فعال‌سازی trust، یا استفاده از کلید واقعی انجام نشد. تنها تغییرات، فایل‌های پژوهشی و آزمون روی شاخهٔ محلی `research/governance-merge-protection-20261125` و یک ورودی append-only در `ENGINEERING_LOG.md` هستند.
