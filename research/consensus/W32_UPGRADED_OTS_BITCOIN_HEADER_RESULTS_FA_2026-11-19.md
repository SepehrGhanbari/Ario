# W32 — Existing W31 OpenTimestamps receipts: read-only upgrade and Bitcoin header corroboration

**Date:** 2026-11-19  
**Project:** SepehrGhanbari/Ario, research/consensus  
**Disposition:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO

## خلاصهٔ فارسی

رفیق، W31 فقط دو رسید Pending داشت. در W32 همان دو رسیدِ ثبت‌شده را بازیابی کردیم: به Alice و Bob فقط درخواست **خواندن GET** فرستاده شد. هیچ هش جدیدی به تقویم‌ها ارسال نشد، هیچ کلید واقعی، حافظهٔ واقعی یا سرویس امضای آریو درگیر نشد. هر دو تقویم مسیر تکمیل‌شده و ادعای یک بلاک Bitcoin را برگرداندند.

بعد، دو سامانهٔ عمومی Blockstream و mempool.space را جداگانه برای سربرگ خام همان دو بلاک استعلام کردیم. برای هر بلاک، هر دو API بایت‌های سربرگ **یکسان** ارائه دادند؛ SHA256d سربرگ دقیقاً به هش بلاک اعلامی رسید، هش با هدف Proof-of-Work موجود در فیلد nBits منطبق بود و **ریشهٔ مرکل در خود سربرگ** با ریشه‌ای که زنجیرهٔ عملیاتِ اثبات OTS از هش فایل مصنوعی W31 تولید می‌کند، دقیقاً یکی بود. این یک تطبیق رمزنگاری‌شدهٔ واقعی و بیرون از تقویم است.

با این حال، **اجرای گره مستقل Bitcoin Core، تأیید کل زنجیرهٔ سربرگ‌ها، همهٔ قواعد سختی/اجماع و استقلال اداری دو ارائه‌دهندهٔ API انجام نشده است**. پس عبارت درست برای نتیجه: PUBLIC_TWO_API_HEADER_CORROBORATION_WITH_POW / BOUNDED_PASS است، نه FULL_INDEPENDENT_BITCOIN_NODE_VERIFICATION و نه C2SP_INDEPENDENT_WITNESS_ESTABLISHED.

آزمایش ۱۹ کنترل آفلاین ارتقای رسید و ۲۲ کنترل آفلاین سربرگ روی هر یک از Windows و Linux موفق شد. شکست‌های اولیه و مسیر اصلاح نیز حفظ شدند؛ موفقیت نهایی به آنها تعمیم داده نمی‌شود.

## 1. Actual result by original public W31 synthetic file

Original exact Git blob: 138c8b056dd3387f31f5a0facedf43b0f221b742  
Original 765-byte synthetic file SHA256: 2078bc80586d0e4b00afa48eb8dea31ab3d4749b4912c57a897e4d5e2fb436df

| Original calendar | Attested Bitcoin height | Header UTC time | Public block hash | Exact updated detached .ots SHA256 |
| --- | ---: | --- | --- | --- |
| Alice | 976596 | 2026-11-19 15:12:56 UTC | 00000000000000000000a6c168915b99fd83334afdc40023901275ac3064ab2d | 5968fd87749621f96c42d1763bd41a8d457187cd55380d2e1ca7132a4518ac35 |
| Bob | 976598 | 2026-11-19 15:27:47 UTC | 00000000000000000000cc5208897fe9ecf9e7ef72cf8b20140599a3d8e0c5b1 | 886a46e7ffe9bc7dcb4d8a118bf98cc1805fa5df7f6002aa1fb15573648dc70a |

**Saved complete machine evidence:**
- [Two upgraded OTS .ots files as complete Base64, exact SHA256, and original HTTPS calendar reply bytes](W32_TWO_READONLY_UPGRADED_OTS_RECEIPTS_2026-11-19.json), Git blob 5d0a7edc1eb8c80cfc52a6d9f0ed9bc1c5fb9b1c.
- [Both actual raw 80-byte block headers from Blockstream and mempool.space, local SHA256d and PoW checks, OTS proof-merkle binding](W32_TWO_EXPLORER_HEADER_CORROBORATION_2026-11-19.json), Git blob dab717f48a9483a7909f70f86b174cadce0ca171.
- The original W31 pending receipts remain preserved unchanged.

## 2. Execution evidence: original red, corrected green

- First [W32 run 44566957794](https://github.com/SepehrGhanbari/Ario/actions/runs/44566957794) FAILED. Mistaken assumption that a PendingAttestation always binds a 32-byte final commitment. Actual W31 pending commitments are 44-byte outputs of OTS ops.
- Second [W32 run 44567402194](https://github.com/SepehrGhanbari/Ario/actions/runs/44567402194) FAILED two synthetic tests. The original file hash and a calendar commitment are distinct OTS tree nodes; initially an upgraded proof was merged at the wrong (root) location.
- Third [W32 run 44567694333](https://github.com/SepehrGhanbari/Ario/actions/runs/44567694333) FAILED one negative test, which incorrectly assumed a bare PendingAttestation to a URL cryptographically authenticates the commitment. The pending-only attestation can be recontextualized; the fixed test expects no Bitcoin confirmation from this untrusted structure.
- Final successful [W32 existing-proof readback run 44567936141](https://github.com/SepehrGhanbari/Ario/actions/runs/44567936141), source commit c7c540565aa51a083336d01211cf09b0190938c6:
  - Ubuntu job 135714714826: 19/19 PASS.
  - Windows 2022 job 135714713936: 19/19 PASS.
  - External GET-only job 135714714796: HTTP 200 for two earlier commitments, two upgraded .ots proofs, zero calendar POSTs.
- Final successful [W32 two-explorer header run 44568749735](https://github.com/SepehrGhanbari/Ario/actions/runs/44568749735):
  - Ubuntu job 135717659513: 22/22 PASS.
  - Windows 2022 job 135717659580: 22/22 PASS.
  - Read-only header job 135717658670: 2 Bitcoin heights × 2 public APIs; matching raw headers, derived block hashes, nBits PoW, and OTS Merkle roots for BOTH blocks.
- Raw successful logs reviewed, not merely workflow status. One-shot GET workflows removed after evidence capture. No scheduled run, new timestamp creation, external enrollment or production trigger.

## 3. Exact code files pinned for source review

- research/consensus/w32_read_only_ots_upgrade.py — Git blob bf7d2ba02a3e072e5934402000d2dd7faf8fe1d3
- research/consensus/test_w32_read_only_ots_upgrade.py — Git blob 683193a3e5ecf13827e6a064f336d378df21397d
- research/consensus/w32_public_bitcoin_header_corrob.py — Git blob 4d3ec3c41431b54b3dfd5167ef47ac43a3bd90a1
- research/consensus/test_w32_public_bitcoin_header_corrob.py — Git blob 91545990d59de64a1fd9a148ef7fb4a67cf6025b

Expected source review: OpenTimestamps operation path to pending-leaf matching, no redirects/POSTs, no unbounded calendar bytes, canonical original Git preimage, exact correspondence of 2 upgraded files to original digest, separate 80-byte header parsing and PoW checks, and safe treatment of fake self-asserted PendingAttestations.

## 4. What is and is NOT established

- OBSERVED: original published W31 *synthetic/public* file digest is correctly bound to both complete detached OTS proofs and externally corroborated Bitcoin block-header merkle roots.
- OBSERVED: independent local calculation verifies SHA256d blockhash and block header proof-of-work target for both reported heights.
- NOT_ESTABLISHED: full Bitcoin Core independently validated header chain, current canonical tip, all difficulty retarget rules, reorg resistance, or trustless network consensus.
- NOT_ESTABLISHED: administrative independence of the two public Bitcoin explorers, the two calendars, or any external C2SP witness.
- NOT_ESTABLISHED: that the timestamped W31 synthetic file contains actual Ario events, real memory, or operational safety. It was explicitly synthetic; this timestamping alone cannot witness any real Ario operation.
- CRITICAL: a valid Bitcoin block-header attestation does NOT mean an Ario C2SP witness cosignature, independent retained high-water keeper, policy approval, or trusted truth.
- NO_GO: real keys, signers, memory admission, Genesis, trust activation, production deployment, merging research as a security feature.

## 5. Exact protocol and privacy scope

Original [OpenTimestamps Python client](https://github.com/opentimestamps/opentimestamps-client) describes upgrading existing .ots receipts via calendars and full independent verification through a Bitcoin Core node. [Python OpenTimestamps](https://github.com/opentimestamps/python-opentimestamps) defines PendingAttestation and BitcoinBlockHeaderAttestation as different levels of evidence.

Only the W31 pre-existing commitment identifiers were sent via GET /timestamp/<commitment> to Alice and Bob. Only public block heights/hashes were queried through GET endpoints of blockstream.info and mempool.space. The raw W31 file and its SHA256 were already publicly published before W32. No private payload, key, owner secret, actual Ario memory record or new POST was transmitted during W32.

## 6. Next optional external improvement (strictly gated)

To upgrade a two-public-explorer corroboration into fully independent Bitcoin consensus verification, independently validate the retrieved OTS timestamp against Bitcoin Core synchronized to real mainnet (or against independently retained, validated full header-chain material). Do not describe an external API as a full independently operated node under Ario's control.

Even after full Bitcoin confirmation, the original W24–W30 goal of an external C2SP witness with separate administrative custody remains open. Timestamping a synthetic document is a useful existence proof, not a solution for signer custody, revocation management or witness independence.

**FINAL: W32_TWO_UPGRADED_OTS=CAPTURED; W32_TWO_PUBLIC_API_HEADER_MATCH=BOUNDED_PASS; FULL_NODE_CHAIN_CONSENSUS=NOT_ESTABLISHED; C2SP_INDEPENDENT_WITNESS=NOT_ESTABLISHED; SOURCE_REVIEW=OPEN; TRUST/GENESIS/PRODUCTION=NO_GO.**
