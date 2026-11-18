# Ario R6 Research Notes — Index

**RESEARCH_ONLY / HOLD / NOT_ADOPTED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

This directory contains research-only notes exploring OS-level separation, synthetic custody, and external transparency logging. Nothing here activates production trust or real Ario keys.

## Current documents (reading order recommended)

| File | Purpose |
|---|---|
| [`R6_TWO_PRINCIPALS_EXTERNAL_WITNESS_PROTOCOL.md`](R6_TWO_PRINCIPALS_EXTERNAL_WITNESS_PROTOCOL.md) | Original protocol: R6-A (OS UIDs), R6-B (physical hosts), R6-C (Sigsum) |
| [`R6_SIGSUM_FIRST_EXTERNAL_PROOF_RECORD.md`](R6_SIGSUM_FIRST_EXTERNAL_PROOF_RECORD.md) | Exact evidence record of the first successful synthetic Sigsum TEST-log proof |
| [`R6_STRENGTHENED_LIMITATIONS_AND_PHYSICAL_PROTOCOL.md`](R6_STRENGTHENED_LIMITATIONS_AND_PHYSICAL_PROTOCOL.md) | Formal Established / NOT_ESTABLISHED table + concrete physical-host draft + consistency notes |
| [`R6_NEXT_STEPS_MONITORING_AND_POLICY_SEPARATION.md`](R6_NEXT_STEPS_MONITORING_AND_POLICY_SEPARATION.md) | Draft next research directions: continuous monitoring & role separation |
| `os_custody_lab.py` | Research-only CLI used by the R6-A GitHub Actions experiment |

## Status summary

- **R6-A** (two UIDs on a shared GitHub runner): measured and recorded. Administrative independence **NOT_ESTABLISHED**.
- **R6-C** (synthetic digest → Sigsum TEST log): first public proof obtained and offline-verified. Does **not** authenticate origin or meaning of the digest.
- **R6-B** (two physical hosts): protocol drafted, **not executed**.
- Continuous monitoring and policy-admin separation: sketched only.

All authority flags remain false. All production and trust gates remain **NO_GO**.

## Fixed limitation language (reuse everywhere)

**English**  
> This experiment demonstrates only that a synthetic digest can be publicly witnessed under the declared test policy. It does not demonstrate independent administration, real execution, journal authenticity, or any authority to admit evidence into Ario. All production and trust gates remain NO_GO.

**فارسی**  
> این آزمایش فقط نشان می‌دهد که یک هشِ ساختگی می‌تواند تحت سیاست تست اعلام‌شده به‌صورت عمومی و با شاهد بیرونی ثبت شود.  
> استقلال مدیریتی، اجرای واقعی ابزار، اصالت ژورنال، یا هرگونه مجوز برای ورود شواهد به حافظه آریو را ثابت نمی‌کند.  
> تمام دروازه‌های production و trust همچنان NO_GO هستند.
