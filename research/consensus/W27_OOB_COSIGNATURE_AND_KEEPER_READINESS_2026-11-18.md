# W27 — OOB cosignature readiness and independent-keeper preflight

**Date: 2026-11-18**  
**Repository:** SepehrGhanbari/Ario / research/consensus  
**Verdict:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_EXTERNAL_CONTACT / NO_ENROLLMENT / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO

## خلاصهٔ فارسی

رفیق، بستهٔ W27 را آماده کردیم تا بتوانیم بعداً یک شاهد با مدیریت واقعاً جدا را بررسی کنیم؛ بدون آنکه امروز به سرویس خارجی درخواست بفرستیم یا کلیدهای واقعی آریو را درگیر کنیم.

سورس W27 به‌صورت آفلاین چک‌پوینت امضاشدهٔ مصنوعی W22 و امضای Ed25519 شاهد مطابق C2SP v1.1 را با کلید عمومیِ ارائه‌شده در فهرست تأییدکننده مقایسه می‌کند. در همهٔ حالات وضعیت اختیار و نگهداری مستقل HOLD می‌ماند؛ چون هم کلید «دریافت‌شده از مسیر مستقل» هنوز فقط یک دادهٔ ورودی است و هم مالکیت/اختیار آن شخص به‌طور بیرونی تأیید نشده. کد هیچ کلیدی را از اینترنت کشف نمی‌کند، چیزی امضا نمی‌کند، چیزی در حافظهٔ آریو ثبت نمی‌کند، و هیچ POST یا ایمیلی نمی‌فرستد.

**شواهد واقعی: ۲۸/۲۸ آزمون روی Windows و ۲۸/۲۸ روی Linux موفق شدند.** آزمون‌ها شامل امضای سالم، امضای خراب، جعل شناسهٔ کلید، جابه‌جایی نام شاهد، چک‌پوینت دست‌کاری‌شده، تاریخ آینده/گذشته، چرخش کلید بدون احراز، نبود منبع مستقل، ادعای «مدیر دیگر» در JSON و یک چک‌پوینت منشعب ولی دارای امضای رمزنگاری‌شدهٔ صحیح‌اند. خروجی آخرین مورد crypto=VALID اما retention=NOT_ESTABLISHED است؛ چون امضای تک‌چک‌پوینت، اثبات تداوم کل تاریخچه نیست.

بستهٔ حضور احتمالی در Witness Network نیز فقط به شکل **پیش‌نویس ارسال‌نشده** ساخته شد. اطلاعات لازم مانند origin عمومیِ جدید، کلید عمومی واقعی لاگ ساختگی، نرخ qpd، تماس مورد تأیید بنیان‌گذار و پذیرش اپراتور خارجی هنوز عمداً خالی‌اند. هرگز از منشأ آزمایشی .invalid مربوط به W22 به‌عنوان لاگ عمومی واقعی استفاده نمی‌کنیم.

## Pinned machine evidence

- Executed source: research/consensus/w27_oob_cosignature_audit.py — Git blob 2f52858290314a9968aeac8ff667879e7c77d75b
- Executed tests: research/consensus/test_w27_oob_cosignature_audit.py — Git blob 0ce3bef2badd670daaa3ec541cd59736f9a99d79
- CI-triggering commit: 39b78519433f55320c40f022c558861143ab5b25
- [Actual GitHub Actions run 44378401555](https://github.com/SepehrGhanbari/Ario/actions/runs/44378401555)
- Linux Python 3.13 job 135063641418: 28 tests / PASS — raw stdout independently inspected
- Windows 2022 Python 3.13 job 135063641864: 28 tests / PASS — raw stdout independently inspected
- All 28 tests are researcher-designed, not independent blind review. W27 does not provide native root-admin separation, durable storage, live network interrogation or genuine third-party custody.

## Supporting preparation files

1. W27_INDEPENDENT_WITNESS_PREP_NO_CONTACT_2026-11-18.md — no-contact preflight, gate register with unresolved fields, nonvalid sample log-list and **UNSENT** participation letter.
2. W27_PUBLIC_WITNESS_CANDIDATES_READ_ONLY_2026-11-18.md — independently sourced *public directory discovery* of publicly listed operator names/about pages, no claim their keys or admins are independently verified.
3. w27_oob_cosignature_audit.py — strict bounded verifier, no network or writing; Ed25519 subset only.
4. test_w27_oob_cosignature_audit.py — 28 positive and falsification cases including valid signed fork and fake different-operator metadata.

## Primary standards and community sources

- [C2SP witness protocol v1.1.0](https://c2sp.org/tlog-witness@v1.1.0): compatible add-checkpoint, monitor retrieval endpoint and atomic saved head before signature response.
- [C2SP cosignatures v1.1.0](https://c2sp.org/tlog-cosignature@v1.1.0): cosignature/v1 Ed25519 message, unsigned 8-byte big-endian timestamp in note signature payload.
- [C2SP checkpoints v1.1.0](https://c2sp.org/tlog-checkpoint@v1.1.0): Ed25519 log type 0x01, Ed25519 cosigner type 0x04; ML-DSA-44 type 0x06 not implemented in W27.
- [C2SP tlog-policy](https://c2sp.org/tlog-policy): witness-quorum rules; cryptographic quorum does not attest organizational independence.
- [Witness Network about](https://witness-network.org/) and [participation](https://witness-network.org/participate/): community is experimental; testing and staging available, production not. Maintainers recommend human-to-human communication.
- [Witness Network current public tables](https://witness-network.org/witness-tables/): publicly listed potential operators, NOT independent keys/hosts vetted for Ario. No enrollment request submitted.

## Research conclusion and no-go gates

- CRYPTO_C2SP_ED25519_SUBSET_VERIFICATION: BOUNDED_PASS (synthetic)
- OUT_OF_BAND_KEY_PIN_AUTHENTICITY: NOT_ESTABLISHED
- OPERATOR_INDEPENDENCE: NOT_ESTABLISHED
- RETAINED_MONITOR_HEAD_AND_CONSISTENCY: NOT_VERIFIED
- SAME_ADMIN_RESTORE_AND_FORK_RESISTANCE: NOT_ESTABLISHED
- ACTUAL_LIVE_ARIO_LOG: NONE
- EXTERNAL_COMMUNICATIONS: NONE
- WITNESS_NETWORK_ENROLLMENT: NONE
- PUBLIC_SYNTHETIC_LOG: NOT_DEPLOYED
- POWER_LOSS, COMPROMISED_OPERATOR, CLOCK_SPOOFING: NOT_TESTED
- GENESIS/TRUST/PRODUCTION: NO_GO
- MERGE: NO_MERGE

**Next decision (not automatically authorized):** obtain a newly created, nonpersonal synthetic C2SP-compatible test log with stable origin and an approved public contact/rate, then seek the founder's explicit approval before sending a participation request. In parallel, design a non-invasive independent OOB key-identity challenge and externally retained high-water audit. No other human reviewer need be silently fabricated; external independent operation can only be verified by evidence from an actually separate administrator, not by additional local scripts.

**Final verdict: W27_PREP_COMPLETE / REAL_INDEPENDENT_CUSTODY_HOLD.**
