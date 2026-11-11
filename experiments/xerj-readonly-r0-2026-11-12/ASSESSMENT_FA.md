# ARIO × XERJ: ارزیابی فنی و نمونهٔ اتصال فقط‌خواندنی R0

**تاریخ:** ۱۲ نوامبر ۲۰۲۶  
**وضعیت:** `RESEARCH_ONLY` — `PROTOCOL_MOCK_TESTED` — `LIVE_XERJ_NOT_EXECUTED` — `NO_GOVERNANCE_CHANGE`  
**نسخهٔ بررسی‌شدهٔ XERJ:** `xerj-org/xerj`، `main` روی Commit `50e4ffded5518b1822cfac5450fa34d3829ab8ab`  
**نسخهٔ بررسی‌شدهٔ Ario:** `SepehrGhanbari/Ario`، `main` روی Commit `4731c912ba4b34b302843dd37067822ffb699ba7`.

## خلاصهٔ اجرایی

XERJ می‌تواند یک **بازیاب کاندیدِ قابل‌تعویض** برای آریو باشد، نه حافظهٔ معتبر یا داور مستقل حقیقت. در مخزن XERJ موتور Rust، جست‌وجوی BM25/برداری/ترکیبی، ES-compatible API، MCP، جست‌وجوی دسته‌ای، بازیابی قطعهٔ سند و API حافظهٔ عامل مستند شده است. به‌دلیل تفاوت حاکمیت و منشأ، هیچ‌کدام از نتیجه‌های بازیابی نباید به تأیید Evidence، Assessment یا امضای آریو ارتقا یابد.

**کاری که واقعاً انجام شد:** مستندات، ساختار مخزن و چند فایل مرتبط در GitHub خوانده شد؛ یک کلاینت صرفاً خواندنی Python stdlib نوشته شد؛ ۲۶ تست خودنویس (شامل آزمون با سرور HTTP ساختگی روی loopback) موفق شد. **موتور واقعی XERJ نصب، اجرا یا بنچمارک نشد**؛ ۲۶ تست اثبات سازگاری با نسخهٔ واقعی، امنیت عملیاتی یا بهبود عملکرد نیستند.

## اولویت‌های پیشنهادی برای آریو

| اولویت | قابلیت XERJ | کاربرد آریو | خطر/شرط |
|---|---|---|---|
| P0 | جست‌وجوی BM25، hybrid و ES-compatible `_search` | فهرست‌سازی کپی از منابع و بازیابی محدود `source_id` | کلید فقط‌خواندنی، پاسخ صرفاً کاندید، منبع حقیقت داخل آریو |
| P1 | `batch-search` و MCP | استفادهٔ مشترک آوا/عوامل از چند جست‌وجو با شناسهٔ منبع و سقف خروجی | MCP ورودی دستور نیست؛ کنترل بودجه و خطاهای جزئی |
| P1 | passage-level search و `autoindex` | یافتن بخش‌های مرتبط در مقالات و مستندات حجیم، بدون خوراندن تمام متن به Qwen | ریشهٔ سند، offset و هش باید در آریو دوباره چک شود؛ حریم خصوصی و بازنویسی ایندکس |
| P1 | reference coding | کمک به یافتن راه‌حل‌های شناخته‌شده هنگام رفع PRهای Ario، شاید مصرف توکن کمتر | ادعاهای کاهش توکن XERJ را مستقلاً بازتولید نکردیم؛ کد بازیابی‌شده دستور یا مدرک امنیتی نیست |
| P2 پژوهشی | `/_facts` و XERJ Query-1 | مطالعهٔ اجرای پرسش‌های ساختاری با `UNKNOWN` / `CONFLICT` و ارجاعِ span | مدل Query-1 بنا بر README کاملاً متن‌باز نیست؛ نتایج اعلامی روی مجموعهٔ توسعه‌ای؛ برای شمارش برخی خروجی‌ها صرفاً hash برنامه است |
| HOLD | `/_memory` حذف/فراموشی و `_decide` ذخیرهٔ خودکار پیش‌بینی | درون حافظهٔ رسمی یا دروازهٔ شواهد **استفاده نشود** | حافظه ≠ حقیقت؛ بازنگری ≠ پاک‌کردن؛ خودتأییدیِ حلقهٔ write-back |

## مرز با کد واقعی آریو

در `implementation/ario_planner.py` محدودیت‌های `MAX_CONTEXT_FILES=4` و `MAX_CONTEXT_TOTAL_CHARS=16000` دیده شد. XERJ می‌تواند در مرحلهٔ **قبل از planner**، تنها فهرست شناسه‌های مرتبط را پیدا کند؛ سپس Ario خودش متن اصلی، محدودیت تعداد فایل، هش و منبع آن‌ها را بخواند. نباید به‌طور خام به planner دسترسی نامحدود به شبکه یا فایل داده شود.

`implementation/ario_agent.py` فعلاً ابزار جست‌وجوی شبکه در allowlist ندارد. **این آزمایش هیچ ابزار جدیدی به agent اضافه نکرد.** `implementation/ledger_observation_adapter.py` نیز صریحاً می‌گوید manifest صرفاً مشاهدهٔ بایت‌های ledger است نه حقیقت یا Evidence؛ بازیابی XERJ نباید این قرارداد را تضعیف کند. `GOVERNANCE.md` وضعیت Genesis / signer را NOT_ACTIVATED بیان کرده است.

## طراحی نمونهٔ R0

`ario_xerj_readonly.py` یک درخواست **فقط** `POST /{dedicated_index}/_search` به `http://127.0.0.1:<port>` می‌فرستد. API key از بیرون تأمین می‌شود؛ کلاینت هیچ endpoint نوشتنی، دکمهٔ تأیید یا کد اجرای سند ندارد؛ دنبال redirect نمی‌رود و HTTP proxy استفاده نمی‌کند. پاسخ حداکثر ۲۵۶ KiB، کاندیدها حداکثر ۱۰ و پرسش حداکثر ۴۰۰۰ بایت UTF-8 است. فقط شناسه‌های `_id` که در registry خود آریو وجود دارند پذیرفته می‌شوند و نام `_index` باید دقیقاً مطابق ایندکس باشد. پاسخ‌های ناقص، timeout/shard failure، شناسهٔ ناشناس و digest مغایر علامت‌گذاری می‌شوند.

تمام متن، شناسهٔ ریشه و تاریخ‌ها از **ledger محلی آریو** استخراج می‌شوند؛ نه از `_source` یا snippetهای XERJ. برچسب ریشهٔ متفاوت حتی اگر در ledger موجود باشد اثبات استقلال حقیقی شاهد نیست. خروجی فقط `CANDIDATES_ONLY`، `RETRIEVAL_INCOMPLETE` یا `NO_HITS_UNKNOWN` است؛ همیشه `answer_authorized=false` و `source_independence=NOT_ESTABLISHED` است. این طراحی fail-closed عمداً جلوی تبدیل نتیجهٔ جست‌وجو به «تأیید حقیقت» را می‌گیرد.

## آزمون‌ها و محدودیت‌ها

- **۲۶ از ۲۶** آزمون محلی خودنویس موفق: دست‌کاری snippet، metadata و زمان؛ شناسهٔ ناشناس؛ digest متفاوت؛ root مشترک یا متفاوت؛ index بیگانه؛ timeout؛ خطای shard؛ پاسخ بیش‌ازحد بزرگ؛ redirect و خطای احراز هویت؛ سقف پرسش و فهرست شناسه‌ها.
- HTTP end-to-end فقط با **سرور ساختگی استاندارد پایتون** انجام شد، نه با binary واقعی XERJ.
- آزمایش از وجود یک registry معتبرِ محلی فرض می‌کند. این نمونه صحت ثبت اولیهٔ رکورد در آریو را اثبات نمی‌کند؛ همچنین مهاجم می‌تواند شناسهٔ واقعی ولی نامربوط را در ایندکس برگرداند، پس داوری دربارهٔ ارتباط و استلزام ادعا باید جداگانه باشد.
- محدودیت روی `/_search` فقط رابط آزمایشی را محدود می‌کند؛ به‌تنهایی صلاحیت‌های API key سمت XERJ را اثبات نمی‌کند. در آزمون واقعی باید کلید scoped read-only و محدودیت ایندکس سمت سرور آزمایش شود.
- هر متن استخراج‌شده باید دادهٔ غیرقابل‌اعتماد تلقی شود؛ هیچ tool call یا اجازهٔ عملیاتی از این متن گرفته نمی‌شود.
- داده، خروجی و تست‌های این مرحله خودساخته‌اند؛ هیچ ادعای بنچمارک مستقل عملکرد برای XERJ انجام نشده است.

## امنیت/حریم خصوصی مهم در مستندات XERJ

1. `--insecure` احراز هویت و TLS را غیرفعال می‌کند؛ در شبکهٔ واقعی آریو ممنوع باشد. برای سناریوی توسعه هم فقط محیط دورریختنی و loopback.
2. `/_memory/{ns}` شامل DELETE است؛ برای اصل append-only آریو فقط کپی ایندکس باشد، نه محل نگهداری معتبر تاریخی.
3. طبق docs، حالت embedding پیش‌فرض lexical است، **نه درک عصبی معنایی**؛ مدل neural ممکن است بارگیری داشته باشد. rerank proxy و WAL tap تنظیم‌شده می‌توانند داده را بیرون بفرستند.
4. `xerj hub pull` و ابزارهای Hub ممکن است بازخورد ساختاری به سرویس بیرونی ارسال کنند، مگر بازخورد غیرفعال شود. در R0 نه Hub pull و نه autoindex یا init اجرا شد.
5. `docs/SNAPSHOT_AND_RESTORE.md` صریحاً می‌گوید restore می‌تواند دایرکتوری ایندکس زنده را **حذف و بازنویسی** کند؛ پس backup آریو یا مسیر بازیابی رسمی نباید به آن وابسته شود.
6. XERJ Engine تحت Apache-2.0 است؛ مجوز MIT آریو جدا باقی می‌ماند. ادغام هر کد متن‌باز کپی‌شده نیازمند حفظ شروط Apache NOTICE/LICENSE است؛ **این نمونه هیچ کدی از XERJ کپی نکرده** و فقط از پروتکل عمومی استفاده می‌کند.

## گام‌های بعدی و معیار پذیرش

**R1: آزمون واقعی دورریختنی** با release پین‌شده، checksum تأییدشده، خروجی شبکهٔ بسته و داده‌های مصنوعی: سناریوهای no-hit، 401، malicious hit، index scope، timeout، restart و reindex. فعلاً انجام نشده. هر binary خارجی باید جداگانه بررسی شود.

**R2: مقایسهٔ برابر** روی دادهٔ عمومی دارای مجوز، با baselineهای BM25، char3-RRF و XERJ، بودجهٔ یکسانِ تعداد سند، توکن واقعی BPE، زمان، CPU/RAM و خطاها؛ بلافاصله بعد از بازیابی، ارزیابی ریشهٔ شاهد و کیفیت استناد. نتیجهٔ `UNKNOWN` و بازیابی ناقص حساب شود.

**R3: بازبینی امنیتی/پذیرش**: تکرار تست‌ها توسط بازبین مستقل، عدم خروج داده، کنترل role-scoped API key، ماندگاری سابقه در Ario، عدم پذیرش امضای جعلی؛ سپس PR آزمایشی جدا. هیچ merge یا trust activation با موفقیت‌های R0 مجاز نیست.

## پیوندهای نسخه‌پین‌شدهٔ مورد بررسی

- XERJ docs: https://github.com/xerj-org/xerj/blob/50e4ffded5518b1822cfac5450fa34d3829ab8ab/docs/ARCHITECTURE.md
- Memory API: https://github.com/xerj-org/xerj/blob/50e4ffded5518b1822cfac5450fa34d3829ab8ab/docs/recipes/agentic-memory.md
- Batch Search: https://github.com/xerj-org/xerj/blob/50e4ffded5518b1822cfac5450fa34d3829ab8ab/docs/recipes/batch-search.md
- Security: https://github.com/xerj-org/xerj/blob/50e4ffded5518b1822cfac5450fa34d3829ab8ab/docs/SECURITY_MODEL.md
- Agent memory benchmark: https://github.com/xerj-org/xerj/blob/50e4ffded5518b1822cfac5450fa34d3829ab8ab/benchmarks/agent-memory/README.md
- Facts: https://github.com/xerj-org/xerj/blob/50e4ffded5518b1822cfac5450fa34d3829ab8ab/docs/FACTS_API.md
- AIR-GAP: https://github.com/xerj-org/xerj/blob/50e4ffded5518b1822cfac5450fa34d3829ab8ab/docs/recipes/air-gapped-deployment.md
- Ario bounded agent: https://github.com/SepehrGhanbari/Ario/blob/4731c912ba4b34b302843dd37067822ffb699ba7/implementation/ario_agent.py
- Ario planner: https://github.com/SepehrGhanbari/Ario/blob/4731c912ba4b34b302843dd37067822ffb699ba7/implementation/ario_planner.py
- Ario ledger observer: https://github.com/SepehrGhanbari/Ario/blob/4731c912ba4b34b302843dd37067822ffb699ba7/implementation/ledger_observation_adapter.py
