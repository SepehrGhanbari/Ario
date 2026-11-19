# W24 — SQLite atomicity and crash-window research, synthetic only

**Date 2026-11-18. State: RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.**

## خلاصهٔ فارسی

رفیق، در W24 دیگر فقط امضای چک‌پوینت را مقایسه نکردیم: یک نمونهٔ کوچک شاهد با SQLite ساختیم. با تراکنش BEGIN IMMEDIATE، بررسی اندازه و ریشهٔ قبلی، تأیید اثبات تداوم و ثبت وضعیت جدید را در یک تراکنش انجام می‌دهد. فقط بعد از COMMIT رسید آزمایشیِ غیررمزنگاری‌شده برمی‌گرداند. هیچ امضای شاهد، کلید خصوصی، شبکه، حافظهٔ واقعی آریو یا مجوز اجرایی به آزمایش وارد نشده است.

**مهم‌ترین نتیجه:** اگر فرایند پیش از COMMIT کشته شود، نسخهٔ قدیمی می‌ماند و می‌توان از نو اقدام کرد؛ اگر پس از COMMIT و پیش از تحویل رسید کشته شود، وضعیت جدید باقی می‌ماند و ارسال مجدد با اندازهٔ درست می‌تواند رسید آزمایشی یکسان بگیرد. درخواست‌های هم‌زمانِ یکسان هر دو نمی‌توانند وضعیت را با old_size یکسان ثبت کنند. اما مدیر دارای حق دسترسی به فایل می‌تواند نسخهٔ قدیمی SQLite را جایگزین کند؛ **این بخش هنوز حل نشده است**. تراکنش سالم برابر با نگهداری مستقل نیست.

## Primary protocol and deliberately narrower implementation

C2SP witness protocol v1.1.0: https://c2sp.org/tlog-witness@v1.1.0 ; section add-checkpoint requires a witness to atomically compare the previously cosigned size and persist the new checkpoint **before returning** a cosignature. It also prescribes HTTP statuses, request format, signatures and origin-specific trusted keys. W24 does **NOT** implement a conforming HTTP API, official wire encoding, cosigner signing, independent key custody or durable anti-rollback anchoring.

C2SP cosignature semantics: https://c2sp.org/tlog-cosignature@v1.1.0 ; no signature exists in W24. A deterministic receipt named UNSIGNED_W24_LAB_RECEIPT is a diagnostic marker, not a cryptographic assertion or a signed approval. W24 uses published W22 signer-valid synthetic size-3, size-8 and conflicting-size-8 notes plus the W20 local 3-to-8 proof.

## Actual pinned source and executed runner evidence

- research/consensus/w24_atomic_witness_lab.py: Git blob 4289c05a811ef38b7177059d1bfce90f44ea841f
- research/consensus/test_w24_atomic_witness.py: Git blob a4bcb449ea949ee412c7db1208ec8486f44d77ce
- Execution commit: 0437a1b560a5d9b648b9154ab2ca9d885e0a7433
- Actual CI run: https://github.com/SepehrGhanbari/Ario/actions/runs/44180092338
- Ubuntu 3.13 job 134381790482: **14 tests / PASS**, raw job log inspected.
- Windows 2022, Python 3.13 job 134381790812: **14 tests / PASS**, raw job log inspected.
- Replays are 14 researcher-designed tests on each OS, NOT 28 independent cases or power-loss durability certification. All uses are isolated scratch SQLite files.
- Source imports the read-only W23 signed-note verifier and proof checker. Key is a public throwaway verifier; no native Ario signer keys are read or used.

## Test matrix

| Test | Measured behavior |
| --- | --- |
| 01 bootstrap signed public fixture | SQLite retains size 3; unsigned lab receipt only |
| 02 signed 3→8 growth | valid proof, committed retained size 8 |
| 03 stale old_size 0 after size 3 | conflict, no change |
| 04 mutated consistency proof | deny, no change |
| 05 conflicting signed size-8 root | deny, retained size 8 unchanged |
| 06 repeat same valid checkpoint | deterministic unsigned receipt after successful new transaction |
| 07 modified signed text | deny before state write |
| 08 hard exit before COMMIT | SQLite transaction rollback, size 3 remains |
| 09 hard exit after COMMIT before response | size 8 retained; child emitted no receipt; replay with old_size 8 returns diagnostic receipt |
| 10 bootstrap hard exit before COMMIT | no retained head |
| 11 two independent processes, legitimate vs same-signer fork | only valid consistent head commits |
| 12 two concurrent identical requests with old_size 3 | one succeeds, the other conflicts |
| 13 attacker/admin replaces SQLite file with a valid older backup | local storage **rolls back** from 8 to 3; only a separate high-water comparison detects it |
| 14 no real authority | zero cosignatures, zero external actions, custody SAME_ADMIN_NOT_INDEPENDENT |

## Important limits / next falsifiers

1. This tests SQLite FULL synchronous and process termination under hosted Linux/Windows runners. It **does not test sudden machine power loss, filesystem honesty, storage controller lies, host snapshots, network filesystems, or same-admin root compromise**.
2. Crash-atomic local state and authenticated external anti-rollback anchoring are **separate properties**. Current external high-water in test 13 is a Python variable in the same test owner context, not authenticated independent custody.
3. Test 11 uses a fork with an invalid 3→8 proof; this **does not constitute an exhaustive race exploration** against two separately consistent future branches. More scheduling/interleavings and mutation tests are needed.
4. No real C2SP cosignature was created or served, no signed request receipt has independent public operator identity, and no real witness service was enrolled. A green CI is not an outside reviewer.
5. W25 should test durable receipt-intent state and the exact ambiguity after a post-commit lost response, concurrency across at least three conflicting future submissions, malformed external-state snapshots, and independently sourced retained high-water. Without a genuinely separate administrator, custody remains NOT_ESTABLISHED.

Research can continue without waiting for additional human reviewers; this is NOT permission to merge, deploy, unlock production signing or waive Ario/Sepehr veto.

**Status: RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / OPERATOR_INDEPENDENCE=NOT_ESTABLISHED / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.**
