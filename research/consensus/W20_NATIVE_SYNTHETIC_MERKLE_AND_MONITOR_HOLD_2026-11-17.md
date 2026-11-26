# W20 — Synthetic Ario-origin Merkle history, compact inclusion/consistency and retained-prior monitor

**Date:** 2026-11-17. **Status:** `RESEARCH_ONLY / 8_SYNTHETIC_EVENTS / 2_EPHEMERAL_SIGNED_CHECKPOINTS / CT_STYLE_COMPACT_PROOF_REPLAY=PASS / 6_UNIT_TEST_METHODS_PASS / 1176_INCLUSION_PAIRS / 1128_CONSISTENCY_PAIRS / 12_OF_13_SELECTED_MUTANTS_KILLED / NATIVE_ARIO_LOG_WITNESSED=NOT_ESTABLISHED / INDEPENDENT_CUSTODY=NOT_ESTABLISHED / NO_GO`.

## برای بنیان‌گذار — خلاصهٔ فارسی

رفیق، گام بعدی بعد از W18/W19 را **عملی و قابل‌شکستن** کردیم: لاگ آزمایشی کوچک خود آریو با **۸ رویداد کاملاً ساختگی**، دو چک‌پوینت که با کلید Ed25519 **موقت** امضا شدند، اثبات درج برای تمام ۸ رویداد و **اثبات فشردهٔ تداوم تاریخچه** از اندازهٔ ۳ تا اندازهٔ ۸.

- **آزمون محاسباتی:** ۱٬۱۷۶ حالت درج و ۱٬۱۲۸ جفتِ اندازهٔ قدیم/جدید با اثبات فشرده اجرا شدند؛ شش گروه تست Python موفق.
- **نسخهٔ اولیه یک ضعف داشت:** فقط برای چند رویداد اثبات درج می‌خواست. اگر رویدادی خارج از آن چند مورد دست‌کاری می‌شد، می‌توانست نادیده بماند. نسخهٔ ثبت‌شده اکنون **اثبات درج تمام رویدادهای ارائه‌شده** را لازم می‌داند، اضافه‌کردن محتوای مستقیم خصوصی را از قالب آزمایشی رد می‌کند، و نتیجهٔ `HOLD/DENY` مناسب می‌دهد.
- **شرط مهم نگهبان:** علاوه بر کلید عمومی، باید **چک‌پوینت قدیمی از قبل نگه داشته‌شده** نیز جدا ارائه شود. وقتی هرکدام نیست، `HOLD_UNCERTAIN`؛ وقتی درخت کوچک‌تر شده یا دو چک‌پوینت هم‌اندازه با ریشهٔ متناقض داریم، `DENY`.
- **۱۳ خرابکاری عمدی در بررسی‌کننده:** ۱۲ مورد به شکست آزمون انجامید؛ **یک جهش زنده ماند** چون حذفِ یک شرطِ تکراری هنوز توسط کنترل تعداد، یکتایی و محدودهٔ اندیس‌ها پوشش داده می‌شد. این باگ اثبات‌شده نیست؛ هر ۱۳ مورد به‌صورت خام منتشر شده‌اند.
- کلیدهای آزمایشی، رویدادها و نمونهٔ ذخیره‌شده **هیچ هویت کاربری واقعی، کلید اصلی آریو یا محتوای حافظهٔ خصوصی** ندارند؛ کلید خصوصی موقت ذخیره نشده است.

**حکم:** تاریخچهٔ مرکلِ آزمایشی با اثبات‌های قابل‌بررسی ساخته شده؛ اما هنوز **سرویس لاگ واقعی آریو، نگهداری مستقلاً تأییدشدهٔ کلید و چک‌پوینت، یا امضای شاهد بیرونی روی مبدأ خود آریو نداریم**. پاسخ درست دربارهٔ اعتماد تولیدی همچنان `NO_GO` است.

## 1. Historical project de-duplication — do NOT call W20 the first local Merkle test

[Issue #171](https://github.com/SepehrGhanbari/Ario/issues/171) describes earlier **R13: 80/80 synthetic local RFC6962 Merkle tests**, R14 process locking, R15 a two-device same-admin high-water replay, R16 public third-party witness cosignatures on **another** transparency log, and R17 an application-readiness HOLD. The original R13 ZIP/source was **not independently retrieved or compared byte-to-byte** in this step. Do not count R13 and W20 as independent replications. **W20 adds a separately authored generator/reader interface in source files, exhaustive compact proof pair checks, full-event inclusion requirements, explicit supplied earlier head/key boundaries, and selected source mutations**. Its two Python modules were still written by the **same** researcher; they are not a third-party implementation.

[W18 external Sigsum public anchor](W18_REAL_EXTERNAL_SIGSUM_PROOF_AND_OFFLINE_REPLAY_2026-11-17.md) and [W19 stricter witness policies](W19_INDEPENDENT_W18_WITNESS_POLICY_AND_CUSTODY_ASSESSMENT_2026-11-17.md) demonstrated a **different fact**: a W17 *public research snapshot*'s hash was included in an external Sigsum test log, with cryptographically verified cosignatures under separate named policies. **That historical receipt does not include, endorse or cosign any W20 native log checkpoints**.

## 2. Exact reproducible source and byte-pinned evidence

All ten W20 files below were **executed/created in a disposable local Python 3.13.5, cryptography 46.0.4 environment**, then imported to GitHub; **every returned Git Blob SHA-1 matched the exact original local bytes**, not a paraphrase. The output source `W20_EXECUTION_RESULTS_2026-11-17.json` has SHA-256 for every input. These are public research fixtures only.

| Source | Exact Git Blob SHA-1 | Purpose |
| --- | --- | --- |
| [`w20_merkle_producer.py`](w20_merkle_producer.py) | `33fa37710bf780e42dc697bb9490b97aa09e68a3` | CT-style domain-separated SHA256 Merkle producer; compact inclusion and consistency generation; ephemeral signed checkpoints |
| [`w20_independent_monitor.py`](w20_independent_monitor.py) | `e0e1132a19fe5774460ccea48ef055eb1787653e` | Separate-source proof and Ed25519 verification; prior head and public key separately supplied; fail-closed monitor; full synthetic event validation |
| [`test_w20_native_log.py`](test_w20_native_log.py) | `66ad63ef9d610165071c1295272b042e7dcc9414` | 6 Python unittest methods, prefix exhaustiveness, mutation/control attack surfaces |
| [`w20_selected_mutation_audit.py`](w20_selected_mutation_audit.py) | `fb8cf16a450b37bbf6aa3fe778d3bc2f597d1901` | 13 standalone ephemeral source mutants against original test methods |
| [`w20_verify_published_fixture.py`](w20_verify_published_fixture.py) | `18a3ea5ee7ab35393fcba40f2a9d2229a82b8f8a` | Strict JSON duplicate-key rejection and read-only offline CLI replay |
| [`W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json`](W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json) | `13779afb7d953846424047bb16f0018b677131c8` | 8 public hash-only synthetic events, 2 signed checkpoint heads, 8 inclusion proofs, 1 compact consistency proof; no private keys |
| [`W20_PRIOR_CHECKPOINT_SIMULATED_PIN_2026-11-17.json`](W20_PRIOR_CHECKPOINT_SIMULATED_PIN_2026-11-17.json) | `3e741e1e6f032748450c9e675608f2cf5ab657bf` | Separate prior-head file **generated by the same author**, not actually independently retained |
| [`W20_EPHEMERAL_PUBLIC_LOG_KEY_2026-11-17.txt`](W20_EPHEMERAL_PUBLIC_LOG_KEY_2026-11-17.txt) | `165c6261b6e1b60b53f194946b43746f0fc80e1a` | Public test signer key; **not independently pinned to a real Ario origin/operator** |
| [`W20_MUTATION_RESULTS_2026-11-17.json`](W20_MUTATION_RESULTS_2026-11-17.json) | `78e8d717f0049c745cf8cb1c20277aad42531115` | Per-mutant observed first failing test and one survivor |
| [`W20_EXECUTION_RESULTS_2026-11-17.json`](W20_EXECUTION_RESULTS_2026-11-17.json) | `12855b497811ecd7b8846a9200160097e4fbe6cd` | Machine-readable test counts, source/fixture hashes, constraints and NO_GO flags |

### Exact local test execution

```sh
cd research/consensus
python -B -m unittest -v test_w20_native_log.py
python -B w20_selected_mutation_audit.py > W20_mutants_recomputed.json

python -B w20_verify_published_fixture.py \
  --fixture W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json \
  --prior W20_PRIOR_CHECKPOINT_SIMULATED_PIN_2026-11-17.json \
  --pinned-public-key-hex "$(cat W20_EPHEMERAL_PUBLIC_LOG_KEY_2026-11-17.txt)"
```

Expected conditional fixture verdict: `HISTORICAL_CONSISTENT / ALL_SUPPLIED_SYNTHETIC_LEAVES_INCLUDED_NOT_AUTHORITY`. **The CLI's key and prior in this demonstration come from the SAME repo, so even a successful verification is conditional on the mock trust roots; it is not proof of operator independence.** Running the suite needs Python 3 with `cryptography` installed. No network or production system needed. The test fixture is intentionally NOT registered with any third-party operator.

## 3. Merkle protocol source and limits

Primary technical reference: [RFC 9162, §2.1.1–2.1.4](https://www.rfc-editor.org/rfc/rfc9162.html#section-2.1) for CT's Merkle tree hash (distinct `0x00` prefix on leaves, `0x01` on branch nodes), compact per-leaf inclusion paths, append-only consistency proof paths, and separate checking against previously obtained tree heads.

**Actually implemented:** a small, bounded `MAX_LEAVES=64` Python educational implementation; a separate-source proof verifier for sizes/roots, strict test fixture event schema, ephemeral signed checkpoint record with an Ario-specific nonproduction domain separator, and no silent permission promotion.

**Not implemented:** the complete IETF Certificate Transparency v2 wire format, original C2SP tlog-witness `add-checkpoint` protocol, an actual internet-reachable Ario test log, unaffiliated registered witnesses, signed external freshness/clock, independent public-key pinning, physically independent checkpoint retention, multi-writer concurrency/atomic durability, real event capture, high-volume streaming, real log history completeness, or actual Ario consent/signing/veto policy. **Do not label this implementation a deployed CT/C2SP compatible service.**

### A subtle crucial distinction

A **complete inclusion-proof set** shows that every **supplied** synthetic event belongs to the signed tree head. It does **NOT** prove the publisher revealed every event that occurred in the actual Ario runtime. Nor does a mathematically valid consistency proof prohibit a malicious signer from *withholding* a later fork, unless independently reachable observers retain and compare signed high-water heads. Both-old snapshots remain a recognized negative limitation. Signed evidence is not world truth or authority.

## 4. Actual red/green test inventory and mutation survivor

- `65` tree sizes (0–64) computed against a separately written flat-forest reference algorithm.
- `1176` exhaustive inclusion index/size pairs for sizes 1–48, with changed-leaf and altered-path failure checks.
- `1128` old/new size pairs for sizes 1–48, with forged old root and corrupted consistency path failure checks.
- Additional negative tests: forged origin and signing key, **same valid signer produces a same-size different-root fork** (DENY), larger fork without valid compact consistency (DENY), size rollback (DENY), no trusted prior (HOLD), no public key (HOLD), omitted leaf proof (HOLD), duplicate index (HOLD), **tamper of a leaf not part of prior subset** (DENY), direct private-looking `payload` key (HOLD) and untrusted label falsely calling itself `USER_VERIFIED` (HOLD).
- The 6/6 unittest method groups **passed**. This does not mean 6 separate independent human auditors.
- Of **13 intentionally selected source mutations**, **12 were caught**. `M12_OMIT_FULL_INCLUSION_SET_CHECK` survived because the remaining **number-of-proofs == number-of-leaves**, **unique-index**, and **index-bounds** conditions together imply the same full coverage. The condition is redundant, so this single survivor is **not by itself a demonstrated exploitable bug**. Preserve the survivor in the JSON; an independent reviewer should attempt to refute that redundancy argument.

## 5. Concrete next gates before accepting a real native Ario origin log

1. **Independent source audit:** a different reviewer re-implements verifier/proofs from RFC 9162 or a mature audited library. Author's own producer and monitor do not count as independent implementations even if files are separate. Revisit R13 source ZIP from #171 if actually available instead of duplicating earlier R13 assurances.
2. **Durable test origin and public key:** choose a stable **synthetic-only** `origin`, bind an externally pinned vkey through separately authenticated operator channel, and ensure key rotation and revocation policy; never use the founder key or Ario independent key. This test currently uses `.invalid` origin and has no live endpoint.
3. **Witness integration:** implement and test an RFC/C2SP-compatible checkpoint and consistency endpoint on a public test-only log, then request independent witness enrollment only after prerequisites in [#171](https://github.com/SepehrGhanbari/Ario/issues/171) are satisfied.
4. **Independent high-water:** a separately administered observer retains the earlier signed checkpoint outside the same repository and rejects a later old-but-signed view. A second GitHub runner controlled by the same repo is **not** independent custody.
5. **Adversarial split views and outages:** independent reviewer supplies two validly signed same-size heads, stale+stale, missing consistency, altered event count, withheld latest, crashed append; return `DENY/HOLD` under explicit freshness/availability rules.
6. **Real runtime compatibility without authority elevation:** inspect actual main agent/event contract and protected draft memory #210/#216 before building any adapter. Provenance tags and memory rewrites must never silently become claims, legitimate user grants or external action authority.
7. **Only after all gates** consider a separate protected implementation proposal; **do not merge this research into main** or claim independent, real Ario witnesses, or any production approval.

**Reviewer request**: reply in [#259](https://github.com/SepehrGhanbari/Ario/issues/259) with `CONFIRMED/REFUTED/UNKNOWN | source commit/blob | independently authored counterexample | original protocol line | reproducible commands | custody assumption`. Keep all negative evidence rather than replacing older W18/W19 checkpoints.

**Protected status:** `#171_NATIVE_WITNESS_OPEN / #259_INDEPENDENT_REVIEW_OPEN / #216_MEMORY_HOLD / #242_DRAFT_HOLD / GENESIS=NO_GO / OWNER_SIGNER=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO / NO_CHATGPT_AUTOMATIONS`.

## 6. Actual separate GitHub-runner reproduction (after original source/fixture publication)

**This is real second-machine execution of the same source bytes, not a new independent human/custodian:**

- First [run 44159178012](https://github.com/SepehrGhanbari/Ario/actions/runs/44159178012) **FAILED before the test stage**, because `setup-python@v5` rejected `cache: false` (it requires an enum if given). Python was installed, but **zero W20 test methods were executed in that attempt**. Preserve this as a non-security CI setup failure.
- Corrected workflow and triggered exactly once more on the isolated research execution branch, with **checkout pinned to W20 source commit `5d3345dfb20bf1e17f7ce97f9cb3832d5c13f6be`**: [run 44159334216](https://github.com/SepehrGhanbari/Ario/actions/runs/44159334216), job `134308599911` completed **SUCCESS** on GitHub's fresh Ubuntu Python 3.13 runner. Installed `cryptography==46.0.4`. Exact stdout: [W20_ACTUAL_GITHUB_REPLAY_STDOUT_2026-11-17.txt](W20_ACTUAL_GITHUB_REPLAY_STDOUT_2026-11-17.txt). [Public-only 30-day artifact](https://github.com/SepehrGhanbari/Ario/actions/runs/44159334216/artifacts/14362592322).
- Actual result: **6 unittest methods PASS**, compact proof exhaustive checks included; source mutation replay matched **12 detected / 1 survived** (the same redundant `M12`); published signed fixture passed the explicit-key + explicit-prior CLI, with `HISTORICAL_CONSISTENT` **and simultaneously `authority=NONE`, `ario_log_witnessed=NOT_ESTABLISHED`, `freshness=UNKNOWN`**.
- After that successful replay, the disposable `.github/workflows/w20-one-shot-merkle.yml` was **deleted from the one-shot execution branch**, preventing future push-triggered W20 jobs. No recurring scheduled workflow or ChatGPT automation created. No third-party public submission/Signature was attempted.
- Concurrent PR activity note: after W20 commits, the shared #242 PR also included **another contributor's** `.github/workflows/w1-provenance-research.yml` outside the W20-only path. Its W1 Python/OS matrix is separate work; W20 did not create, alter, remove or approve it. Therefore do not report that **every** file in #242 is under `research/consensus/` without checking the latest PR diff.

**Updated epistemic disposition:** `SOURCE-PINNED SECOND-RUNNER REPLAY=VERIFIED / ACTUAL_INDEPENDENT_HUMAN_REVIEW=0 / OUT-OF-BAND_PRIOR_AND_LOG_KEY_PIN=NOT_ESTABLISHED / ACTUAL_ARIO_NATIVE_LOG_WITNESSED=NOT_ESTABLISHED / NO_REAL_KEYS / NO_EXTERNAL_EGRESS / #242_DRAFT_HOLD`.
