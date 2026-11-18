# W26 — Native Linux UID and SO_PEERCRED custody research

**2026-11-18 — RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## خلاصهٔ فارسی

رفیق، W25 نشان داد دو دیتابیس تحت اختیار یک مدیر شاهد مستقل نیستند. در W26 با سه UID متفاوت واقعی در هسته Linux آزمایش کردیم. فایل ناشر، دفتر شاهد، و یک سرویس سوکت محلی فقط‌خواندنی زیر هویت‌های جدا قرار گرفتند. ناشر غیرممتاز نتوانست دفتر شاهد را بخواند، تغییر دهد، پاک کند، بازنام‌گذاری کند یا از راه‌های پیوند سخت/نمادین جایگزین کند؛ از طریق سوکت مجاز فقط سرآیند عمومی را خواند. Linux SO_PEERCRED هویت محلی فرایند متصل را مشخص کرد.

**آزمایش واقعی GitHub Actions: ۲۴/۲۴ کنترل بومی Linux و ۱۰/۱۰ تست سیاستی موفق شدند.**

**محدودیت حیاتی:** کاربر root همان ماشین توانست فایل شاهد را تغییر دهد و سپس در آزمایش برگرداند. بنابراین جداسازی دسترسی بین دو UID در محدودهٔ همان ماشین اثبات شد، اما استقلال واقعی مدیر/نگهدارنده اثبات نشد. حتی اگر ارتباط با سوکت از UID صفر رد شود، مدیر root می‌تواند خود را به‌جای UID مجاز اجرا کند. هیچ امضای شاهد، کلید اصلی آریو، حافظهٔ اصلی یا اقدام تولیدی انجام نشده است.

## 1. Actual source and runnable evidence

- Source: research/consensus/w26_linux_uid_lab.py — exact Git blob 7a514c35921db204f89492788d865b9d6aaf9265
- Tests: research/consensus/test_w26_linux_uid_lab.py — exact Git blob 4b4456c1efdabe6f246591eeaf982d700280efaf
- Final CI-triggering source commit: 17abf487c1857af35efc2ed8b8cae6da913336fa
- [Actual final GitHub Actions run 44376106044](https://github.com/SepehrGhanbari/Ario/actions/runs/44376106044)
- Native Linux job 135055592210 — PASSED 24/24; exact runner JSON includes root_admin_can_override=true and independent_operator_custody=NOT_ESTABLISHED
- Policy job 135055591411 — PASSED 10/10; raw job logs independently read from GitHub
- Local disposable Linux container Python 3.13.5 — 24/24 native + 10/10 policy, actual source blob verified against GitHub readback
- Ubuntu 24.04 GitHub-hosted jobs used. Windows native SID/ACL was **NOT_RUN** in W26.

## 2. Historic failed CI attempts (preserved, not relabeled)

- [run 44374995352](https://github.com/SepehrGhanbari/Ario/actions/runs/44374995352): policy passed but native job failed *before its tests* because private GitHub checkout path was inaccessible to synthetic UID.
- [run 44375303196](https://github.com/SepehrGhanbari/Ario/actions/runs/44375303196): policy passed, native failed *before tests* because the runner-private RUNNER_TEMP ancestor was unreadable to synthetic UID.
- [run 44375590477](https://github.com/SepehrGhanbari/Ario/actions/runs/44375590477): policy passed; native failed *before tests* because the child guard attempted to resolve inaccessible runner-private RUNNER_TEMP.
- Final [run 44376106044](https://github.com/SepehrGhanbari/Ario/actions/runs/44376106044): both jobs passed. The final code created only a fresh randomized root-owned /tmp/ario-w26-* scratch directory within a disposable runner, copied the script byte-for-byte into that directory, and scoped the child guard to that directory; it did **not** widen permissions of GitHub checkout or RUNNER_TEMP. It also drains one bounded request before denying an unauthorized socket peer to avoid a send/close race.

## 3. Test matrix and falsification

| Native operation | Observed result |
| --- | --- |
| Publisher reads own state | ALLOWED |
| Publisher reads, truncates, unlinks, chmods, renames witness file | DENIED |
| Publisher creates, symlinks or hardlinks inside witness directory | DENIED |
| Witness reads own state, publisher cannot write it directly | ALLOWED for witness / DENIED for publisher |
| Witness reads publisher-private file | DENIED |
| Publisher unlinks witness-owned socket | DENIED |
| Publisher reads public head through read-only Unix socket | READ_ONLY_HEAD |
| Third UID connects to socket | DENIED_PEER_UID |
| Publisher sends unsupported WRITE or oversized message | DENIED |
| Socket peer with UID 0 not on allowlist | DENIED_PEER_UID |
| Ledger bytes after unprivileged attack attempts | UNCHANGED |
| Shared root rewrites witness-owned ledger directly | **SUCCEEDED** — counterexample to independent-administration claim |
| Actual witness cosignatures, external messages, production effects | ZERO |

These are 24 developer-designed checks, not an exhaustive threat-model or blind security evaluation. Unix SO_PEERCRED authenticates a LOCAL kernel UID, not an independent cloud operator, ownership history or out-of-band public key. The W26 served head is a fixed synthetic public test object; no complete C2SP witness or W25 signer interface was installed.

## 4. Specifications and next scope

- [C2SP tlog-witness v1.1.0](https://c2sp.org/tlog-witness@v1.1.0) requires cryptographic checkpoint verification and persistent witness state before cosignature response. W26 tests **only** local OS access boundaries.
- [Linux capabilities manual](https://manpages.ubuntu.com/manpages/noble/man7/capabilities.7.html) describes capabilities that allow privileged code to bypass ordinary file permissions. Two UIDs on a root-administered machine do not establish true independent custody.
- Current: OS_NATIVE_UID_DAC=BOUNDED_PASS; LOCAL_PEERCRED=BOUNDED_PASS; SHARED_ADMIN_ANTI_ROLLBACK=NOT_ESTABLISHED; OUT_OF_BAND_KEY_PIN=NOT_ESTABLISHED; WORLD_FRESHNESS=UNKNOWN; TRUE_ARIO_EVENT_CAPTURE=NOT_ESTABLISHED.
- W27 should investigate a **genuinely separately administered** retention operator with an out-of-band authenticated key and external checkable receipt, or prepare only a read-only interoperability and preregistration design until explicit consent for durable public test-log submission. Do not infer true independence from two VMs, two accounts, two UIDs, two bots, or one owner's cloud accounts.
- No merge, key change, Genesis, founder/Ario veto change, trust activation, or production authorization.

**Final: RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.**
