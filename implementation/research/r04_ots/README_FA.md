# آریو R04 — آرشیو قابل‌بررسی رسید OpenTimestamps

**وضعیت:** `RESEARCH_ONLY / SYNTHETIC / PENDING_BITCOIN / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`

**منبع اولیه:** [Issue #280](https://github.com/SepehrGhanbari/Ario/issues/280) و [رسید ثبت‌شده](https://github.com/SepehrGhanbari/Ario/issues/280#issuecomment-6990276287). آزمایش قبلی RERE-01 به commit `7e1891abbe3532da7fdb1f1c1ea4daa4997f6156` اشاره دارد؛ این PR هیچ کدی از حافظهٔ اصلی را عوض نمی‌کند.

## خلاصهٔ قابل‌فهم

**چه کاری واقعاً انجام شد؟** در ۱۸ نوامبر ۲۰۲۶ یک چک‌پوینت کاملاً ساختگی ۶ رکوردی به سه تقویم عمومی OpenTimestamps ارسال شد؛ فایل رسید واقعی `.ots` با ۳ مسیر `PendingAttestation` دریافت شد. فایل JSON اصلی و تمام بایت‌های رسید در همین PR قرار دارند؛ صرفاً گزارش یا روایت نیستند.

**هنوز چه چیزی ثابت نشده؟** هیچ تأیید نهایی در بلاک بیت‌کوین ثبت و بررسی نشده است. در بازبینی تازه با نسخهٔ رسمی `opentimestamps-client==0.8.0` هر سه تقویم همچنان `Pending confirmation in Bitcoin blockchain` گزارش کردند؛ `verify` و `upgrade -n` کد خروج ۱ داشتند. داشتن سه تقویم نیز به معنای سه مدیر مستقل نیست.

**مسئلهٔ اصلی حافظه:** وقتی وضعیت قبلی ۶ رکوردی را یک نگهدارندهٔ واقعاً بیرونی حفظ کرده باشد، بازگردانی تاریخچه به ۴ رکورد قابل رد است. اگر همان ناشر بتواند تاریخچه و «آخرین وضعیت ثبت‌شده» را با هم عوض کند، صرف هش و مقایسهٔ شماره کافی نیست. OpenTimestamps بعد از تکمیل فقط می‌تواند به اثبات وجود یک تعهد در گذشته کمک کند؛ نمی‌گوید کدام نسخه آخرین/کامل‌ترین است.

## فایل‌ها

- `synthetic_checkpoint_r04.json`: اصل پروندهٔ ۶۱۳ بایتی (SHA256: `c37da68d045da9c85a90dc679857c017ed0bbd1454e51d9033ef9a48e799a68a`).
- `synthetic_checkpoint_r04.ots.b64`: رسید واقعی ۵۴۹ بایتی در قالب Base64 متن (SHA256 باینری: `5b7fc36d470560adbc8fd4620436451ea43ea0578bf50e7ca6104ce0280c3bf6`). صرفاً به دلیل امکان افزودن پروندهٔ متنی به GitHub است.
- `manifest.json`: هش‌ها، منشأ و محدودیت‌های ادعاها.
- `verify_r04.py`: ممیز تنهاخواندنی با کتابخانهٔ استاندارد پایتون؛ **خروجی `EXACT_ARCHIVED_BYTES_MATCHED` فقط به معنای تطابق بایت‌های آرشیو است، نه اثبات بیت‌کوین.**
- `implementation/tests/test_r04_ots_archive.py`: ۱۷ تست مثبت و منفی، شامل دستکاری فایل، رسید، rollback، جعل استقلال شاهد، split view و نبود floor.
- `REVIEW_EN.md`: دستور بازبینی برای همکاران دیگر.
- `LIVE_RECHECK_2026-11-18.md`: خروجی بررسی مجددِ واقعی، همچنان `PENDING`.

## راه بازتولید

از ریشهٔ مخزن:

```bash
python implementation/research/r04_ots/verify_r04.py
cd implementation
python -m pytest -q tests/test_r04_ots_archive.py
```

برای بازسازی فایل `.ots` بدون اتصال شبکه:

```python
import base64
from pathlib import Path
folder = Path("implementation/research/r04_ots")
proof = base64.b64decode((folder / "synthetic_checkpoint_r04.ots.b64").read_bytes())
(folder / "synthetic_checkpoint_r04.json.ots").write_bytes(proof)
```

پس از نصب کلاینت رسمی OpenTimestamps در **محیط آزمایشی**، در همان پوشه:

```bash
ots info synthetic_checkpoint_r04.json.ots
ots verify -f synthetic_checkpoint_r04.json synthetic_checkpoint_r04.json.ots
ots upgrade -n synthetic_checkpoint_r04.json.ots
```

گزینهٔ `-n` در دستور upgrade نسخهٔ اصلی رسید را تغییر نمی‌دهد. پیش از هر ارتقای غیرآزمایشی، نسخهٔ سالمِ اولیه را جداگانه نگه دارید. برای اثبات مستقل بیت‌کوین، ارزیابی معتبر بلاک/هدر لازم است؛ صرف پاسخ تقویم یا خروجی `ots info` کافی نیست. مستند رسمی: https://github.com/opentimestamps/opentimestamps-client

### نکتهٔ بایت‌به‌بایت در ویندوز

اجرای نخست GitHub Actions روی ویندوز، با وجود PASS لینوکس، چهار تست را به‌خاطر تبدیل خودکار LF به CRLF در فایل JSON رد کرد. به‌جای پذیرش یا نرمال‌سازی بی‌صدا، فقط در همین پوشه، `.gitattributes` برای فایل اصلی `-text` تنظیم شد تا Git دقیقاً همان ۶۱۳ بایت تاریخی را تحویل دهد. دو تست جدید این مرز را بررسی می‌کنند: بایت‌های صحیح باید PASS شوند و نسخهٔ CRLF باید REJECT شود. اجرای نخستین شکست در [CI RED #44391355514](https://github.com/SepehrGhanbari/Ario/actions/runs/44391355514) ثبت و بدون پاک‌کردن سابقه نگه‌داری شده است. اجرای اصلاح‌شده در [CI #44391716450](https://github.com/SepehrGhanbari/Ario/actions/runs/44391716450) روی Linux و Windows **SUCCESS** شد؛ تا زمان تأیید دوبارهٔ همین README، مقدار SHA نهایی PR باید جداگانه کنترل شود.

## چک‌لیست برای بازبین

۱. آیا فایل JSON و رسیدِ decodeشده با SHA256 اصلی و کامنت Issue #280 دقیقاً تطبیق دارند؟  
۲. آیا تغییر حتی یک بایت از هر کدام توسط آزمون رد می‌شود؟  
۳. آیا اثبات **واقعاً** به یک بلاک معتبر بیت‌کوین رسیده، یا هنوز Pending است؟ شمارهٔ بلاک، زمان بررسی و منبع داده را ثبت کنید.  
۴. آیا مرجعِ نگهداری `last_seq + hash` از اختیار ناشر بیرون است، و هویت و محل نگهداری‌اش واقعاً مستقل آزمایش شده؟ **فعلاً خیر.**  
۵. اگر ناشر بتواند هم تاریخچه و هم مرجع خودش را عقب ببرد، آیا ادعای ضد rollback رد می‌شود؟ **بله؛ در آزمایش منفی قابل بازتولید است.**  
۶. آیا قطع شبکه، fork، گم‌شدن پاسخ، تغییر/ابطال کلید و بازگردانی وضعیت شاهد با نگهداری مستقل آزموده شده؟ **هنوز خیر.**

**نتیجه:** فقط بستهٔ پژوهشیِ بازبینی‌پذیر؛ هیچ تغییر در `main`، حافظهٔ تولید، signer، Genesis یا قواعد اعتماد و هیچ مجوز مرجی ایجاد نمی‌کند.
