# W16 — Custody and freshness cannot be self-certified: protected research decision record

**Date:** 2026-11-17. **Decision ID:** `DR-RES-W16-DRAFT` (research recommendation, **NOT** founder/adoption approval).  
**Status:** `HOLD_UNCERTAIN / OPERATOR_INDEPENDENCE=NOT_ESTABLISHED / TRUST_ACTIVATION=NO_GO / GENESIS=NO_GO / PRODUCTION=NO_GO / NO_MERGE`.

## خلاصهٔ کوتاه فارسی

نتیجهٔ مهم W14–W16 را به‌صورت تصمیم قابل‌ارجاع ثبت می‌کنیم:

**دو کلید، دو شناسهٔ کاربری، دو فایل، دو آدرس اینترنتی یا دو شاهدِ امضاشده، خودبه‌خود به معنای «دو نگهدارندهٔ مستقل» نیست.** اگر شخصی بتواند هر دو مسیر را مدیریت کند یا آخرین نسخه را پنهان کند، یک شاهد قدیمیِ معتبر می‌تواند به‌جای نسخهٔ تازه نمایش داده شود.

ما از GitHub واقعاً یک فایل شاهد تازه دریافت کردیم (W15) و نسخهٔ قدیمی را نسبت به آن رد کردیم. ولی GitHub هنوز زیر اختیار مدیر همان مخزن است. **در W16 یک نگهبان آزمایشیِ صرفاً خواندنی اضافه کردیم که در نبود اصالتِ مستقلِ شاهد/تازگی، حتی با دو نام متفاوت مدیر، اجازهٔ انجام عمل نمی‌دهد.** با ۲۴ سناریوی ساختگی و ۱۳ خرابکاری عمدی امتحان شد. این آزمایش **نه** هویت صادرکنندگان را احراز می‌کند، **نه** کلید اصلی آریو را استفاده می‌کند و **نه** چیزی را در حافظهٔ واقعی تغییر می‌دهد.

یک نکتهٔ بسیار مهمِ تاریخی هم پیدا شد: [Issue #171](https://github.com/SepehrGhanbari/Ario/issues/171) از قبل مسیر Witness Network را دنبال کرده است. R12 در آنجا دربارهٔ **دو شاهد واقعی عمومی برای یک لاگ Android Transparency بیرونی** گزارش می‌دهد؛ نه لاگ آریو. R17 نیز **هشت پیش‌نیاز ثبت‌نام آزمایشیِ هنوز اثبات‌نشده** را فهرست می‌کند. بنابراین W16 را به همان مسیر وصل می‌کنیم؛ شاهد مستقل «از صفر» ساخته نشده و هیچ شاهدی برای لاگ آریو ثبت نشده است.

## 1. What was actually executed and committed

| Artifact | Exact executed Git Blob SHA-1 | Evidence grade |
| --- | --- | --- |
| [`w16_custody_preflight.py`](w16_custody_preflight.py) | `5aa44491c6dfd7649a9b7372312985c233b155fc` | Python 3.13.5 read-only **declared-observation** policy, no crypto, network or real effects |
| [`test_w16_custody_preflight.py`](test_w16_custody_preflight.py) | `c977c976ad88b014f3a688ebcb9d33a3d95145db` | 3 unittest method groups PASS; 24 named synthetic comparison scenarios |
| [`w16_mutation_audit.py`](w16_mutation_audit.py) | `749548e8c56f3ddb58173a75a3726ad3453b7294` | 13 deterministic disposable source mutations against those tests |
| [`W16_MUTATION_AUDIT_2026-11-17.json`](W16_MUTATION_AUDIT_2026-11-17.json) | `c21a38d1b8b5e16a48c8e98bad732dea1197ec74` | Actual per-mutant first failure, SHA-256, 13/13 **selected** mutations detected |

All four were executed/created locally and **read back from the research branch with Git blob identities matching the locally executed bytes**. The 24 cases and 13 mutants were developed by the **same researcher** and are not blinded independent trials. No secrets or actual Ario public/secret signing keys were used.

Run from a disposable checkout with Python 3 (stdlib only; no install needed):

```sh
cd research/consensus
python -B -m unittest -v test_w16_custody_preflight.py
python -B w16_mutation_audit.py > /tmp/W16_mutations_reproduced.json
# expected: unittest groups 3 PASS, cases 24, selected mutants 13, killed 13
```

Do not mistake the latest green implementation CI check for proof that W16 was separately run in CI: the repository's implementation workflow is not an independent W16 review. The new code is an isolated research artifact, not a new enforcement hook in `ario_agent.py` or PR #210.

## 2. Precise behavioral boundary

The W16 `assess(local, references, known_highwater)` consumes **already-declared normalized inputs**. It makes no claim to validate real Ed25519 signatures or the identity of a GitHub operator. `reported_signature_valid`, `admin_root`, `provider` and `readback_source` are **untrusted field values**, even when they say `VERIFIED`. Outputs always set `independent_administrative_custody=NOT_ESTABLISHED`, `remote_currentness=NOT_ESTABLISHED`, `human_consent=NOT_ESTABLISHED`, `operational_authority=NONE`, `external_actions=0`, `memory_admitted=false`.

| Bounded input | Output | What it really means |
| --- | --- | --- |
| Local epoch older than any observed newer declared reference | `DENY / LOCAL_BELOW_LATEST_OBSERVED_REFERENCE` | Data inconsistency conditional on declared references; reference origin must still be authenticated |
| Local or remote older than **retained** high-water | `DENY / ...BELOW_RETAINED_HIGHWATER` | Works if high-water was separately protected; simulator doesn't protect it |
| Two references with different head hash for same epoch | `DENY / DECLARED_SPLIT_VIEW_SAME_EPOCH` | **Declared** split view, not cryptographically verified log equivocation; attacker may inject fake metadata (false denial possible) |
| Missing/unreachable remote | `HOLD_UNCERTAIN / NO_REFERENCE_AVAILABLE` | No silent acceptance on outage |
| Same admin controls two providers or two nominal signers | `HOLD_UNCERTAIN / SAME_DECLARED_ADMIN_ROOT` | Multiple copies do not count as independent custodians |
| Two different `admin_root` strings from one untrusted producer | `HOLD_UNCERTAIN / DISTINCT_ADMIN_LABELS_UNVERIFIED` | A label is not an external identity proof |
| Both old checkpoint and old signed reference appear mutually consistent | **`HOLD_UNCERTAIN`**; may show **read-only preview** | Strengthens W15's `DECLARED_ELIGIBLE` by preventing downstream accidental promotion to operational permission |
| Matching declared head and permissible read-only display | `HOLD_UNCERTAIN` with `read_only_preview=true` | A non-vacuous positive *display*, not a memory assertion, key activation or action authority |

**Negative rule for future consumers:** `read_only_preview` must **never** be interpreted as `SUPPORTED`, `ACCEPTED`, `TRIGGERED`, `GRANTED`, authenticated person consent or independent witness certification.

The mutation exercise made 13 independently chosen source changes *by the same test author*, including silently treating same-admin as independent, turning off high-water and fork checks, accepting duplicate witness keys, allowing fake operational authority and inventing verified currentness. Every one of those **13 chosen** defects produced a failing control. This is **test sensitivity**, not a 100% real security rating.

## 3. Existing project work reconciled — avoid duplicate governance lanes

| Existing project research | Already demonstrated or declared | W16 interpretation |
| --- | --- | --- |
| [R12–R17 external Witness Network work, Issue #171](https://github.com/SepehrGhanbari/Ario/issues/171) | Reports public cosignatures by Markovian/Geomys for an **external** Android log; operator keys initially drawn from public in-band pages, not independently pinned; R17 preapplication still blocked by eight missing fields | **Do not equate** third-party signature checks with witnessing of Ario's log, off-band operator key attestation or a public log enrollment. #171 remains the right external operator coordination issue |
| [W14 native four Linux UID test](W14_OS_UID_CUSTODY_AND_ROLLBACK_NEGATIVES_2026-11-17.md) | Kernel DAC blocked unprivileged cross-read; common root could read all lab key material and restore both displayed public views | Real UID separation only, not independent administrator custody |
| [W15 GitHub provider readback](W15_EXTERNAL_FRESH_REFERENCE_AND_OPERATOR_BOUNDARY_2026-11-17.md) | GitHub E1 signed public anchor actually fetched and pinned; E0+E1 denial; E0+E0 old view remains internally consistent | Provider network separation **without** repo-admin separation or freshness proof |
| [Protected memory version decision #216](https://github.com/SepehrGhanbari/Ario/issues/216) | Option B (immutable V1 + opt-in V2 sidecar) remains proposed/HOLD | W16 cannot approve memory V2, importer status, source truth or prospective actions |
| [Independent-review request #259](https://github.com/SepehrGhanbari/Ario/issues/259) | Requests independent reproduction of source/tests and negative cases | Extend existing review request; do not create a redundant implementation PR or claim external reviewer has responded |

R12–R17 details are **read from the first-party issue record**; this W16 session did **not** obtain the original private/local R17 ZIP or independently repeat those earlier witness cosignature validations.

## 4. What external protocol sources really require (not what this toy does)

1. [The Update Framework Specification](https://theupdateframework.github.io/specification/latest/) and [TUF metadata roles](https://theupdateframework.io/docs/metadata/) distinguish role-trusted keys, versions, timestamp expiration, a retained prior trusted version and rollback/freeze detection. TUF is a software-update security protocol, **not** direct Ario action consent or memory truth certification.
2. [RFC 9162 Certificate Transparency v2](https://www.rfc-editor.org/rfc/rfc9162.html) addresses signed tree heads and cryptographic consistency proofs. **W14/W15/W16 are not CT Merkle logs**, do not prove inclusion or completeness, and do not verify a log-gossip network.
3. [C2SP Transparency Log Witness Protocol v1.1.0](https://c2sp.org/tlog-witness@v1.1.0), [Witness Network participation](https://witness-network.org/participate/) and [log-list format](https://witness-network.org/log-list-format/) describe a log origin, public vkey, checkpoint/consistency operations and witness cosignatures. A witness specifically follows one log's checkpoints and validates consistency. W16 has **no Ario-origin log**, no public test-log key pin, no independent enrollment and no external application sent.

None of these standards says that two public URLs controlled by one repository owner are two independent custodians.

## 5. Mandatory acceptance gates before claiming independent custody

**All gates are currently OPEN / NOT ESTABLISHED:**

- [ ] **Operator identity:** two actual separately administered operators, independently authenticated outside the very memory/repository they're checking; document different admin roots, legal/technical control and recovery without guessing.
- [ ] **Pinned trust root:** independently obtained and authenticated public vkeys/key rotation evidence, not self-certified `admin_root` strings or GPT-generated profiles.
- [ ] **Real log interface:** dedicated Ario *testing-only* log origin and its signed checkpoint + verifiable append-only consistency proof, not W15's synthetic linear hash chain. Eight R17 fields in #171 must be supplied and vetted beforehand.
- [ ] **Freshness agreement:** verifier checks current consistency and previous retained high-water, supports multiple operators/quorum, bounded staleness from a trusted clock, and stays `HOLD_UNCERTAIN` on unavailable/disagreeing/historical-only references.
- [ ] **Common-owner failure control:** with one administrator able to rewrite local and hosted state, negative tests must prove they **cannot** be marketed as independently witnessed. Adversary withholding E2, republishing E0 and changing both vkeys is a required red test.
- [ ] **No authority confusion:** witnessed append-only history remains distinct from claim truth, two-party Ario/founder veto, signed user consent, action idempotency and memory admission.
- [ ] **Independent reviewer:** a separate person/device/role submits a new counterexample and actual source-pinned replication with `CONFIRMED/REFUTED/UNKNOWN`. Self-authored tests and CodeRabbit rate limits do not satisfy this.
- [ ] **Explicit protected authorization:** only a separate approved governance/security decision may ever change a NO_GO. Research PR or green CI must not trigger it.

**Engineering decision for now:** keep `RESEARCH_ONLY / #171_OPERATOR_HOLD / #259_REVIEW_OPEN / #216_MEMORY_HOLD / #242_DRAFT / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO / NO_AUTOMATIONS`.

**A useful failure is not a defeat:** `UNKNOWN` is the correct answer whenever we lack evidence of who truly controls the alleged independent witness.
