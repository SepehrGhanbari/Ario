# W18 — An external witness path that does not require Ario to operate its own witnesses

**Research date:** 2026-11-17. **Decision:** `ACTIONABLE_PATH_IDENTIFIED / PUBLIC_ONLY_MANIFEST_PREPARED / DRY_RUN_PASS / ACTUAL_SIGSUM_PROOF=NOT_OBTAINED / REAL_ARIO_LOG_WITNESSED=NOT_ESTABLISHED / RESEARCH_ONLY / DRAFT_HOLD`.

## برای بنیان‌گذار — جواب کوتاه فارسی

**راه پیدا شد:** لازم نیست خودمان سه سرورِ «شاهد مستقل» بسازیم. می‌توانیم ابتدا با [Sigsum](https://www.sigsum.org/getting-started/) یک **اثبات ثبت عمومی** برای هشِ بستهٔ پژوهشی آریو بگیریم. سیاست آزمایشی موجود `sigsum-test1-2025` ثبت را با **امضای معتبر حداقل دو شاهد از سه کلید شاهد شناخته‌شده** می‌پذیرد. نگهداری این شاهدها خارج از مخزن آریو است؛ اما استقلال واقعیِ اداری آن‌ها، در این پژوهش مستقل ممیزی نشده است.

این یک **میان‌بُر واقعی برای شاهد بیرونیِ یک رکورد آریو** است: آریو فقط هش/مجموعهٔ ارجاع فایل‌های *عمومی* را می‌فرستد، Sigsum برای آن ثبت و رسید قابل‌بررسی صادر می‌کند، و بازبین دیگری می‌تواند با `sigsum-verify` بدون شبکه آن را راستی‌آزمایی کند. لازم نیست برای این فاز کلید اصلی بنیان‌گذار، کلید مستقل آریو یا دادهٔ خصوصی‌ای خرج شود.

**اما:** شاهدهای Sigsum در این فاز، **لاگ Sigsum** را همراه اثبات درج رکورد آریو تأیید می‌کنند؛ نه اینکه لاگ اختصاصی و تاریخچهٔ تمام رویدادهای آریو عضو Witness Network شده باشد. این روش **نمی‌گوید چه کسی واقعاً اجازه داده، آیا تمام رویدادها ثبت شده‌اند، آخرین نسخه کدام است یا یک ادعای حافظه حقیقت دارد.**

من یک مانیفستِ فقط‌عمومیِ W17 با هش ثابت، اسکریپت ارسال فقط با رضایت صریح و **تستِ بدون شبکه** ساختم. نتیجهٔ فعلی: بدون تأیید، چیزی به Sigsum ارسال نشده و **هیچ رسید خارجیِ امضاشده‌ای هنوز نداریم**. این وضعیت را با `NOT_OBTAINED` ثبت کرده‌ام، نه با واژهٔ «موفق».

## 1. Verified existing external infrastructure

The Sigsum [official getting-started guide](https://www.sigsum.org/getting-started/) explicitly gives a **two-of-three** test quorum under named policy `sigsum-test1-2025`:

```
log 4644af2abd40f4895a003bca350f9d5912ab301a49c77f13e5b6d905c20a5fe6 https://test.sigsum.org/barreleye
witness poc.sigsum.org/nisse         1c25f8a44c635457e2e391d1efbca7d4c2951a0aef06225a881e46b98962ac6c
witness rgdd.se/poc-witness          28c92a5a3a054d317c86fc2eeb6a7ab2054d6217100d0be67ded5b74323c5806
witness witness1.smartit.nu/witness1 f4855a0f46e8a3e23bb40faf260ee57ab8a18249fa402f2ca2d28a60e1a3130e
group quorum-rule 2 poc.sigsum.org/nisse rgdd.se/poc-witness witness1.smartit.nu/witness1
quorum quorum-rule
```

The [official service inventory](https://www.sigsum.org/services/) lists the test log and three test witness public keys, plus **separate stable log/witness services**; the test network explicitly has no uptime, retention, audit or human-operator independence guarantee from this Ario review. The [Sigsum proof format](https://github.com/sigsum/sigsum-go/blob/main/doc/sigsum-proof.md) binds a submitted signed checksum to an inclusion proof, a log tree head and cosignatures under the chosen policy. An **actual** offline verifier invocation is the acceptance step. A page listing three keys is **not a proof** that anyone has cosigned our record.

Compared with [Witness Network log participation](https://witness-network.org/participate/), this allows **faster external anchoring of an Ario research artifact without constructing our own public log**. The direct Ario-log witnessing route remains separate: stable origin, out-of-band public log vkey, real append-only checkpoint/consistency service, independent operator enrollment and pinned witness trust.

## 2. What has been authored and really checked (5 files)

| Artifact | Exact public Git Blob / local execution | Description |
| --- | --- | --- |
| [W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json](W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json) | `52c009c22c5cbaca686c18498bb395f863a33f44`; SHA-256 `ee83050bff68f9b73afb115949bca8c46bb09462a6f000eecb9ed07bf2855769` | Exact byte-pinned PUBLIC_ONLY snapshot references to four W17 research Git blobs, pinned historical commit `fa4216c546...`, no keys or private user data |
| [w18_sigsum_one_shot.sh](w18_sigsum_one_shot.sh) | `2cd9c130d984eb33555e2e10610bde01f9caaa56` | Version-pinned named-policy one-shot, **default DRY RUN**, requires a literal explicit approval flag before external submission, rejects any manifest bytes other than the hash above |
| [test_w18_sigsum_dryrun.sh](test_w18_sigsum_dryrun.sh) | `e094f5f6744ae735e26d9750769c448f476caad1` | Locally executed shell syntax, public manifest schema/pin, no-network default, unauthorized submit and absent proof refusal, changed-byte rejection even with approval flag |
| [W18_DRYRUN_OBSERVATIONS_2026-11-17.json](W18_DRYRUN_OBSERVATIONS_2026-11-17.json) | `9ea10edae25c88f26b214a6f189b221a03a64f8b` | Six observed bounded negative/positive **offline** development checks (no Sigsum binary or live signed proof), environment and original source hashes |
| **This source-audited decision packet** | Current Git blob: see GitHub content API | Original external URLs, real vs future states, and independent reviewer acceptance criteria |

The Bash+Python test ran in a disposable ChatGPT Linux container. **Shell syntax passed and test exited 0**; separate intentionally unauthorized and proof-missing commands exited 2; one-byte edited manifest was refused in dry-run and submit with approval flag. Public manifest SHA pinned. No Sigsum binaries were installed in that isolated runner (outbound DNS unavailable), **no live Sigsum submission was even attempted**. The only new network actions were earlier read-only inspection of original public documentation. Do not inflate these results into real witness signatures.

The submit tool creates a **new ephemeral test submitter key inside `mktemp -d`** and does not call any Ario signer or modify any Ario ledger. After an actual verified submission it would preserve only the public manifest, submitter public key, proof and policy for independent review, never the test private key. Key deletion prevents reusing that key for later rounds, so any continuing signer identity and multi-epoch operations would need a separately reviewed custody design.

## 3. Explicit manual consent and realistic execution sequence

**Stage A: completely offline, no third-party publication** (already locally executed):

```bash
bash research/consensus/test_w18_sigsum_dryrun.sh
bash research/consensus/w18_sigsum_one_shot.sh --dry-run \
  research/consensus/W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json
```

**Stage B: only after the human founder explicitly approves publishing the exact W18 manifest hash**. Use a *disposable Linux container/VM*, **never the Ario real key/signer host**, a current audited Go toolchain and the version from [Sigsum official instructions](https://www.sigsum.org/getting-started/):

```bash
go install sigsum.org/sigsum-go/cmd/sigsum-key@v0.14.1
go install sigsum.org/sigsum-go/cmd/sigsum-policy@v0.14.1
go install sigsum.org/sigsum-go/cmd/sigsum-submit@v0.14.1
go install sigsum.org/sigsum-go/cmd/sigsum-verify@v0.14.1
export PATH="$(go env GOPATH)/bin:$PATH"
sigsum-policy show sigsum-test1-2025
# Review output against the pinned two-of-three test policy above.

ARIO_W18_PUBLIC_SUBMISSION_APPROVED=YES \
bash research/consensus/w18_sigsum_one_shot.sh --submit \
  research/consensus/W18_PUBLIC_RESEARCH_ANCHOR_MANIFEST_2026-11-17.json \
  /tmp/ario_w18_verified_receipt_001
```

**Stage C: independent offline verification of the actual, nonempty proof** (also NOT YET RUN):

```bash
bash research/consensus/w18_sigsum_one_shot.sh --verify \
  /tmp/ario_w18_verified_receipt_001/manifest.json \
  /tmp/ario_w18_verified_receipt_001/submitter.pub \
  /tmp/ario_w18_verified_receipt_001/manifest.proof
```

Only after this tool reports a real Sigsum cryptographic policy pass **and a separate reviewer independently inspects the files**, should the public-only receipt be attached to PR #242. At that point the justified claim would be **"a public research snapshot's checksum was included in an externally witnessed Sigsum log under a named quorum policy"**. It would *not* be "Ario itself has independent trusted custodians for all its events." The script has **no scheduled trigger**, and no automated egress in default mode.

**Warning:** Sigsum publication is a third-party public, potentially permanent event; even test signing is not an action to perform silently. The script's literal opt-in is a usability guard, **not a cryptographic proof of human approval**. We will not issue a real key or send a public submission in this research response.

## 4. Minimal criteria for real evidence and negative tests

Reviewers must report `CONFIRMED/REFUTED/UNKNOWN`, exact source SHA, tool version, verified witness quorum, and a new adversarial negative test:

1. Independently obtain and review the published `sigsum-test1-2025` policy and witness public keys outside the Ario repo; verify that 2 distinct recognized witness signatures are **actually cryptographically checked by `sigsum-verify`**, not simply present as text or two copies of one key. Audit organizational separation if claiming two independently controlled *administrative* entities.
2. Attach genuine `manifest.proof`, public `submitter.pub`, public manifest bytes and a witnessed log tree-head record from a **successful real test submission**. An empty/mocked proof, a 200 response from a site, or a CI success is **not evidence**.
3. Modify one byte in the manifest and require `sigsum-verify` to **fail**. Remove a cosignature / corrupt a tree-head signature and require **fail** under the 2-of-3 threshold. Fewer than 2 valid different witness key signatures must not pass.
4. Run an independent Sigsum monitor for this public submitter key and see its leaf, or at least verify log inclusion/consistency from independently fetched log data. This matters for split-view/freeze threat models.
5. Show an old, fully valid Sigsum proof for epoch 0 **does not automatically imply epoch 1 doesn't exist**. Maintaining a protected, independently retained latest Ario anchor/monotonic epoch is a separate requirement.
6. Ensure only synthetic/public hashes go into external systems. Never send actual user chats, private memory, owner key, Ario private independent key, password or the real signer identity.
7. For the later **dedicated Ario log** path, follow [#171](https://github.com/SepehrGhanbari/Ario/issues/171) and its 5 official log form items plus 8 **Ario internal** evidence gates from W17. Actual Ario origin witnessed only if a real third-party cosignature for that **exact origin** verifies, not if a Sigsum entry contains a convenient filename.

A signed Sigsum proof means **public commitment under defined cryptographic trust**, not content truth, verified memory evidence, user consent, true administrative independence, action authorization or veto bypass.

## 5. Review ownership and hard safety boundaries

- **[Issue #171](https://github.com/SepehrGhanbari/Ario/issues/171):** external witness network, test-log enrollment, operator key and custody evidence. Avoid presenting Sigsum submission as actual `#171` enrollment.
- **[Issue #259](https://github.com/SepehrGhanbari/Ario/issues/259):** independent replay and source/protocol critique, including trust-policy downgrade, forged public key and stale-proof counterexamples.
- **[Issue #216](https://github.com/SepehrGhanbari/Ario/issues/216):** protected memory V1/V2 interpretation and action permission; **W18 cannot approve or change it**.
- **[Draft PR #242](https://github.com/SepehrGhanbari/Ario/pull/242):** this bounded research code and evidence only, not runtime hooking or merge.

**Current truth:**
`OFFLINE_DRY_RUN=PASS / PUBLIC_MANIFEST=READY / NETWORK_SUBMISSION=NOT_ATTEMPTED / REAL_SIGSUM_PROOF=NOT_OBTAINED / REAL_ARIO_LOG_WITNESSED=NOT_ESTABLISHED / INDEPENDENT_OPERATORS_ATTESTED=NOT_ESTABLISHED / ALL_PRODUCTION_OR_TRUST_ACTIONS=NO_GO / NO_AUTOMATIONS`.

**This is a concrete feasible route rather than more same-admin toy witnesses. It is not yet the external cryptographic result.**
