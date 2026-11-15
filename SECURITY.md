# Ario Security Policy / سیاست امنیتی آریو

**Scope:** Maintained open-source repository `SepehrGhanbari/Ario`. This is a responsible-disclosure and deployment-safety guide, **not** a certification, a cryptographic trust anchor, or authorization to admit evidence. Last source review: 2026-11-15.

**فارسی:** [بخش فارسی](#farsi)

## Reporting a security issue

**Do not post exploits, private keys, credentials, personal data or nonpublic vulnerabilities in a public GitHub issue.**

Send a private report to **[sepehr.ghanbari@proton.me](mailto:sepehr.ghanbari@proton.me)**, subject prefix `[SECURITY]`. Include affected version or commit, minimal reproduction, observed and expected behavior, impact, and safe contact details. Avoid transmitting secrets unless a separately authenticated encrypted channel has been established. No verified public PGP key is specified in this policy.

The current project is maintained by one person. Acknowledgement, triage and a potential fix are handled **as capacity permits**, without a guaranteed response deadline, staffed security team, SLA or embargo. Reporters and maintainer should coordinate public disclosure when possible. For an exposed live endpoint, the operator must apply local containment without assuming the issue will be fixed immediately.

## What is and is not protected

| Component / claim | Verified bounded behavior and operational limit |
|---|---|
| Ordinary task agent (`implementation/ario_agent.py`) | Appends **plain JSONL** task events and checks record format and duplicate task IDs. These checks do **not** cryptographically detect malicious rewriting of the entire ledger. Do not call it immutable or universally tamper-evident. |
| CLI access control | Runs under the invoking operating-system account. **No built-in app login, RBAC or session manager** in the ordinary agent CLI; file permissions and process isolation are deployment responsibilities. |
| File observations and storage | Agent read operations can record file content or derived observations in **unencrypted JSONL**. Protect sensitive data using OS permissions and separately configured disk/storage encryption. Encryption-at-rest is **not** built in to that ledger. |
| Local Ollama planner | Numeric loopback validation, no ambient proxy and redirect refusal are implemented for the bounded planner. Planning context still travels over **plain HTTP on loopback**. Loopback is **not TLS encryption**. Never expose this endpoint to an untrusted network. |
| SHA-256 and research integrity checks | Some research components hash **specific declared bytes**. A matching hash does not establish source independence, truth, universal record integrity, or an external custody guarantee. |
| M0 / CLI structural `PASS` | Structural test or audit success **does not** authorize evidence admission, model truth or independent witness status. Preserve the original result's limitation fields and provenance. |
| Authentication and encryption for other services | Must be verified **per component and deployment**, not assumed from the existence of a library, cloud platform, or policy. |
| Log retention / incident recovery | No global promise that every action is logged, that all logs resist a privileged writer, or that every retention/rollback policy is enforced. Backups are useful but not proof of survival or integrity. |

**Status of the old local planner report:** [Issue #163](https://github.com/SepehrGhanbari/Ario/issues/163) was closed on 2026-11-15 following merged [PR #177](https://github.com/SepehrGhanbari/Ario/pull/177). Its tests support a *bounded local transport fix*, not blanket safety of other network setups.

## Contributor and deployment precautions

- **Validate input for its intended domain, then encode at the output boundary.** Removing whitespace is not an XSS sanitizer. For untrusted text in HTML use DOM `textContent` or context-appropriate escaping; attribute, URL and JavaScript contexts require additional validation.
- **Do not commit secrets or private records.** Apply least privilege, keep dependencies reviewed, and isolate test and production credentials.
- **Treat test failures and UNKNOWN as reportable outcomes.** Neither CI green nor model agreement is an authority for publication, evidence admission or identity.
- **Do not publicly expose local Ollama, task-agent write controls, unreviewed experiment servers, or log directories.** For services exposed over a network use independently configured authentication and TLS.
- **Consider external encrypted storage, independently controlled history and periodic restore tests** for deployments handling sensitive data. Do not claim these controls are provided by this repository unless demonstrated.

Example — **HTML text context only**, using Python standard library:

~~~python
import html

MAX_LENGTH = 4096

def process_input(user_input: str) -> str:
    if not isinstance(user_input, str):
        raise ValueError("Invalid input type")
    trimmed = user_input.strip()  # Trimming is NOT XSS protection.
    if len(trimmed) > MAX_LENGTH:
        raise ValueError("Input too long")
    return trimmed

def encode_html_text(user_input: str) -> str:
    return html.escape(process_input(user_input), quote=True)
~~~

This does **not** make arbitrary HTML, URL, JavaScript, CSS or attribute interpolation safe. Use the output-context-specific API and checks.

## Review and tool status

GitHub checks and comments are useful but **not** a universal security audit. Some PRs have owner-directed admissions rather than independent human approvals. A green CodeRabbit status is not equivalent to closing its inline findings, and repository rules do not guarantee independent assessment of every change.

| Item | Status as verified for this document |
|---|---|
| Project CI and bounded tests | Recorded on specific commits; not a security certification |
| Independent approval for every PR | **Not established** |
| Dependabot configuration | **Not verified**; no `.github/dependabot.yml` in the inspected tree |
| GitHub secret-scanning configuration | **Not verified** from repository source |
| Security testing | **Partial**, only when exact test/run evidence is supplied |
| Independent penetration test | **Not verified** |
| Owner/Genesis cryptographic signer | **NOT_ACTIVATED** per [GOVERNANCE.md](./GOVERNANCE.md) |

Developers may use Bandit, Semgrep, dependency auditing, OWASP guidance and other tools, but mentioning them is **not** evidence they were executed. Report exact command, tool version, commit and results, including failures.

Security documentation itself does **not** change license rights, branch protection, governance, keys, trust or runtime behavior. See [GOVERNANCE.md](./GOVERNANCE.md) and [AGENTS.md](./AGENTS.md).

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [GitHub repository](https://github.com/SepehrGhanbari/Ario)

---

<a id="farsi"></a>

# Farsi: سیاست امنیتی

**دامنه:** مخزن متن‌باز رسمی آریو. این سند راهنمای گزارش مسئولانه و احتیاط‌های استقرار است؛ **گواهی امنیت، ریشهٔ اعتماد رمزنگاری‌شده یا مجوز پذیرش شاهد نیست**.

## گزارش آسیب‌پذیری

**اطلاعات محرمانه، کلید، رمز، دادهٔ شخصی و جزئیات بهره‌برداری از آسیب‌پذیریِ غیردرخشده را در ایشوی عمومی ننویسید.**

گزارش خصوصی را به **[sepehr.ghanbari@proton.me](mailto:sepehr.ghanbari@proton.me)** با پیشوند موضوع `[SECURITY]` بفرستید. نسخه یا کامیت آسیب‌دیده، روش بازتولید کم‌خطر، رفتار مشاهده‌شده، اثر و راه تماس را مشخص کنید. بدون کانال رمزنگاری‌شده و تأییدشده، خودِ رمز یا کلید خصوصی را نفرستید. کلید عمومی PGP تأییدشده‌ای در این سند معرفی نشده است.

پروژه فعلاً **یک نگهدارنده** دارد. دریافت، بررسی و رفع مشکل در حد توان انجام می‌شود؛ **مهلت پاسخ، رفع خطا، تیم دائمی امنیت یا SLA تضمین نمی‌شود**. افشای عمومی را در صورت امکان با گزارش‌دهنده هماهنگ می‌کنیم. استقراردهنده باید خطر فوری را در سامانهٔ خودش مهار کند.

## حفاظت‌های موجود و محدودیت‌ها

| بخش | رفتار محدود و مرز ادعا |
|---|---|
| عامل معمولی `ario_agent.py` | رویدادها را در **JSONL ساده** ثبت می‌کند و قالب رکورد و تکرار شناسهٔ کار را بررسی می‌کند. این حفاظت، تغییرِ عمدی تمام دفتر توسط نویسندهٔ فایل را رمزنگارانه کشف نمی‌کند؛ دفتر **تغییرناپذیر یا ضد دستکاری کامل نیست**. |
| دسترسی CLI | با حساب فراخوانِ سیستم‌عامل اجرا می‌شود؛ **ورود برنامه‌ای، RBAC و مدیریت جلسهٔ داخلی ندارد**. مجوز فایل‌ها و جداسازی فرایند به استقرار بستگی دارد. |
| محتوای فایل و ذخیره‌سازی | عامل می‌تواند محتوای فایل یا مشاهدهٔ مشتق‌شده را در دفتر **JSONL بدون رمزنگاری سطح برنامه** ثبت کند. برای دادهٔ حساس باید مجوز سیستم‌عامل و رمزنگاری جداگانهٔ فضای ذخیره‌سازی به‌کار رود. |
| برنامه‌ریز Ollama | مقصد loopback را اعتبارسنجی می‌کند، پروکسی محیط و ریدایرکت را کنار می‌گذارد ولی داده را با **HTTP ساده روی loopback** می‌فرستد؛ loopback معادل TLS نیست. |
| SHA-256 و بررسی‌های پژوهشی | تطبیق هشِ **بایت‌های مشخص**، حقیقت، استقلال شاهد یا نگهداری بیرونی را ثابت نمی‌کند. |
| `PASS` ساختاری M0/CLI | به‌تنهایی پذیرش شاهد، صحت ادعا یا اختیار یک بازبین مستقل را مجاز نمی‌کند. |
| امنیت مؤلفه‌های دیگر | احراز هویت، TLS و ذخیره‌سازی امن باید **برای هر مؤلفه و استقرار جداگانه** بررسی شود. |
| لاگ و بازیابی | ثبت همهٔ اقدامات، ضد دستکاری بودن تمام لاگ‌ها و اجرای سیاست نگهداری سراسری تضمین نشده است. پشتیبان‌گیری به‌تنهایی شاهد صحت نیست. |

[ایشوی #163](https://github.com/SepehrGhanbari/Ario/issues/163) مربوط به پروکسی Ollama در ۱۵ نوامبر ۲۰۲۶ پس از ادغام [PR #177](https://github.com/SepehrGhanbari/Ario/pull/177) بسته شد. این یک اصلاح محدودِ انتقال محلی است، نه تضمین امنیت همهٔ شبکه‌ها.

## احتیاط‌های برنامه‌نویسی و استقرار

- **ورودی را اعتبارسنجی و هنگام خروجی، متناسب با محل استفاده کدگذاری کنید.** `strip()` صرفاً فاصله‌ها را حذف می‌کند و مانع XSS نیست. برای درج متن نامطمئن در DOM از `textContent` یا کدگذاری مناسب استفاده کنید؛ URL و JavaScript قواعد اضافی دارند.
- **کلید و اطلاعات محرمانه را در Git ثبت نکنید**؛ اصل حداقل دسترسی و جدایی محیط آزمایش و تولید را رعایت کنید.
- **شکست آزمون و UNKNOWN را نگه دارید.** سبزشدن CI یا توافق چند مدل مجوز پذیرش شاهد یا اثبات حقیقت نیست.
- سرویس Ollama، ابزارهای نوشتن عامل، سرورهای آزمایشی و دفترهای ثبت را روی اینترنت عمومی قرار ندهید. سرویس بیرونی به TLS و احراز هویت مستقل نیاز دارد.
- برای دادهٔ حساس از ذخیره‌سازی رمزنگاری‌شدهٔ بیرونی، تاریخچهٔ مستقل و تست بازگردانی کمک بگیرید؛ **این‌ها قابلیتِ اثبات‌شدهٔ خودکارِ آریو نیستند**.

مثال زیر فقط کدگذاری **متن HTML** را نشان می‌دهد، نه پاک‌سازی همه‌منظوره:

~~~python
import html

MAX_LENGTH = 4096

def process_input(user_input: str) -> str:
    if not isinstance(user_input, str):
        raise ValueError("نوع ورودی نامعتبر")
    trimmed = user_input.strip()  # حذف فاصله‌ها مانع XSS نیست.
    if len(trimmed) > MAX_LENGTH:
        raise ValueError("ورودی بسیار طولانی")
    return trimmed

def encode_html_text(user_input: str) -> str:
    return html.escape(process_input(user_input), quote=True)
~~~

برای HTML به‌شکل markup، ویژگی‌ها، URL، JavaScript و CSS باید از راهکار مخصوص همان زمینه استفاده شود.

## وضعیت بازبینی و ابزارها

وجود CI و نظر خرگوشک **ممیزی امنیتی مستقل همگانی نیست**. استثنای ثبت‌شدهٔ مالک به‌معنی تأیید بازبین مستقل نیست؛ سبزبودن CodeRabbit Check هم شش گفت‌وگوی باز را به‌طور خودکار حل نمی‌کند.

| مورد | وضعیت مستند |
|---|---|
| CI و تست‌های محدود | فقط در همان کامیت و محیط گزارش‌شده معتبر |
| تأیید مستقل تمام PRها | **اثبات نشده** |
| پیکربندی Dependabot | **تأییدنشده**؛ فایل `.github/dependabot.yml` دیده نشد |
| اسکن اسرار GitHub | **تأییدنشده**؛ تنظیمات حساب در این سند بررسی نشده |
| تست‌های امنیتی | **جزئی**؛ شواهد هر اجرا باید جداگانه ثبت شود |
| تست نفوذ مستقل | **تأییدنشده** |
| امضای رمزنگاری‌شدهٔ رسمی مالک | طبق [GOVERNANCE.md](./GOVERNANCE.md) **فعال نشده** |

استفاده از Bandit، Semgrep، OWASP و ابزارهای مشابه پیشنهاد می‌شود؛ نام بردن ابزار به‌معنی اجرای آن نیست. نسخه، دستور، کامیت، خروجی و نتایج منفی را ثبت کنید.

این سند به‌تنهایی مجوز MIT، قوانین شاخه، کلیدها، اختیار حاکمیتی یا رفتار runtime را تغییر نمی‌دهد. [GOVERNANCE.md](./GOVERNANCE.md) و [AGENTS.md](./AGENTS.md) را ببینید.
