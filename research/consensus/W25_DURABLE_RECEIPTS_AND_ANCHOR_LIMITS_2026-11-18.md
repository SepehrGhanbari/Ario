# W25 — Durable unsigned receipts and simulated anchor rollback boundaries

**2026-11-18 — RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## خلاصهٔ فارسی

رفیق، در W25 آزمایش کردیم که بعد از ثبت پایدار چک‌پوینت، اگر پاسخ به درخواست‌کننده گم شود، بتوان دقیقاً همان رسید را بازیابی کرد. دو پایگاه SQLite آزمایشی جدا ساختیم: دفتر درخواست/رسید و دفتر مرجع چک‌پوینت. هر دو زیر اختیار **همان مدیر آزمایش** هستند؛ بنابراین این **یک شاهد مستقل واقعی نیست**.

درخواست ابتدا PENDING می‌شود و هیچ رسیدی ندارد. مرجع جداگانه با کلید عمومی آزمایشیِ صریح، امضای چک‌پوینت و اثبات تداوم را می‌سنجد و وضعیت را ثبت می‌کند. نهایی‌ساز تنها در صورت تطبیق تاریخچه، رسید تشخیصی **غیررمزنگاری‌شده** را همراه با وضعیت FINAL به‌طور پایدار ثبت می‌کند. کلید واقعی آریو، امضای شاهد واقعی، شبکهٔ خارجی، حافظهٔ اصلی یا اختیار تولیدی وارد آزمایش نشده است.

**نتیجهٔ مثبت:** بازیابی بعد از سقوط و گم‌شدن پاسخ، درخواست‌های تکراری، تعارض شناسه، درخواست‌های هم‌زمان، فساد پایگاه‌داده، دست‌کاری رسید و اعتبار واقعی فایل‌های W22 بررسی شدند؛ آخرین اجرای GitHub Actions در هر دو Windows و Linux تعداد **۲۸/۲۸ PASS** داشت.

**نتیجهٔ منفی:** اگر هر دو دیتابیس با اختیار مدیر مشترک به نسخهٔ قدیمی برگردند، مقایسه می‌تواند همچنان MATCH شود. مدیر مشترک حتی می‌تواند مرجع ساختگیِ مورد انتظار را در فایل ناظر وارد کند. این مثال نقض، استقلال نگهداری و احراز هویت بیرونی را رد می‌کند؛ استقلال در عمل **NOT_ESTABLISHED** است.

## Exact source and pinned CI

- Source: research/consensus/w25_receipt_anchor_lab.py ; Git blob 203dd84795460dc6d62dfe68638d2406db8a28bd
- Tests: research/consensus/test_w25_receipt_anchor.py ; Git blob 58aa8a96f84f2343ac4cff689a75c5d83b65c369
- CI-trigger commit: 267a5239b10c70b4d8b2f9af7b43ba3296a9ba78
- Final actual CI: https://github.com/SepehrGhanbari/Ario/actions/runs/44358311510
- Windows 2022 Python 3.13 job 134992360380: **28 of 28 PASS**, real job stdout checked
- Ubuntu Python 3.13 job 134992361139: **28 of 28 PASS**, real job stdout checked
- Prior baseline (only 27 tests): https://github.com/SepehrGhanbari/Ario/actions/runs/44357631533 . **Do not relabel its 27/27 as 28/28.**
- Local preliminary: 27 discovered cases, 26 passed and one W22-specific case skipped because GitHub fixture files were absent from disposable local scratch. Final local: 28 cases, 27 passed and one W22-specific case skipped. **Both official GitHub runners actually ran and passed the W22 signed-note/consistency/fork case.**
- Dependencies: previously published W23 strict signed-note reader, W22 synthetic valid/fork notes and W20 compact proof; ephemeral W25 test keys exist in RAM only. All tests author-designed, not blind validation.

## Technical evidence

The local database stores request ID, original expected size, public signed-note hash/root, proof hash, PENDING/FINAL state, and unsigned deterministic diagnostic receipt. The simulated anchor database stores its latest size/root and a historical size/root record. Each update uses a SQLite transaction. Checks and persistence precede any diagnostic receipt response.

Cases demonstrated:
- after-prepare-commit crash: durable pending state, repeat request resumes;
- before-anchor-commit crash: anchor remains old, finalize holds;
- after-anchor-commit crash: anchor retains progress, finalize resumes;
- before-final-commit crash: no issued receipt, retry completes;
- after-final-commit crash: requester's lost response is recovered exactly;
- duplicate request identity with different signed bytes: denied;
- concurrent same-request finalization: equal stored receipts;
- wrong log signature, mismatched proof or signed fork: rejected;
- single-database rollback against newer retained anchor: detected;
- coordinated rollback of both same-admin databases: NOT DETECTED;
- forged same-admin anchor contents can produce synthetic success: custody authenticity NOT ESTABLISHED;
- invalid SQLite contents or modified stored receipt: fail closed.

### RED to GREEN: historical receipt recovery

The first 27/27 CI run had a real omitted case: once a newer checkpoint committed, looking up an already FINAL older receipt returned HOLD. An explicit new test for this behavior **FAILED (RED)** locally. Repair: store the accepted size/root history in the anchor DB within the same transaction, then permit returning an older finalized receipt only if its historical root is present and the current local/anchor heads agree. The new regression test passed locally, and in final 28/28 Windows/Linux CI. The stored history is still under a shared administrator, not a trusted external attestation.

## Original sources, boundaries and W26

- Official tlog-witness v1.1.0: https://c2sp.org/tlog-witness@v1.1.0 ; atomically check the old size, retain updated checkpoint before cosignature response.
- Official cosignature v1.1.0: https://c2sp.org/tlog-cosignature@v1.1.0 ; actual cosigner signatures are authenticated cryptographic statements. **W25 emits none.**
- No compliant HTTP add-checkpoint wire implementation, no signed witness reply, no separate operator, no certified power-loss persistence, no out-of-band public key pin, no live Ario events, no production authority and no independent custody.
- W26 should test *genuinely distinct operating-system identities, access-control denial and public-key custody verification* in disposable environments; distinct accounts under one machine administrator still do not prove independent operator sovereignty. Any lasting public external anchoring needs a separate explicit decision and threat model.

Every W25 status preserves authority NONE, external actions zero, witness signatures issued zero, source truth UNKNOWN, world freshness UNKNOWN, memory admission false, operator independence NOT_ESTABLISHED. Never treat a synthetic unsigned receipt as C2SP cosignature or governance approval.

**RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.**
