# W19 — Independent adversarial assessment of W18 Sigsum proof and witness custody

**Date:** 2026-11-17  
**Decision:** `HISTORICAL_PUBLIC_SIGSUM_INCLUSION=VERIFIED / CROSS_ORGANIZATION_SIGNATURE_POLICY=VERIFIED_FOR_THE_SAME_RECEIPT / ORIGINAL_TEST1_QUORUM_ORGANIZATIONAL_INDEPENDENCE=INSUFFICIENT / PRIVATE_KEY_ADMIN_CUSTODY=NOT_ESTABLISHED / ARIO_NATIVE_EVENT_LOG_WITNESS=NOT_ESTABLISHED / RESEARCH_ONLY / HOLD`.

## خلاصهٔ فارسی برای بنیان‌گذار — اول این قسمت کافی است

رفیق، **رسید W18 معتبر بود، اما سیاست انتخاب‌شدهٔ اولیه یک ضعف اساسی داشت**: سه شاهد Sigsum با نام‌های `nisse`، `rgdd` و `witness1.smartit.nu` را **سه کارمندِ یک شرکت** اداره می‌کنند. این سه کلید مستقلِ رمزنگاری‌شده به‌خودی‌خود **سه شرکت یا سه مدیر حقوقی مستقل** نیستند. خودِ صفحهٔ تیم Glasklar Teknik هر سه را در فهرست کارکنان آورده است.

**کشف تازه:** در همان رسید W18 **۱۵ امضای شاهد با هش کلید متمایز** وجود دارد، نه فقط سه شاهدِ سیاست قدیمی. با محاسبهٔ SHA-256 کلیدهای عمومیِ منتشرشده در منابع بیرونی، امضاهای مربوط به **Google TrustFabric** و **Remora** نیز پیدا شدند. روی یک GitHub runner مستقل از ماشینِ ارسالکننده (ولی همچنان زیر حساب/مالک همین مخزن)، ابزار اصلی `sigsum-verify@v0.14.1` اجرا شد:

- **سیاست سخت‌گیرانهٔ ۱:** فقط اگر **Glasklar + Google** هر دو امضای معتبر داشته باشند → **PASS**.
- **سیاست سخت‌گیرانهٔ ۲:** فقط اگر **Remora + Google** هر دو امضای معتبر داشته باشند → **PASS**.
- حذف امضای Google از رسید → **هر دو سیاست جدید رد می‌کنند**؛ ولی **سیاست اولیهٔ test1 همچنان قبول می‌کند**. یعنی شکاف اصلی واقعاً قابل‌بازتولید است.
- حذف امضای Glasklar یا Remora از سیاست مربوط، و جایگزینی کلید جعلی Google → **رد شدند**.

**نتیجه:** می‌توانیم برای همین **یک رکورد پژوهشی عمومی** امضای معتبر شاهدها با هویت اپراتوریِ منتشرشده توسط **سازمان‌های متفاوت** را بررسی کنیم، **بدون ثبت مجدد هیچ داده یا ساختن کلید**. این هنوز به معنی ممیزی واقعیِ مدیران/نگهداری کلید خصوصی، شاهددار شدنِ تمام لاگ آریو یا اجازهٔ اقدام نیست. شاهد Google در محیط **DEV** است و طبق سایت رسمی خود Google هیچ تضمین پایداری/عدم تغییر کلید ندارد.

## 1. Directly inspected source and cryptographic evidence

| Exact artifact | What was independently checked | Status |
| --- | --- | --- |
| [W18 public manifest](W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json), SHA256 `ee83050bff68f9b73afb115949bca8c46bb09462a6f000eecb9ed07bf2855769` | Four referenced W17 Git blob IDs were each read by GitHub connector at exact historical commit `fa4216c54617523d7a7b23cdd0f605610aa81cf7`: **4/4 exact matches** | `RECORD_SCOPE_VALIDATED` |
| [W18 real proof](W18_SIGSUM_VERIFIED_INCLUSION_PROOF_2026-11-17.proof), SHA256 `edae4603b5f8a32a3ab9f989ebf499f31fb12864708e5fc675308cf6d847d8b6` | Original W18 official verifier in [run 44142359329](https://github.com/SepehrGhanbari/Ario/actions/runs/44142359329) and separate no-submit verifier in [run 44143155573](https://github.com/SepehrGhanbari/Ario/actions/runs/44143155573) both **PASS**, four corrupt variants denied | `ORIGINAL_TEST_POLICY_CRYPTO_PASS` |
| [W19 Glasklar+Google policy](W19_GLASKLAR_GOOGLE_REQUIRED.policy), Git blob `30d3109868ad2b38676af0aa2ade878e217f36a3` | **BOTH** nisse and Google's official DEV witness key required. Actual `sigsum-verify -p` passed on **unchanged W18 proof** | `CROSS_PUBLISHED_ORGANIZATIONS_CRYPTO_PASS` |
| [W19 Remora+Google policy](W19_REMORA_GOOGLE_REQUIRED.policy), Git blob `cc2061542cbb6cac3252cebc350eb8b71c2c8d78` | **BOTH** Remora and Google witness public keys required. Actual `sigsum-verify -p` passed on **unchanged W18 proof** | `TWO_PUBLISHED_OPERATORS_CRYPTO_PASS` |
| [W19 executable source](w19_verify_cross_operator_existing_proof.sh), Git blob `88cb4967c93e89e279916fbaace06a31792826dd` | Checks pinned manifest/proof, hashes witness raw public keys to match signed receipt key IDs, and executes real cryptographic verification and negative tests | `RERUNNABLE` |
| [W19 actual GitHub one-time run](https://github.com/SepehrGhanbari/Ario/actions/runs/44146907147), commit `6197696065563da47fc63ce3de7fad5b6ebe7bfc` | Job **SUCCESS**, [public stdout artifact](https://github.com/SepehrGhanbari/Ario/actions/runs/44146907147/artifacts/14357286779), 2 new positive policies, 5 labeled negative/policy-degradation controls | `ACTUALLY_EXECUTED` |
| [Machine-readable W19 results](W19_WITNESS_ORGANIZATIONAL_INDEPENDENCE_AND_STRICT_POLICY_RESULTS_2026-11-17.json) | Actual case IDs, exact witness public-key hashes and source links | `ARCHIVED` |

All W19 checks used **the existing public W18 proof** only; the verification runner installed **only** the official Sigsum verifier. It made **no new Sigsum publication, no new signature, no Ario private-key operation**. Its two custom policy files and source are research material on Draft PR #242, not a production trust policy already deployed in Ario. The one-time `.github/workflows/w19-cross-operator-once.yml` file was deleted from the disposable execution branch after the successful run.

## 2. The organizational finding — **verified from first-party public disclosures**

[Sigsum's original test1 policy](https://www.sigsum.org/getting-started/) recognizes these keys:

| Witness | Operator evidence | Organization relationship |
| --- | --- | --- |
| `poc.sigsum.org/nisse` | Niels Möller; see [Sigsum documented test policies](https://docs.rs/sigsum/latest/sigsum/policy/static.SIGSUM_TEST_2025_3.html) | Glasklar Teknik staff |
| `rgdd.se/poc-witness` | Rasmus Dahlberg; see same test-policy source | Glasklar Teknik staff |
| `witness1.smartit.nu/witness1` | Elias Rudberg; see same test-policy source | Glasklar Teknik staff |

[Glasklar Teknik's own staff page](https://www.glasklarteknik.se/about/) lists all three people. Thus, `sigsum-test1-2025` requires **two different recognized public keys**, **not** two employees of different companies. Separate legal/administrative control is a **stronger** requirement not demonstrated by this policy. This does **not** make the cryptographic proof invalid or show any operator wrongdoing.

The original test1 verification **continued to PASS even after deleting Google's cosignature from the receipt**. That is the decisive **policy-sensitivity counterexample**: test1 succeeds without involving a public witness outside this Glasklar group.

**Additional first-party external operator evidence:** [TrustFabric witnesses](https://transparency.dev/witnesses/) explicitly identifies `transparency.dev/DEV:witness-little-garden` as a **Google TrustFabric team witness on Google Cloud**. It explicitly warns DEV witnesses are best-effort, may reset, rotate keys, disappear, and **must not be relied upon**. [Witness Network's operator table](https://witness-network.org/witness-tables/) identifies `remora.n621.de` with Florian Larysch, a separately published operator. This verifies **public organizational labels**, not actual independent administrators or controls over those private signing keys.

**Matched cryptographic witness-key hashes actually inside W18 proof:**

| Witness public identity | Published 32-byte public key | SHA256(public key) in cosignature key-hash |
| --- | --- | --- |
| nisse / Glasklar | `1c25f8a44c635457e2e391d1efbca7d4c2951a0aef06225a881e46b98962ac6c` | `1c997261f16e6e81d13f420900a2542a4b6a049c2d996324ee5d82a90ca3360c` |
| remora / independently published individual operator | `ebcdeb78e7fdb2ef9227b2c1ef11e94600b55b4d6d9a57877e31ee89e59adc36` | `86b5414ae57f45c2953a074640bb5bedebad023925d4dc91a31de1350b710089` |
| Google TrustFabric DEV | `2b6eb0ec483503544cde4e8fc1ce6d1921db21dffccc186865f808f7625443cc` | `d960fcff859a34d677343e4789c6843e897c9ff195ea7140a6ef382566df3b65` |

SHA256 matching is only a *precondition*. The **actual** verification of witness signatures, log tree head, inclusion proof and quorum was performed by `sigsum-verify@v0.14.1` under the newly authored named public-key policies.

## 3. Results of the one-shot, **verifier-only** W19 run

| ID | Experiment on actual public W18 receipt | Actual result |
| --- | --- | --- |
| P01 | Require **Glasklar + Google** both signatures | **PASS** |
| P02 | Require **Remora + Google** both signatures | **PASS** |
| N01 | Delete Google signature; check previous `sigsum-test1-2025` policy | **PASS** — demonstrates original policy never required Google |
| N02 | Delete Google; check both NEW required-two policies | **Both DENY** |
| N03 | Delete Glasklar signature; check policy P01 | **DENY** |
| N04 | Delete Remora signature; check policy P02 | **DENY** |
| N05 | Replace Google public key in policy; check P01 | **DENY** |

Primary preserved stdout labels: `W19_P01_GLASKLAR_AND_GOOGLE_STRICT_CROSS_OPERATOR_POLICY_PASS`, `W19_P02_REMORA_AND_GOOGLE_STRICT_CROSS_OPERATOR_POLICY_PASS`, `W19_N01_ORIGINAL_TEST_POLICY_STILL_ACCEPTS_WITHOUT_GOOGLE_CONFIRMS_COMMON_ORG_RISK`, `W19_N02_BOTH_STRICT_POLICIES_REJECT_MISSING_GOOGLE`, `W19_N03_STRICT_A_REJECTS_MISSING_GLASKLAR`, `W19_N04_STRICT_B_REJECTS_MISSING_REMORA`, `W19_N05_STRICT_A_REJECTS_FORGED_GOOGLE_PUBLIC_KEY`. Source: [GitHub Actions run #44146907147](https://github.com/SepehrGhanbari/Ario/actions/runs/44146907147). All negatives were *tests on copies*; actual published proof bytes were not changed.

## 4. Hard limitations and final threat assessment

| Security claim | Grade | Interpretation |
| --- | --- | --- |
| Exact W17 manifest bytes tied to four actual W17 historical Git blobs | **VERIFIED** | Public source-integrity reference, not scientific truth |
| Actual Sigsum log inclusion under 2-of-3 test witness policy | **VERIFIED** | Official cryptographic verifier PASS |
| Same proof under **Glasklar + Google** and **Remora + Google** mandatory signatures | **VERIFIED** | Cross-published operator identities established cryptographically **for this one historical tree head** |
| Full independent OS/admin control over those witness signing keys | **NOT ESTABLISHED** | Google's and named operators' webpages are not an OS access/custody audit |
| Reliable, long-term production witness availability | **NOT ESTABLISHED** | All relevant tests were on TEST/DEV services, some explicitly no-guarantees |
| Ario's **own** append-only event log witnessed under its origin | **NOT ESTABLISHED** | Sigsum signs a tree containing ONE externally published W17 research record's checksum, not Ario's internal event journal |
| Completeness of events or proof of the **latest** Ario epoch | **NOT ESTABLISHED** | Withheld/missing future epochs remain undetectable without actual independent monitor/high-water |
| Actual founder+Ario key-based consent, legitimate human intent | **NOT ESTABLISHED** | Submitter's Ed25519 key was ephemeral and never bound to actual Ario permission or owner signer |
| Truth of memory content, source claims, action permission | **NOT ESTABLISHED / NONE** | A witnessed hash proves public commitment of bytes, not their truth or authorized effect |
| Reviewer legally/administratively independent of the same GitHub repo | **NOT ESTABLISHED** | New verifier runner is a separate machine but uses the repo publisher's self-authored policies/code |

A cosignature carries an authenticated timestamp string (this proof's 15 show Unix `1794938200`, **17 Nov 2026 17:56:40 UTC**), but [Sigsum's proof verification documentation](https://github.com/sigsum/sigsum-go/blob/main/doc/sigsum-proof.md) states that timestamp values are **not otherwise evaluated as a freshness proof** after signature verification. Do not call this a trusted statement of the latest world state.

**One more caution:** external public-key pinning here used official provider sources and static research policy files, but these custom policy files are still distributed through the **same Ario GitHub repository**. For a real independence claim, outside reviewers must obtain and pin policy keys and monitor references from a genuinely separate trusted channel; a self-authored JSON stating `owner=independent` is never enough.

## 5. Decision, review assignment, and next safe engineering step

**Accept W18 as a research result:** `HISTORICAL_EXTERNAL_SIGSUM_PUBLIC_RECORD=VERIFIED`, with W19 cross-operator cryptographic strengthening. Preserve the negative finding `INITIAL_TEST1_POLICY_NOT_ORGANIZATIONALLY_INDEPENDENT`, do not rewrite W18 history.

**Review next:** Independent verifier obtains the exact W18 manifest/public key/proof, official original Google/Glasklar/Remora keys from outside Ario, reruns both W19 policies, and independently checks which organization can actually control/revoke each signer, retained witness high-water state and test-log data availability. Require a novel adversarial counterexample and a benign positive.

**For native Ario log witnessing (Issue #171):** build a separate **public synthetic Ario test log** with a stable test origin and independently verifiable append-only consistency proofs, pin a long-lived testing-only origin public key with reviewed custody, define a real monitor/high-water retention process outside the repo's single admin, and pursue witnessed checkpoints from separately controlled operators. This is a distinct project phase and **does not require re-signing or modifying the historical W18 Sigsum proof**.

**Keep protected controls:** `#242_DRAFT_HOLD / #171_NATIVE_LOG_OPEN / #259_INDEPENDENT_REVIEW_OPEN / #216_HOLD / GENESIS=NO_GO / SIGNER=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO / NO_AUTO_SUBMISSION`.
