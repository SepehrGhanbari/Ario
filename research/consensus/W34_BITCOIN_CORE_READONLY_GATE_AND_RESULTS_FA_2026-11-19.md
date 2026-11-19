# W34 — Bitcoin Core local validation readiness / source-aware HOLD

**Date:** 2026-11-19  
**Repository:** SepehrGhanbari/Ario — research/consensus  
**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO

## خلاصهٔ فارسی (برای کسی که سورس را نمی‌خواند)

رفیق، W31–W33 نشان دادند دو رسید آزمایشی OpenTimestamps واقعاً به سربرگ بلاک‌های بیت‌کوین متصل شده‌اند و پنج سربرگ متوالی را دو سرویس عمومی یکسان برگردانده‌اند. W34 قرار بود این نتیجه را به بررسی با **Bitcoin Core واقعی و همگام‌سازی‌شده** ارتقا بدهد.

پیش‌نیاز واقعی هنوز موجود نیست: در محیط کاری این آزمایش ابزار bitcoin-cli نصب نیست و هر دو دستگاه Desktop Commander ثبت‌شده آفلاین بودند. بنابراین **به هیچ گرهٔ معتبر و همگام‌شده وصل نشدیم، هیچ IBD انجام ندادیم و هیچ ادعای تأیید کامل Bitcoin Core نمی‌کنیم**.

به جای نمایش نتیجهٔ غیرواقعی، یک ممیز خواندنی ساختیم که دقیقاً دو رسید OTS اصلی W31/W32 را از Git blob پین‌شده می‌خواند، مسیرهای مرکل را بازحساب می‌کند و برای اجرای دستی آینده فقط از چند فرمان خواندنی Bitcoin Core روی 127.0.0.1 استفاده می‌کند. مهم‌تر: حتی یک پاسخ RPC ساختگی با تمام فیلدهای «درست» فقط «سازگاری ظاهری با دادهٔ فراخوان» را نشان می‌دهد، نه اثبات اصالتِ خودِ گره.

**نتیجهٔ واقعی:** ۴۰/۴۰ آزمون Linux و ۴۰/۴۰ آزمون Windows موفق. هر دو سیستم استخراج و بررسی آفـلاین همان رسیدهای W31 را نیز اجرا کردند. بررسی حقیقی Bitcoin Core **NOT_EXECUTED**.

## شواهد ماشینی واقعی و کد پین‌شده

- [GitHub Actions W34 (final post-hardening run 44575032229)](https://github.com/SepehrGhanbari/Ario/actions/runs/44575032229)
- Ubuntu Python 3.13 job 135740103644: **40/40 PASS** و اجرای offline W31/W32 receipts، raw log خوانده شد
- Windows 2022 Python 3.13 job 135740104392: **40/40 PASS** و اجرای offline W31/W32 receipts، raw log خوانده شد
- Environment inventory job 135740104265: **BITCOIN_CLI_BINARY_ABSENT** — no real node interaction
- Original first all-green 40/40 run: [44574588852](https://github.com/SepehrGhanbari/Ario/actions/runs/44574588852); final source hardened to make failed CLI execution exit with nonzero status
- Final retest-triggering code commit: **0de234f433644e2f414230a4c369e23d05d30a87**
- Research source research/consensus/w34_local_bitcoin_core_receipt_gate.py — **Git blob 91ce4a4caf00ffba45ed6a35e0bbaa19426e4a97**
- 40 test cases research/consensus/test_w34_local_bitcoin_core_receipt_gate.py — **Git blob 68adb94563f79ec9fd5e4fe43ec004e23e008a71**
- Exact original W32 OTS evidence Git blob **5d0a7edc1eb8c80cfc52a6d9f0ed9bc1c5fb9b1c**; original public W31 SHA256 **2078bc80586d0e4b00afa48eb8dea31ab3d4749b4912c57a897e4d5e2fb436df**
- Pinned block heights 976596 (Alice) and 976598 (Bob), exact public Bitcoin blockhashes retained from W32

## Negative controls and legitimate acceptance boundary

Tests use a synthetic RPC adapter for correct-looking getblockchaininfo, getblockhash and getblockheader replies. They verify failure-closed behavior for wrong network, initial block download still running, not enough confirmations, missing genesis, altered block hashes, corrupted PoW or Bitcoin Merkle roots, swapped or malformed .ots, incorrect synced-chain progress, missing local CLI, unsupported RPC commands, fake confirmations, output label overrides and repeated/replayed readback.

Even the perfect fake RPC case **never sets FULL_NODE_VERIFIED**; operational status always HOLD, authority NONE, Genesis/Trust/Production NO_GO. Successful crypto parsing is not independent operator custody.

The local CLI path, when a genuinely available node exists, issues ONLY these read calls: getblockchaininfo, getblockhash 0 / 976596 / 976598 / current height, and getblockheader for the two pinned hashes with raw hex. No wallet methods, transaction submission, key handling, network POST or persistent configuration change. The script does not install bitcoind, initiate IBD, copy cookie credentials or log secrets. It enforces 127.0.0.1:8332 and the default local cookie-authentication mechanism of bitcoin-cli.

### Exact future manual acceptance (ONLY if a node is already available)

1. Use a **separate research/testing computer**, not the Ario founder/independent key host. Confirm Bitcoin Core is genuinely installed, using Bitcoin mainnet, already synchronized and locally operator-controlled. A *pruned* node suffices to validate the chain while retaining historical headers; initial sync still downloads and validates historical blocks.
2. Create a separate isolated clone of this research branch, not a forced checkout of an active Ario working tree.
3. From that isolated clone, Python 3.13: install the explicitly pinned research parser package opentimestamps==0.5.0; run the offline check first:

       python -B research/consensus/w34_local_bitcoin_core_receipt_gate.py --offline

4. Only with the node running and synced, run the read-only comparison:

       python -B research/consensus/w34_local_bitcoin_core_receipt_gate.py --local-rpc

5. For an independently reproducible official OpenTimestamps check, use the ORIGINAL 765-byte public W31 synthetic file, the TWO already-upgraded .ots proof files retained in W32 and the official OpenTimestamps client against the authenticated local Bitcoin Core node. Verify both independently and retain full logs, node version, chain ID, best chain status, block hashes, and enough provenance about the node's prior IBD. Do not include an RPC cookie, username, password or private datadir in any GitHub artifact. Do not use a third-party remote JSON-RPC and call it local.
6. Do not turn green local RPC output into an Ario authorization. Even if Bitcoin timestamp verification succeeds on a real validated node, the independent C2SP witness/keeper requirement remains unmet.

**Cost / device warning:** A fresh Bitcoin Core node must initially download and validate substantial Bitcoin history, even when pruned. Do not use expensive cloud services, start large downloads, install system software or pay for resources silently. Obtain founder permission and verify device capacity first.

## Why not automatically run Bitcoin Core in GitHub Actions?

GitHub-hosted ephemeral runners do not ship with a prevalidated and synced mainnet Bitcoin Core database. Installing an executable is not the same as completing initial block download and consensus validation. The W34 one-shot CI intentionally used **NO** node, **NO** wallet and **NO** blockchain download. Using public block explorers from W32/W33 is not a substitute for this missing condition.

## Open for source review

- Source crypto inputs are Git blob pinned, not working-tree text subject to Windows CRLF conversion.
- The returned statuses, including those from spoofed RPC data, are irrevocably HOLD/NO_GO and cannot grant memory, signer or trust authority.
- Future actual-node results must be recorded with explicit provenance and should be independently reproduced with the official OpenTimestamps client.
- Independent code review is not established by 40 researcher-authored tests, nor by using two operating systems.

**FINAL:** W34_OFFLINE_SOURCE_TESTS=40/40_PER_OS_PASS; OFFLINE_PUBLIC_W31_OTS=PASS; REAL_BITCOIN_CORE_MAINNET_NODE=NOT_AVAILABLE; ACTUAL_FULL_NODE_OTS_VERIFICATION=NOT_EXECUTED; INDEPENDENT_C2SP_WITNESS=NOT_ESTABLISHED; SOURCE_REVIEW=OPEN; PRODUCTION/TRUST/GENESIS=NO_GO.
