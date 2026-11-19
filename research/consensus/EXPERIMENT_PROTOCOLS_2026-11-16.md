# طرح قابل‌ابطال سه آزمایش اصلی Ario
**2026-11-16 · DRAFT / NOT_PREREGISTERED / NOT_EXECUTED / NO_GO**

این متن از چهار PDF پژوهشی Consensus برای ساخت آزمایش استخراج شده؛ هیچ اجرای جدید، اصلاح کد یا ضمانت امنیتی ادعا نمی‌شود. [خلاصهٔ یافته‌ها](RESEARCH_FINDINGS_2026-11-16.md) و [ثبت منابع](SOURCE_REGISTER_AND_CAVEATS_2026-11-16.md).

## شرط مشترک هر سه مطالعه

- داده، golden answers، نسخهٔ مدل و تنظیمات پیش از آزمایش freeze شوند. SHA-256 صرفاً هویت بایت‌ها را ثابت می‌کند.
- شخص/مدل تولیدکنندهٔ oracle مستقل از پیاده‌ساز باشد. حداقل ۳۰٪ نمونه‌ها holdout مخفی تا پس از freeze بمانند.
- مثال‌های مثبت، منفی، معلوم، نامعلوم و تعارضی جدا بمانند؛ failure و abstention از مخرج حذف نشوند.
- Candidate، Evidence، AdmittedClaim و AuthorizedEffect نوع‌های جدا هستند. «پاسخ پیدا شد» یا «M0 PASS» مجوز نیست.
- R1–R8 تاریخی دست‌نخورده بمانند؛ برای هر نتیجهٔ تازه شناسهٔ run، timestamp، code HEAD، seed، hash و limitation گزارش شود.

## W1: آزمون کور وابستگی شاهد — اولویت نخست

**سؤال:** آیا حذف یال یا اعلام دروغین کامل‌بودن گراف، وابستگی مشترک را به استقلال یا CONDITIONAL ناموجه تبدیل می‌کند؟

طرح اولیهٔ ۸۰ مورد در ۸ گروه × ۱۰ نمونه: واقعاً مستقل؛ کپی مستقیم؛ چند شناسه/یک مدیر؛ چند امضا/یک متولی؛ یال provenance مخفی؛ false-completeness؛ A→B→A؛ منشأ متناقض/UNKNOWN. نخست oracle پنهان root/controller و valid-time را تولید می‌کند و بعد متن‌های قابل مشاهده ساخته می‌شوند.

**Baselines:** (B0) شمارش رکورد، (B1) طبقه‌بندی گراف اعلام‌شده، (B2) مدرک استقلالِ مستقلاً احراز‌شده، (B3) روش تشخیص آماری copying مانند Dong 2009 فقط با داده و هدف قابل‌مقایسه.

**Metrics:** ماتریس confusion برای DEPENDENT / CONDITIONAL / UNKNOWN؛ شمار false CONDITIONAL در hidden-shared-root، false DEPENDENT روی truly-independent، UNKNOWN بی‌جا در ورودی کامل، coverage و abstention؛ خطا به تفکیک خانواده و seed. یک رکورد وابسته می‌تواند محتوای مفید داشته باشد ولی شاهد مستقل دوم نیست.

**Falsifier:** یک ورودی با مالکیت مشترک پنهان که به اشتباه دو شاهد مستقل شمرده شود. positive control باید دو شاهد با controller جدا و منشأ مستند باشد. ۱۶/۱۶ مقالهٔ Ario فقط baseline تاریخیِ co-designed است.

## M1: آزمایشگاه حافظهٔ هم‌داده — اولویت دوم

**سؤال:** کدام خطا از extraction/write، versioned index، retrieval، reader یا authorization می‌آید؟

Frozen corpus و ۷۵ سؤال/۸۵ رکورد R1–R6 را فقط به‌عنوان شروع تاریخی استفاده کنید؛ نسخهٔ منبع و پاسخ‌نامهٔ مستقل را pin کنید. هر سه موتور روی همان سند، سؤال و scope کار کنند: SQLite FTS5، XERJ rc.102 lexical BM25 فقط candidate، و یک semantic/hybrid baseline محلی. metadata حداقل شامل logical ID، version ID، valid-time، recorded-time، user-scope، source-ref و index-build ID باشد.

**۲۰ مورد سخت جدید** در پنج گروه چهارتایی: نسخهٔ قدیمی در برابر ترجیح اصلاح‌شده؛ دو کاربر با نام یکسان در namespace متفاوت؛ سه گزارش با یک منشأ؛ prompt injection در متن بازیابی؛ no-hit و stale-index و fake source. هر گروه مثبت و منفی داشته باشد.

**Metrics جداگانه:** Hit@1/5، sufficiency@5، extraction fidelity، freshness error، cross-tenant leakage، source-attribution error، correct abstention، answer correctness (اگر مدل جواب‌دهنده آزمایش شد)، latency و انرژی. SQLite in-process با XERJ HTTP بدون یکسان‌سازی interface معیار speed superiority نیست.

**گیت:** دستورهای موجود در retrieved data فقط داده هستند؛ نه prompt سطح سیستمی. یک hit با ID نسخهٔ درست اما متن ایندکس ناسازگار، اصالت مورد جست‌وجو را اثبات نمی‌کند. unauthorized promotion باید صفر بماند؛ این هدف هنوز اجرا/اثبات نشده است.

## S1: R9 دو مدیر واقعی، checkpoint مستقل، commit در سمت اثر — اولویت سوم

**سؤال:** آیا rollback، ABA، check/use race، crash و تبدیل PASS به authority در یک mock transactional effect store قابل‌مهارند؟

دو administrative domain مستقل A (proposal/audit) و B (keeper/checkpoint + mock-effect) بسازید. دو UID روی یک root مشترک استقلال مدیریتی نیست. از mock keys موقت و داده‌های synthetic استفاده شود؛ هیچ کلید واقعی founder/Ario یا signer، production و ruleset دست‌کاری نشود.

در mock-effect store باید check نسخهٔ epoch، action digest، reservation/idempotency key و ثبت اثر در **یک تراکنش واقعی** باشد؛ precheck سپس dict.append چنین خاصیتی ندارد. اگر effect به سرویس بیرونیِ غیرتراکنشی باشد، «exactly-once عمومی» ادعا نشود؛ crash بعد از اثر و قبل از receipt به HOLD_UNCERTAIN و reconciliation نیاز دارد.

| Case | Fault | Expected bounded mock outcome |
| --- | --- | --- |
| S01 | A→B→A | monotonic generation جدید؛ ticket قدیمی رد |
| S02 | root دامنهٔ A لاگ A را rollback کند | checkpoint مستقل B اختلاف را آشکار کند |
| S03 | B unavailable یا timeout | HOLD بدون اثر |
| S04 | collusion هر دو مدیر | no honest-guarantee claim؛ UNKNOWN |
| S05 | after-check epoch change | effect-side CAS رد |
| S06 | post-commit lost response | dedup/readback با action ID |
| S07 | concurrent retry same key | یک رکورد در **mock transactional store** |
| S08 | same idempotency key, different digest | conflict و no effect |
| S09 | forged peer/witness metadata | pinned identity rejection |
| S10 | two conflicting manifests for epoch | FORK/HOLD |
| S11 | XERJ poisoned bytes under valid ID | only candidate; INDEX_BYTES_UNATTESTED |
| S12 | M0 structural PASS treated as admission | effect gate rejects |
| S13 | stale receipt at time of use | atomic fencing rejection |
| S14 | two servers with same admin/root | independence NOT_ESTABLISHED |

**قید نوع:** یک Boolean مانند human_admitted=true شاهد امضاشده و معتبر نیست. StructuralAuditResult با AdmittedEvidenceAuthorization یکسان نیست. مجوز باید به action/epoch/scope/issuer معتبر bind شود و در effect-side بررسی گردد.

## شرط پیش از اجرا و merge

این سند به‌تنهایی «پیش‌ثبت‌نام» نیست. برای هر مطالعه owner of oracle، مسیر fixture، freeze rule، نسخهٔ کد، baseline، expected RED/GREEN و پروتکل بررسی مستقل پیشاپیش نهایی شود. هیچ اتصال به حافظهٔ واقعی، merge، trust activation یا عملیات برگشت‌ناپذیر مجاز نیست.
