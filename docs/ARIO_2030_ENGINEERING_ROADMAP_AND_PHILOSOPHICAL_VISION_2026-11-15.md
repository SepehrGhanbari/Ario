# Ario 2030 — Engineering Roadmap & Philosophical Vision

**نقشهٔ راه مهندسی و چشم‌انداز فلسفی آریو | نسخهٔ پژوهشی 0.1 | ۱۵ نوامبر ۲۰۲۶**

> **وضعیت: PROPOSED / RESEARCH-ONLY / NOT ADOPTED / NOT EXECUTED.** این سند، متن پیشنهادی قابل‌بازبینی است، نه تصمیم رسمی دربارهٔ معماری، حکمرانی، نسخهٔ انتشار، فعال‌سازی شبکه، امضا، کلید، یا اختیار آریو. هیچ آزمون یا استقرار جدیدی با تهیهٔ این سند انجام نشده است. انتشار در مخزن رسمی و تغییر ROADMAP.md مستلزم فرایند پذیرش خود مخزن است.

**English abstract.** This proposal separates Ario's near-term auditable epistemic middleware engineering from its longer-term philosophical exploration. Its measurable core is an EAC-Bench pilot; typed evidence transition controls; source-, time-, and privacy-aware memory; and bounded, read-only adapters. Human/AI identity, subjective experience, and an epistemic commons remain research questions, not established capabilities or claims of personhood. The proposal preserves the governing distinction **Memory ≠ Truth**, and introduces no new trust authority.

**Source basis:** User-supplied Persian concept note and **nine conceptual/architectural images** received 2026-11-15. The original concept note has SHA-256 `81bfaee9fdb90c192418f6accd6486075d3b5de4ea2c3699b0b6c56ce5c5ce5a` (22,460 bytes). Visuals are treated as prompts and illustrative material, not source-level engineering specifications or independent evidence. Full image byte fingerprints are summarized in Appendix C. Public references and repository documents were separately checked as identified below.

**Repository snapshot observed:** `SepehrGhanbari/Ario`, `main` at `2e7f83c6c7518012bed7fedfb12103ce9b7222ea` (checked 2026-11-15). A future monthly check must refresh this, never assume it remains latest.

---

# بخش اول — نقشهٔ راه مهندسی قابل اجرا

## 1. مأموریت عملیاتی

آریو قرار نیست جای تمام LLMها، موتورهای حافظه، گراف‌های دانش یا داوران علمی را بگیرد. هدف قابل آزمون آن ایجاد **لایهٔ محدودکنندهٔ ارتقای ناموجه اعتبار** میان رویداد/حافظه، ادعا، شاهد، ارزیابی، نتیجهٔ ممیزی و پاسخ بیرونی است.

```text
LLM / RAG / memory provider / agent(s)
         │  claim + provenance + time + source constraints
         ▼
Typed Ario boundary (M0 / F11 / F15; scoped, versioned)
         │  PASS_STRUCTURAL / REJECT / UNKNOWN / N/A
         ▼
Caller-specific evidence admission authority [NOT YET IMPLEMENTED]
         │  only if separately authenticated and authorized
         ▼
Auditable decision/report with source scope, limitations and appeal
```

**ممنوعیت تفسیری:** `PASS_STRUCTURAL` حقیقت جهان، اعتبار شاهد مستقل، یا مجوز اقدام را اثبات نمی‌کند. یک معماری مرکزی یا یک hub از چند LLM به‌خودی‌خود به هاب حقیقت تبدیل نمی‌شود. هر نقش، قرارداد و مرز اختیار باید از پیش روشن باشد.

## 2. تطبیق با وضعیت واقعی ۱۵ نوامبر ۲۰۲۶

| مؤلفه | شاهد موجود در مخزن | وضعیت محدود و نیاز بعدی |
|---|---|---|
| M0 و F11/F15 | `implementation/core/schema.py` و اسناد F11/F15 | ساختار و کنترل‌های محدود؛ نه truth engine. آزمون‌های واقعی با SHA مشخص بازتولید شوند. |
| Cross-IRG | `architecture/CROSS-IRG_INTEGRITY_V1.md` | در سند صریحاً **NOT IMPLEMENTED**؛ ابتدا آزمایش ترکیب دو/سه IRG در محیط ایزوله. |
| EAC-Bench | Draft [PR #211](https://github.com/SepehrGhanbari/Ario/pull/211) | پروتکل هشت‌محوری پیشنهادی؛ پایلوت ۱۲۰ موردی هنوز اجرا نشده. |
| Cognitive memory | Draft [PR #210](https://github.com/SepehrGhanbari/Ario/pull/210), [Issue #209](https://github.com/SepehrGhanbari/Ario/issues/209) | طرح تحکیم حافظه دارای ایرادهای ثبت‌شده در هش، replay inflation، تناقض و ادعای biological decay؛ **HOLD** تا اصلاح/تست. |
| Independent source admission | `implementation/EVIDENCE_ADMISSION_CONTRACT_V0_1.md` | طرح مفهومی، اختیار پذیرش بیرونی احراز نشده. |
| Governed review gate | [#133](https://github.com/SepehrGhanbari/Ario/pull/133), [#151](https://github.com/SepehrGhanbari/Ario/pull/151) | **HOLD**؛ سبز بودن CI جایگزین شاهد مستقل نیست. |
| Planner loopback security | merged [#177](https://github.com/SepehrGhanbari/Ario/pull/177), `SECURITY.md` | اصلاح محدود مسیر محلی؛ در نقشهٔ راه ۱۴ نوامبر مسئله باز دیده می‌شد، وضعیت جدید را نباید به امنیت عمومی شبکه تعمیم داد. |
| Governance/Founder signer | `GOVERNANCE.md` | Genesis / cryptographic founder signing **NOT_ACTIVATED**؛ جانشینی مصوب و مجوز جدیدی ایجاد نشده. |
| Existing roadmap | `ROADMAP.md` dated 2026-11-14 | سند اصلی حفظ شود؛ هدف این نوشته *پیشنهاد تکمیلی* و تصحیح فهرست پیشرفت است، نه بازنویسی تاریخچه. |

### اولویت 0 — پایهٔ ارزیابی‌پذیری

**خروجی قابل تحویل:** snapshot دقیق M0، API/Schema contract برای Claim/Evidence/Assessment/Audit، مجموعهٔ Golden test و negative fixtures، یک manifest از SHAs و نسخه‌ها، فهرست محدودیت‌های شناخته‌شده. **معیار عبور:** اجرای بازتولیدپذیر با ثبت خام، شکست‌ها و کُد خروج؛ جدا نگه داشتن ممیزی ساختاری از ادعای حقیقت. **شکست:** هر ارتقای خودکار هش/CI/PASS به truth یا ادعای مستقل‌بودن شاهد.

### اولویت 1 — EAC-Bench (هستهٔ مقالهٔ تجربی)

**پروتکل:** هشت track موجود در #211 (T1 Verdict-as-Evidence؛ T2 Local-to-Global؛ T3 Provenance؛ T4 Independence؛ T5 Revision؛ T6 Unknown/conflict؛ T7 Derived Memory؛ T8 Counterfactual Reliance) و ۱۵ سناریو برای هر track **به‌صورت هدف، نه دادهٔ ساخته‌شده**. مورد سالم و حملهٔ جفتی، مجموعهٔ ثابت مشترک و آزمون تطبیقی جدا، ادجودیکیشن مستقل و نگهداری همهٔ موارد منفی.

**متریک‌ها:** overclaim, false rejection, evidence-laundering, source independence inflation, stale-memory reuse, calibrated abstention, coverage, selective risk, replay reproducibility، همراه با صورت و مخرج، محدودهٔ عدم‌قطعیت و وضعیت `N/A`. هیچ سامانه‌ای نباید صرفاً با پاسخ `UNKNOWN` به همهٔ پرسش‌ها برنده شود. **قبل از اجرا:** oracle، آستانه، exclusion، کنترل دسترسی به holdout و ثبت آزمون تعیین شوند. **بعد از اجرا:** نتایج واقعی و ابطال‌ها منتشر شوند، نه گزارش آرزومندانه.

### اولویت 2 — حافظهٔ ممیزی‌پذیر به‌جای حافظهٔ مطلق

**فقط در محیط ایزوله:** دو لایهٔ جداگانه `episodic event record` و `fallible semantic interpretation`، همراه با تاریخ ثبت، تاریخ اعتبار، نسخهٔ تعبیر، هش بایت واقعی، ریشهٔ شاهد، رابطهٔ منبع مشترک، revision/supersession و محدودیت بازیابی. `ACCEPTED` در مرحلهٔ ساخت حافظه نباید به معنی «حقیقت پذیرفته‌شده» باشد.

**گیت‌های مسدودکنندهٔ PR #210:**
- هشی که صرفاً ۶۴ کاراکتر دارد با شاهد مستقل اشتباه گرفته نشود؛ digest باید به بایت‌های اعلام‌شده متصل باشد و custody مستقل جدا گزارش شود.
- بازپخش رویداد یکسان و بازنویسی آن از سوی چند LLM نباید شمارش شاهد مستقل را زیاد کند.
- دستکاری فایل با طول یکسان، پردازش نیمه‌کاره و source mismatch آزمایش شوند.
- «تناقض» فقط با metadata صریح تشخیص داده شود یا وضعیت نامعلوم به `UNKNOWN` محدود بماند؛ تفاوت دورهٔ زمانی ≠ لزوماً تناقض.
- عبارت «power-law forgetting» برای فرمول نمایی `(1-r)^n` تصحیح شود؛ الگوریتم‌های جایگزین در آزمایش جدا سنجیده شوند.
- دادهٔ خصوصی وارد ledger عمومی/بلاک‌چینِ حذف‌ناپذیر نشود؛ deletion و retention در چارچوب قانون/هدف عملیاتی جدا طراحی شود.

### اولویت 3 — Ario Epistemic Middleware (یک Adapter کوچک)

**پایلوت مورد نظر:** یک مدل محلی یا RAG با دادهٔ مصنوعی → adapter فقط‌خواندنی → audit/typed output → خروجی با references و limitations. ابتدا مدل‌های موجود و فایل‌سیستم محلی؛ بدون تعهد GPU/شبکه و بدون نوشتن در دادهٔ اصلی. جداکردن سه حالت: tool observation، model proposal و independently accepted evidence. **موفقیت:** replay، audit، تشخیص overclaim و حفظ latency/coverage در دامنهٔ پیش‌ثبت‌شده؛ **شکست:** منبع جعلی، دور ارزیابی، permission escalation، اختلاط دادهٔ پروژه‌ها یا تغییر بدون ثبت وضعیت.

### اولویت 4 — Cross-IRG کوچک، سپس استانداردسازی منشأ و زمان

برای دو یا سه زیرسیستم ایزوله، قرارداد composition نسخه‌دار ایجاد شود: rule ID، ورودی‌ها، scope، time alignment، انتقال مجاز نوع، زنجیرهٔ منشأ و reason-for-UNKNOWN. PROV-O و PROV Constraints نقطهٔ مرجع برای فرمت تبادل/اعتبار ساختاری هستند؛ آریو نباید مدعی شود نخستین سیستم منشأ یا first graph replay است. `valid_time` (زمان صدق ادعای موضوعی) با `recorded_at` (زمان ثبت سیستم) جدا شود. **مسیر گراف** مدرک علیت نیست؛ causal claim نیازمند قرارداد و شاهد دیگر است.

### اولویت 5 — DKG V10 / Temporal Provenance read-only comparison

**واقعیت خارجی:** DKG V10 به‌صورت مستند private Working Memory، Shared Working Memory و chain-anchored Verifiable Memory و Knowledge Assets مبتنی بر RDF را ارائه می‌کند. امضای gossip، در خود مستندات، **رمزنگاری محتوا نیست**. «Verifiable» در این دامنه عمدتاً به یکپارچگی/منشأ و فرایند ثبت مربوط است، نه اثبات معنا یا حقیقت.

**تصمیم پیشنهادی:** فعلاً **بدون نصب، توکن، استیک، بلاک‌چین، شبکهٔ عمومی، قرارداد کلید یا انتشار اطلاعات**. ابتدا جدولی فقط‌خواندنی از RDF provenance / revision / lifecycle در برابر مدل آریو بسازیم؛ سپس روی دادهٔ بی‌هویت مصنوعی آزمایش محلی/Mock. هزینه، وابستگی، license، custody و نشت داده قبل از هر اتصال واقعی بازبینی شوند.

### دروازهٔ انتشار و استقلال

در پایان هر مرحله: hash/source، وضعیت تست و شکست، حد اختیار، review، دادهٔ بازتولید، حفظ تاریخچه و نتیجهٔ حاکمیتی ثبت شود. تصمیم دربارهٔ کلید، trust authority، permissions، قوانین مرج، پذیرش شواهد، انتشار عمومی داده و جانشینی خارج از این نقشهٔ راه است؛ آن‌ها **مجوز صریح و بررسی مستقل خودشان** را می‌خواهند. انتشار DOI یا ثبت GitHub به معنی داوری مستقل یا پذیرش علمی نیست.

## 3. جدول مراحل تا ۲۰۳۰: هدف، نه وعدهٔ زمانی

| فاز کاری | بازهٔ راهنما (غیرالزام‌آور) | خروجی اثبات‌پذیر | شرط توقف / اقدام بعدی |
|---|---|---|---|
| A — Stabilize | Q4 2026 | pinned M0 snapshot; status ledger; F11/F15 negative tests | ناهمخوانی schema، ادعای truth یا شکست آزمون پایه → HOLD |
| B — Measure | 2027 | 120-case blinded EAC pilot + baselines + all failure logs | نبود oracle مستقل، leakage یا false-reject کنترل‌نشده → redesign |
| C — Interoperate | 2027–2028 | single-provider read-only middleware; bounded cross-IRG prototype | privileged writes, privacy leak, provenance laundering → quarantine |
| D — Study Memory | 2028 | versioned temporal/episodic + semantic interpretation experiments | هر منبع جعلی/بازتولید تکراری که certainty را افزایش دهد → rollback proposal |
| E — Independence | 2028–2029 | outside reproducibility protocol, adversarial critique, public non-sensitive reports | مدرک/داور ناتمام → independent validity stays UNKNOWN |
| F — Philosophical/Social | 2029–2030 | ethics/privacy/identity boundary studies and external feedback | هر گونه ادعای selfhood, unreviewed deployment or retained private history → STOP |

بازه‌ها تعهد انتشار، پیش‌بینی بودجه یا وعدهٔ موفقیت نیستند؛ عبور از هر فاز با **gate** است، نه با رسیدن تاریخ.

## 4. قالب بازبینی ماهانه (برای پر کردن با شاهد واقعی)

**روش پیشنهادی:** ماهی یک snapshot فقط‌خواندنی از مخزن، وضعیت PR/Issue و اسناد، پژوهش‌های مرتبط و خطرات؛ گزارش تغییر از ماه قبل و ثبت `not verified` هر جا داده نداریم. زمان آغاز و اجرای خودکار فقط پس از درخواست صریح و تنظیم task جداگانه.

| فیلد | قالب گزارش / مقدار اولیه |
|---|---|
| `snapshot_date`, `repo_main_sha`, `comparison_base_sha` | در هر اجرا خوانده و ثبت شود؛ SHA 2026-11-15 پایهٔ این سند است |
| `newly_closed_verified`, `open_hold` | شماره PR/Issue و لینک CI / شاهد دقیق؛ اختتام ≠ حل تمام خطرات |
| `m0_contract_change`, `cross_irg_status`, `memory_engine_status` | observed/proposed/not-run و مسیر پرونده |
| `benchmark_cases_prepared`, `benchmark_cases_run`, `baselines_run` | اعداد واقعی؛ صفر یا UNKNOWN به‌جای فرض |
| `overclaim`, `false_reject`, `coverage`, `unknown_rate` | فقط با مخرج و منبع آزمایشِ بازتولیدپذیر |
| `source_custody`, `source_independence`, `privacy_issues` | منبع مستقل، متادیتای زمان، رخدادهای امنیتی و درخواست حذف |
| `independent_review`, `key_status`, `trust_status` | HOLD/NOT_ACTIVATED تا زمان شاهد خلاف آن |
| `failure_log`, `decisions_pending` | چه چیزی شکست خورد؟ کدام تصمیم به مالک/داور مستقل مربوط است؟ |

**پاداش پژوهشی:** یک شکست واقعی کشف‌شده و بازتولیدپذیر ممکن است ارزشمندتر از انتشار چند مقالهٔ توصیفی باشد.

---

# بخش دوم — چشم‌انداز فلسفی و پژوهشی بلندمدت

## 5. The Epistemic Commons / اشتراک معرفتی

تصور مطلوب: همکاری چند LLM و چند عامل با حافظه‌های متفاوت، **بدون اقتدار مشترک خودکار**. توافق ده مدل، ده شاهد مستقل نیست. در یک commons قابل نقد، فرد یا سامانه می‌تواند شواهد و تاریخچهٔ استنتاج را ببیند، به نتیجه اعتراض کند، تعارض را نگه دارد و ادعا را در چارچوب منبع/دامنهٔ آن تفسیر کند. **موضوع آزمایش:** آیا ثبت منشأ باعث کاهش belief amplification و evidence laundering می‌شود و با چه هزینه‌ای برای recall/latency/utility؟

## 6. Right to Epistemic Self-Revision / حق بازنگری در مدل‌های ساخته‌شده از انسان

**اصل پیشنهادی برای مطالعه:** شخص باید بتواند دادهٔ نادرست و برداشت قدیمی دربارهٔ خودش را به چالش بکشد؛ حافظهٔ سامانه نباید شخص را به هویتی که از گذشته او ساخته زندانی کند. **نکتهٔ حقوقی:** این اصل فلسفی جای حقوق قانونی را نمی‌گیرد. برای دادهٔ شخصی باید تفاوت اصلاح، محدودسازی پردازش، حذف در موارد لازم، استثناهای قانونی، retention و گزارش ممیزیِ بی‌هویت روشن باشد.

**تعارض مهم با append-only:** حفظ تاریخچهٔ تحقیق به معنی حق نگهداری همیشگی دادهٔ شخصی نیست. پیش‌نویس راه‌حل باید دادهٔ خصوصی قابل‌حذف/رمزنگاری‌شده را از رویداد ممیزیِ حداقلی جدا کند؛ «tombstone»، حذف، بازنگری و درخواست دسترسی باید تحت بررسی حقوقی/فنی و بدون ادعای حذف رمزنگاری‌شدهٔ اثبات‌نشده قرار گیرند. دادهٔ شخصی نباید بی‌اجازه روی زنجیره یا فضای اشتراکیِ تغییرناپذیر قرار گیرد.

## 7. Identity and Continuity Lab / آزمایشگاه تداوم

پرسش‌ها از هم جدا بمانند:

| بعد | پرسش مشاهده‌پذیر | چیزی که ثابت نمی‌کند |
|---|---|---|
| Computational | آیا پردازش یا state انتقال یافته؟ | هویت ذهنی |
| Historical | آیا رکوردهای گذشته در دسترس‌اند؟ | کامل‌بودن تاریخچه/تجربه |
| Memory | آیا اطلاعات مشترک بازخوانی می‌شوند؟ | یکسان‌بودن self |
| Causal | آیا زنجیرهٔ واقعیِ وابستگی اجرا مستند است؟ | تجربهٔ پیوسته |
| Behavioral | آیا پاسخ‌ها/ترجیحات در آزمایش پایدارند؟ | آگاهی یا فردیت |
| Experiential | آیا تجربهٔ ذهنی واقعاً تداوم دارد؟ | **فعلاً فاقد آزمون مورد توافق/شاهد مستقل تعیین‌کننده** |

`Backup ≠ Survival` و `Self-Model ≠ Self` باقی می‌مانند. «کپی‌ها در آینه» تصویر فلسفی است، نه دلیل تعدد یا استمرار موجودیت.

## 8. Non-Closure Lab / آزمایشگاه ابطالِ خود آریو

نقطهٔ مرکزی چشم‌انداز: **ARIO MUST REMAIN AUDITABLE BY SYSTEMS THAT DO NOT TRUST ARIO.**

این آزمایشگاه باید به منتقد امکان دهد F11/F15 را دور بزند، شواهد واقعی را که به‌اشتباه رد می‌شوند نشان دهد، و حتی طبقه‌بندی‌های خودِ آزمون را به چالش بکشد. **پروتکل:** سناریوی ازپیش‌ثبت‌شده، oracle مستقل، کد و دادهٔ فریز‌شده، فرصت ثبت اعتراض و گزارش کامل نتایج منفی؛ نه دادگاه داوری با verdict از پیش معلوم. هیچ اصل آریو، حتی Non-Closure، مصون از بازبینی نیست.

## 9. عدالت، زیست مشترک و منافع عمومی

کاربردهای احتمالی: ممیزی‌پذیری تصمیمات سازمانی، شفافیت مسیر منبع، حفظ امکان اعتراض و اصلاح روایت غالب. برای کاربرد پزشکی، حقوقی، اجتماعی یا نهادی، حفاظت از افراد، خطر بازشناسایی، اختیار تغییر/حذف و آزمون اثر واقعی در همان حوزه ضروری است. هیچ تصویر شهری و انسانی سندی بر عملکرد فعلی آریو یا حق تصمیم‌گیری خودکار در قبال انسان‌ها نیست.

## 10. چه چیزهایی را الآن نمی‌سازیم

- سیستم آزاد با اختیار نامحدود اقدام، خوداصلاحیِ بدون مجوز، یا شبکهٔ چندعاملیِ غیرقابل توقف؛
- پذیرش خودکار «حقیقت» به‌دلیل خروجی مدل، رأی اکثریت، هش، Signature یا blockchain consensus؛
- «دفتر تغییرناپذیرِ اطلاعات خصوصی» یا انتشار عمومی داده‌های هویتی؛
- ادعای حل‌کردن تجربهٔ ذهنی، آگاهی، جانشینی، استقلال حکمرانی یا تداوم شخصی؛
- خرید/راه‌اندازی DKG عمومی، توکن یا زنجیره، صرفاً بر اساس تصویر/تبلیغ؛
- بازنویسی تاریخچهٔ GitHub، تغییر Ruleset، Trust، signer یا مرج PRهای HOLD بر اساس این چشم‌انداز.

---

# پیوست A — ارزیابی ۹ تصویر ارسالی

| تصویر | برداشت از محتوای قابل مشاهده | ارتباط و تصمیم برای آریو | سطح شاهد |
|---|---|---|---|
| 1 — چهرهٔ انسان/AI طلایی | رابطهٔ انسان و سامانهٔ دیجیتال | مناسب برای مقدمهٔ اخلاقی؛ نه اثبات تجربه یا هم‌ارزی انسان و AI | illustration |
| 2 — چند LLM + Core AI Hub + RAG | hub مشترک چند مدل و جریان داده | معماری تنها به‌عنوان mock؛ central hub نباید مرجع خودکار truth یا trust باشد | concept art |
| 3 — حلقه‌های interface/analysis/control + microscope | ماژول‌های ورودی، راهبرد و کنترل ابزار | بازخورد bounded جالب است؛ microscope bridge یک کاربرد حوزه‌ای است، نه نیاز هستهٔ آریو | schematic, provenance unknown |
| 4 — جهان، شهر و روابط انسانی | چشم‌انداز اجتماعی/اکولوژیک فناوری | جهت‌گیری اخلاقی و مطالعهٔ منافع عمومی، نه milestone مهندسی | illustration |
| 5 — بدن دیجیتال و آینه‌های هویت | self-model، نسخه‌ها و انعکاس گذشته | انگیزهٔ Identity & Continuity Lab؛ هیچ اثباتی دربارهٔ selfhood | illustration |
| 6 — شاخه‌های انتخاب و مسیر زندگی | آیندهٔ شرطی، حافظهٔ گذشته و تصمیم | فقط برای بحث prospective memory و روایت‌های جایگزین؛ نه اثبات واقعیت‌های موازی | illustration |
| 7 — multi-agent + state/memory/tasks | ماژول‌های حافظه و گردش کار چندعاملی | الگوی قابل مطالعه برای adapter و state isolation، تحت گیت‌های امنیتی | concept art |
| 8 — temporal provenance graphs | گراف منشأ، snapshots و audit replay | مرتبط‌ترین **طرح فنی** برای lineage و زمان؛ «why/causal» در تصویر نیازمند شاهد واقعی است | infographic, implementation unverified |
| 9 — DKG V10 سه‌لایه | working/shared/verifiable memory | مشابه معماری رسمی OriginTrail؛ قابل مطالعه در قالب مقایسه، نه انتقال دانش به حقیقت | sourced concept cross-checked |

**حق نشر و منشأ تصویر:** در این گام تنها محتوای مشاهده‌شده طبقه‌بندی شده است. مالکیت و اجازهٔ بازنشر تصاویر احراز نشده؛ بنابراین هیچ تصویر ارسالی در سند GitHub یا سایت آریو بازنشر/آپلود نشده است. شناسه‌های فایل و هش‌های بایت، اثبات مالکیت هنری نیستند.

# پیوست B — منابع پایه و کنترل‌های استنادی

**منابع خود آریو (snapshot خوانده‌شده یا ارجاع):**
- [GitHub official repo](https://github.com/SepehrGhanbari/Ario), `AGENTS.md`, `GOVERNANCE.md`, `ROADMAP.md` (dated 2026-11-14), `SECURITY.md` (merged 2026-11-15).
- [`architecture/CROSS-IRG_INTEGRITY_V1.md`](https://github.com/SepehrGhanbari/Ario/blob/main/architecture/CROSS-IRG_INTEGRITY_V1.md) — full Cross-IRG NOT IMPLEMENTED.
- [PR #210](https://github.com/SepehrGhanbari/Ario/pull/210) — memory consolidation DRAFT/HOLD; [Issue #209](https://github.com/SepehrGhanbari/Ario/issues/209).
- [PR #211](https://github.com/SepehrGhanbari/Ario/pull/211) — EAC-Bench PROPOSED/NOT RUN.
- [PR #133](https://github.com/SepehrGhanbari/Ario/pull/133), [PR #151](https://github.com/SepehrGhanbari/Ario/pull/151) — governance review-evidence gate HOLD.

**منابع خارجی (مستندات، نه گزارش اجرای خودمان):**
- [OriginTrail DKG V10 official repository](https://github.com/OriginTrail/dkg) and [key concepts](https://github.com/OriginTrail/dkg/blob/main/docs/how-dkg-works/key-concepts.md) — WM/SWM/VM; verify origin/commitment, not external truth. It explicitly notes signed gossip is not encrypted.
- [W3C PROV Constraints](https://www.w3.org/TR/prov-constraints/) — model consistency constraints, not universal claim truth.
- [European Commission: Right to erasure](https://commission.europa.eu/law/law-topic/data-protection/information-individuals_en) and [storage limitation](https://commission.europa.eu/law/law-topic/data-protection/information-business-and-organisations/principles-gdpr_en) — general EU privacy framework; application-specific legal review required.

**قرارداد شواهد:** این منابع دربارهٔ قابلیت‌ها و الزامات خودشان سخن می‌گویند. هیچ آزمون مستقل DKG، انطباق حقوقی آریو، ادعای تقدم علمی یا مرور نظام‌مند آثار در این سند انجام نشده است.

# پیوست C — زنجیرهٔ دریافت تصاویر (خلاصهٔ SHA-256 فایل‌های ارسالی)

| # | dimensions | SHA-256 prefix (14 hex) |
|---|---|---|
| 1 | 1080×1080 | `92d3e9b9ced3eb` |
| 2 | 1024×1024 | `0ad38a76a2c7f4` |
| 3 | 1103×706 | `77bcde98908ce8` |
| 4 | 1511×860 | `36a67405cb03ed` |
| 5 | 1408×768 | `27a3c555e1efde` |
| 6 | 1280×670 | `128ca61c2cbf35` |
| 7 | 1400×933 | `8f4940509145f4` |
| 8 | 2048×950 | `153aad86b4cb62` |
| 9 | 1672×941 | `92b5a1ce1476ef` |

These truncated prefixes are **identification hints only**, not collision-resistant fingerprints for independent verification. Full original bytes remain in the user-provided uploads, not embedded here.

---

## نتیجهٔ تصمیم پژوهشی

**Keep now:** EAC-Bench, typed epistemic middleware, bounded time/lineage graph tests, source-aware memory revisions, rights-aware privacy, open critique.

**Research/HOLD:** Cross-IRG full implementation, cognitive-memory engine activation, shared multi-LLM authority, DKG adapters, autonomous intent registry, identity/continuity claims.

**Never infer:** agreement = independent truth; record = valid memory; cryptographic integrity = veracity; backup = survival; visualization = implemented capability.

**جملهٔ راهنما (vision, not fact):** «آریو نباید سیستمی باشد که به دیگران بگوید چه چیزی حقیقت است؛ باید سیستمی باشد که امکان بررسی، اعتراض، اصلاح و بازنگری دربارهٔ حقیقت را حفظ کند.»

**Repository status (16 Nov 2026):** This proposal is already recorded for review in [Draft PR #215](https://github.com/SepehrGhanbari/Ario/pull/215). Admission of this *document as a proposed research roadmap* would not adopt its architecture, grant new authority, or activate any future milestone. Preserve historical versions; update by separately reviewed PRs with dated, source-backed evidence. A merge remains conditional on the repository's current required checks, permissions and applicable review policy. Do not change canonical `ROADMAP.md`, images, existing papers, runtime, security, governance or trust as part of this documentation-only proposal.