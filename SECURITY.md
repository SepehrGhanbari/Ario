# 🔒 Security Policy

**Farsi: [سیاست امنیتی](#farsi)**

This document outlines the security policies and procedures for the **Ario - Auditable Epistemic Framework for AI** project.

---

## 📋 Security Philosophy

Ario takes security seriously. As a framework for auditable AI systems, we recognize that:
- **Security is foundational** to trust and reliability
- **Transparency is essential** for accountability
- **Defense in depth** provides robust protection
- **Continuous improvement** is necessary in a changing threat landscape

---

## 🚨 Reporting Security Issues

### If You Discover a Vulnerability

**DO NOT** create a public GitHub issue. Instead:

1. **Email**: Send details to [sepehr.ghanbari@proton.me](mailto:sepehr.ghanbari@proton.me)
2. **Subject**: Use prefix `[SECURITY]` in the subject line
3. **Include**:
   - Detailed description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested mitigation (if any)

### Response Process

1. **Acknowledgment**: You will receive a response within 48 hours
2. **Triage**: Our security team will assess the issue
3. **Remediation**: We will develop and test a fix
4. **Disclosure**: Coordinated disclosure with proper credit

### Timeline

| Severity | Response Time | Fix Time |
|----------|---------------|----------|
| Critical | 24 hours | 7 days |
| High | 48 hours | 14 days |
| Medium | 72 hours | 30 days |
| Low | 1 week | Next release |

---

## 🛡️ Security Best Practices

### For Contributors

#### Code Security
- **Input Validation**: Always validate and sanitize user input
- **Dependency Security**: Keep dependencies updated
- **Secrets Management**: Never commit secrets to version control
- **Error Handling**: Don't expose sensitive information in errors
- **Logging**: Be careful with sensitive data in logs

#### Secure Coding Guidelines
```python
# ✅ DO:
def process_input(user_input: str) -> str:
    # Validate input type
    if not isinstance(user_input, str):
        raise ValueError("Invalid input type")
    
    # Sanitize input
    sanitized = user_input.strip()
    
    # Validate length
    if len(sanitized) > MAX_LENGTH:
        raise ValueError("Input too long")
    
    return sanitized

# ❌ DON'T:
def unsafe_process(user_input: str) -> str:
    # No validation
    return user_input  # XSS vulnerability!
```

### For Users

#### Deployment Security
- **Network Isolation**: Run Ario in isolated networks
- **Access Control**: Limit access to sensitive endpoints
- **Monitoring**: Monitor system logs for suspicious activity
- **Updates**: Keep Ario and dependencies updated
- **Backups**: Regularly backup critical data

#### Configuration Security
- Use strong, unique passwords
- Enable two-factor authentication
- Rotate API keys regularly
- Limit permissions (principle of least privilege)
- Use HTTPS for all communications

---

## 🔍 Security Features

### Built-in Protections

1. **Evidence Integrity**
   - SHA-256 hashing for all evidence
   - Immutable audit trails
   - Cryptographic verification

2. **Access Control**
   - Role-based permissions
   - Authentication required
   - Session management

3. **Data Protection**
   - Encryption at rest
   - Encryption in transit
   - Data minimization

4. **Audit Logging**
   - All actions logged
   - Tamper-evident logs
   - Retention policies

### Security Review Process

All code changes go through:
1. **Automated Scanning**: Static analysis tools
2. **Manual Review**: Security-focused code review
3. **Dependency Check**: Vulnerability scanning
4. **Testing**: Security test cases

---

## 📊 Known Security Considerations

### Current Security Posture

| Area | Status | Notes |
|------|--------|-------|
| Code Review | ✅ Active | All PRs reviewed |
| Dependency Scanning | ✅ Active | Using Dependabot |
| Secret Scanning | ✅ Active | GitHub secret scanning |
| Vulnerability Disclosure | ✅ Active | Coordinated disclosure |
| Security Testing | ⚠️ Partial | Need more security tests |
| Penetration Testing | ❌ Not Started | Future consideration |

### Open Security Issues

- **Issue #163**: Ollama loopback planner proxy concern
  - Status: Under investigation
  - Severity: High
  - Action: Disable Ollama integration until resolved

---

## 🛠️ Security Tools

### Recommended Tools

1. **Static Analysis**
   - `bandit` - Python security linter
   - `safety` - Dependency vulnerability checker
   - `semgrep` - Custom security rules

2. **Dynamic Analysis**
   - `OWASP ZAP` - Web application security scanner
   - `Burp Suite` - Web vulnerability scanner

3. **Monitoring**
   - `Sentry` - Error tracking
   - `Datadog` - System monitoring
   - Custom logging

### Usage Examples

```bash
# Install security tools
pip install bandit safety semgrep

# Run security checks
bandit -r implementation/
safety check
semgrep --config=auto implementation/
```

---

## 🎓 Security Resources

### Learning Materials
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [Python Security](https://wiki.python.org/moin/Security)

### Security Checklists
- [ ] Input validation implemented
- [ ] Output encoding applied
- [ ] Authentication required
- [ ] Authorization checks in place
- [ ] Error messages don't leak information
- [ ] Logging doesn't contain sensitive data
- [ ] Dependencies are up to date
- [ ] Secrets are properly protected

---

## 📞 Security Contacts

| Role | Contact | PGP Key |
|------|---------|---------|
| Security Lead | sepehr.ghanbari@proton.me | Available on request |
| Project Owner | sepehr.ghanbari@proton.me | Available on request |

---

## ✅ Security Acknowledgements

We would like to acknowledge the following individuals and organizations for their security contributions:

- [List will be populated as contributions are received]

---

# Farsi: سیاست امنیتی

این سند **سیاست‌ها و رویه‌های امنیتی** پروژه **آریو - چارچوب معرفت‌شناسی قابل بررسی برای هوش مصنوعی** را شرح می‌دهد.

---

## 📋 فلسفه امنیتی

آریو امنیت را بسیار جدی می‌گیرد. به عنوان یک چارچوب برای سیستم‌های هوش مصنوعی قابل بررسی، ما تشخیص می‌دهیم که:
- **امنیت پایه و اساس** اعتماد و قابلیت اطمینان است
- **شفافیت ضروری** برای مسئولیت‌پذیری است
- **دفاع در عمق** حفاظت قوی فراهم می‌کند
- **بهبود مستمر** در چشم‌انداز تهدیدات در حال تغییر ضروری است

---

## 🚨 گزارش مسائل امنیتی

### اگر آسیب‌پذیری کشف کردید

**ایجاد issue عمومی در GitHub نکنید**. در عوض:

1. **ایمیل**: جزئیات را به [sepehr.ghanbari@proton.me](mailto:sepehr.ghanbari@proton.me) ارسال کنید
2. **موضوع**: از پیشوند `[SECURITY]` در موضوع استفاده کنید
3. **شامل**:
   - توضیح دقیق آسیب‌پذیری
   - مراحل تکرار
   - تأثیر بالقوه
   - اقدامات تخفیف پیشنهاد شده (اگر وجود داشته باشد)

### فرآیند پاسخ

1. **تأیید دریافت**: ظرف 48 ساعت پاسخ دریافت خواهید کرد
2. ** اولویت‌بندی**: تیم امنیتی ما مسئله را ارزیابی خواهد کرد
3. **راهکار**: ما یک اصلاح توسعه و تست خواهیم کرد
4. **افشا**: افشای هماهنگ با اعتبار مناسب

### جدول زمانی

| شدت | زمان پاسخ | زمان اصلاح |
|------|------------|------------|
| بحرانی | 24 ساعت | 7 روز |
| بالا | 48 ساعت | 14 روز |
| متوسط | 72 ساعت | 30 روز |
| پایین | 1 هفته | نسخه بعدی |

---

## 🛡️ بهترین روش‌های امنیتی

### برای مشارکت‌کنندگان

#### امنیت کد
- **اعتبارسنجی ورودی**: همیشه ورودی کاربر را اعتبارسنجی و تمیز کنید
- **امنیت واسطه‌ها**: واسطه‌ها را به‌روز نگه دارید
- **مدیریت اسرار**: هرگز اسرار را در کنترل نسخه commit نکنید
- **مدیریت خطاها**: اطلاعات حساس را در خطاها افشا نکنید
- **لاگ‌گیری**: در لاگ‌ها با داده‌های حساس مراقب باشید

#### راهنمای کدنویسی امن
```python
# ✅ انجام دهید:
def process_input(user_input: str) -> str:
    # اعتبارسنجی نوع ورودی
    if not isinstance(user_input, str):
        raise ValueError("نوع ورودی نامعتبر")
    
    # تمیز کردن ورودی
    sanitized = user_input.strip()
    
    # اعتبارسنجی طول
    if len(sanitized) > MAX_LENGTH:
        raise ValueError("ورودی بسیار طولانی")
    
    return sanitized

# ❌ انجام ندهید:
def unsafe_process(user_input: str) -> str:
    # بدون اعتبارسنجی
    return user_input  # آسیب‌پذیری XSS!
```

### برای کاربران

#### امنیت استقرار
- **ایزولاسیون شبکه**: آریو را در شبکه‌های ایزوله اجرا کنید
- **کنترل دسترسی**: دسترسی به endpoints حساس را محدود کنید
- **مانیتورینگ**: لاگ‌های سیستم را برای فعالیت‌های مشکوک نظارت کنید
- **به‌روزرسانی**: آریو و واسطه‌ها را به‌روز نگه دارید
- **پشتیبان‌گیری**: به طور منظم از داده‌های حیاتی پشتیبان تهیه کنید

#### امنیت تنظیمات
- از رمزهای عبور قوی و منحصر به فرد استفاده کنید
- احراز هویت دو عاملی را فعال کنید
- به طور منظم کلیدهای API را چرخش دهید
- مجوزها را محدود کنید (اصل حداقل دسترسی)
- از HTTPS برای تمام ارتباطات استفاده کنید

---

## 🔍 ویژگی‌های امنیتی

### حفاظت‌های داخلی

1. **یکپارچگی شواهد**
   - هش SHA-256 برای تمام شواهد
   - مسیرهای بررسی غیرقابل تغییر
   - تأیید cryptographic

2. **کنترل دسترسی**
   - مجوزهای مبتنی بر نقش
   - احراز هویت مورد نیاز
   - مدیریت جلسه

3. **حفظ داده‌ها**
   - رمزنگاری در حالت استراحت
   - رمزنگاری در حین انتقال
   - حداقل‌سازی داده‌ها

4. **لاگ‌گیری بررسی**
   - تمام اقدامات لاگ می‌شوند
   - لاگ‌های ضد دستکاری
   - سیاست‌های نگهداری

### فرآیند بررسی امنیتی

تمام تغییرات کد از طریق این مراحل می‌گذرانند:
1. **اسکن خودکار**: ابزارهای تحلیل استاتیک
2. **بررسی دستی**: بررسی کد با تمرکز امنیتی
3. **بررسی واسطه‌ها**: اسکن آسیب‌پذیری
4. **تست**: موارد تست امنیتی

---

## 📊 ملاحظات امنیتی شناخته شده

### وضعیت امنیتی فعلی

| حوزه | وضعیت | یادداشت‌ها |
|------|--------|------------|
| بررسی کد | ✅ فعال | تمام PRها بررسی می‌شوند |
| اسکن واسطه‌ها | ✅ فعال | استفاده از Dependabot |
| اسکن اسرار | ✅ فعال | اسکن اسرار GitHub |
| افشای آسیب‌پذیری | ✅ فعال | افشای هماهنگ |
| تست امنیتی | ⚠️ جزئی | نیاز به تست‌های امنیتی بیشتر |
| تست نفوذ | ❌ شروع نشده | در نظر برای آینده |

### مسائل امنیتی باز

- **Issue #163**: نگرانی proxy در برنامه‌ریز loopback Ollama
  - وضعیت: در حال بررسی
  - شدت: بالا
  - اقدام: غیرفعال کردن یکپارچه‌سازی Ollama تا زمان حل

---

## 🛠️ ابزارهای امنیتی

### ابزارهای توصیه شده

1. **تجزیه و تحلیل استاتیک**
   - `bandit` - لینتر امنیتی Python
   - `safety` - چک کننده آسیب‌پذیری واسطه‌ها
   - `semgrep` - قوانین امنیتی سفارشی

2. **تجزیه و تحلیل دینامیک**
   - `OWASP ZAP` - اسکنر امنیت برنامه‌های وب
   - `Burp Suite` - اسکنر آسیب‌پذیری وب

3. **مانیتورینگ**
   - `Sentry` - ردیابی خطاها
   - `Datadog` - مانیتورینگ سیستم
   - لاگ‌گیری سفارشی

### مثال‌های استفاده

```bash
# نصب ابزارهای امنیتی
pip install bandit safety semgrep

# اجرا کردن چک‌های امنیتی
bandit -r implementation/
safety check
semgrep --config=auto implementation/
```

---

## 🎓 منابع امنیتی

### مواد آموزشی
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [امنیت Python](https://wiki.python.org/moin/Security)

### چک‌لیست‌های امنیتی
- [ ] اعتبارسنجی ورودی پیاده‌سازی شده
- [ ] کدگذاری خروجی اعمال شده
- [ ] احراز هویت مورد نیاز است
- [ ] بررسی‌های مجوز در جای خود هستند
- [ ] پیام‌های خطا اطلاعات را افشا نمی‌کنند
- [ ] لاگ‌ها حاوی داده‌های حساس نیستند
- [ ] واسطه‌ها به‌روز هستند
- [ ] اسرار به درستی محافظت می‌شوند

---

## 📞 تماس‌های امنیتی

| نقش | تماس | کلید PGP |
|------|-------|----------|
| سرپرست امنیت | sepehr.ghanbari@proton.me | در صورت درخواست |
| مالک پروژه | sepehr.ghanbari@proton.me | در صورت درخواست |

---

## ✅ تشکرهای امنیتی

ما می‌خواهیم از افراد و سازمان‌های زیر به خاطر مشارکت‌های امنیتی‌شان تشکر کنیم:

- [لیست با دریافت مشارکت‌ها پر خواهد شد]
