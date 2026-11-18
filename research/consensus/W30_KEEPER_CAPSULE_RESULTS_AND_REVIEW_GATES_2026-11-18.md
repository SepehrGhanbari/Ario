# W30 — External-keeper evidence capsule (OFFLINE, UNSENT) + falsification record

**2026-11-18 — RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_CONTACT / NO_EXTERNAL_SUBMISSION / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## خلاصهٔ فارسی برای بنیان‌گذار

رفیق، در W30 یک قالب «رسیدِ نگهدارندهٔ بیرونی» ساختیم تا زمانی که روزی نگهدارنده‌ای **واقعاً مستقل** داشته باشیم، بتوانیم مدارک او را بدون حدس بررسی کنیم. این مرحله صرفاً آفلاین است؛ «نگهدارندهٔ بیرونی» هنوز واقعاً متصل نیست.

این رسید آزمایشی یک زنجیرهٔ امضاشده با سه نوع رویداد دارد:
- OBSERVE: ثبت چک‌پوینتِ امضاشدهٔ لاگ و اثبات تداوم Merkle
- ROTATE: انتقال کلید با امضای کلید قبلی **و پذیرش امضاشدهٔ کلید جدید**
- REVOKE: ثبت ابطال کلید فعال؛ بعد از آن هیچ رکورد جدیدی معتبر نیست

هر رکورد شمارهٔ پیوسته، زمان اعلام‌شده، شناسهٔ لاگ، هش رکورد قبلی و امضای Ed25519 جداگانه دارد. ساختار از JSON با ترتیب کلیدِ ثابت و دامنهٔ امضای اختصاصی W30 استفاده می‌کند. **این امضا، امضای C2SP Witness نیست**؛ فقط قالب پژوهشی آریو است. چک‌پوینت‌های درون رسید جداگانه با W23/C2SP Ed25519 و اثبات مرکل بررسی می‌شوند.

**شواهد واقعی:** GitHub Actions روی Windows و Linux هر کدام ۶۰/۶۰ آزمون موفق. اجرای نخست قرمز بود؛ ۱۳ آزمون مسیر موفق به خطای تولید پاسخ برخورد می‌کردند، چون کلید تشخیصی در شیء نتیجه دوبار مقداردهی می‌شد. علت اصلاح و کد منطق گزارش نتیجه با فهرست مجازِ فیلدهای تشخیصی سخت‌گیرانه شد. تاریخچهٔ قرمز پاک نشده است.

مهم‌ترین نتیجهٔ منفی این است که اگر **تمام زنجیرهٔ رسید و رکورد مرجعِ ذخیره‌شده** با هم به گذشته برگردند، آزمایش نمی‌تواند به‌تنهایی کشف کند که قبلاً ابطالی ثبت شده بود. رکورد مرجع همچنان از ورودی فراخوان می‌آید و منشأ مستقل آن به اثبات نرسیده است. خودِ مالک کلید نیز می‌تواند یک زنجیرهٔ امضاشدهٔ ظاهراً معتبر بسازد. امضای خوب جای استقلال نمی‌نشیند.

## Exact executable evidence and pins

- Verified code: research/consensus/w30_offline_custodian_capsules.py — Git blob a81bbd9d69e84cbd1989cb0e5ddd5405da7ed05b
- Verified 60 tests: research/consensus/test_w30_offline_custodian_capsules.py — Git blob 32d03095bf1a73d4ef4d4d8ddecdeb47c1e6a554
- Final CI-triggering commit: d03c3344e6531a6ebac057f26781d359fcb313fc
- **Actual successful GitHub Actions:** https://github.com/SepehrGhanbari/Ario/actions/runs/44390349888
  - Ubuntu Python 3.13 job 135105972179: Ran 60 tests, OK — raw logs inspected
  - Windows 2022 Python 3.13 job 135105972643: Ran 60 tests, OK — raw logs inspected
- **Historical failed GitHub Actions (do not relabel as PASS):** https://github.com/SepehrGhanbari/Ario/actions/runs/44390151437
  - Ubuntu 135105277947: 60 attempted; **13 ERROR** in success path, not cryptographic verification failures.
  - Windows 135105278730: FAILED; full count not asserted here.
  - Fix: return diagnostics added through an explicit allowlist, with permanent NO_GO and authority=NONE labels protected.
- No external key discovery, no actual independent witness, no external write, no real private Ario key, no production signer or memory writes.

## Selected experimental checks

| Research input | Bounded outcome |
| --- | --- |
| Original W22 signed size-3 note | Valid source signature for published synthetic log |
| Size-3 to size-8 with original W20 proof | Valid bounded Merkle consistency |
| Chained records with separate receipt Ed25519 signatures | Valid for *caller-provided* initial key |
| Change previous hash, delete middle record, reorder or duplicate | Reject chain |
| Signed size-8 to size-3 rollback or equal-size signed fork | Reject |
| Corrupt W22 signed note, modified proof, mutated capsule signature | Reject |
| Rotate key with old-key signature and new-key consent | Verify in research only |
| Rotate without dual consent, reuse old key, use obsolete key after rotation | Reject |
| Revoke current active key; attempt later event | Reject subsequent event |
| Remove revocation while unchanged later floor exists | Detect truncated chain |
| Remove revocation **and replace floor** with earlier matching value | **Undetectable as rollback** using only caller-provided records |
| Attacker creates fresh signing key and self-pinned signed receipt | Cryptographically valid, but independence remains NOT_ESTABLISHED |
| Claimed operator label says independent | Never treated as independent identity proof |
| Valid timestamp | Only locally checked declared timestamp; no trusted clock or world freshness attested |
| Test-only private keys | Generated in test RAM; verifier has no signer API |

## Security, interoperability and governance boundaries

- Primary C2SP semantics: https://c2sp.org/tlog-witness@v1.1.0 , https://c2sp.org/tlog-cosignature@v1.1.0 , https://c2sp.org/tlog-checkpoint@v1.1.0 . The **embedded W22 note** uses a strict Ed25519 C2SP signed-note subset, but custom W30 JSON receipt signature is **NOT a normative C2SP cosignature**.
- W30 canonical JSON is a strict research encoding, **not** general JCS/RFC8785; interoperability with another independently written validator has NOT been established.
- The initial Ed25519 receipt-verifier key is supplied by the caller. Neither its source nor the administrator who controls its secret key is independently verified.
- Rotation/REVOKE processing records are only about the **research receipt key**; they are **not** Ario founder key or Ario autonomous key rotation/revocation procedures.
- Record time is an untrusted self-asserted POSIX timestamp constrained by a caller-supplied evaluation time. It is NOT independently trusted.
- Replaying a truncated historical chain and replacing the caller-provided floor can erase evidence of prior revocation unless a genuinely separate custodian retains the earlier hash.
- A green CI job demonstrates reproducible author-designed tests, **not** independent source review. A dedicated reviewer issue must remain open with explicit non-merge gates.
- Full C2SP wire compatibility, ML-DSA, independent keeper, external monitored head, power-cut durability, independent backups, compromised operators, and real Ario event origin are **NOT_TESTED**.

## Release gate / reviewer checklist

1. **P0:** Verify independent admin custody and an OOB-authenticated initial pin **outside claimant's infrastructure**. Two websites, two devices or two cloud accounts under one administrator do not suffice.
2. **P0:** Independently retained high-water floor and revocation record, plus evidence of a keeper's own rollback/recovery and full readback after loss of one source.
3. **P0:** Reject signature-only promotion into production, memory, Genesis, signers, trust or any policy authority.
4. **P1:** Have a second, separately written verifier audit exact canonical byte encoding and signature semantics (test independent vector acceptance, not shared Python code).
5. **P1:** Verify rotation two-key consent, revoked-key replay, unknown schema/fields, malformed base64, hash-chain continuity, signed inconsistent log head, time metadata.
6. **P1:** Check actual log contents are synthetic/public and founder explicitly approves external submission before any participation/email or public archive.
7. **P1:** Distinguish the custom W30 research capsule format from standard C2SP checkpoint cosignature; no premature interoperability claim.

**FINAL: W30_OFFLINE_TESTS=BOUNDED_PASS; REAL_INDEPENDENT_KEY_PROVENANCE=NOT_ESTABLISHED; RETAINED_THIRD_PARTY_FLOOR=NOT_ESTABLISHED; READY_TO_MERGE=NO; PRODUCTION=NO_GO.**
