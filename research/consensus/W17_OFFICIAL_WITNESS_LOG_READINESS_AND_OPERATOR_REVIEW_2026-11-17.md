# W17 — Source-verified witness preapplication: separate public paperwork from independent custody

**Date:** 17 November 2026  
**Decision marker:** `DR-RES-W17-SOURCE-REVIEW / RESEARCH_ONLY / NO_EXTERNAL_APPLICATION / WITNESS_CUSTODY=NOT_ESTABLISHED / OWNER_SIGNER=NO_GO / MEMORY_V2=HOLD / NO_MERGE`

## ۱. خلاصهٔ فارسی برای بنیان‌گذار — نیاز نیست همهٔ سورس‌ها را بخوانی

رفیق، گره اصلی را پیدا کردیم: **پنج موردی که Witness Network برای معرفی یک لاگ به‌طور عمومی می‌خواهد با هشت مدرک امنیتیِ داخلی آریو یکی نیستند.** یک فرم تکمیل‌شده، به معنی «شاهد مستقل ثبت و تأیید شد» نیست.

- منابع رسمی را مستقیم خواندیم: راهنمای مشارکت، قالب فهرست لاگ‌ها، پروتکل شاهد نسخهٔ 1.1.0 و استاندارد TUF.
- فهرست عمومی *testing* را در ۱۷ نوامبر بازیابی کردیم: ۱۷ ورودی `vkey` دیدیم؛ نام **Ario/SepehrGhanbari به‌صورت صریح** نبود. این فقط یک مشاهدهٔ محدود است، نه اثبات نبودن یک لاگ با نام دیگر.
- در پروندهٔ قدیمی [#171](https://github.com/SepehrGhanbari/Ario/issues/171) آزمایش واقعیِ امضاهای شاهد عمومی برای **لاگِ دیگری** گزارش شده، نه برای لاگ آریو. اصل فایل ZIP محلی R17 را در این مرحله به‌طور مستقل باز نکردیم.
- یک آزمون ۳۰ حالتهٔ صرفاً پژوهشی اضافه کردیم که تفاوت «اطلاعات فرم نوشته شده» و «هویت و اختیار واقعاً تأیید شده» را حفظ می‌کند. حتی اگر تمام فیلدها پر و دو مدیر «مستقل» ادعا شده باشند، خروجی هنوز `NOT_ESTABLISHED / NONE` است.
- هیچ پیام، درخواست ثبت‌نام، کلید واقعی، امضا، به‌روزرسانی `main` یا اتوماسیون ارسال نشده/انجام نشده است.

**تصمیم پیشنهادی:** تا وقتی مبدأ لاگ آزمایشی آریو، کلید عمومی از مسیر مستقل، نگهداری مستقل، چک‌پوینت و اثبات سازگاری با بازبین واقعی وجود ندارد، `NO_GO` پابرجاست. هیچ خروجیِ این پژوهش مجوز فعالیت حافظه، تأیید حقیقت یا اختیار امضا نمی‌دهد.

## 2. Three different gates: correct the R17-versus-official conflation

The [official *log* participation guidelines](https://witness-network.org/participate/) request:
1. stable log **origin** line;
2. published public **log vkey** (page recommends Ed25519 key type 0x01);
3. claimed **add-checkpoint rate**;
4. list requested: **testing** or **staging** (official page states production not available);
5. public **contact** information.

The same page separately describes **witness operator** participation, including operator public name, configured log lists, public witness vkey key type 0x04 (cosignature/v1) and service `add-checkpoint` URL. **These are two different roles.**

The eight earlier missing items in [Ario's R17 research Issue #171](https://github.com/SepehrGhanbari/Ario/issues/171) are *project-specific preapplication/evidentiary gates*, not eight formally required fields on the Witness Network's public log form:
`operator_public_name`, `real_log_origin`, `origin_control_evidence`, `dedicated_test_log_vkey`, `test_key_custody_evidence`, `checkpoint_url`, `consistency_url`, `public_operator_contact`.

For this W17 audit, all eight remain `NOT_VERIFIED_IN_AVAILABLE_PUBLIC_PROJECT_RECORD`. This means **not substantiated by the available record we inspected**, not a claim that a real person or a file cannot exist elsewhere. Their earlier author-reported test pass counts do not independently establish missing proofs.

**Future reviewers must not approve on paperwork alone**: even if all 5+8 fields are filled, [W17's structural-only checker](w17_witness_preapplication_audit.js) returns `system_ready=false`, `action_authority=NONE`, `authenticated_operator_independence=NOT_ESTABLISHED`. The test does not independently validate actual signing keys or humans.

## 3. Exact primary sources inspected on 17 Nov

| Original, versioned source | What was checked | What was NOT checked |
| --- | --- | --- |
| [Witness Network — Participate](https://witness-network.org/participate/) | Separate log versus witness roles; origin/vkey/rate/list/contact; `testing/staging` only and suggested human contact | Actual approval or operator agreement for Ario |
| [Witness Network — Log-list format](https://witness-network.org/log-list-format/) | `logs/v0`; ordered `vkey`, optional `origin`, `qpd`, `contact`; qpd range 1 ≤ qpd < 2^31 | Cryptographic integrity of any particular rendered log list |
| [Witness Network — Log lists](https://witness-network.org/log-lists/) | Public testing list URL and staging/production distinction; testing is explicitly unstable | Whether all possible log origins are listed or every witness has applied its config |
| [C2SP — tlog-witness v1.1.0](https://c2sp.org/tlog-witness@v1.1.0), dated 7 Oct 2026 | Original full primary text read via Firecrawl; a witness receives an origin-signed checkpoint plus consistency proof and tracks a last accepted checkpoint per log | No real Ario-origin checkpoint/proof or registered witness was sent/tested; no operator custody was established |
| [TUF spec 1.0.37](https://theupdateframework.github.io/specification/latest/), modified 8 Oct 2026 | A trusted client must detect rollback/freeze using versioned metadata and previous trusted state under its own assumptions | This is a software-update protocol, not an Ario consent or source-truth oracle |

**Actual public testing log-list snapshot:** [`https://testing.witness-network.org/log-list.1`](https://testing.witness-network.org/log-list.1) was scraped with Firecrawl freshness option `maxAge:0` on 17 Nov. In its **rendered text** 17 `vkey`, 17 `qpd`, 17 `contact` lines and a `logs/v0` header appeared, with **no literal case-insensitive Ario/SepehrGhanbari mention**. This is **not a signed raw-byte snapshot**; a scrape result is not proof of a currently authentic, complete or immutable public registry. An alternative origin label may exist. The official testing list itself warns about instability. We did not contact the operators or submit anything.

## 4. Machine-auditable work created here

- [W17 structural preapplication checker](w17_witness_preapplication_audit.js), plain JS standalone, run in isolated V8 without network or user secrets.
- [W17 30 self-authored test results](W17_PREAPPLICATION_TEST_RESULTS_2026-11-17.json), run from the exact functions committed in that source.
- [Machine-readable source/missing-proof register](W17_WITNESS_SOURCE_AND_MISSING_EVIDENCE_REGISTER_2026-11-17.json), one row for each official public field and each internal R17 research gate, plus primary source provenance and limited testing-list observation.

**Thirty development cases matched their own expected outcome** (not 30 independent witness probes). The principal negative controls include `claimed_independence={verified:true}`, `admin_count=1000`, two distinct fake admin labels and a syntactically plausible fake public vkey. They can make **form fields present** without granting **operator or key custody**. Positive controls: the public form may be structurally complete for `testing` or `staging`, and the eight internal strings may be present for a human *documentation review*, but **none** asserts actual current operator, log approval, human consent, memory admission or execution authority.

**Reproduction without secret keys** (GitHub research branch checkout only):
```sh
node research/consensus/w17_witness_preapplication_audit.js > W17_recomputed.json
# Compare all 30 ID / reason outputs with committed W17_PREAPPLICATION_TEST_RESULTS_2026-11-17.json.
# Do not run this against a production signer or upload any real secret.
```
The generated output is a *test-report JSON*, not a second operator signature or an approval record.

## 5. What must be verified separately before even considering a testing-tier application

Reviewers should answer `CONFIRMED / REFUTED / UNKNOWN` and attach **source link + exact evidence + real verifier identity**, rather than just green checkmarks:

- [ ] **Owner/primary-source review:** inspect both [#171](https://github.com/SepehrGhanbari/Ario/issues/171) R12–R17 notes and **original local ZIP files if actually available**. Do not claim an inaccessible ZIP has been reviewed.
- [ ] **Actual dedicated Ario test log:** a stable origin, public log key/vkey with out-of-band trust binding, *synthetic-only* append-only data/checkpoint with a real consistency proof; no user private chats or owner key.
- [ ] **Operator control and custody:** independently confirm the log operator/admin, key custody and permitted recovery/rotation; no inference from a URL, two UIDs on one root, two public signers or the owner's own self-attestation.
- [ ] **External witness identity:** two real separately administered witness operators if that's the proposed policy, with **independent public-key pinning**, real checkpoint cosignature tied to the Ario test-log origin and consistency verification. A genuine signature on a different Android log remains **irrelevant to admission of an Ario log**.
- [ ] **Freshness / unavailable source:** define trusted high-water persistence, time/freeze limits and what happens when independent newer checkpoints cannot be reached. If newest cannot be verified, `HOLD_UNCERTAIN`.
- [ ] **Operational controls:** signed consistency information never implies source-world truth, human consent, Ario's own veto, safe memory admission or permission for a prospective task. No action until separately governed.
- [ ] **New independent negative and positive:** a new attacker-authored old+old rollback / forged public vkey / compromised admin example and a non-vacuous benign read-only example.
- [ ] **External communication:** do not submit an application or start a witness service automatically; the official site prefers human-to-human interaction and the public record lacks verified contact/origin information.

## 6. Cross-issue decision; final research disposition

The [existing Witness Network readiness issue #171](https://github.com/SepehrGhanbari/Ario/issues/171) owns **operator preapplication/evidence**; the [independent reviewer request #259](https://github.com/SepehrGhanbari/Ario/issues/259) owns **code/source audit**; the [memory semantic hold #216](https://github.com/SepehrGhanbari/Ario/issues/216) owns **V1 versus V2/permission policy**. The research-only [Draft PR #242](https://github.com/SepehrGhanbari/Ario/pull/242) holds executable artifacts. **Do not open a parallel protected approval lane.**

**VERIFIED_THIS_TURN:** public original participation/log-format/protocol primary text read; testing-list rendered 17-entry snapshot inspected; W17 30 author-designed structural tests run; GitHub source evidence register published.

**NOT_ESTABLISHED:** out-of-band operator key pin, independent admin, actual Ario log/witness enrollment, currentness of all witnesses, independent source proof, any real-world user consent, externally reviewed test report.

**NEXT ACTUAL DEPENDENCY:** a *human-controlled, independently managed* test-log and witness operator identity/custody and a fresh checkpoint/consistency audit. Until then `R17=HOLD / W17=RESEARCH_ONLY / #216=HOLD / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO / NO_AUTOMATIONS`.
