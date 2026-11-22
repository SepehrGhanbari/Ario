# R63 G5 — Founder-reported iPhone Notes minimum: offline manual rollback falsification

**Date:** 2026-11-22  
**Scope:** `RESEARCH_ONLY / SYNTHETIC_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`

## 1. Exactly what was reported

Founder stated in this conversation:
- the synthetic minimum `(epoch=research_nov_2026_no_signer,seq=3,head=6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1)` was copied into the iPhone Notes app;
- iPhone access is separate from the desktop publisher.

**We did not access, photograph, inspect, execute code on or attest the iPhone.** The founder did **not yet return** an observation of *these specific* three challenge candidates as read against the phone's Note. User-report of separate phone access is **a manual precondition assertion**, not a cryptographic/admin separation proof. Do not upgrade `PHONE_MIN_FLOOR_INDEPENDENTLY_ATTESTED` to PASS.

## 2. Source and original-journal provenance

The actual private founder Windows Sandbox test ZIP was parsed **read-only** without executing its contents:

- Original G4 archive `R63-G4-Evidence-4796-e5cd1c02.zip` SHA256 `43055b3e4c89074d39c369ee464833f7367c99b425f82a78b3cf96f41fe4c2f2`. Stored privately; raw original not published.
- Raw V1 `408` bytes, SHA256 `2e1918b2c890dcf337b314692d7201a8cbdc223046322ea45953615de3144ec8`.
- Raw V2 `1,485` bytes, SHA256 `9c221fa381fed4cfecc71d89e285bdb8ecc0995bfb49f8572a3177bbd4c66ac0`.
- Exact V1/V2 bytes equal the previously generated public **synthetic** `seq=3` G5 fixtures, not merely a matching head. Do not infer a live Ario production event from this deterministic equality.
- Fixed historical checkpoint artifact SHA256 `e218d3d05a613024eb26a8e67052aeb61d77d14d6be8ecdede2ed5c27c1a78db`, already historically published as a synthetic-only Sigstore Rekor entry, index `4033996846`. **Rekor is historical inclusion, not authoritative newest state.**

For a rollback, the verifier was given **the literal first two records of the raw G4 V1 and V2 journal**. Both older journals remain individually well formed and jointly canonical:

- `seq=2`, head `cce8dfa45814ef13524b65f02d314a0841123fe310bdc3b745964d044d2b636a`;
- V1 SHA256 `da328144c9de3f5163cc0f7c79240930e997c8f03b10729320ca318c466f66fa`;
- V2 SHA256 `e258b0076b2b260c70ba8dfa7f787d3f41e50aef398c40bcbdc5ce14a8205813`.

At pinned `seq=3` this is **`HOLD_ROLLBACK` despite local self-consistency**. A same-seq fork using a valid rehashed third event has local head `7e51cfc087b43a9a96ae2fd3b3f90277df02f5a0f1be641af04ff805655ce876` and produces `HOLD_FORK`. The original G4 `seq=3` gives `CONSISTENT_WITH_RETAINED_HISTORICAL_MINIMUM_NOT_LATEST`.

## 3. Implemented source / tests / CI

New files on `research/r63-g5-offline-pinned-minimum-20261122`:
- `research/r63_g5_floor_custody_ci/offline_minimum/g5_phone_manual_compare.py`: caller-provided minimum comparison, canonical dual-journal validation, explicit negative outcomes; **always** reports `reference_origin=CALLER_SUPPLIED_UNVERIFIED__PHONE_ORIGIN_NOT_ATTESTED`, `phone_contents_cryptographically_verified=false`, `automatic_external_latest_custody=NOT_ESTABLISHED`, `authorization=NONE`.
- `research/r63_g5_floor_custody_ci/offline_minimum/test_g5_phone_manual_compare.py`: eight additional falsification controls (old chain, valid current, valid fork, absent/invalid reference, invalid V2, valid extension). The previous 16 controls in `test_g5_floor.py` remain intact.
- `.github/workflows/r63-g5-offline-minimum.yml`: executes the new tests in both Windows and Linux and strictly asserts that the CLI's deliberate rollback exit code **2** is NOT mistaken for a successful candidate; the CI step itself exits zero only after checking the fail-closed verdict and explicit unverified reference field.

**Validation:** Local CPython 24/24 PASS. [GitHub Actions #45022163850](https://github.com/SepehrGhanbari/Ario/actions/runs/45022163850): Windows 2022 and Ubuntu 24.04 jobs **both SUCCESS** after generated fixtures, existing Python tests (16), new manual-source tests (8), existing JavaScript phone-verifier controls (8) and explicit negative CLI. No real signer or host computer was accessed.

**Preserved intermediate red CI results:** `#45022072243` failed workflow YAML parse due to an unquoted colon in a step name; `#45022106775` passed all 8 new Python tests and produced expected `HOLD_ROLLBACK EXIT=2` but the shell runner incorrectly propagated that deliberately nonzero exit as failure. Both issues were fixed **in the test harness only**. Do not erase or recast the RED historical runs.

## 4. Critical threat-model truth

The desktop test can parse the public checkpoint and receive a user-supplied `seq/head` **without any actual phone read**. Therefore the technical simulation's green verdict does **not** establish that the desktop verifier obtained its pin from an independently managed location. The desktop admin can also edit the comparator or invoke `--independent-pin-confirmed`; these are test-control flags, not secure signals of trust.

The only human-enforced protection available with a standalone phone Note is:
1. Founder independently reads the already retained `seq=3` and full head **on the iPhone**, without changing it;
2. compares **a suspect desktop candidate** against it, and refuses any action if seq < 3 or if seq == 3 but head differs;
3. **does not let the desktop's program, cloud account or recovery credentials silently modify the phone record**.

Even if (1–3) hold, the resulting model is a **manual independently remembered minimum**, not automated authoritative latest, not a device-attested secure element, not a trusted external key-management service and not a real Ario authorization gate. The independent-control claim remains self-reported until a device/account test.

## 5. Exact founder manual test still awaiting human observation

The founder can perform this with only the existing Notes app, without installing or running any program on the iPhone. Compare the Note's seq/head against these two intentionally **false/old** candidates:

- **Candidate A:** `seq=2`, head `cce8dfa45814ef13524b65f02d314a0841123fe310bdc3b745964d044d2b636a` -> should refuse as `HOLD_ROLLBACK`.
- **Candidate B:** `seq=3`, head `7e51cfc087b43a9a96ae2fd3b3f90277df02f5a0f1be641af04ff805655ce876` -> should refuse as `HOLD_FORK`.

This is a requested **human check**, not a secret challenge: both values are synthetic, public and known to the publisher. No biometric, private data, screen share or phone account credential is requested. If user reports both rejected while observing Notes locally, record as `FOUNDER_REPORTED_PHONE_VISUAL_COMPARE=PASS_MANUAL_NOT_MACHINE_ATTESTED`, **not** independent custodian/latest activation.

## 6. Decision

`G5_ORIGINAL_G4_BYTES_SYNTHETIC_REPLAY=PASS`  
`G5_LOCAL_ROLLBACK_AND_FORK_FALSIFICATION=PASS`  
`G5_GITHUB_WINDOWS_LINUX_CI=PASS`  
`FOUNDER_REPORTED_PHONE_NOTE_RETAINED=YES`  
`FOUNDER_PHONE_MANUAL_COMPARISON_OF_2_CANDIDATES=PENDING`  
`IPHONE_ADMIN_SEPARATION=FOUNDER_REPORTED_NOT_INDEPENDENTLY_TESTED`  
`G5_EXTERNAL_AUTOMATIC_AUTHORITATIVE_LATEST=NOT_ESTABLISHED`  
`GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO`.

No merge, real keys, signer, provisioning, automatic remote write or user Notes modification.
