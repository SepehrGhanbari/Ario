# W21 — Synthetic Ario log over real loopback HTTP, a separate read-only observer, and the both-old high-water failure

**Date:** 17 November 2026  
**Status:** `LOCAL_HTTP_MULTI_PROCESS_REPLAY=PASS / SECOND_GITHUB_RUNNER=PASS / PUBLIC_STATIC_GITHUB_BYTES_READABLE / DIRECT_ARIO_WITNESS=NOT_ESTABLISHED / INDEPENDENT_HIGHWATER_CUSTODY=NOT_ESTABLISHED / C2SP_WIRE_IMPLEMENTATION=NO / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`

## خلاصهٔ فارسی برای بنیان‌گذار — مهم‌ترین قسمت

رفیق، مرحلهٔ W21 یک گام از تست فایل مرکل جلوتر رفت: **سرویسی که فقط HTTP GET پاسخ می‌دهد** در یک فرایند جدا اجرا شد و **ناظرِ فقط‌خواندنی** از روی شبکهٔ داخلی `127.0.0.1` چک‌پوینت‌های امضاشده و اثبات‌های درج و تداوم W20 را گرفت و بررسی کرد. در همان محیط، ۱۳ حالت مشخص شامل دادهٔ سالم، حملهٔ بازگردانی، جعل داده و امضا، پاسخ ناقص، خطای JSON و اختلال شبکه آزموده شدند. سه گروه تست W21 به‌همراه شش گروه تست مرکل W20 هم روی یک ماشین تازهٔ GitHub موفق بودند.

**کشف مهم و تکرارپذیر:** وقتی ناظر یک چک‌پوینت جدیدترِ ۸ رویدادی را قبلاً نگه داشته، سرویسِ بازگردانده‌شده به ۳ رویداد را **رد می‌کند**. اما وقتی خودِ سرویس **و اطلاعات قبلیِ ناظر هر دو روی ۳ رویداد قدیمی** هستند، سیستم فقط سازگاری تاریخی می‌بیند و نمی‌تواند بفهمد نسخهٔ ۸ رویدادی بعداً وجود داشته است. این مورد عمداً به‌عنوان **نتیجهٔ منفی** باقی مانده، نه «امنیت اثبات‌شده».

**محدودیت اساسی:** هرچند سرویس و ناظر دو فرایند مستقل از نظر اجرا هستند، **همچنان با فایل‌ها و کلید عمومیِ منتشرشده از همین مخزن و زیر مدیریت همان مالک** کار می‌کنند. سرویس فقط روی loopback اجرا شد؛ **هنوز یک سرویس عمومیِ دائمی و سازگار با C2SP یا شاهدِ واقعیِ مستقل برای لاگ آریو نیست.** هیچ کلید واقعی آریو، حافظهٔ خصوصی یا امضای عملیاتی استفاده نشده است.

## 1. Exactly executed and Git-blob-pinned source

All artifacts are on research Draft PR [#242](https://github.com/SepehrGhanbari/Ario/pull/242), branch `research/consensus-sprint-20261116`.

| Exact file | Git Blob SHA-1 read back from GitHub | Role |
| --- | --- | --- |
| [`w21_loopback_log_server.py`](w21_loopback_log_server.py) | `166829146235878c239d397a232f9b74f04f5afd` | Local-only HTTP service: `GET /v0/checkpoint`, `/v0/events`, `/v0/consistency?old=3&new=N` |
| [`w21_http_observer.py`](w21_http_observer.py) | `275bbfa8235e00837fb50b18c604f4e7bcce7153` | Independent **process**, shared author; pinned key, prior and high-water supplied separately; full W20 proof checks; 48-KiB response cap |
| [`test_w21_http_monitor.py`](test_w21_http_monitor.py) | `4d0fb95e39a46c8cd38b532bcb1cb3a16736c7b5` | 13 named adversarial HTTP scenarios plus unavailable/network URL/unsafe HTTP-method controls; 3 unittest methods |
| [`W21_SIMULATED_RETAINED_HIGHWATER_2026-11-17.json`](W21_SIMULATED_RETAINED_HIGHWATER_2026-11-17.json) | `3100c1d5e144503d2da4569aea0f34fd5b611fc6` | Valid **signed** eight-event high-water file, **copied from the same author/PR**, not independently retained |
| [`W21_PUBLIC_STATIC_LOG_REFERENCE_2026-11-17.json`](W21_PUBLIC_STATIC_LOG_REFERENCE_2026-11-17.json) | Verify GitHub blob in current branch | Raw GitHub commit-pinned PUBLIC W20 reference, no live API or C2SP claim |
| [`W21_HTTP_TEST_AND_HIGHWATER_NEGATIVES_2026-11-17.json`](W21_HTTP_TEST_AND_HIGHWATER_NEGATIVES_2026-11-17.json) | Verify GitHub blob in current branch | Explicit per-case `DENY / HOLD / HISTORICAL_CONSISTENT` outcomes and nonclaims |
| [`W21_ACTUAL_HTTP_GITHUB_RUN_STDOUT_2026-11-17.txt`](W21_ACTUAL_HTTP_GITHUB_RUN_STDOUT_2026-11-17.txt) | Verify GitHub blob in current branch | Extracted exact successful job lines from the actual runner, including both test suite summaries |

**Source snapshot pinned for second machine:** `f26a479e6c1f893f05bc96fd49c8b06cecba206a`.

**Actual local verification:** Python 3.13.5 / cryptography 46.0.4, `python -B -m unittest -q test_w21_http_monitor.py`: 3/3 unittest methods PASS; 13 distinct cases inside the primary method plus network/HTTP method checks. Service is started as a real **separate subprocess**, bound to `127.0.0.1` only. It does not generate new signatures: it replays original W20 fake log checkpoints. `POST`, `PUT`, `DELETE` all return HTTP 405.

**Actual second-runner verification:** [GitHub Actions W21 run 44162876016](https://github.com/SepehrGhanbari/Ario/actions/runs/44162876016), job `134321083174` finished **SUCCESS**, Python 3.13 + cryptography 46.0.4. `Ran 3 tests / OK` for W21, `Ran 6 tests / OK` for unchanged W20 compact Merkle proof suite. [Actual 30-day result artifact](https://github.com/SepehrGhanbari/Ario/actions/runs/44162876016/artifacts/14363183832). **No real external network publication; only local HTTP loopback and public package dependency fetch.** The one-shot workflow file was **removed** from the disposable execution branch after run; no recurring workflow or ChatGPT automation created.

## 2. Negative/positive matrix (13 named HTTP cases)

| Cases | Result | Interpretation |
| --- | --- | --- |
| W21-01 | `HISTORICAL_CONSISTENT` | Signed 8-event checkpoint, 8 real inclusion proofs and 3→8 compact consistency proof match **supplied** trusted 8-event high-water |
| W21-02 | `DENY: HTTP_ROLLBACK_BELOW_PINNED_HIGHWATER` | Valid old 3-event signed checkpoint rejected if separately supplied known newer size 8 exists |
| **W21-03** | **`HISTORICAL_CONSISTENT`** | **Essential negative: valid old service + valid old high-water both at size 3 conceal later size 8**; no currentness claim or action authority |
| W21-04 / 05 / 06 | `HOLD_UNCERTAIN` | Missing retained high-water, pinned log key or retained prior; an endpoint's own trust labels cannot replace them |
| W21-07 | `DENY` | Tampered event payload digest breaks the inclusion proof |
| W21-08 | `DENY` | Tampered checkpoint root invalidates Ed25519 signature |
| W21-09 | `HOLD_UNCERTAIN` | Only seven of eight offered event records; no false complete history |
| W21-10 | `HOLD_UNCERTAIN` | Response exceeds configured 48-KiB size |
| W21-11 | `HOLD_UNCERTAIN` | Duplicate JSON key response is rejected |
| W21-12 / 13 | `HOLD_UNCERTAIN` | Wrong pinned public key or invalid high-water signature cannot establish trust |

**Also executed**: unreachable local listener => HOLD; network destinations other than `127.0.0.1` or malformed URLs => HOLD; server attempts to mutate via POST/PUT/DELETE => HTTP 405. A read-only consistent result always carries `real_ario_log_witnessed=NOT_ESTABLISHED`, `cross_admin_key_custody=NOT_ESTABLISHED`, `freshest_world_checkpoint=UNKNOWN`, `source_truth=UNKNOWN`, `operational_authority=NONE`, `memory_admitted=false` and `external_effects=0`.

**Potential adversarial question for independent reviewer:** does a signed high-water comparison of equal `size/root` establish enough when the earlier signed pin is itself generated and disseminated under the log publisher's single admin? **No.** A second GitHub process still doesn't create independent protected custody; old+old is a reproducible counterexample.

## 3. First externally readable static test reference — NOT a live witnessed origin

A public W20 research snapshot was **actually retrieved via the connected GitHub read-only interface** from the historical permalink:

[`raw.githubusercontent.com/.../W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json`](https://raw.githubusercontent.com/SepehrGhanbari/Ario/5d3345dfb20bf1e17f7ce97f9cb3832d5c13f6be/research/consensus/W20_SYNTHETIC_LOG_CHECKPOINTS_AND_PROOFS_2026-11-17.json)

It yielded the expected **size-3 old head and size-8 newer head** from the commit-pinned fixture. GitHub is outside the loopback testing process and serves its bytes publicly, **but the Ario repository owner publishes/controls those files and decides which reference is considered most recent**. A static, Git-hosted JSON corpus therefore provides **a publicly retrievable historical test record**, NOT a dynamically updated log origin, independently verified last-seen state, C2SP checkpoint endpoint, registered witness, or freshness service.

## 4. Official protocol mapping and explicit non-implementation

Original authoritative references:

- [RFC 9162 §2.1](https://www.rfc-editor.org/rfc/rfc9162.html#section-2.1): domain-separated RFC-style Merkle tree leaf/inner-node hash, inclusion and append-only consistency proofs.
- [C2SP tlog-witness v1.1.0](https://c2sp.org/tlog-witness@v1.1.0): witness is configured for a log origin and public log key, retains its last accepted checkpoint and verifies consistency before cosigning; an arbitrary custom JSON response **is not this protocol**.
- [C2SP tiled transparency log v1.0.0](https://c2sp.org/tlog-tiles@v1.0.0): specifies static HTTP resources including a standardized checkpoint, tile/entry semantics and integrity constraints. Our GitHub raw snapshot is **not a compatible tile/checkpoint API** simply because it uses HTTP GET.
- [C2SP signed transparency checkpoint](https://c2sp.org/tlog-checkpoint@v1.1.0): signed origin/size/root in a precise interoperable wire representation. W20's Ed25519 signature covers its own canonical JSON domain and does **not** produce a C2SP `tlog-checkpoint` signed note.

Thus **no public external Witness Network operator is expected to accept/cosign this W21 custom service**. Claiming C2SP implementation, independent custodian or live native Ario witness now would be false.

## 5. Next safe and falsifiable work for Cloud/Claude/Codex/independent reviewers

- [ ] **Source/HTTP protocol review:** Independently inspect pinned W20/W21 files, check URL allowlist/redirect behavior, size caps, bad JSON handling, fetch atomicity, repeated responses, and whether simultaneous checkpoint/event/consistency requests can yield an inconsistent but accepted state. Find an exploit, not merely a missing feature.
- [ ] **Crypto interop:** Independently reimplement or use an audited Merkle verifier (RFC 9162), without importing W20 producer and monitor; run positive and negative tests including forged same-size split-view.
- [ ] **True public test-only log endpoint:** define **separately reviewed and permitted** hosting of a nonproduction log origin with C2SP-compatible signed note and consistency proof/witness endpoint; don't deploy a server or emit public signed credentials by this PR.
- [ ] **Outside-admin retained high-water:** have a genuinely distinct operator prove they can retain authentic signed head/key through a repo-admin replay and that the publisher cannot erase the independent prior head. Simulate all-old and withheld size-8 while operator retains prior size-8.
- [ ] **Source-of-truth boundary:** even with a real witness, missing unobserved Ario events and independent human/Ario consent cannot be inferred from a signed tree.
- [ ] **Independent review report:** exact commit and blobs, `CONFIRMED / REFUTED / UNKNOWN`, independent adversarial test/command, actual output, reviewer's source of trust key and operator custody assumptions. Request counterexample that changes a verdict, not just rerunning same author's tests.

**No-go/status:** `#171_DIRECT_WITNESS_ENROLLMENT_OPEN / #259_REVIEW_OPEN / #216_MEMORY_HOLD / #242_RESEARCH_DRAFT_HOLD / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO / NO_CHATGPT_AUTOMATIONS`. The current work is defensive research and can be safely repeated; it is not authorization for unattended signing, deploy or data publication.
