# R63 G5 — Pinned public historical minimum, deterministic rollback, and offline separate-device handoff

**Date:** 2026-11-22  
**Status:** `RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`

## Problem and honest authority boundary

G4's founder-operated Windows Sandbox proved the synthetic Named Pipe can gate requests by a caller's actual Windows token SID, but it did **not** provide an independently administered latest `(seq,head)` authority.

G5 now tests the narrower, immediately falsifiable statement:

> A full, cryptographically self-consistent *local* rollback from the previously observed synthetic seq=3 state to seq=2 **must fail** under a verifier that has independently retained the prior `(epoch,seq,head)` minimum.

The phrase **independently retained** is a *physical/operator precondition* of a two-device gate, not something a single-machine Python flag, GitHub runner, or same-admin Docker process can prove.

## Exact research-only fixed minimum

- `epoch=research_nov_2026_no_signer`, `seq=3`;
- `head=6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1`;
- Original public synthetic checkpoint file SHA-256 `e218d3d05a613024eb26a8e67052aeb61d77d14d6be8ecdede2ed5c27c1a78db` (377 bytes);
- The historical public Sigstore Rekor record is global index `4033996846` from [actual one-shot Cosign Actions #44943687610](https://github.com/SepehrGhanbari/Ario/actions/runs/44943687610). Previously official Cosign verified the bundle against expected workflow identity/issuer; this particular minimum-floor test does **not** rerun Fulcio root-chain validation or prove latest log status.
- Pinned frozen V9-format V2 sidecar SHA-256 `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`.

The data are deterministic `a/1, b/2, c/3` synthetic reservations; **the historical Rekor record must not be represented as attesting the later founder's G4 execution**.

## Executed results

Original founder-uploaded G4 evidence (already audited in [G4 raw-byte review](../r63_g4_peer_ci/R63_G4_FOUNDER_SANDBOX_RAW_BYTE_AUDIT_2026-11-22.md)) was privately read to create full seq=3 and truncated seq=2 V1/V2 journal artifacts **without modification of the original upload**.

**Both local journals at seq=2 are internally valid.** SHA-256, from actual V1/V2 bytes:
- seq2 V1 = `da328144c9de3f5163cc0f7c79240930e997c8f03b10729320ca318c466f66fa`; V2 = `e258b0076b2b260c70ba8dfa7f787d3f41e50aef398c40bcbdc5ce14a8205813`; old head `cce8dfa45814ef13524b65f02d314a0841123fe310bdc3b745964d044d2b636a`.
- seq3 V1 = `2e1918b2c890dcf337b314692d7201a8cbdc223046322ea45953615de3144ec8`; V2 = `9c221fa381fed4cfecc71d89e285bdb8ecc0995bfb49f8572a3177bbd4c66ac0`; head as above.

The **original, pinned V9 `spend_chain_v2.review`** independently accepts both seq2 and seq3 as valid *local* chains with `LOCAL_SELF_ADMINISTERED_NO_ROLLBACK_PROOF`. Our new standard-library `g5_retained_floor.py` independently validates canonical V1 append order, each V2 domain-separated hash, seq/prev, nonce and ID uniqueness, R60 sorted content commitments, and the pinned public checkpoint digest.

Actual executed verdicts:
- locally coherent `seq=2` against trusted pinned historical minimum `seq=3` => **`HOLD_ROLLBACK`**, process exit 2;
- a locally coherent `seq=3` fork with a different head => **`HOLD_FORK`**;
- full matching seq=3 => `CONSISTENT_WITH_EXTERNAL_HISTORICAL_MINIMUM_ONLY_NOT_LATEST`;
- verifier has not physically verified external pin retention => **`HOLD_INDEPENDENT_PIN_NOT_ESTABLISHED`**, even with correct data;
- invalid/truncated chains, mismatched V1/V2 or corrupted checkpoint => `HOLD`.

**Two independent implementations and CI:**
- Python standard library `unittest` **16/16 PASS**;
- JavaScript `crypto.subtle` verification logic, under Node VM **8/8 PASS**. This tests V1/V2 bytes and SHA-256 on the same deterministic fixture without trusting a publisher-supplied seq/head field.
- [GitHub Actions #45017321849](https://github.com/SepehrGhanbari/Ario/actions/runs/45017321849), both Windows 2022 and Ubuntu 24.04 jobs **SUCCESS**, including explicit expected negative exits `HOLD_ROLLBACK` and `HOLD_INDEPENDENT_PIN_NOT_ESTABLISHED`. Initial RED [#45017226603](https://github.com/SepehrGhanbari/Ario/actions/runs/45017226603) preserved: Win checkout CRLF broke exact byte checkpoint hash, Linux pwsh propagated deliberate exit-2 despite correct assertions. Fixed only exact-checkpoint LF attribute and explicit successful shell end; acceptance predicates unchanged.
- Full Chromium mobile UI automation **NOT VERIFIED (runner timeout)**; JavaScript cryptographic logic in Node VM did pass. Phone runtime is therefore a separate field acceptance gate.

## Chat-only off-device test package — do not put founder files on public GitHub

`Ario-R63-G5-Offline-Independent-MinFloor-Research.zip`: **25,385 bytes; SHA256 `bc3becbaec764ea7496537abbd5644c56a1c1b23a9c7b52d50652fec3480bf75`**. 17 members including `SHA256SUMS.txt`; 16/16 internal hashes verified, no executable installer, no signer key, no real service or OS policy change.

It contains a standalone offline HTML verifier with an immutable test-only seq=3 pin, three synthetic candidate JSON files (known valid seq3, coherent rollback seq2, same-seq fork), the public synthetic checkpoint and Sigstore bundle, a manual-export minimum-floor JSON, Python/JS sources and tests, and a Persian README.

**Proposed founder off-device acceptance (NOT YET EXECUTED):**
1. Transfer/extract the exact package onto the **phone**, with no desktop write/control/sync/admin path; **do not use signer laptop**.
2. Open the standalone HTML using the phone's local browser, preferably offline. Select the three candidate files *in order*: normal seq3 => consistent with historical minimum; seq2 => `HOLD_ROLLBACK`; seq3 fork => `HOLD_FORK`.
3. Export `G5-PHONE-PINNED-MINIMUM-SEQ3.json` and retain it on the phone without sharing write access back to desktop.
4. Collect on-device images / readback, inspect whether the desktop has file/sync/account recovery rights, and demonstrate after restarting the phone that the pin still survives. This is **manual antirollback vs publisher domain**, not an unattended authoritative latest floor.
5. If phone WebCrypto unavailable, local code differs, or the phone and desktop share write/admin/sync credentials: return HOLD, do **not** disable security policy.

**Key distinction:** An externally administered historical Rekor inclusion is a real historic witness, but **not** a current authoritative latest-state service. A phone held under founder control can offer a **separately retained minimum** against a desktop publisher only if its storage and write credentials truly are not accessible to desktop; it is not independent from the founder. This test never proves a remote service's completeness, latest-pointer freshness, network availability, signer authority or complete key use.

## Final

`G5_LOCAL_SEQ2_ROLLBACK=HOLD_ROLLBACK_VERIFIED`  
`G5_SOURCE_TESTS=PYTHON16_JS8_PASS_DUAL_OS`  
`G5_PUBLIC_SYNTHETIC_HISTORICAL_REKOR=PREVIOUSLY_VERIFIED`  
`G5_REAL_SEPARATE_DEVICE_PIN=NOT_EXECUTED`  
`G5_LIVE_INDEPENDENT_ADMIN_CUSTODY=NOT_ESTABLISHED`  
`G5_AUTHORITATIVE_LATEST=NOT_ESTABLISHED`  
`NO_REAL_KEYS / NO_MERGE / PRODUCTION=NO_GO`.
