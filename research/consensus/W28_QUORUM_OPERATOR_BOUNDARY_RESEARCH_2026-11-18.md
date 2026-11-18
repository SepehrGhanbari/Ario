# W28 — Quorum signatures vs true independently administered custody

**2026-11-18 — RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_EXTERNAL_CONTACT / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## خلاصه فارسی

رفیق، W28 یک نگهبان آزمایشی است که امضای معتبر و تداوم درخت مرکل را با استقلال مدیریتی اشتباه نمی‌گیرد. چک‌پوینت‌های امضاشده مصنوعی W22 (درخت ۳ و ۸ و یک fork با امضای معتبر) با اثبات مرکل W20 و امضاهای دو شاهد آزمایشی W27 بررسی شدند.

**نتیجه قطعی در محدوده آزمایش: ۳۷/۳۷ آزمون Windows و ۳۷/۳۷ آزمون Linux موفق.** حتی وقتی دو امضای سالم با دو کلید متفاوت، دو نام متفاوت و اثبات تداوم درست داریم، نتیجه فقط CRYPTOGRAPHIC_QUORUM_AND_CONSISTENCY_BOUNDED_PASS_ONLY / HOLD است، نه پذیرش شاهد مستقل.

اگر دو نام یک کلید عمومی داشته باشند، امضاها دو رأی محسوب نمی‌شوند. اگر دو کلید در یک گروه مدیریتی ادعایی باشند، تعارض اعلام می‌شود. اگر گروه‌ها هم ادعای استقلال کنند، آن ادعا خوداظهاری است و وضعیت STILL HOLD می‌ماند. هیچ کلید واقعی آریو یا درخواست خارجی وارد آزمون نشده است.

**شکست اولیه حفظ شد:** نخستین اجرای CI با ۹ failure و ۲ error روبه‌رو شد چون Base64 می‌تواند کاراکتر + داشته باشد و Parser به اشتباه از آخرین + کلید عمومی را تقسیم می‌کرد. با تفکیک فقط دو جداکننده اول اصلاح شد. همه ۳۷ آزمون روی هر دو OS دوباره اجرا و موفق شدند.

## 1. Exact source pins and verified CI

- Source: research/consensus/w28_quorum_independence_falsifier.py ; Git blob ab0f09698ea39dbc3bcbf5edf4a739195f8fab5f
- Tests: research/consensus/test_w28_quorum_independence_falsifier.py ; Git blob 413674c666d59818fea835ee51ef96c76b29e295
- Initial FAILED CI (both OS): https://github.com/SepehrGhanbari/Ario/actions/runs/44384989837 ; trigger e74539b330e79b45e040bd487a77d47c344c2acd
- Minimal fix: commit 9559393e4121139761a06dfd10045b77a4792888
- **Final real GitHub Actions CI:** https://github.com/SepehrGhanbari/Ario/actions/runs/44385149052
- Ubuntu Python 3.13 job 135087546434: 37/37 PASS; actual raw job log read
- Windows 2022 Python 3.13 job 135087545872: 37/37 PASS; actual raw job log read
- Author-designed regression checks, not blind third-party review. Cross-OS CI is not independent operator custody.

## 2. Positive cases and falsifiers

| Input and threat | Observed result |
| --- | --- |
| W22 valid signed 3→8 growth + W20 Merkle proof + two W27-format test cosignatures | Cryptographically bounded pass, operational policy remains HOLD |
| Repeated same signer listed as two votes | DENY |
| Distinct signer names wrapping the same underlying Ed25519 public key | DENY |
| Only one signature for a two-signature required threshold | DENY |
| Different keys self-claiming one common administrator | HOLD / CLAIMED_OPERATOR_GROUP_COLLISION |
| Different keys self-claiming different independent administrators | STILL HOLD; no external identity proof |
| Valid signed older tree 8→3 compared with supplied size-8 head | Rollback detected |
| Same-size valid signed fork compared with supplied original head | Fork detected |
| Both supposedly prior and new heads rolled back to old size 3 | Internal consistency can still pass. **Not detectable without independently retained head.** |
| No previous pinned checkpoint supplied | NO_PREVIOUS_HEAD_SELF_REPORTED; no anti-rollback proof |
| Altered consistency proof, wrong note, malformed signature, stale/future timestamp | DENY |
| Unpinned witness, swapped note/signature, altered log origin, key name collision | DENY |
| Valid signatures and a matched claimed quorum | Never elevate to TRUST_ACTIVATION, never admit memory |

All outputs preserve operational authority NONE, Genesis and Production NO_GO, trust activation NO_GO, external actions ZERO, and independent operator custody NOT_ESTABLISHED.

## 3. Official standards: what is and is not claimed

- https://c2sp.org/tlog-witness@v1.1.0 : official witness protocol for verification and persistence before cosignature.
- https://c2sp.org/tlog-cosignature@v1.1.0 : a cosignature refers to log origin, root, size, timestamp and signer history; no automatic statement of administrator independence.
- https://c2sp.org/tlog-policy : development-stage policy schema includes known logs, witnesses and quorum groups; different names have no inherent organizational meaning and duplicate underlying public keys are prohibited.
- https://witness-network.org/participate/ : any public enrollment or operator contact is outside W28.

W28 is NOT a tlog-policy parser, C2SP HTTP witness, OOB key provenance verifier, independently retained head monitor, complete event witness, production signer, or assurance that the world has no hidden fork.

## 4. Remaining gating decision

W28_CRYPTO_CHECKS = BOUNDED_PASS; OOB_PIN_AUTHENTICITY = NOT_ESTABLISHED; EXTERNAL_OPERATOR_INDEPENDENCE = NOT_ESTABLISHED; RETAINED_EXTERNAL_HIGH_WATER = NOT_ESTABLISHED; REAL_ARIO_EVENTS = NONE; LIVE_NETWORK = NONE; KEY_ACTIVATION = NO_GO; TRUST_ACTIVATION = NO_GO; GENESIS = NO_GO; MERGE = NO_MERGE.

Next research W29: simulate two observation channels with independent histories and deliberate loss/rollback, then identify what concrete external evidence would turn the existing simulated separation into actual separately administered custody. No automatic confidence upgrade should occur.

**RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO.**
