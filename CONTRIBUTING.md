# 🤝 Contributing to Ario

**Farsi: [راهنمای مشارکت در آریو](#farsi)**

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
5. Test your changes:
   ```bash
   python -m pytest implementation/tests/
   ```
6. Commit with clear messages:
   ```bash
   git commit -m "feat: add new feature X"
   ```
7. Push and create a PR

#### Pull Request Guidelines
- **Title**: Clear and descriptive
- **Description**: Explain what and why
- **Tests**: Add tests for new functionality
- **Documentation**: Update docs if needed
- **Code Style**: Follow existing patterns
- **Sign-off**: Use `git commit -s` for DCO

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
- Python 3.8+
- Git
- GitHub account

### Installation
```bash
# Clone the repository
git clone https://github.com/SepehrGhanbari/Ario.git
cd Ario

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e .
pip install -r requirements-test.txt
```

### Running Tests
```bash
# Run all tests
python -m pytest implementation/tests/

# Run specific test
python -m pytest implementation/tests/test_agent_runtime.py

# With coverage
python -m pytest --cov=implementation implementation/tests/
```

---

## 📜 Code of Conduct

We expect all contributors to follow our [Code of Conduct](CODE_OF_CONDUCT.md).
Be respectful, inclusive, and professional.

---

## 🎓 Good First Issues

Look for issues labeled:
- `good first issue` - Beginner-friendly
- `help wanted` - Needs assistance
- `documentation` - Documentation improvements

---

## 📞 Communication

- **GitHub Issues**: For bug reports and feature requests
- **GitHub Discussions**: For general questions and discussions
- **Pull Requests**: For code contributions

---

## ✅ Recognition

All meaningful contributions will be recognized:
- Added to CONTRIBUTORS.md
- Mentioned in release notes
- Invited to become maintainers (for significant contributions)

---

# Farsi: راهنمای مشارکت در آریو

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
5. تغییرات را تست کنید:
   ```bash
   python -m pytest implementation/tests/
   ```
6. با پیام‌های واضح commit کنید:
   ```bash
   git commit -m "feat: اضافه کردن ویژگی X"
   ```
7. Push کنید و PR ایجاد کنید

#### راهنمای Pull Request
- **عنوان**: واضح و توصیفی
- **توضیحات**: توضیح دهید چه کاری انجام دادید و چرا
- **تست‌ها**: تست‌های جدید برای قابلیت‌های جدید اضافه کنید
- **مستندات**: اگر لازم است مستندات را آپدیت کنید
- **سبک کد**: از الگوهای موجود پیروی کنید
- **امضا**: از `git commit -s` برای DCO استفاده کنید

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
- Python 3.8+
- Git
- حساب GitHub

### نصب
```bash
# کلون کردن ریپازیتوری
git clone https://github.com/SepehrGhanbari/Ario.git
cd Ario

# ایجاد محیط مجازی
python -m venv venv
source venv/bin/activate  # در Windows: venv\Scripts\activate

# نصب واسطه‌ها
pip install -e .
pip install -r requirements-test.txt
```

### اجرا کردن تست‌ها
```bash
# اجرا کردن تمام تست‌ها
python -m pytest implementation/tests/

# اجرا کردن تست خاص
python -m pytest implementation/tests/test_agent_runtime.py

# با پوشش کد
python -m pytest --cov=implementation implementation/tests/
```

---

## قوانین رفتار

ما از تمام مشارکت‌کنندگان انتظار داریم که [قوانین رفتار](CODE_OF_CONDUCT.md) ما را دنبال کنند.
احترام‌گذار، فراگیر و حرفه‌ای باشید.

---

## ارتباط

- **GitHub Issues**: برای گزارش باگ‌ها و درخواست ویژگی‌ها
- **GitHub Discussions**: برای سوالات عمومی و بحث‌ها
- **Pull Requests**: برای مشارکت در کد

---

## شناسایی

تمام مشارکت‌های معنادار شناسایی خواهند شد:
- اضافه شدن به CONTRIBUTORS.md
- ذکر در یادداشت‌های نسخه
- دعوت به تبدیل شدن به maintainer (برای مشارکت‌های قابل توجه)
