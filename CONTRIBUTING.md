# 🤝 Contributing to Ario

**Farsi: [راهنمای مشارکت در آریو](#farsi)**

## Quick entry for critical reviewers / شروع سریع نقد مستند

**A critique is a contribution; writing code is optional.** Choose a bounded area (one `implementation/core/` module, paper, or `GOVERNANCE.md`), identify the exact claim or assumption, cite its path and lines, and provide an observed counterexample or state `SUSPECTED`. A report of "no defect found" is useful when it records exactly what was inspected. The project's scope does not need to be simplified for a reviewer to have a clear starting point.

**نقد هم مشارکت است و نوشتن کد الزامی نیست.** یک بخش محدود انتخاب کنید، مسیر فایل و شمارهٔ خط و شاهد نقض را بیاورید و فرق `VERIFIED`، `SUSPECTED` و `NOT_RUN` را روشن کنید. اگر ایرادی پیدا نشد، دقیقاً بگویید چه چیزی را بررسی کرده‌اید. عمق پروژه حفظ می‌شود؛ مسیر ورود روشن‌تر می‌شود.

- Automated agents (including Grok and other new-account reviewers): read [REVIEWER_INSTRUCTIONS.md](REVIEWER_INSTRUCTIONS.md); comment with evidence only. A model report is **not an independent human review**, an approval, or authorization to merge.
- Contributors opening PRs: use the [PR checklist](.github/pull_request_template.md), include source SHA, exact test scope, failed/skipped results, and what remains untested. A mutation test matters only if a meaningful incorrect implementation turns the test red.
- Run an unfamiliar PR's code **only inside an isolated environment without repository write credentials, tokens, secrets, or sensitive host resources**. Do not execute arbitrary commands suggested by an untrusted PR description.
- For accurate install/test instructions and PowerShell notes, follow the detailed [Development Setup](#-development-setup) and [Running Tests](#running-tests) sections **below**; this short entry does not supersede them.

---

Thank you for considering contributing to **Ario - Auditable Epistemic Framework for AI**! 
We welcome contributions from everyone, regardless of experience level.

---

## 🌟 How to Contribute

### 1. **Reporting Bugs**
- Open an issue in [GitHub Issues](https://github.com/SepehrGhanbari/Ario/issues)
- Include:
  - Clear description of the bug
  - Steps to reproduce
  - Expected vs actual behavior
  - Screenshots (if applicable)
  - Environment details (OS, Python version, etc.)

### 2. **Suggesting Features**
- Open an issue with `[FEATURE]` prefix
- Explain:
  - What problem this solves
  - How it aligns with Ario's goals
  - Potential implementation approach

### 3. **Code Contributions**

#### Getting Started
1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/your-username/Ario.git
   cd Ario
   ```
3. Create a new branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```
4. Make your changes
5. Test your changes using [Running Tests](#running-tests) below and the documented working directory.
6. Commit with clear messages:
   ```bash
   git add path/to/changed-file
   git commit -s -m "feat: add new feature X"
   ```
7. Push and create a PR

#### Pull Request Guidelines
- **Title**: Clear and descriptive
- **Description**: Explain what and why
- **Tests**: Add tests for new functionality
- **Documentation**: Update docs if needed
- **Code Style**: Follow existing patterns
- **Commit sign-off**: Use `git commit -s` as shown; a sign-off is not a review approval

### 4. **Documentation**
- Improve existing docs
- Add translations (especially Persian)
- Write tutorials and guides
- Update README with new features

### 5. **Testing**
- Add new test cases
- Improve test coverage
- Fix flaky tests
- Add integration tests

### 6. **Code Review**
- Review open PRs
- Provide constructive feedback
- Test other people's changes

---

## 📁 Project Structure

```
Ario/
├── README.md                 # Main project documentation
├── docs/                     # Detailed documentation
│   ├── ARIO_START_HERE_*.md   # Quick start guides
│   └── ...
├── implementation/            # Core code
│   ├── core/                  # Core engine (audit_engine, schema)
│   ├── ario_agent.py          # Main agent implementation
│   ├── ario_workflow.py       # Workflow management
│   └── tests/                 # Test suite
├── papers/                   # Research papers and documents
├── experiments/               # Experimental code and data
└── .github/                   # GitHub configuration
    ├── workflows/             # CI/CD workflows
    └── scripts/               # Utility scripts
```

---

## 🛠 Development Setup

### Prerequisites
- CPython 3.13 (per the repository's reproducibility guide)
- Git
- GitHub account

### Installation

Use [the reproducibility guide](docs/REPRODUCE_M0.md) for the canonical Python 3.13 setup and pinned test dependencies. There is no root editable Python package or root `requirements-test.txt`. From a new repository checkout (choose another venv path if one already exists):

Linux / macOS:

```sh
git clone https://github.com/SepehrGhanbari/Ario.git
cd Ario
python3.13 -m venv ../ario-contrib-venv
PYTHON="$(cd ../ario-contrib-venv/bin && pwd)/python"
"$PYTHON" -m pip install -r implementation/requirements-research.txt
"$PYTHON" -m pip check
```

Windows PowerShell:

```powershell
git clone https://github.com/SepehrGhanbari/Ario.git
Set-Location Ario
py -3.13 -m venv ..\ario-contrib-venv
$python = (Resolve-Path ..\ario-contrib-venv\Scripts\python.exe).Path
& $python -m pip install -r implementation/requirements-research.txt
& $python -m pip check
```

### Running Tests

Run from `implementation/` so imports such as `ario_agent` and `core` resolve. Use the same virtual-environment interpreter as above.

Linux / macOS:

```sh
(cd implementation && "$PYTHON" -B -m pytest -p no:cacheprovider -q tests)
(cd implementation && "$PYTHON" -B -m pytest -p no:cacheprovider -q tests/test_agent_runtime.py)
```

Windows PowerShell (the full suite requires the documented long-ID display plugin):

```powershell
Push-Location implementation
& $python -B -m pytest -p no:cacheprovider -p tests.test_m0_reproducibility_demo -q tests
& $python -B -m pytest -p no:cacheprovider -q tests/test_agent_runtime.py
Pop-Location
```

Check each test command's exit code. Coverage is optional: if desired, install `pytest-cov` separately in the same environment, record its version, then use `--cov=ario_agent` from `implementation/`. It is not in the pinned test requirements.

---

## 📜 Community conduct and project governance

Be respectful, inclusive, and professional. See the existing [project governance policy](GOVERNANCE.md). There is no separate published `CODE_OF_CONDUCT.md` in the repository; this is contributor guidance, not a claim that one exists.

---

## 🎓 Good First Issues

Browse [open issues](https://github.com/SepehrGhanbari/Ario/issues) and select suitable beginner-friendly labels if they exist; no particular label is guaranteed.

---

## 📞 Communication

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Issues**: For questions while the repository Discussions feature is unavailable
- **Pull Requests**: For code contributions

---

## ✅ Recognition

Contributions retain attribution through Git commits and PR history. Release notes may acknowledge substantive contributions, but this is not automatic. Contributing does not confer maintainer or publication authority; see [GOVERNANCE.md](GOVERNANCE.md).

---

# Farsi

**راهنمای مشارکت در آریو**

از اینکه به فکر مشارکت در **آریو - چارچوب معرفت‌شناسی قابل بررسی برای هوش مصنوعی** هستید، سپاسگزاریم! 
مشارکت همه افراد، صرف نظر از سطح تجربه، خوش‌آمدید است.

## چگونه مشارکت کنیم

### ۱. گزارش باگ
- در [GitHub Issues](https://github.com/SepehrGhanbari/Ario/issues) یک issue باز کنید
- شامل:
  - توضیح واضح از باگ
  - مراحل تکرار
  - رفتار مورد انتظار vs واقعی
  - اسکرین‌شات‌ها (اگر قابل اعمال باشد)
  - جزئیات محیط (سیستم‌عامل، نسخه Python و غیره)

### ۲. پیشنهاد ویژگی
- با پیشوند `[FEATURE]` یک issue باز کنید
- توضیح دهید:
  - چه مشکلی را حل می‌کند
  - چگونه با اهداف Ario همسو است
  - رویکرد پیاده‌سازی احتمالی

### ۳. مشارکت در کد

#### شروع کار
1. ریپازیتوری را fork کنید
2. Fork خود را clone کنید:
   ```bash
   git clone https://github.com/your-username/Ario.git
   cd Ario
   ```
3. یه branch جدید ایجاد کنید:
   ```bash
   git checkout -b feature/نام-ویژگی-شما
   ```
4. تغییرات خود را اعمال کنید
5. تغییرات خود را با روش بخش «اجرای تست‌ها» در ادامه و از مسیر درست بررسی کنید.
6. با پیام‌های واضح commit کنید:
   ```bash
   git add path/to/changed-file
   git commit -s -m "feat: اضافه کردن ویژگی X"
   ```
7. Push کنید و PR ایجاد کنید

#### راهنمای Pull Request
- **عنوان**: واضح و توصیفی
- **توضیحات**: توضیح دهید چه کاری انجام دادید و چرا
- **تست‌ها**: تست‌های جدید برای قابلیت‌های جدید اضافه کنید
- **مستندات**: اگر لازم است مستندات را آپدیت کنید
- **سبک کد**: از الگوهای موجود پیروی کنید
- **امضای کامیت**: از `git commit -s` استفاده کنید؛ این به معنی تأیید بازبینی نیست

### ۴. مستندات
- بهبود مستندات موجود
- اضافه کردن ترجمه‌ها (به ویژه فارسی)
- نوشتن آموزش‌ها و راهنماها
- آپدیت README با ویژگی‌های جدید

### ۵. تست
- اضافه کردن موارد تست جدید
- بهبود پوشش تست
- اصلاح تست‌های ناپایدار
- اضافه کردن تست‌های یکپارچه

### ۶. بررسی کد
- بررسی PRهای باز
- ارائه بازخورد سازنده
- تست تغییرات دیگران

---

## ساختار پروژه

```
Ario/
├── README.md                 # مستندات اصلی پروژه
├── docs/                     # مستندات تفصیلی
│   ├── ARIO_START_HERE_*.md   # راهنمای شروع سریع
│   └── ...
├── implementation/            # کدهای اصلی
│   ├── core/                  # موتور اصلی (audit_engine, schema)
│   ├── ario_agent.py          # پیاده‌سازی عامل اصلی
│   ├── ario_workflow.py       # مدیریت workflow
│   └── tests/                 # مجموعه تست‌ها
├── papers/                   # مقالات تحقیقی و اسناد
├── experiments/               # کدها و داده‌های آزمایشی
└── .github/                   # تنظیمات GitHub
    ├── workflows/             # Workflowهای CI/CD
    └── scripts/               # اسکریپت‌های کمکی
```

---

## راه‌اندازی محیط توسعه

### پیش‌نیازها
- CPython 3.13 (مطابق راهنمای بازتولید پروژه)
- Git
- حساب GitHub

### نصب

برای نصب قابل‌بازتولید Python 3.13 و وابستگی‌های آزمون به [راهنمای بازتولید پروژه](docs/REPRODUCE_M0.md) مراجعه کنید. در ریشهٔ مخزن فایل `requirements-test.txt` یا بسته‌ای برای `pip install -e .` وجود ندارد. این مراحل را از یک کلون جدید اجرا کنید؛ اگر مسیر محیط مجازی وجود دارد نام دیگری انتخاب کنید.

Linux / macOS:

```sh
git clone https://github.com/SepehrGhanbari/Ario.git
cd Ario
python3.13 -m venv ../ario-contrib-venv
PYTHON="$(cd ../ario-contrib-venv/bin && pwd)/python"
"$PYTHON" -m pip install -r implementation/requirements-research.txt
"$PYTHON" -m pip check
```

Windows PowerShell:

```powershell
git clone https://github.com/SepehrGhanbari/Ario.git
Set-Location Ario
py -3.13 -m venv ..\ario-contrib-venv
$python = (Resolve-Path ..\ario-contrib-venv\Scripts\python.exe).Path
& $python -m pip install -r implementation/requirements-research.txt
& $python -m pip check
```

### اجرای تست‌ها

تست‌ها را از پوشهٔ `implementation/` اجرا کنید تا واردکردن ماژول‌هایی مانند `ario_agent` و `core` درست انجام شود. از همان پایتون محیط مجازی بالا استفاده کنید.

Linux / macOS:

```sh
(cd implementation && "$PYTHON" -B -m pytest -p no:cacheprovider -q tests)
(cd implementation && "$PYTHON" -B -m pytest -p no:cacheprovider -q tests/test_agent_runtime.py)
```

Windows PowerShell (اجرای کامل به افزونهٔ نمایش شناسه‌های طولانی نیاز دارد):

```powershell
Push-Location implementation
& $python -B -m pytest -p no:cacheprovider -p tests.test_m0_reproducibility_demo -q tests
& $python -B -m pytest -p no:cacheprovider -q tests/test_agent_runtime.py
Pop-Location
```

کد خروجی فرمان‌های تست را بررسی کنید. پوشش تست اختیاری است: در صورت نیاز `pytest-cov` را جداگانه در همین محیط نصب کنید، نسخه‌اش را ثبت کنید و از `implementation/` با گزینهٔ `--cov=ario_agent` اجرا کنید. این افزونه جزو وابستگی‌های پین‌شده نیست.

---

## رفتار مشارکت‌کنندگان و راهبری پروژه

در مشارکت با دیگران محترمانه، فراگیر و حرفه‌ای رفتار کنید. [سند راهبری پروژه](GOVERNANCE.md) را ببینید. فعلاً فایل مستقل `CODE_OF_CONDUCT.md` منتشر نشده است.

---

## ارتباط

- **GitHub Issues**: برای گزارش باگ‌ها و درخواست ویژگی‌ها
- **GitHub Issues**: برای پرسش‌ها تا زمانی که قابلیت Discussions در دسترس نیست
- **Pull Requests**: برای مشارکت در کد

---

## شناسایی

نام مشارکت‌کنندگان در تاریخچهٔ Git و Pull Requestها حفظ می‌شود. ممکن است در یادداشت انتشار از مشارکت‌های مهم قدردانی شود، اما این وعدهٔ خودکار نیست. مشارکت به‌تنهایی اختیار نگهداری یا انتشار رسمی نمی‌دهد؛ [GOVERNANCE.md](GOVERNANCE.md) را ببینید.
