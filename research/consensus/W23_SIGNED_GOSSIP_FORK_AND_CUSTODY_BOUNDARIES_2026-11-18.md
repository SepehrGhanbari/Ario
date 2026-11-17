# W23 — Signed checkpoint gossip, fork evidence, and custody boundaries

**Date:** 2026-11-18
**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO

## خلاصهٔ فارسی

W23 با همان چک‌پوینت‌های امضاشدهٔ ساختگی W22، یک ممیز آفلاین تازه ساخت. این ممیز بدون شبکه، بدون امضا و بدون تغییر فایل، نمای دو یا چند ناظر را مقایسه می‌کند. دو چک‌پوینت معتبر با اندازهٔ یکسان ۸ و ریشهٔ متفاوت که با کلید آزمایشی مشترک امضا شده‌اند، به‌عنوان SIGNED_EQUIVOCATION_PROVEN تشخیص داده می‌شوند.

اما اگر ناشر و هر دو ناظر فقط نسخهٔ معتبر قدیمی با اندازهٔ ۳ را نشان دهند، توافق آنها **هیچ تضمینی از تازگی** ندارد. برچسب ناظرهای A/B/C هویت واقعی نیست؛ هیچ استقلال اداری یا نگهداری بیرونی به‌دست نیامده است.

## Exact files and replay

- research/consensus/w23_checkpoint_gossip.py — no-I/O verifier, strict W22 signed-note subset and compact Merkle consistency check; Git blob 640421e74519d77ab1ac50a1f606a90a0a3498bf.
- research/consensus/test_w23_checkpoint_gossip.py — 16 author-designed positive and negative tests; Git blob c0d931ad1064310513e1c84d2b2346805c92df3b.
- W22 fixture Git blob 6aaf4b53e4f1e3e88556fcfbbbfddaef3445da8e; W20 published compact proof Git blob 13779afb7d953846424047bb16f0018b677131c8.
- Readback of both new GitHub source blobs exactly matched locally executed Git hashes.
- Local Python 3.13.5 and cryptography 46.0.4: 16/16 unittest PASS.
- GitHub Actions run https://github.com/SepehrGhanbari/Ario/actions/runs/44174186535 : Windows 2022 / Python 3.13.17 (job 134360997277) 16/16 PASS; Ubuntu / Python 3.13.18 (job 134360997635) 16/16 PASS. Both job logs inspected; these are **the same 16 tests replayed on separate machines**, not 32 independent threat cases.
- Temporary no-secret, no-schedule research workflow: .github/workflows/w23-gossip-research.yml. Retain the immutable run URL and remove the temporary workflow after recording.

## Exact observed boundaries

| Research input | Finding |
| --- | --- |
| Two valid same-signer size-8 notes, unequal roots | SIGNED_EQUIVOCATION_PROVEN, returns both note SHA-256s |
| Previous size 3 to new size 8 with valid compact proof | CONSISTENT_GROWTH_NOT_FRESHNESS |
| No proof / altered proof across different sizes | HOLD; bad proof is **not itself** proof of equivocation |
| Retained size 8 but observed size 3 | DENY_ROLLBACK_RELATIVE_TO_RETAINED |
| Both peers still see size 3 | OBSERVED_AGREEMENT_NOT_WORLD_FRESHNESS |
| Three peers see size 3, size 8, and the same-signer size-8 fork | SIGNED_EQUIVOCATION_PROVEN on size-8 pair |
| No public key pin, malformed signed note or invalid view set | HOLD |
| All cases | operational_authority NONE, memory_admitted false, source/latest-world truth UNKNOWN, independent custody NOT_ESTABLISHED |

This same-signer same-size conflict is a **cryptographic contradiction within the synthetic test log**. It is NOT evidence that the real Ario log was forked, that an external witness observed the fork, or that the log key is controlled by an authenticated person.

## Original standards and why W24 is different

C2SP checkpoint syntax: https://c2sp.org/tlog-checkpoint@v1.0.0
C2SP witness protocol: https://c2sp.org/tlog-witness@v1.1.0
C2SP cosignature semantics: https://c2sp.org/tlog-cosignature@v1.1.0

The C2SP witness protocol expressly requires that the latest cosigned checkpoint be retained **atomically**, and that the state be persisted **before returning** a cosignature. W23 does not implement witness add-checkpoint, cosignatures, concurrency control, durable storage, authenticated witness keys, full tile API, public HTTPS endpoints, or real independent custody.

**W24 high-value negative experiment (synthetic only):** an independent-process mock witness using a SQLite transactional head, with simultaneous same-size forks and increasing-size submissions, injected failure before/after transaction commit and before response, an old-state restoration test, and no release of a cosignature if uncertain. Test the exact crash/race documented by C2SP; label every same-admin process as non-independent. Record RED mutations and standalone run receipts. Do not deploy or connect any Ario signer.

A true outside witness/monitor still requires separately administered custody and authenticated out-of-band pins. A cloud runner controlled by the same owner does not establish either. No live public test log was enrolled or submitted, no owner/private key used, no actual Ario event ingested, no main merge, no trust activation. Research is not blocked by absent human reviewers, but green CI must never be presented as a human endorsement.
