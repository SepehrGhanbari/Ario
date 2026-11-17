# R6-C — First Public TEST-Log Proof: Exact-History Evidence Record (2026-11-18)

**RESEARCH_ONLY / PUBLIC_TEST_LOG_PROOF_VERIFIED / AUTHORITY=NO_GO / ADMINISTRATIVE_INDEPENDENCE=NOT_ESTABLISHED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

## Artifact and reproducibility

| Item | Exact value |
| --- | --- |
| Research PR | [#273](https://github.com/SepehrGhanbari/Ario/pull/273) |
| Published-workflow HEAD | `14d0c902f777a5acedde10a0709f3551d3ea8ddb` |
| Workflow | `.github/workflows/r6-synthetic-sigsum-proof.yml` |
| Actual GitHub Actions run | [44175613003](https://github.com/SepehrGhanbari/Ario/actions/runs/44175613003) |
| Public-only artifact | [14368549819](https://github.com/SepehrGhanbari/Ario/actions/runs/44175613003/artifacts/14368549819) |
| Artifact ZIP SHA-256 | `ccefd806ea14d6a000b22a8b07b09c50e22097adf95ecba85fa0e8faefdb0d7e` |
| Artifact ZIP size | 4190 bytes |
| SHA-256 of public checkpoint bytes | `6c36e6a928199e0c2c5c452f2d719d13bdd4b8fdd6add9ddcd3d7be97702a44f` |
| SHA-256 of proof bytes | `65c43c4217b5e6c09880beeb9af7b924ea4c71d053e7ad65747f1e53660a9a33` |
| SHA-256 of public test key | `e824e100cf6035c1f9eeb90c37628d388a3fa66d911694f88258a8f9ebbcb01a` |
| SHA-256 of Sigsum built-in test policy text | `efd91055479db94ebc296e65cad1a9876b10b18a6852d1e24fcae9cd5fb5bb44` |
| Public test policy | `sigsum-test1-2025`, 2-of-3 external witness quorum |
| Reported test-log leaf index | 279032 |
| Reported test-log tree size | 279033 |

The artifact contains **only six files**, all public and nonsecret:
`synthetic-checkpoint.json`, `synthetic-anchor-key.pub`,
`synthetic-checkpoint.json.proof`, `policy.txt`, `input-sha256.txt`,
`public-manifest.sha256`. The **ephemeral private test key was NOT uploaded**.
The ZIP and all four file hashes were read back independently from the
workflow artifact and cross-checked against the included manifest.
(The public test proof's 15 `cosignature` records are **NOT** 15 independent
valid witness authorities; only the policy's 2-of-3 verification result is
authoritative for this test.)

## What actually ran

1. A fresh GitHub-hosted Ubuntu job installed the Sigsum client at
   `sigsum-go@v0.14.1` and generated **a disposable Ed25519 test-only key**.
2. Published a synthetic checkpoint JSON containing **only** the previously
   publicly reported journal digest:
   `da706a049e5fbacb3c94804f969686047907863d36cf29d77c10e10de52c948e`,
   `reported_sequence=3`, and reference to [prior R6-A CI 44173643104](https://github.com/SepehrGhanbari/Ario/actions/runs/44173643104).
   This is a **CLAIM copied from that CI output**, not a new independent
   extraction or authentication of the old custodian.
3. `sigsum-submit -P sigsum-test1-2025 -k <ephemeral test key> ...`
   submitted the synthetic digest to the **externally operated Sigsum TEST
   transparency log**. The log returned a plaintext inclusion proof.
4. `sigsum-verify -k <public test key> -P sigsum-test1-2025 <proof> <checkpoint`
   exited successfully. This checks the signature, inclusion proof and the
   policy's witness quorum **without network access at verification time**.
5. Altering the checkpoint by appending a newline made verification **fail**.
   The tamper-negative check was recorded as successful.
6. Uploaded the **public-only evidence bundle**, digest
   `ccefd806ea14d6a000b22a8b07b09c50e22097adf95ecba85fa0e8faefdb0d7e`.

Actual workflow log contains:
- `R6_EXTERNAL_TEST_LOG_SUBMISSION: PROOF_RECEIVED`
- `R6_SIGSUM_OFFLINE_VERIFICATION: PASS`
- `R6_SIGSUM_TAMPER_NEGATIVE: PASS`
- `R6_ADMIN_INDEPENDENCE: NOT_ESTABLISHED`
- `R6_EXECUTION_REALITY: NOT_ESTABLISHED`
- `R6_PRODUCTION_TRUST_ACTIVATION: NO_GO`

## Strong but bounded result

**VERIFIED:** a specifically identified *synthetic public checkpoint's bytes*
were submitted to Sigsum's external test log; a proof satisfying its declared
2-of-3 witness test policy was obtained and cryptographically verified with
the official client. Edited bytes failed verification.

**UNKNOWN / NOT_ESTABLISHED:** independence of the test signer E from the
same person administering C; independent custody of C's original nonce
journal; reliable fresh checkpoint generation from C; real tool execution,
execution admission and semantic truth; durability/availability of Sigsum's
*test* service; independent monitoring for fork/equivocation; current
revocation/freshness; permission of any Ario signer, memory or trust.

**Crucial distinction:** independent outsiders can witness **publication of a
signed digest**, but publication of a **caller-controlled digest** does not
authenticate its factual content or its claimed producer. There was **no
integration** with `SourceMonitoringGuard`, `ConsolidationEngine`,
`ProspectiveMemoryRegistry`, real signer, Ruleset or trust activation.

## Long-term record and next step

The GitHub Actions artifact is retained for **30 days**, reported to expire
**2026-12-17**. Its content digest and these proof/policy hashes are
**recorded in Git**, but a digest alone cannot reconstruct a proof after the
artifact expires. Preserve the ZIP separately if a long-lived independent
audit is required. No auto-upload to a production store was attempted.

**Next physical two-host experiment, not yet executed:** replay synthetic E/C
with desktop E and laptop C, separate low-privilege OS accounts and tested
ACLs. Pin and retain the independently witnessed checkpoint on an external
observer and compare with the next verified checkpoint. If the same
administrator can change both E/C policies, call the result OS-level
separation, never administrative independence. In all circumstances,
`evidence_admission_allowed=false` and production remains NO_GO.

## خلاصهٔ فارسی

هشِ **ساختگی و عمومی** را واقعاً به یک دفتر خارجی فرستادیم؛ رسید گرفتیم،
امضای شاهدان و مسیر ثبت را با ابزار رسمی به‌صورت آفلاین بررسی کردیم، و
تغییر یک بایتِ ورودی باعث رد رسید شد. این اولین شاهد بیرونی واقعی برای
**انتشار هش** است، نه اثبات اجرای واقعی ابزار یا استقلال مدیریت کلید آریو.
کلید اصلی و حافظه و قواعد اعتماد هیچ تغییری نکرده‌اند.

**DRAFT / HOLD / NOT_ADOPTED / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**
