# W33 — Five contiguous Bitcoin headers and non-authorizing Core gate

**Date:** 2026-11-19  
**Repository:** SepehrGhanbari/Ario / research/consensus  
**State:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.

## خلاصهٔ فارسی

رفیق، W33 گام بعدی W32 بود. در W32 دو رسید OpenTimestamps مربوط به یک فایل مصنوعی و عمومی را با بلاک‌های بیت‌کوین 976596 و 976598 تطبیق دادیم. در W33، پنج سربرگ متوالی 976596 تا 976600 را بررسی کردیم.

دو سربرگ قبلی از **Git blob ثابتِ مدارک W32** خوانده شدند تا با تعویض فایل working tree تغییر نکنند. سربرگ‌های 976597 و 976599 و 976600 فقط با GET از دو API عمومی Blockstream و mempool.space دریافت شدند. پاسخ‌های هر دو API برای هر سه سربرگ، بایت‌به‌بایت برابر بودند. کد هش دوگانه SHA256، وضعیت Proof-of-Work از nBits، اتصال parent-hash، و ثابت‌ماندن nBits در همین پنج بلاک خارج از مرز تنظیم سختی را بررسی کرد.

**نتیجه:** هر پنج بلاک از نظر همین آزمایش به هم متصل‌اند. اما فقط پنج سربرگ تأیید شده‌اند؛ کل زنجیرهٔ بیت‌کوین، قوانین دشواری در تمام تاریخ، وضعیت بهترین زنجیره و اعتبارسنجی مستقل توسط Bitcoin Core **انجام نشده است**. دو API عمومی هم شاهد مستقل مدیریتی C2SP نیستند. هیچ کلید یا دادهٔ واقعی آریو استفاده نشد و هیچ مجوز اعتماد یا تولید صادر نشد.

## شواهد واقعی CI

- [W33 final successful run 44571643663](https://github.com/SepehrGhanbari/Ario/actions/runs/44571643663), code commit 8c8122132bdb1504d2506a49731e8ecce58d796d.
- Linux job 135727996398: **28/28 PASS** (log inspected).
- Windows 2022 job 135727996446: **28/28 PASS** (log inspected).
- One-shot GET job 135727995771: **five connected raw block headers / two public APIs / zero POST requests**.
- [Earlier W33 run 44571141267](https://github.com/SepehrGhanbari/Ario/actions/runs/44571141267): 26/26 initial tests per OS plus positive live linkage, before security hardening.
- [Retained RED run 44571526116](https://github.com/SepehrGhanbari/Ario/actions/runs/44571526116): 2 failures in error-message diagnostics after limiting override fields. The error-report allowlist was minimally repaired to permit the block-height diagnostic but not authority labels. RED not reclassified as PASS.

### Pinned Git evidence and code

- W33 source: research/consensus/w33_five_header_chain_and_core_gate.py — Git blob ed149aed45e552077a6e0ed5cf24c3f6e6642a37
- 28 tests: research/consensus/test_w33_five_header_chain_and_core_gate.py — Git blob b1190c5fef44ff8025e2fbac925adfabdf29958a
- Final raw evidence: research/consensus/W33_FIVE_HEADER_FINAL_PINNED_RETEST_EVIDENCE_2026-11-19.json — Git blob 9c85e958b9d0242ce7edb8548f76694da4099d2c
- Earlier raw live evidence: research/consensus/W33_FIVE_HEADER_TWO_EXPLORER_READBACK_EVIDENCE_2026-11-19.json; preserved as original evidence for reproducibility.
- Immutable W32 base evidence: Git blob dab717f48a9483a7909f70f86b174cadce0ca171
- The W33 raw evidence includes the six read-only raw 80-byte replies, both provider labels, recomputed local hashes, parent pointers, target bits, source commit and job IDs.

## Actual contiguous block hashes

| Height | Locally derived SHA256d block hash |
| ---: | --- |
| 976596 | 00000000000000000000a6c168915b99fd83334afdc40023901275ac3064ab2d |
| 976597 | 00000000000000000000c8f4825684592b14f460d33508cddad2a6d6f0a2534b |
| 976598 | 00000000000000000000cc5208897fe9ecf9e7ef72cf8b20140599a3d8e0c5b1 |
| 976599 | 000000000000000000015c517743911a76b2df8b354bf877b6c249c623695713 |
| 976600 | 00000000000000000001fbea30dad96a9449de2ac465309922f20cfe2b09eb86 |

The previous-block-hash for each successor matches the prior header's double-SHA256 block hash. All five individual headers pass bounded nBits/PoW checking, and their nBits agree. This is NOT proof of full Bitcoin consensus from Genesis.

## Negative controls and Core gate

The 28 source tests cover exact Git-blob pins, correct PoW for original W32 anchors, corrupt nonce, malformed size/hex, invalid compact target, unauthorized HTTP host or redirected URL, duplicate/missing provider, conflicting provider bytes, forged metadata, correctly hashed but unlinked blocks, offline zero-network operation and fake Bitcoin Core RPC claims.

The Bitcoin Core gate deliberately rejects an unsupported RPC response and **never** grants Bitcoin full-node verification merely because a JSON object claims mainnet, synchronization, matching block hashes, or a node status. No genuine Bitcoin Core mainnet node connected to this experiment. Even a genuine node verifying Bitcoin's own chain would not establish the separate-administrator C2SP witness sought for Ario.

## References and next acceptance condition

- [Official OpenTimestamps client](https://github.com/opentimestamps/opentimestamps-client): full independent Bitcoin timestamp verification with a synchronized Bitcoin Core node, including a pruned node.
- [Bitcoin Core validation](https://bitcoin.org/en/bitcoin-core/features/validation): Core validates consensus rules on its own database.
- [Bitcoin Core blockchain RPC](https://bitcoincore.org/en/doc/28.0.0/rpc/blockchain/verifychain/) and [getblockchaininfo](https://bitcoincore.org/en/doc/28.0.0/rpc/blockchain/getblockchaininfo/).

For a real FULL_NODE_VERIFIED claim, first obtain a genuinely independently validated mainnet Bitcoin Core chain and run the official OpenTimestamps verification of both original W31 detached receipts on that node, preserving the node provenance, chain status and readback outputs. Running a regtest node, trusting an unauthenticated remote RPC, or viewing two block explorers **does not** meet this condition.

**W33_FIVE_HEADER_LINK=BOUNDED_PASS / W33_TWO_PUBLIC_APIS=OBSERVED / BITCOIN_CORE_FULL_CONSENSUS=NOT_ESTABLISHED / INDEPENDENT_C2SP_CUSTODY=NOT_ESTABLISHED / SOURCE_REVIEW=OPEN / NO_MERGE / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.**
