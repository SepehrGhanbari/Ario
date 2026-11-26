# W29 — Dual-observer crash, split-view and coordinated rollback laboratory

**Date:** 2026-11-18  
**Project:** SepehrGhanbari/Ario / research/consensus  
**State:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_EXTERNAL_CONTACT / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.

## خلاصهٔ فارسی

رفیق، آزمایش W29 با دو فایل SQLite جدا برای دو «ناظر آزمایشی» انجام شد و هر دو سیستم Linux و Windows تمام ۴۰ آزمون را با موفقیت گذراندند. دو فرایند مجزا نیز واقعاً روی فایل‌های جدا کار کردند؛ سقوط سخت فرایند با os._exit قبل و بعد از COMMIT به صورت آزمایشی بازتولید شد.

**یافتهٔ مثبت محدود:** اگر ناظر A وضعیت درخت با ۸ برگ را ثبت کرده و ناظر B هنوز روی ۳ باشد، اختلاف آن‌ها به‌تنهایی فورک نیست. با اثبات تداوم صحیح RFC6962 می‌توان عقب‌بودن ناظر دوم را از دو ریشهٔ ناسازگار در اندازهٔ یکسان تفکیک کرد. اگر یکی از دو فایل به نسخهٔ قبلی برگردد، با مقایسهٔ دو دیدگاه اختلاف مشاهده می‌شود. اگر یک چک‌پوینت قبلیِ جدیدتر دست‌نخورده باقی مانده باشد، بازگردانی هر دو فایل به نسخهٔ قدیمی نیز نسبت به آن چک‌پوینت شناسایی می‌شود.

**شکست ساختاری حفظ‌شده:** اگر هر دو فایل SQLite و شواهد قبلی با هم به عقب برگردند، دو ناظر باز هم می‌توانند کاملاً سازگار به نظر برسند. در W29 هیچ شاهد سوم واقعی یا نگهداری مستقل وجود نداشت. چک‌پوینت سوم نیز صرفاً ورودیِ ارائه‌شده توسط آزمایش است، نه مرجع بیرون از اختیار ناشر. مدیر مشترک می‌تواند همان ورودی را هم جایگزین کند.

پس آنچه ثابت شده، رفتار محدود کد در برابر سناریوهای ساختگی و بایت‌های امضاشدهٔ W22 است، نه استقلال مدیریتی، مقاومت در برابر مدیر سیستم، نبود فورک پنهان، یا صحت رویدادهای واقعی آریو.

## 1. Exact machine evidence

- Source: research/consensus/w29_dual_observer_rollback_lab.py — Git blob c179dacb74008d9cf7bc46d5a69ae5a8977344a4
- Tests: research/consensus/test_w29_dual_observer_rollback_lab.py — Git blob 5380df6cc8cb910e1a32822f537ded3eeda27d04
- Original published W22 synthetic signed checkpoints and same-signer signed fork, plus W20 3-to-8 consistency proof.
- CI-trigger commit: 08b2d8fae8c754c699793bb3f6960ce4e034d832
- Actual GitHub Actions: https://github.com/SepehrGhanbari/Ario/actions/runs/44388220676
- Ubuntu Python 3.13 job 135098474152: Ran 40 tests / OK; raw job stdout inspected.
- Windows 2022 Python 3.13 job 135098474650: Ran 40 tests / OK; raw job stdout inspected.
- Genuine subprocess process-crash injection codes 91 (before SQLite commit) and 92 (after commit but before response), verified in both OS test jobs.
- Multiprocessing spawn workers on distinct SQLite databases, and competing workers on one database, ran in the same CI jobs.
- Tests authored by project researcher; PASS does not establish independent external review, power-failure safety, or actual separate administrators.

## 2. Evidence matrix

| Test category | Observed behavior |
| --- | --- |
| Both observers initially accept valid W22 signed 3-leaf checkpoint | Equal valid readbacks, but status HOLD |
| Both grow 3 to 8 with original Merkle proof | Both stores persisted signed size-8 head |
| One observer offline or storage corrupt | HOLD, no fake quorum |
| One observer at 3, other at 8, valid consistency proof provided | ONE_OBSERVER_LAGS_BUT_CONSISTENCY_PROVEN_FOR_SUPPLIED_NOTES; HOLD |
| One at 3, other at 8, proof missing or corrupted | DIFFERING_VIEWS_NO_CONSISTENCY_PROOF; HOLD |
| Two validly signed size-8 checkpoints with different roots | TWO_SIGNED_SAME_SIZE_FORK; HOLD |
| Single-observer rollback while other remains at size 8 | Different views visible; additional consistency must be verified |
| One or both views below an unchanged caller-supplied size-8 floor | OBSERVER_BELOW_SUPPLIED_FLOOR; HOLD |
| Both stores rolled back to size 3 without a protected floor | Both appear to agree. Negative control: rollback undetectable |
| Caller supplies rolled-back size-3 floor as well | Still internally consistent; no independent floor provenance |
| Floor size 3 and two heads at size 8 but no consistency proof | FLOOR_TO_OBSERVER_PROOF_UNVERIFIED |
| Floor size 3 and two heads at size 8 with original proof for each | Bounded consistency, not independent custody |
| Before-commit process death | Previous head remains; request may be retried |
| After-commit process death, response lost | New head persisted; same signed checkpoint can be replayed |
| Same-head retry, duplicate concurrent writers | Idempotent or one conflicts; no silent divergent commit |
| Tampered note bytes, metadata or signature | HOLD or DENY |
| Reader notes reused under two distinct display labels | False independence not accepted |

## 3. C2SP comparison

The official witness protocol https://c2sp.org/tlog-witness@v1.1.0 says that the witness checks log signatures and Merkle consistency and retains its state before emitting a cosignature. Its monitor interface can expose prior cosigned checkpoints. Official cosignature semantics https://c2sp.org/tlog-cosignature@v1.1.0 describe consistency with the cosigner's prior observed views, not complete global event coverage. This W29 code implements NEITHER the official HTTP service NOR real witness cosignatures.

W29 checks the strict W22 Ed25519 signed-note subset and compact RFC6962 proof via the previously published W23 parser. Readback values are self-reported local JSON from files; the channel itself carries no independent signed identity, no authenticated third-party operator, no external governance authority or trusted public key pin.

Every research result preserves policy HOLD, authority NONE, no memory promotion, no cosignature issued, no external log submission, no Trust Activation and no Production. Two files are not two operators. Two local processes are not two operators. A third self-supplied saved checkpoint is not an independently protected high-water mark.

## 4. Remaining blockers / W30 proposal

1. Externally retained checkpoint: NOT_ESTABLISHED; recovery after simultaneous rollback of all same-admin state is not provable.
2. Observer authentication and key pinning from independently verified channel: NOT_ESTABLISHED.
3. Administrative separation from Ario publisher and founder-controlled infrastructure: NOT_ESTABLISHED.
4. Third-party witness enrollment, external publishing, contacts or network writes: NONE.
5. Windows-native SID custody, real power-loss test, compromised administrator/revocation, hardware isolated signing: NOT_TESTED here.
6. W30 research option: preregister an immutable evidence capsule format for an outside keeper to return (log identity, initial verified pin, checkpoint, independently retained prior head, readback timestamp, signature, key rotation/revocation chain, explicit operator boundaries), and red-team the capsule offline before contacting any third party. Actual independence remains HOLD until an outside keeper with separately verified operational control exists.

**Verdict: W29_DUAL_OBSERVER_LOGIC=BOUNDED_PASS; TRUE_INDEPENDENT_KEEPER=NOT_ESTABLISHED; PRODUCTION=NO_GO; TRUST_ACTIVATION=NO_GO; NO_MERGE.**
