# W22 — C2SP signed-note checkpoints and a limited HTTP tile lab for Ario

**Research-only / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.**

## خلاصهٔ فارسی برای بنیان‌گذار

رفیق، W21 هنوز چک‌پوینت را در JSON اختصاصی آریو می‌داد. در W22 یک نمونهٔ عمومیِ کاملاً ساختگی از **چک‌پوینت متنیِ امضاشده با قالب C2SP** ساختیم، ریشهٔ آن را به هشت رویداد آزمایشی W20 وصل کردیم و از `/checkpoint`، تایل هش‌ها و بستهٔ رویدادها روی `127.0.0.1` ارائه دادیم. کلید Ed25519 صرفاً برای تولید دو چک‌پوینت و یک نمونهٔ فورک آزمایشی در حافظه ساخته شد؛ **کلید خصوصی ذخیره یا منتشر نشد**.

یک ناظر Python از کد تولیدکننده استفاده نمی‌کند و یک بررسی‌کنندهٔ مستقل از آن با **Go و فقط کتابخانهٔ استاندارد** نیز قالب امضا/کلید/ریشه را بررسی می‌کند. نمونهٔ معتبر پذیرفته شد و چندین نمونهٔ خراب رد شدند. برای سازگاری با نمونهٔ بیرونی، محاسبهٔ `key ID` با **مثال رسمی C2SP** تطبیق داده شد.

**نتیجهٔ محلیِ بازتولیدشده:** ۹ گروه unittest موفق، ۱۱ از ۱۱ خرابکاری انتخاب‌شدهٔ کد توسط تست‌های هدفمند شناسایی شدند؛ بررسی‌کنندهٔ Go دو چک‌پوینت معتبر را قبول و یک اندازهٔ دست‌کاری‌شده را رد کرد. **این‌ها آزمون‌های طراحی‌شده توسط همان پژوهشگرند، نه تأیید انسانی مستقل یا امضای شاهد بیرونی.**

نقص بنیادی همچنان آشکار است: اگر ناشر و ناظر هر دو فقط نسخهٔ قدیمیِ **معتبر و امضاشده** را داشته باشند، از رخ‌دادن نسخهٔ تازه مطلع نمی‌شوند. امضای سالم ≠ تازگی واقعی. برای اطمینان از تاریخچه باید آخرین چک‌پوینت را یک ناظر با **نگهداری واقعاً مستقل** از ناشر حفظ کند.

## 1. Primary protocols versus what W22 actually implements

Original primary specifications consulted on 17 November 2026:

- [C2SP Transparency Log Checkpoints v1.0.0](https://c2sp.org/tlog-checkpoint@v1.0.0) — text is origin, decimal size, base64 RFC6962 Merkle root, final newline; an empty separator line, then signed-note lines. W22 implements a **single strict Ed25519 log signature** only, not other signatures/extension lines.
- [C2SP signed-note](https://c2sp.org/signed-note@main) — exact note signature format and vkey: `name + hex(sha256(name || LF || 0x01 || 32-byte-public)[:4]) + base64(0x01 || public)`. The test includes the **external example** `example.com/foo+530d903a+...`, checking the documented key ID.
- [C2SP tlog-tiles v0.1.0](https://c2sp.org/tlog-tiles@v0.1.0) — `/checkpoint` text/plain, `/tile/0/0.p/<width>` binary leaf-hash tile and `/tile/entries/0.p/<width>` uint16-length-prefixed public test entries.
- [C2SP tlog-witness v1.1.0](https://c2sp.org/tlog-witness@v1.1.0) — separate witness protocol expects an authenticated log origin, previous checkpoint, consistency proof and signed monitoring response. **W22 does not implement `POST /add-checkpoint`**, an outside witness, or a complete witness registry.
- [RFC 9162, Merkle section 2.1](https://www.rfc-editor.org/rfc/rfc9162.html#section-2.1) — SHA256 leaves prefixed `0x00` and internal nodes prefixed `0x01`.

**Implemented subset only:** size 3 and size 8 *partial level-0* hash tiles, 8 synthetic hash-only records, strict signed note syntax, a separate published-but-self-originated test vkey, a retained-but-self-originated test high-water, and a **nonstandard, explicitly labeled** `/w22/consistency/3/8` JSON endpoint reusing the previously tested compact proof code.

**NOT implemented:** complete C2SP tiled API including other levels/mutable served checkpoint history, official witness `add-checkpoint` exchange, consistency proof tiles at arbitrary historical sizes, signed witness cosignature, independent clock, durable real logging, event ingestion, external key pinning, transport TLS, live internet service, one-shot external Sigsum publication, human/Ario veto or production trust activation. Use the label `C2SP_SIGNED_NOTE_WIRE_SUBSET`, **never** `WITNESS_NETWORK_COMPATIBLE_SERVICE`.

## 2. Exact source and runnable reproduction

All W22 files are under `research/consensus/`; W20 `w20_independent_monitor.py` and `W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json` are **pre-existing dependencies** that W22 does not overwrite.

| Path | Purpose |
| --- | --- |
| `w22_note_fixture.py` | Generates new ephemeral Ed25519 C2SP note fixture, same-signer malicious fork, public vkey; never writes the private key |
| `W22_PUBLIC_SYNTHETIC_SIGNED_NOTES_2026-11-17.json` | Fixed public synthetic note fixture; note files are also separate |
| `W22_PREVIOUS_CHECKPOINT.note`, `W22_CURRENT_CHECKPOINT.note`, `W22_SAME_SIGNER_FORK.note` | Raw signed-note bytes for one previous, one new and one maliciously equivocated checkpoint |
| `W22_PUBLIC_LOG_VERIFIER.vkey` | Public test verifier key; **not actually out-of-band pinned** |
| `w22_tile_server.py` | GET-only HTTP loopback facsimile for one tiny size, separate process, no POST writes |
| `w22_note_monitor.py` | Strict independent-source Python note+tile+entry+local compact proof verifier, explicit prior/high-water input |
| `w22_note_go_check.go` | Go standard-library-only, separate-language note/public-key/signature/root checker |
| `test_w22_checkpoint_interop.py` | Nine unittest groups; positive case, official vkey known example, old+old warning, signed fork, real redirect destination never contacted, tampered tile/entry/consistency, outage |
| `w22_selected_mutation_audit.py` + `W22_SELECTED_MUTATION_RESULTS_2026-11-17.json` | Eleven author-selected source mutations against corresponding targeted controls; 11 killed; **not blind adversarial testing** |
| `w22_replay_no_egress.sh`, `W22_REPLAY_STDOUT_2026-11-17.txt` | Local one-command replay with no HTTP request outside loopback and Go `GOPROXY=off`; no scheduled tasks |
| `W22_EXECUTION_RESULTS_2026-11-17.json` | Machine output, exact source Git hashes, negative limitations and separate-runner status |

To repeat from the research branch, in a disposable Python 3.13 environment with `cryptography==46.0.4` and Go 1.23+ installed:

```sh
cd research/consensus
bash w22_replay_no_egress.sh
```

Replays the 9 Python groups, 11 selected source mutation runs, Go old+new positive checks, one Go negative, and no new signing. No private key needed for any replay. The published fixtures were generated once, locally, using a throwaway ephemeral signer; rerunning `w22_note_fixture.py` will necessarily create *different* public keys and signatures.

## 3. Important actual observed controls

- **Positive:** current size-8 signed note verifies against an explicitly passed *public test* vkey, 8 binary leaf hashes and 8 uint16-framed synthetic events; root matches; separate local compact proof verifies retained size 3 → 8; output `HISTORICAL_CONSISTENT`, `operational_authority=NONE`, `latest_world_state=UNKNOWN`.
- **Failure: rollback:** when the observer retains the *new size-8* signed checkpoint, a stale HTTP server serving size 3 gets `DENY/OLDER_THAN_RETAINED_HIGHWATER`.
- **Unsolved both-old:** when both the server and retained high-water are size 3, an internally valid historical state remains `HISTORICAL_CONSISTENT`; `latest_world_state=UNKNOWN`. This is the key counterexample to any broad “anti-rollback solved” claim.
- **Failure: fork:** a different size-8 root signed by the **same ephemeral signer** is rejected against the previously retained size-8 root. An inconsistent previous and high-water pair of the same size is also denied.
- **Failure: coordinated data rewrite:** both tile hashes and entries changed together still fail to match the signed checkpoint root.
- **Failure: proof corruption:** a changed compact consistency path gets `DENY`.
- **HTTP security:** redirect target is a second actually reachable local server; hit counter stayed **zero**. Bad signing bytes, leading-zero note size, mismatched tile, malformed/truncated entry, network outage, `POST /checkpoint` and missing key/prior/high-water fail closed.
- **11 deliberately weakened versions** disabled validation steps such as signature verification, key-ID binding, root check, leaf/tile binding, stale-head refusal, fork refusal, redirect refusal, consistency proof, no-action authority and high-water requirement. All 11 were detected by their respective same-author tests. These are **selected mutation sensitivity**, not a general security percentage.

**Test harness caveat:** an initial parallel mutation full-suite attempt exceeded resource/time limits; it produced **no valid mutation verdict**. The final reported 11/11 run uses **targeted bounded test methods** for each mutation and completed. Both facts should remain in the record, without upgrading the test strength.

## 4. Exact epistemic/administrative boundaries

A C2SP-syntax-correct Ed25519 signature proves that **a holder of that specific private key signed a particular note**. It does **not** prove the human owner, independent operator, complete capture of real Ario events, newest tree state, consent to a real effect, source truth or Ario's willingness to act. The current fake origin contains `.invalid` and has **no registered public endpoint**. The vkey and two retained heads are all published through the **same project admin**, so their true *out-of-band* status is `NOT_ESTABLISHED`.

This is a research-only educational C2SP checkpoint and subset-of-tiles interface. **Do not merge into `main`, connect production memory or set `TRUST_ACTIVATION=GO`.**

## 5. How to continue without requiring a human review board

The founder is the only human in this project. This is **not** a reason to block all research, run scripted tests or public documents. It does require precise labels:

1. Independent machine/compiler/language replays count as **cross-environment or cross-implementation checks**, not independent human approval.
2. Follow up with third-party public protocol test vectors or implementations for wire compatibility, more deliberately hostile byte-level fuzz/mutation controls and log/witness **crypto-policy** verification; never accept self-authored test expected values as external world truth.
3. A later *synthetic-only public log deployment* needs a separately approved non-secret endpoint and out-of-band pubkey/monitor; it must distinguish itself from Ario's actual owner signer and include a stated operator trust model.
4. For a **separately administered witness** or real human intent signature, label the requirement `NOT_ESTABLISHED` until such a principal **actually exists**. Another subprocess or cloud runner controlled by the same GitHub account does not satisfy it.
5. Any external test-log submission is a potentially lasting side effect; the founder's earlier consent was specific to W18 and is **not** blanket permission for W22 submissions.

**Issue tracking:** Witness custody/origin [#171](https://github.com/SepehrGhanbari/Ario/issues/171), reproducible adversarial challenges [#259](https://github.com/SepehrGhanbari/Ario/issues/259), protected memory semantics [#216](https://github.com/SepehrGhanbari/Ario/issues/216), research Draft PR [#242](https://github.com/SepehrGhanbari/Ario/pull/242).


## 6. W22 targeted loopback proxy hardening (additional reproducible correction)

**New falsifier:** Python `urllib.request.build_opener()` can construct a default proxy handler from untrusted `http_proxy` and an empty `no_proxy`. Even when a URL contains `127.0.0.1`, blindly following these environment settings can route a supposedly loopback-only request through an arbitrary HTTP proxy. W22 was updated to use explicit `ProxyHandler({})` **plus the already tested no-redirect handler**. The new test spawns a reachable local proxy trap, sets `http_proxy`, `HTTP_PROXY`, `ALL_PROXY`, and empty `no_proxy`/`NO_PROXY`, reloads the monitor with those hostile variables, and confirms **successful direct verified observation with exactly zero trap hits**.

The original W22 GitHub one-shot [run 44170398864](https://github.com/SepehrGhanbari/Ario/actions/runs/44170398864) ran source commit `d07620afa5e0e2f69daa6284ba0789b3a5957840` and passed **8 unit methods / 10 selected mutants + Go validation** *before* this proxy hardening. That is real, bounded evidence and must not be relabeled as testing the later patch. The **updated** local source passes **9 unit methods / 11 selected mutants**, including an explicit `M11_ALLOW_HTTP_ENV_PROXY` variant killed by the new test. New source and runner must be pinned separately. The source-mutation model remains same-author, and the test-only loopback restriction is not a deployment-ready TLS/policy solution.
