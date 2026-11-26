# ثبت منابع و هشدارهای علمی — مطالعات Consensus مربوط به Ario
**2026-11-16 · SOURCE_TRIAGE / PARTIAL_PRIMARY_VERIFICATION / NO_GOVERNANCE_CHANGE**

این فایل راهنمای بازیابی و سنجش اعتبار منابع است، نه مقالهٔ جدید و نه داوری رسمی. از بازنشر متن/شکل‌های دارای حق نشر خودداری شده و به صفحات اولیه ارجاع داده شده است. لینک سه Thread در [برنامهٔ هفت‌روزه](CONSENSUS_7_DAY_PLAN_2026-11-16.md) وجود دارد.

## فایل‌های مبنای دریافت‌شده

| منبع Consensus | صفحات | SHA-256 پیوست |
| --- | ---: | --- |
| Literature for Ario’s Witness-Provenance Study (نام فایل گفت‌وگو: _ (1).pdf) | ۸ | 69d621e417398a6f8a978c2d6ace629fb9ab4eb9985bb3e4f50ac187a771860f |
| Conduct_a_rigorous_source-grounded_scholarly_posi.pdf | ۶ | 9ce47e665673382592ac12b776e883ee33fb17489055efb15eb624af12d66fa1 |
| Research_task_for_Ario_Epistemic_Middleware_memo.pdf | ۱۰ | 9a5651214299f7e0818b7d50982eb73bae0d5d0513d2df2ac5716f3ef34bca6a |
| Research_task_for_Ario_R9_security_evaluate_exter.pdf | ۷ | 23b58d5e79d4d0bdff4271ce3338848dc177fc078547c3d53826fc0ddf21511f |

این هش‌ها هویت **پیوست‌های دریافت‌شده** را ثبت می‌کنند؛ ارزیابی اصالت علمی یا حق انتشار نیستند. PDFها در مخزن GitHub آپلود نشده‌اند.

## کلید اعتبار

- **PRIMARY_METADATA_CHECKED:** عنوان/نویسندگان/DOI یا شناسه و چکیده در سایت اصلی ناشر، کنفرانس، دانشگاه یا arXiv در ۱۶ نوامبر ۲۰۲۶ بررسی شده است. این وضعیت به‌معنی بازاجرای روش یا تأیید علمی شخص ثالث نیست.
- **AUTHOR_ABSTRACT_CHECKED:** منبع نویسنده‌محور/خودمیزبان بررسی شده؛ هنوز بررسی مستقل کامل ندارد.
- **CONSENSUS_ONLY:** صرفاً در گزارش AI آمده؛ پیش از استناد رسمی، DOI، روش و اصل مقاله باید بررسی شود.
- **DESIGN_ANALOGY:** مفهومی مفید از یک زمینهٔ دیگر، ولی baseline مستقیم Ario نیست.
- **ERROR_IN_REPORT:** مثال یا تفسیر نادرست/مغایر با قواعد اولیه؛ کپی نشود.

## ۱۱ منبع اصلی اولویت‌دار

| مقاله و سال | پیوند اصلی/DOI | سطح کنترل | چه چیزی برای Ario مفید است و حدش |
| --- | --- | --- | --- |
| Dong, Berti-Équille, Srivastava, **Integrating Conflicting Data: The Role of Source Dependence** (2009) | [PVLDB / DOI](https://doi.org/10.14778/1687627.1687690) | PRIMARY_METADATA_CHECKED | تشخیص آماری کپی و truth discovery؛ **خودش احراز اصالتِ منشأ اعلام‌شده نیست** |
| Douceur, **The Sybil Attack** (2002) | [Springer DOI](https://doi.org/10.1007/3-540-45748-8_24) | PRIMARY_METADATA_CHECKED | یک کنترل‌کننده با چند هویت؛ هم‌ارز ممیزی شاهد تاریخی نیست |
| Dong et al., **SOLOMON: Seeking the Truth Via Copying Detection** (2010) | [PDF نویسنده](https://yifanhu.net/PUB/solomon_vldbDemo.pdf) | AUTHOR_ABSTRACT_CHECKED | نمایش copy-detection؛ demo paper و نه کنترل کامل حاکمیتی |
| Bauer, Leucker, Schallhart, **Runtime Verification for LTL and TLTL** (2011) | [ACM DOI](https://doi.org/10.1145/2000799.2000800) | PRIMARY_METADATA_CHECKED | حکم inconclusive برای مشاهدهٔ جزئی؛ منشأ و سه برچسب Ario معادل خودکار آن نیست |
| Paccagnella et al., **Custos: Practical Tamper-Evident Auditing...** (2020) | [NDSS](https://www.ndss-symposium.org/ndss-paper/custos-practical-tamper-evident-auditing-of-operating-systems-using-trusted-execution/) | PRIMARY_METADATA_CHECKED | حسابرسی لاگ و کشف دست‌کاری با protocol مستقل؛ ثبت‌شدن تمام رخدادهای جهان را ثابت نمی‌کند |
| Soriano-Salvador & Guardiola-Múzquiz, **SealFS** (2021) | [Elsevier DOI](https://doi.org/10.1016/j.cose.2021.102325) | PRIMARY_METADATA_CHECKED | forward-integrity و محدودیت compromise؛ root مستقل از خودش اثبات نشده |
| Maharana et al., **Evaluating Very Long-Term Conversational Memory of LLM Agents / LoCoMo** (2024) | [ACL](https://aclanthology.org/2024.acl-long.747/) | PRIMARY_METADATA_CHECKED | معیار حافظهٔ طولانی و رویدادهای زمانی؛ نه آزمون source identity یا trust authorization |
| Chhikara et al., **Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory** (ECAI 2025 / آنلاین 2026) | [Publisher DOI](https://doi.org/10.3233/FAIA251160) | PRIMARY_METADATA_CHECKED | extraction/update و baseline مقیاس؛ سیاست پاک‌کردن raw events نیازمند بررسی implementation است |
| Joshi, **Eywa: Provenance-Grounded Long-Term Memory for AI Agents** (2026) | [arXiv](https://arxiv.org/abs/2605.30771) | PRIMARY_METADATA_CHECKED / PREPRINT | evidence-first write، retrieval قطعی و جدایی prompt instruction؛ 90.19% عدد خودِ paper با مدل/judge خاص است |
| Zheng et al., **Engineering Reliable Commit Gates for Agentic AI / VP-CONTROL** (2026) | [arXiv](https://arxiv.org/abs/2609.10969) | PRIMARY_METADATA_CHECKED / PREPRINT | source diversity در برابر model votes و after-check race؛ انتقال به R9 هنوز آزمایش نشده |
| Alvarez et al., **ProvenanceGuard: Source-Aware Factuality Verification for MCP-Based LLM Agents** (2026) | [arXiv](https://arxiv.org/abs/2606.18037) | PRIMARY_METADATA_CHECKED / PREPRINT | تفاوت support با attribution و خطای cross-source conflation؛ احراز استقلال controller را حل نمی‌کند |

**منابع دیگر برای صف بررسی** (فقط Consensus و بدون کنترل کامل این نوبت): Li et al. 2016 truth-discovery survey، Taleb et al. 2023 uncertainty in runtime verification، TOKI، A-MEM، Graphiti، Rebound 2026 و Agent Flight Recorder. هیچ عدد تجربی جدید از این ردیف‌ها وارد معیار پذیرش یا سند مقاله نشود تا اصل آن‌ها خوانده شود.

## خطاها و خطرهای قابل‌تشخیص در خروجی AI

1. **ERROR_IN_REPORT — SHA-256 حافظه:** مثال صفحهٔ ۵ گزارش حافظه مقدار e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855 را برای متن غیرتهی گذاشته است؛ این هشِ رشتهٔ تهی است. **به عنوان مثال معتبر یا قرارداد hash استفاده نشود.**
2. **ERROR_IN_REPORT — «atomic» شبه‌کد R9:** صفحات ۳–۴ گزارش R9 عملیات Python dict.get، set و append را «Atomic Effect-Side Check» می‌نامند؛ چنین عملیاتی بدون تراکنش و کنترل هم‌زمانی ضمانت اتمیک/دقیقاً یک‌بار ندارند. human_admitted boolean به‌تنهایی authority قابل احراز نیست؛ ConcurrencyError در قطعه تعریف نشده است.
3. **OVERCLAIM — قطعیت crypto:** عبارت «SHA-256 tamper resistance / truth» را به «سازگاری بایت‌های داده با digest مرجع معتبر» محدود کنید. هیچ hashing به‌تنهایی منشأ، صداقت ضبط یا تمامیت رویدادهای ثبت‌نشده را اثبات نمی‌کند.
4. **OVERGENERALIZATION — MemGPT/Mem0:** توصیف تمام memory systems کلاسیک به عنوان «حذف‌کنندهٔ تاریخچه» از یک مرور AI برای همهٔ نسخه‌ها قابل استناد نیست؛ read/write/retention هر پروژه باید از متن اولیه و سورس خودش استخراج شود.
5. **BENCHMARK_MISMATCH — LoCoMo:** چکیدهٔ اولیه ACL صریحاً از گفت‌وگوهای تقریباً ۶۰۰ turn و ۱۶K token به‌طور متوسط و حداکثر ۳۲ جلسه حرف می‌زند. اعداد کوچک‌تر یا جدول‌های AI باید با تعریف dataset split/نسخه بررسی شوند، نه بی‌دلیل جایگزین آمار اصل شوند.
6. **NOVELTY_OVERCLAIM:** UNKNOWN و source copying ریشهٔ پژوهشی پیش از Ario دارند؛ ۱۶/۱۶ سناریوی co-designed را نمی‌توان validation مستقل یا performance در جهان واقعی نوشت.
7. **PROVENANCE_SEMANTICS:** verificationِ نسبت‌دادن یک جمله به source (ProvenanceGuard) با اثبات independent administrative custody یا true-world claim یک چیز نیست.
8. **R9 EXTERNAL EFFECTS:** نتیجهٔ صفر اثر ناامن در mock یا ۲۱۶ episode VP-CONTROL تنها نسبت به همان target و fault model معنا دارد؛ برای effect خارجی و سناریوی فروپاشی دو trust domain، ضمانت کلی صادر نمی‌کند.

## ارجاع پروژه و مراحل بازبینی

- [یافته‌ها و تصمیم‌های اولیه](RESEARCH_FINDINGS_2026-11-16.md)
- [پروتکل‌های آزمون W1/M1/S1](EXPERIMENT_PROTOCOLS_2026-11-16.md)
- [برنامهٔ هفت‌روزه و لینک Threadها](CONSENSUS_7_DAY_PLAN_2026-11-16.md)

**پیش از citation نهایی در مقاله:** DOI و نسخهٔ دقیق primary paper، روش، baseline، جدول اصلی، license، دادهٔ باز و محدودیت را دوباره ارزیابی کنید. این فایل خود گزارش Consensus را به حقیقت بدل نمی‌کند؛ در صورت نامعلوم بودن، صریحاً UNKNOWN بماند. هیچ کد، signer، Ruleset، main یا حافظهٔ واقعی آریو در این کار تغییر نکرده است.
