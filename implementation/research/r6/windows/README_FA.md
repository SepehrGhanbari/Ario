# آریو R6-B — بستهٔ قابل‌انتقال بین دسکتاپ و لپ‌تاپ (Windows / PowerShell 5.1)

**پژوهشی و دورریختنی: `RESEARCH_ONLY / NOT_ADOPTED / DRAFT / HOLD / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`.**

این بسته برای **دو دستگاه واقعی بدون Desktop Commander، بدون Python cryptography، بدون دسترسی Administrator و بدون Windows Sandbox** طراحی شده است. روی Windows PowerShell داخلی ویندوز، امضای RSA-2048/SHA-256 را فقط روی بایت‌های ساختگی بررسی می‌کند. همهٔ داده‌ها آزمایشی‌اند. **در این نسخه هیچ کلید واقعی آریو یا سرویس بیت‌کوینی/Sigsum استفاده نمی‌شود.**

## مشخصات مشاهده‌شدهٔ دو دستگاه

| دستگاه | سیستم | Python | cryptography | VirtualizationFirmwareEnabled |
| --- | --- | --- | --- | --- |
| لپ‌تاپ؛ نگهدارندهٔ آزمایشی C | Windows 10 Pro Build 19045 | 3.15.0 | missing | False |
| دسکتاپ؛ اجراکنندهٔ آزمایشی E | Windows 10 Pro Build 19045 | 3.13.14 | missing | True |

این آزمایش به Python و مجازی‌سازی نیازی ندارد. روی لپ‌تاپ به Sandbox تکیه نکنید و BIOS/Hyper-V را تغییر ندهید.

## فایل‌های بسته

- `R6-Windows-Portable.ps1`: اسکریپت تنها برای `Make / Inspect / Revoke / Status`.
- `README_FA.md`: همین دستورها.

کد در مسیر آزمایشگاهی `implementation/research/r6/windows/` است. **قبل از اجرا فایل را از همان PR/commit بررسی کنید.** برای راحتی، GitHub Actions نسخه‌ای از دو فایل را به‌صورت یک ZIP عمومیِ فاقد کلید منتشر می‌کند. ZIP بستهٔ اسکریپت با ZIP رسیدِ ساختگی که بعداً تولید می‌شود **متفاوت** است.

## مرحلهٔ ۱ — دسکتاپ E

بستهٔ منتشرشده را به `Downloads/Ario-R6-Windows-Lab` استخراج کنید. PowerShell **معمولی** (نه Run as administrator) باز کنید:

```powershell
$script = Join-Path $env:USERPROFILE 'Downloads\Ario-R6-Windows-Lab\R6-Windows-Portable.ps1'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$script" -Mode Make
```

`-ExecutionPolicy Bypass` فقط برای همین فرایند جدید PowerShell است، تنظیم امنیتی سراسری ویندوز را تغییر نمی‌دهد. **فقط پس از تطبیق فایل با منبع رسمی همین PR اجرا شود.** خروجی JSON باید `reason_code=SYNTHETIC_BUNDLE_CREATED` بدهد، به‌همراه `public_key_sha256` و `bundle_path`.

این دستور کلید **کاملاً جدید و ساختگی** در `%LOCALAPPDATA%\Ario-R6-Windows-Test-v1` می‌سازد. آن کلید **هیچ ارتباطی با کلید آریوی واقعی ندارد**. فایل `executor-private-test-only.xml` صرفاً کلید خصوصی همین آزمایش است و نباید از دسکتاپ خارج شود.

**فقط فایل `R6-public-handoff-<nonce>.zip` داخل `bundle_path` را** با فلش، یک پوشهٔ اشتراکی امن یا انتقال دستی به پوشهٔ Downloads لپ‌تاپ ببرید. ZIP فقط `r6-public.xml` و `r6-receipt.json` دارد؛ کلید خصوصی ندارد. از کپی‌کردن پوشهٔ کامل آزمایش خودداری کنید.

## مرحلهٔ ۲ — لپ‌تاپ C

همان بستهٔ اسکریپت را روی لپ‌تاپ هم در Downloads استخراج کنید. فایل `R6-public-handoff-*.zip` را از دسکتاپ به Downloads لپ‌تاپ بیاورید. در PowerShell معمولی:

```powershell
$script = Join-Path $env:USERPROFILE 'Downloads\Ario-R6-Windows-Lab\R6-Windows-Portable.ps1'
$bundle = Get-ChildItem -Path (Join-Path $env:USERPROFILE 'Downloads\R6-public-handoff-*.zip') |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$script" -Mode Inspect -BundleZip "$bundle"
```

انتظار: `reason_code=SYNTHETIC_RECEIPT_RECORDED` و `record_count=1`. **هش `public_key_sha256` لپ‌تاپ باید با هش خروجی دسکتاپ حرف‌به‌حرف یکی باشد.** این تطبیق دستی فقط تناقض را پیدا می‌کند؛ چون یک نفر دو دستگاه را اداره می‌کند، به معنی تأیید مستقل هویت نیست.

دوباره **همان دستور Inspect روی همان ZIP** را بزنید. انتظار: `reason_code=REJECT_REPLAY_NONCE` و `record_count=1`، بدون تغییر head.

برای مشاهدهٔ وضعیت نگهدارنده، بدون تغییر:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$script" -Mode Status
```

**فعلاً `-Mode Revoke` را اجرا نکنید** تا ابتدا رسید مثبت و رد تکرار ثبت شود؛ ابطال برگشت‌ناپذیرِ همین هویت آزمایشی است و بعد از آن رسید جدید از همان کلید پذیرفته نمی‌شود. این هیچ تأثیری بر کلید واقعی آریو ندارد.

## چه چیزی را برای بازبینی بفرستید؟

فقط `reason_code`, `record_count`, `head_sha256`, و `public_key_sha256` خروجی مرحلهٔ E و C را بفرستید. مسیرهای شامل نام کاربری، XML خصوصی، داده‌های شخصی، رمزها، اصل پوشهٔ آریو و کلیدهای واقعی را نفرستید. اگر نیاز شد، می‌توانید **فقط ZIP عمومی رسید ساختگی** را نیز برای بازبینی بارگذاری کنید.

## مرز ادعاها

- آزمون اولیه در **Windows GitHub Actions روی یک runner واحد** انجام می‌شود؛ موفقیت آن اثبات نمی‌کند این دو کامپیوتر فیزیکی به‌درستی کار کرده‌اند.
- اولین بار کلید عمومی C از **همان ZIP ارسالی E** وارد می‌شود: `SELF_PINNED_SYNTHETIC`، نه هویتِ از مسیر بیرونی تأییدشده. تطبیق هش بین دو دستگاه نباید به استقلال مدیریتی ارتقا یابد.
- `C-synthetic-history.jsonl` فقط محلی و قابل‌دست‌کاری توسط مدیر همان دستگاه است. قفل فایل، نگهداری همزمان یا `Flush(true)` برابر با لاگ واقعاً append-only یا ضد rollback نیست. پاک‌کردن داده‌ها یا برگرداندن هر دو وضعیت C و پین هنوز می‌تواند باعث بازپخش شود.
- هیچ آزمون `EACCES` بین دو سیستم‌عامل Windows در این بسته اجرا نمی‌شود؛ ارتباط با شبکه، اتوماسیون، رمزنگاری هویت مستقل، ابطال بیرونی و ساعت مستقل **NOT_ESTABLISHED** باقی می‌ماند.
- کلید RSA این آزمایش در پوشهٔ موقت کاربردیِ کاربر ذخیره می‌شود و **غیرقابل‌استخراج سخت‌افزاری نیست**؛ به‌هیچ‌وجه یک آرایش امنیتی تولیدی محسوب نمی‌شود.
- هیچ مسیر اتصال به `SourceMonitoringGuard`, `ConsolidationEngine`, `ProspectiveMemoryRegistry`, امضاکننده، Genesis یا فعال‌سازی اعتماد وجود ندارد.

**تمام خروجی‌ها همیشه `evidence_admission_allowed=false`, `memory_write_allowed=false`, `signing_authority_allowed=false`, `trust_activation_allowed=false` هستند.**

اصل: **`MEMORY != TRUTH / CLAIM != PROOF / REVIEWABLE != AUTHORIZED`.**
