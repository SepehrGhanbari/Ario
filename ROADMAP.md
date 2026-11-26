# 🗺️ Ario Project Roadmap

**Farsi: [برنامه راهبردی پروژه آریو](#farsi)**

This document outlines the vision, goals, and proposed milestones for the **Ario - Auditable Epistemic Framework for AI** project.

**Status — 14 November 2026:** Roadmap goals are proposals, not completed security controls or authority to merge, deploy, sign, or release. Current facts come from GitHub PRs, current source and active rulesets. The reference M0 engine is labeled `M0-1.2` in `docs/REPRODUCE_M0.md`; a possible project release tag is a separate, uncommitted decision.

**وضعیت — ۱۴ نوامبر ۲۰۲۶:** هدف‌های این سند پیشنهادی‌اند و گواهی اجرای گیت امنیتی یا مجوز ادغام، استقرار، امضا و انتشار نیستند. واقعیت‌ها باید از PRها، کد و Rulesetهای جاری بررسی شوند. موتور مرجع M0 طبق `docs/REPRODUCE_M0.md` با برچسب `M0-1.2` مستند است؛ نسخهٔ انتشار احتمالی پروژه تصمیمی مستقل و هنوز تصویب‌نشده است.

---

## 🎯 Vision

To create a **world-class, auditable framework** for AI systems that can:
- Distinguish between memory and truth
- Trace claims to their evidence
- Preserve revision history
- Maintain epistemic integrity

---

## 📅 Current Status (November 2026)

### ✅ Completed
- [x] **Core Architecture** - M0 engine with audit capabilities
- [x] **Research Foundation** - Philosophical and technical papers
- [x] **Bilingual Documentation** - English and Persian support
- [x] **Test Suite** - pytest regressions exist; quantitative test coverage has not been measured here.
- [ ] **Independent review-evidence gate — NOT INSTALLED / HOLD** - PR #133 remains open and PR #151 remains draft; neither establishes a required independent-evidence check on `main`.

### 🚧 In Progress
- [ ] **Public Demo** - Draft source PR #164 under `docs/`; not an established website deployment.
- [ ] **Governance Implementation — HOLD** - Independently verify trustworthy check production, durable evidence custody, adversarial forgery/bypass and fail-closed repair, then obtain a separate authorized decision. The existing native approvals and `m0-regression` requirement are distinct.
- [ ] **Ava Research** - Identity dialogue experiments (PR #134)
- [ ] **Claude Integration** - Advisory review workflow (PR #162)
- [ ] **Security Audit** - Ollama loopback investigation (Issue #163)

---

## 🎯 Roadmap

### 📌 Q4 2026 (Current Quarter)

#### High Priority
- **Keep #133/#151 HOLD** - Validate independent check producer and evidence custody, spoof/bypass defense and safe repair; require explicit owner-authorized adoption before any activation. This roadmap creates no exception.
- **Review and, when authorized, merge PR #164 source** - First resolve draft/accessibility issues.
- **Deploy public demo separately** - Integrate reviewed `docs/` assets into the actual `website/` deployment path, test accessibility/security, and verify a real deployment; merge is not deployment.
- **Resolve Issue #163** - Fix Ollama security concern
- **Complete PR #134** - Finish Ava research experiments

#### Medium Priority
- **Improve Documentation** - Add CONTRIBUTING.md, ROADMAP.md, SECURITY.md
- **Community Building** - Attract more contributors
- **Test Coverage (aspirational)** - Define the measured code, denominator, exclusions and pinned optional `pytest-cov` run before establishing a baseline; 90%+ is a target, not a result.
- **Performance Optimization** - Improve core engine speed

#### Low Priority
- **Website Improvements** - Better UX/UI
- **Additional Demos** - More interactive examples
- **Integration Tests** - End-to-end testing

### 📌 Q1 2027

#### Core Development
- **Potential project release** - Decide a separate project release label after review; this does not change or replace the `M0-1.2` engine label.
- **Evidence Admission** - Independent evidence provenance (Issue #81)
- **Safety Framework** - RAAD-SAF implementation (Issue #82)

#### Research
- **Identity Studies** - Two-Ava dialogue analysis (Issue #138)
- **Provenance Benchmark** - Blind provenance-dependence tests (Issue #128)
- **Mission Drift Analysis** - Privacy-safe public benefit research (Issue #140)

#### Community
- **First Major Release** - v1.0.0
- **Contributor Onboarding** - Improved documentation
- **Community Events** - Workshops and presentations

### 📌 Q2 2027

#### Advanced Features
- **Multi-Agent Support** - Multiple AI agents interaction
- **Real-time Auditing** - Continuous monitoring
- **Explainability** - Better interpretation tools

#### Ecosystem
- **Plugin System** - Extensible architecture
- **API Documentation** - Public API release
- **Integration Guides** - Third-party tool integration

---

## 🎪 Milestones

### 🏆 Milestone 1: Core Stability (Q4 2026)
- **Goal**: Stable M0 engine with governance
- **Deliverables**:
  - Reproduce reference engine `M0-1.2` at a named Git SHA; do not imply an engine-version downgrade
  - Independent review-evidence gate validated and separately authorized before any activation (currently HOLD)
  - Review demo source and independently verify any website deployment
  - Close security issues only after verified remediation

### 🏆 Milestone 2: First Release (Q1 2027)
- **Goal**: First major public release
- **Deliverables**:
  - Possible project release tag (name/date undecided; distinct from M0 engine rule version)
  - Complete documentation
  - Active community
  - Research papers published

### 🏆 Milestone 3: Ecosystem Growth (Q2 2027)
- **Goal**: Growing ecosystem and adoption
- **Deliverables**:
  - Plugin system
  - Public API
  - Integration guides
  - Case studies

---

## 📊 Success Metrics

### Code Quality

**Targets, not baselines.** Coverage should be computed only after pinning optional `pytest-cov` in the documented Python 3.13 virtual environment, defining measured files, line denominator and exclusions, and recording the command, report and Git SHA. This document claims no measured coverage percentage.

- [ ] Aspirational measured line coverage > 90% (baseline UNKNOWN)
- [ ] Zero critical bugs
- [ ] All PRs reviewed within 48 hours
- [ ] Documentation complete

### Community
- [ ] 50+ stars on GitHub
- [ ] 10+ active contributors
- [ ] 20+ issues resolved per month
- [ ] Regular community meetings

### Research
- [ ] 5+ research papers published
- [ ] 3+ conference presentations
- [ ] Academic collaborations
- [ ] Industry partnerships

---

## 🤝 How You Can Help

### For Developers
- **Contribute Code** - Fix bugs, add features
- **Improve Tests** - Add more test cases
- **Review PRs** - Help with code reviews
- **Write Docs** - Improve documentation

### For Researchers
- **Conduct Studies** - Use Ario for research
- **Publish Papers** - Share findings
- **Collaborate** - Work with other researchers
- **Present** - Speak at conferences

### For Users
- **Test** - Try out demos and provide feedback
- **Report Bugs** - Help improve quality
- **Suggest Features** - Shape the future
- **Spread the Word** - Tell others about Ario

---

## 📞 Contact

- **GitHub**: [SepehrGhanbari/Ario](https://github.com/SepehrGhanbari/Ario)
- **Website**: [ario-research-independent.vercel.app](https://ario-research-independent.vercel.app/)
- **Issues**: [GitHub Issues](https://github.com/SepehrGhanbari/Ario/issues)
- **Public questions / پرسش و نقد عمومی**: [Issue #106](https://github.com/SepehrGhanbari/Ario/issues/106)

---

# Farsi

**برنامه راهبردی پروژه آریو**

این سند **چشمانداز، اهداف و برنامه زمانی** پروژه **آریو - چارچوب معرفت‌شناسی قابل بررسی برای هوش مصنوعی** را شرح می‌دهد.

---

## 🎯 چشمانداز

ایجاد یه **چارچوب جهانی و قابل بررسی** برای سیستم‌های هوش مصنوعی که بتوانند:
- حافظه را از حقیقت متمایز کنند
- ادعاها را به شواهدشان وصل کنند
- تاریخچه بازبینی را حفظ کنند
- یکپارچگی معرفت‌شناختی را حفظ کنند

---

## 📅 وضعیت فعلی (نوامبر 2026)

### ✅ تکمیل شده
- [x] **معماری اصلی** - موتور M0 با قابلیت‌های بررسی
- [x] **پایه تحقیقاتی** - مقالات فلسفی و فنی
- [x] **مستندات دوزبانه** - پشتیبانی فارسی و انگلیسی
- [x] **مجموعه تست** - تست‌های pytest وجود دارند؛ درصد پوشش واقعی اینجا اندازه‌گیری نشده است.
- [ ] **گیت مستقل شواهد بازبینی — نصب‌نشده / HOLD** - PR #133 هنوز باز و PR #151 پیش‌نویس است؛ گیت مستقل پیشنهادی Check الزامی روی `main` نیست.

### 🚧 در حال انجام
- [ ] **دموی عمومی** - سورس پیش‌نویس PR #164 در `docs/` است و استقرار سایت محسوب نمی‌شود.
- [ ] **پیاده‌سازی حکمرانی — HOLD** - ناشر معتبر مستقل Check، نگهداری ماندگار شواهد، آزمون جعل/عبور و ترمیم fail-closed باید بررسی شوند و تصمیم مجاز جداگانه گرفته شود؛ تأییدهای معمول گیت‌هاب و `m0-regression` همان گیت مستقل نیستند.
- [ ] **تحقیق Ava** - آزمایش‌های دیالوگ هویت (PR #134)
- [ ] **یکپارچه‌سازی Claude** - جریان کار بررسی مشاوره‌ای (PR #162)
- [ ] **بررسی امنیتی** - تحقیق درباره نگرانی امنیتی Ollama (Issue #163)

---

## 🎯 برنامه راهبردی

### 📌 سه‌ماهه چهارم 2026 (سه‌ماهه جاری)

#### اولویت بالا
- **حفظ HOLD برای #133/#151** - بررسی ناشر مستقل Check، نگهداری شواهد، مقاومت در برابر جعل/عبور و ترمیم امن؛ فعال‌سازی فقط پس از تصمیم مجاز جداگانه. این سند استثنا نیست.
- **بازبینی و سپس ادغام مجاز سورس PR #164** - ابتدا ایرادهای پیش‌نویس و دسترس‌پذیری رفع شوند.
- **استقرار مستقل دموی عمومی** - فایل‌های بازبینی‌شدهٔ `docs/` را جدا به مسیر انتشار `website/` متصل و امنیت، دسترس‌پذیری و انتشار واقعی را بررسی کنید؛ مرج به‌تنهایی انتشار نیست.
- **حل Issue #163** - رفع نگرانی امنیتی Ollama
- **تکمیل PR #134** - اتمام آزمایش‌های تحقیقی Ava

#### اولویت متوسط
- **بهبود مستندات** - اضافه کردن CONTRIBUTING.md، ROADMAP.md، SECURITY.md
- **ساخت جامعه** - جذب مشارکت‌کنندگان بیشتر
- **پوشش تست (آرمانی)** - پیش از اعلام خط‌پایه، فایل‌ها/مخرج/استثناها و اجرای پین‌شدهٔ `pytest-cov` را مشخص کنید؛ ۹۰٪+ هدف است، نه نتیجه.
- **بهینه‌سازی عملکرد** - بهبود سرعت موتور اصلی

#### اولویت پایین
- **بهبود وب‌سایت** - UX/UI بهتر
- **دموهای بیشتر** - مثال‌های تعاملی بیشتر
- **تست‌های یکپارچه** - تست‌های end-to-end

### 📌 سه‌ماهه اول 2027

#### توسعه اصلی
- **انتشار احتمالی محصول** - برچسب جداگانهٔ نسخهٔ پروژه پس از بازبینی تعیین شود و با نسخهٔ موتور `M0-1.2` اشتباه نشود.
- **پذیرش شواهد** - منشأ مستقل شواهد (Issue #81)
- **چارچوب ایمنی** - پیاده‌سازی RAAD-SAF (Issue #82)

#### تحقیقات
- **مطالعات هویت** - تحلیل دیالوگ‌های دو Ava (Issue #138)
- **معیار منشأ** - تست‌های نابینای وابستگی به منشأ (Issue #128)
- **تحلیل انحراف ماموریت** - تحقیق درباره منافع عمومی با حریم خصوصی (Issue #140)

#### جامعه
- **اولین نسخه اصلی** - v1.0.0
- **راه‌اندازی مشارکت‌کنندگان** - بهبود مستندات
- **رویدادهای جامعه** - کارگاه‌ها و ارائه‌ها

### 📌 سه‌ماهه دوم 2027

#### ویژگی‌های پیشرفته
- **پشتیبانی چند عاملی** - تعامل چندین عامل هوش مصنوعی
- **بررسی بلادرنگ** - مانیتورینگ مداوم
- **قابلیت توضیح** - ابزارهای تفسیر بهتر

#### اکوسیستم
- **سیستم افزونه** - معماری قابل توسعه
- **مستندات API** - انتشار API عمومی
- **راهنمای یکپارچه‌سازی** - یکپارچه‌سازی با ابزارهای شخص ثالث

---

## 🎪 نقاط عطف

### 🏆 نقطه عطف 1: پایداری اصلی (سه‌ماهه چهارم 2026)
- **هدف**: موتور M0 پایدار با حکمرانی
- **تحویل‌ها**:
  - بازتولید موتور مرجع `M0-1.2` با SHA مشخص؛ نه تنزل نسخهٔ موتور
  - گیت مستقل شواهد فقط پس از اعتبارسنجی و مجوز جداگانه فعال شود (فعلاً HOLD)
  - بازبینی سورس دمو و بررسی جداگانهٔ استقرار سایت
  - بستن مسائل امنیتی تنها پس از اصلاح تأییدشده

### 🏆 نقطه عطف 2: اولین نسخه (سه‌ماهه اول 2027)
- **هدف**: اولین نسخه عمومی اصلی
- **تحویل‌ها**:
  - نسخهٔ احتمالی انتشار پروژه (شماره/تاریخ هنوز تعیین نشده؛ مستقل از نسخهٔ موتور M0)
  - مستندات کامل
  - جامعه فعال
  - مقالات تحقیقی منتشر شده

### 🏆 نقطه عطف 3: رشد اکوسیستم (سه‌ماهه دوم 2027)
- **هدف**: اکوسیستم در حال رشد و پذیرش
- **تحویل‌ها**:
  - سیستم افزونه
  - API عمومی
  - راهنمای یکپارچه‌سازی
  - مطالعات موردی

---

## 📊 معیارهای موفقیت

### کیفیت کد

**هدف‌ها، نه خط‌پایهٔ سنجیده‌شده.** سنجش پوشش باید با نصب و پین `pytest-cov` اختیاری در محیط Python 3.13، تعریف فایل‌ها، خطوط مخرج و استثناها و ثبت فرمان، گزارش و SHA انجام شود. این سند درصد پوشش اندازه‌گیری‌شده ادعا نمی‌کند.

- [ ] هدف آرمانی پوشش خطوط > ۹۰٪ (خط‌پایه UNKNOWN)
- [ ] بدون باگ‌های بحرانی
- [ ] بررسی تمام PRها در کمتر از 48 ساعت
- [ ] مستندات کامل

### جامعه
- [ ] 50+ ستاره در GitHub
- [ ] 10+ مشارکت‌کننده فعال
- [ ] 20+ issue حل شده در ماه
- [ ] جلسات منظم جامعه

### تحقیقات
- [ ] 5+ مقاله تحقیقی منتشر شده
- [ ] 3+ ارائه در کنفرانس‌ها
- [ ] همکاری‌های آکادمیک
- [ ] شراکت‌های صنعتی

---

## 🤝 چگونه می‌توانید کمک کنید

### برای توسعه‌دهندگان
- **مشارکت در کد** - رفع باگ‌ها، اضافه کردن ویژگی‌ها
- **بهبود تست‌ها** - اضافه کردن موارد تست بیشتر
- **بررسی PRها** - کمک به بررسی کدها
- **نوشتن مستندات** - بهبود مستندات

### برای محققان
- **انجام مطالعات** - استفاده از Ario برای تحقیقات
- **انتشار مقالات** - به اشتراک گذاری یافته‌ها
- **همکاری** - کار با سایر محققان
- **ارائه** - سخنرانی در کنفرانس‌ها

### برای کاربران
- **تست** - امتحان کردن دموها و ارائه بازخورد
- **گزارش باگ‌ها** - کمک به بهبود کیفیت
- **پیشنهاد ویژگی‌ها** - شکل دادن به آینده
- **تبلیغ** - معرفی Ario به دیگران

---

## 📞 تماس

- **GitHub**: [SepehrGhanbari/Ario](https://github.com/SepehrGhanbari/Ario)
- **وب‌سایت**: [ario-research-independent.vercel.app](https://ario-research-independent.vercel.app/)
- **Issues**: [GitHub Issues](https://github.com/SepehrGhanbari/Ario/issues)
- **Public questions / پرسش و نقد عمومی**: [Issue #106](https://github.com/SepehrGhanbari/Ario/issues/106)
