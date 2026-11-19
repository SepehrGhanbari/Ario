# W31 — Real external OpenTimestamps pilot, PUBLIC SYNTHETIC ONLY

**2026-11-19 — RESEARCH_ONLY / PENDING / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## خلاصهٔ فارسی برای سپهر

رفیق، این بار یک قدم واقعی بیرون از آزمایشگاه برداشتیم: **هش ۳۲‌بایتی یک فایل کاملاً ساختگی و عمومی را واقعاً به دو سرور خارج از گیت‌هاب و آریو فرستادیم.** هر دو سرور Alice و Bob در شبکهٔ OpenTimestamps پاسخ HTTP 200 دادند و رسید Pending واقعی برگرداندند.

رسیدها را با کتابخانهٔ رسمی OpenTimestamps نسخهٔ 0.5.0 در Linux و Windows بررسی کردیم. هر کدام یک گواه Pending برای همان هش داشتند، به قالب فایل مستقل .ots تبدیل شدند و پس از تبدیل نیز بدون اختلاف بازخوانی شدند.

**این هنوز شاهد مستقل C2SP نیست و زمان Bitcoin هم هنوز تأیید نشده است.** سرور تقویم وعدهٔ ثبت هش را داده، اما نه کلید مستقل شاهد آریو احراز شده، نه مدیران این سرورها از نظر استقلال ممیزی شده‌اند، نه بلاک تأییدشده‌ای را راستی‌آزمایی کرده‌ایم. دادهٔ واقعی آریو، گفتگو، کلید خصوصی یا حافظه منتشر نشده است.

## 1. Exact evidence and pinned references

- Public LF-byte fixture: research/consensus/W31_PUBLIC_SYNTHETIC_TIMESTAMP_PREIMAGE_2026-11-19.json
- Exact original Git blob (765 bytes): 138c8b056dd3387f31f5a0facedf43b0f221b742
- Exact SHA256 of original Git blob: 2078bc80586d0e4b00afa48eb8dea31ab3d4749b4912c57a897e4d5e2fb436df
- Allowlisted one-shot sender: research/consensus/w31_public_ots_calendar_probe.py
- **Real external POST GitHub Actions run 44531802958:** https://github.com/SepehrGhanbari/Ario/actions/runs/44531802958 ; job 135586756893
- Full original raw calendar receipts (base64 included): research/consensus/W31_OTS_TWO_CALENDAR_PENDING_RECEIPTS_2026-11-19.json
- Official-library no-network verifier: research/consensus/w31_verify_ots_pending_receipts.py
- Verified binary detached .ots outputs, encoded base64: research/consensus/W31_OTS_OFFLINE_VALIDATED_DETACHED_PROOFS_2026-11-19.json
- **Final real cross-OS offline parser run 44532669602:** https://github.com/SepehrGhanbari/Ario/actions/runs/44532669602 ; Ubuntu job 135589817210 PASS, Windows job 135589817757 PASS. Outputs byte-for-byte equivalent.
- Initial offline parser run 44532389345: https://github.com/SepehrGhanbari/Ario/actions/runs/44532389345 ; Linux PASS, **Windows FAIL** because checkout converted LF to CRLF. Fixed with git cat-file blob of the pinned original Git object, not by normalizing the committed fixture. This RED run remains preserved.
- One-shot external POST workflow REMOVED immediately after successful responses in commit c2c7392b1ac651e46ef9889e16021002df449f68.

## 2. Two actual calendar responses

| Calendar | HTTPS | Raw reply | Reply SHA256 | OTS pending parser |
| --- | --- | --- | --- | --- |
| alice.btc.calendar.opentimestamps.org | 200 | 137 bytes | 030343de6dfcc98a6915557249aff35fe45a19fb664a3356dec163ed3d8f71f2 | PASS, 1 pending, 0 Bitcoin |
| bob.btc.calendar.opentimestamps.org | 200 | 135 bytes | d560880e03078f60e9363fd929a1ab6ffd1b1f95e245a872c6606f1a5da20a38 | PASS, 1 pending, 0 Bitcoin |

Derived and round-trip verified detached binary proofs:

- Alice: 202 bytes, SHA256 676c0f99d485cb24f1d80354c38bc043dbe51dffe7f0bd6e1dc992d85fdb7ba4
- Bob: 200 bytes, SHA256 7c6442facc66e3ab4cbf7b532ddccbd3fe5a15ce3f321e1b85f2b93d9dff999c

Both binary proofs are retained as full base64 inside the recorded JSON so a separate implementation can reconstruct and recheck them. No BTC block confirmation is present; no future upgrade has been tested.

## 3. Important limitations / no false independence

1. A real, externally administered HTTPS service responded to a public synthetic hash: OBSERVED. This is an actual external interaction, not just a local SQLite simulation.
2. Two calendar names do not establish that their managers are distinct or noncolluding: ADMINISTRATIVE_INDEPENDENCE=NOT_ESTABLISHED.
3. They are OpenTimestamps calendars, **not C2SP tlog-witness services**. No actual Ario C2SP cosignatures or independently authenticated witness keys have been received.
4. The fixture file is NOT the actual Ario event log, memory, Genesis state or signer ledger. There is no proof of semantic truth, log completeness or hidden-fork absence.
5. A pending calendar receipt is NOT a confirmed Bitcoin timestamp. Actual blockchain verification and future retention/upgrade are NOT_ESTABLISHED.
6. All cryptographic parsing/CI evidence is from author-provided tools and the official library, NOT an independently commissioned source review.
7. No permanent service, account, email, personal data, key, login, rule, trust setting, main branch merge or production path was touched.

## 4. Next evidence gates

- Upgrade the two *existing* pending proofs when the calendars expose a Bitcoin-rooted attestation, and verify the block against an independently retrieved Bitcoin header. No need to re-POST the digest.
- Preserve initial pending proofs and their exact Git hashes, rather than rewriting history when upgrading.
- Distinguish external timestamp existence from actual independent C2SP checkpoint witness custody.
- Continue source review in Issue #284, marking external C2SP custody and OOB pinned witness identity as NOT_ESTABLISHED.

References: https://opentimestamps.org/ ; https://c2sp.org/tlog-witness@v1.1.0 ; https://c2sp.org/tlog-cosignature@v1.1.0

**FINAL: REAL_EXTERNAL_PENDING_RESPONSES=2/2; OFFLINE_PROOF_PARSE_LINUX_WINDOWS=PASS; BITCOIN_ANCHOR=NOT_CONFIRMED; INDEPENDENT_C2SP_WITNESS=NOT_ESTABLISHED; PRODUCTION=NO_GO.**
