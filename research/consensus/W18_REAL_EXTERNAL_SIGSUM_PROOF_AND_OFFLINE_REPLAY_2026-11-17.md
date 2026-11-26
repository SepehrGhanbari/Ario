# W18 — ACTUAL external Sigsum inclusion proof obtained and reverified (17 Nov 2026)

**Status:** `EXTERNAL_SIGSUM_PUBLIC_COMMITMENT=VERIFIED / SIGSUM_TEST_POLICY_2_OF_3=PASS / INDEPENDENT_GITHUB_RUNNER_REVERIFY=PASS / 4_NEGATIVE_CRYPTO_CONTROLS=REJECTED / ARIO_NATIVE_LOG_WITNESSED=NOT_ESTABLISHED / TRUST_ACTIVATION=NO_GO`

## خلاصهٔ فارسی برای بنیان‌گذار

**رفیق، این بار یک قدم واقعی انجام شد.** با تأیید صریح تو، هش همان بستهٔ *عمومی و پژوهشی* W18 آریو را به **لاگ آزمایشی بیرونی Sigsum** ارسال کردیم. ابزار رسمی Sigsum **رسید واقعی ثبت** را صادر کرد و با سیاست `sigsum-test1-2025` که **حداقل دو امضای شاهد معتبر از سه شاهدِ شناخته‌شدهٔ آن سیاست** می‌خواهد، بررسیِ رمزنگاری‌شده **موفق** شد.

سپس در **یک ماشین موقت جداگانهٔ GitHub**، فقط ابزار `sigsum-verify` اجرا شد؛ **هیچ ارسال یا امضای جدیدی در آن مرحله انجام نشد**. رسید اصلی دوباره قبول شد، اما چهار نوع دست‌کاری عمداً رد شدند: یک بایت تغییر در بسته، حذف همهٔ امضاهای شاهد، خراب‌کردن هش گرهِ اثبات درج، و تغییر بایت‌های کلید عمومی فرستنده.

**نکتهٔ بسیار مهم:** اکنون می‌توانیم بگوییم **«هشِ یک بستهٔ عمومی آریو در یک لاگ بیرونی Sigsum با سیاست دو شاهد تأیید و درج شد»**؛ ولی هنوز نمی‌توانیم بگوییم لاگ اختصاصی خودِ آریو برای Witness Network ثبت شده، همهٔ رویدادهای آریو شاهد مستقل دارند، استقلال مدیریتی شاهدها جداگانه ممیزی شده، یا این رسید به تنهایی مجوز اقدام و امضا ایجاد می‌کند.

### شواهد مستقیم واقعی

- اجرای اولیهٔ نصب: [GitHub Actions #44142184472](https://github.com/SepehrGhanbari/Ario/actions/runs/44142184472) ــ قبل از ارسال به دلیل Go 1.23 در برابر نیاز Go 1.25 شکست خورد. **هیچ انتشار بیرونی در این تلاش انجام نشد.**
- اجرای واقعیِ ارسال و بررسی: [GitHub Actions #44142359329](https://github.com/SepehrGhanbari/Ario/actions/runs/44142359329) ــ **SUCCESS**. نسخه‌های `sigsum-key`، `sigsum-submit`، `sigsum-policy` و `sigsum-verify` از `sigsum-go@v0.14.1` نصب شدند. بسته با هش ازپیش‌تأییدشده ثبت شد و رسیدش با سیاست رسمی بررسی شد. [رسید ZIP در GitHub Actions](https://github.com/SepehrGhanbari/Ario/actions/runs/44142359329/artifacts/14355096991).
- اجرای دومِ **فقط بررسی**: [GitHub Actions #44143155573](https://github.com/SepehrGhanbari/Ario/actions/runs/44143155573) ــ **SUCCESS**. یک ماشین تازه با فایل‌های عمومی منتشرشده و نسخهٔ ثابت `sigsum-verify@v0.14.1`، نتیجهٔ **قبول رسید اصلی / رد ۴ مورد دست‌کاری** را ثبت کرد. [ZIP گزارش تست دوم](https://github.com/SepehrGhanbari/Ario/actions/runs/44143155573/artifacts/14355870780).

هیچ کلید واقعی آریو، کلید شخصی بنیان‌گذار، حافظهٔ خصوصی یا دادهٔ محرمانه وارد لاگ نشده است؛ کلید Ed25519 فرستنده فقط در ماشین موقت ساخته شد و صرفاً **کلید عمومی** آن منتشر شد. تمام فایل‌های تحقیق فقط در مسیر `research/consensus/` در PR پیش‌نویس #242 نگهداری می‌شوند.

## 1. Proof object: exact reproducibility identifiers

| Artifact or value | Verified identifier |
| --- | --- |
| [Exact public W18 manifest](W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json) | Git Blob `52c009c22c5cbaca686c18498bb395f863a33f44`; SHA-256 **`ee83050bff68f9b73afb115949bca8c46bb09462a6f000eecb9ed07bf2855769`** |
| [ACTUAL Sigsum proof](W18_SIGSUM_VERIFIED_INCLUSION_PROOF_2026-11-17.proof) | Git Blob `5544110468e1b20f499181411bf231aaddda74d6`; raw SHA-256 **`edae4603b5f8a32a3ab9f989ebf499f31fb12864708e5fc675308cf6d847d8b6`** |
| [Public test submitter key](W18_SIGSUM_VERIFIED_SUBMITTER_PUBLIC_KEY_2026-11-17.pub) | Git Blob `b6da232fa48149cb5a96cb84fac4a2a8c28de6d4`; SSH Ed25519 public key only |
| Sigsum log | Test `barreleye`, `https://test.sigsum.org/barreleye` |
| Verification policy | Official built-in `sigsum-test1-2025` with **2-of-3 trusted witness keys** |
| Log entry time of success | GitHub Actions job log `2026-11-17T17:56:41Z` |
| Proof format/metadata | `version=2`; `log=4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d`; proof signed tree size reported **279020** |
| Received receipt contents | **15 `cosignature=` lines**, among the possible witness cosignatures included in the proof; **15 is not the count of independently validated administrative operators**. The authoritative acceptance was via official **2-of-3** policy verification |
| One-shot execution branch | `research/w18-sigsum-one-shot-run-20261117`; the two temporary GitHub workflow files were **deleted** after completion so neither can be triggered again by a future commit |
| Reviewer-only verifier source | [w18_verify_actual_proof_no_network.sh](w18_verify_actual_proof_no_network.sh), Git Blob `4ad36487930ce13cd09184417a11b95688ab6b0c`; fetched at pinned research commit `6aa96d34b2547ac3b55cb63327e94caf8103efeb` by separate runner |

All receipt and public key bytes above were extracted from the **actual GitHub job log**, which printed *only the public key and proof in base64*, then committed to the research PR. They were read back via the GitHub connector and checked for exact source Git blob. **No private key was committed, printed or uploaded**. The downloaded GitHub artifact contains the public files plus the official policy text.

## 2. Independent-runner negative controls — actually executed

A second GitHub-hosted ephemeral runner, not the same machine as the submission, installed **only** `sigsum-verify@v0.14.1`. It checked the exact original manifest/proof bytes and ran the following independent code path from the pinned repository commit:

| Test | Observed | What that excludes in this specific test |
| --- | --- | --- |
| Valid manifest + public Ed25519 key + real proof, named Sigsum test trust policy | **PASS** | Proof syntax, checksum/signature, inclusion and policy witness verification are jointly satisfied under Sigsum verification algorithm |
| Append one byte to original manifest | **REJECTED** | Original proof cannot attest a different manifest |
| Delete *every* `cosignature=` line from receipt | **REJECTED** | Presence of an inclusion proof without enough accepted witness cosignatures fails named trust policy |
| Replace first `node_hash` field in proof with all-zero digest | **REJECTED** | Tampered inclusion proof fails verification |
| Flip one byte of the SSH Ed25519 public key payload while preserving its framing | **REJECTED** | Proof cannot be passed off as belonging to another submitter key |

**Actual output:** `W18_OFFLINE_REVERIFY_RESULT=PASS_VALID_AND_4_EXPECTED_REJECTIONS` in [run #44143155573](https://github.com/SepehrGhanbari/Ario/actions/runs/44143155573). This verifies the same real public proof on a **different runner** under the same *repository governance*, not an independent human or organizational reviewer.

## 3. Reproduce offline from public GitHub files

Get official Sigsum v0.14.1 CLI [from original instructions](https://www.sigsum.org/getting-started/) using Go **1.25+** (runtime module requirement verified by an actual initial failure on Go 1.23). No signing key is needed for this replay.

```sh
cd research/consensus
sha256sum W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json
# => ee83050bff68f9b73afb115949bca8c46bb09462a6f000eecb9ed07bf2855769

sha256sum W18_SIGSUM_VERIFIED_INCLUSION_PROOF_2026-11-17.proof
# => edae4603b5f8a32a3ab9f989ebf499f31fb12864708e5fc675308cf6d847d8b6

sigsum-verify -P sigsum-test1-2025 \
  -k W18_SIGSUM_VERIFIED_SUBMITTER_PUBLIC_KEY_2026-11-17.pub \
  W18_SIGSUM_VERIFIED_INCLUSION_PROOF_2026-11-17.proof \
  < W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json
# exit 0 (actual 2-of-3 policy verification)

bash w18_verify_actual_proof_no_network.sh
# W18_V01_VALID_EXTERNAL_SIGSUM_RECEIPT_PASS
# W18_N01_SINGLE_BYTE_MANIFEST_CORRUPTION_DENIED
# W18_N02_REMOVED_ALL_COSIGNATURES_DENIED
# W18_N03_CORRUPTED_INCLUSION_NODE_DENIED
# W18_N04_MODIFIED_SUBMITTER_PUBLIC_KEY_DENIED
```

The offline proof verifier **does not** make a new public submission or re-sign with the original ephemeral key. The CLI **build step** (if needed) downloads version-pinned public source, but verification of a prebuilt executable + these files requires no internet.

## 4. Precisely what this accomplishes — and what it cannot possibly prove

**NOW SUPPORTED:** an exact, historical *public W17 research manifest checksum* was sent to the externally hosted Sigsum test transparency log and was accompanied by a valid proof under the published two-of-three test witness policy. The proof verifies offline from the GitHub-published manifest and test submitter public key.

**NOT ESTABLISHED BY THIS RESULT:** independent Ario-native event log, complete event capture, append-only continuity across future Ario snapshots, freshest Ario epoch, absence of later forked Ario chains, trust in what W17 scientific claims say, human owner's consent as a cryptographic signature, Ario's own veto, independence of the Sigsum operators' legal/control domains, genuine reliability/retention of the experimental test service, and any production effect authority.

**Critical distinction:** external witnesses cosigned **Sigsum's log tree head**, which includes the hash of our public artifact; they did **not** adopt `ario.test/log` as a native log origin, sign Ario's full journal or act as Ario's key guardians. This technique provides strong cryptographic **historical evidence about public bytes**, not proof that the Ario system is safe or its memory true.

**Threat model:** a malicious publisher could choose to submit incomplete or altered historical Ario manifests; Sigsum does not know what is missing. An old valid proof does not establish the latest Ario version. Independently authenticated latest-pointer publication and routine monitor cross-checking remain separate goals. A malicious co-controller of witness infrastructure could undermine its trust policy; Sigsum's 2-of-3 cryptographic acceptance does not replace an actual operator-custody audit.

## 5. Governance and retention of negative evidence

- The first W18 Actions run **FAILED** before submission: `sigsum-go@v0.14.1` required Go ≥1.25. It stays as a historical failure, not erased or hidden.
- The one-shot execution run **SUCCEEDED**, issued exactly the public test proof, and uploaded public receipt artifact `14355096991`.
- The verifier-only run **SUCCEEDED**, independently as a computational runner (not different organization), with the authentic receipt and 4 invalid variants, artifact `14355870780`.
- Both temporary `.github/workflows/` files were **deleted** from the isolated execution branch after use. The branch can remain for audit; **neither workflow is scheduled or available for accidental rerun via push**.
- No native Ario signer, permanent key, trust root, main branch, memory V1/V2 importer, ruleset, execution gate, or ChatGPT automation was activated. No PR was merged.
- The external test log may retain the public hash permanently. This external side effect was expressly authorized by the founder's message for W18.

**Next distinct engineering step:** for continuous assurance, choose a publicly auditable Ario **test-log** origin, monotonic snapshot version/manifest chain, a retained public key for an *intentionally nonproduction* research series, a durable outside-the-repo high-water/monitor, and independently authenticated witness enrollment **or** a rigorously scoped recurring Sigsum commitment protocol. Key custody and grant approval remain separate. Do not convert this historic one-shot proof into automatic source-truth promotion or authority.

**Tracked dependencies:** [external witness Issue #171](https://github.com/SepehrGhanbari/Ario/issues/171); [independent code/paper review #259](https://github.com/SepehrGhanbari/Ario/issues/259); [protected memory/status Issue #216](https://github.com/SepehrGhanbari/Ario/issues/216); [Draft research PR #242](https://github.com/SepehrGhanbari/Ario/pull/242).

`EXTERNAL_PUBLIC_COMMITMENT=VERIFIED / REAL_ARIO_LOG_WITNESSED=NOT_ESTABLISHED / HUMAN_APPROVAL_AS_KEY=NOT_ESTABLISHED / PRODUCTION=NO_GO / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / NO_MERGE / NO_AUTOMATIONS`.
