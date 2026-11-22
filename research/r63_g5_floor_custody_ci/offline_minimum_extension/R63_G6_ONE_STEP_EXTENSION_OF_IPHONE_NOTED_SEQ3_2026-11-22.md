# R63 G6 — One research-only V9 V2 extension from founder's seq=3 pinned historical minimum

**Date:** 2026-11-22  
**Decision:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO.

## 1. Why

The founder attested to retaining a synthetic G5 historical minimum on a separately accessed iPhone Notes record, without changing it after the earlier manual rollback/fork comparisons:

- `epoch=research_nov_2026_no_signer`
- `seq=3`
- `head=6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1`.

No phone contents or OS permissions were independently fetched or attested. **Do not change the phone minimum in this stage.** This report never claims phone audit, external automated custodian or latest-state attestation.

## 2. Source-backed one-event append

Starting from raw synthetic journals in founder's **G4 Windows Sandbox** evidence ZIP, run ID `4796-e5cd1c02`, original archive SHA-256 `43055b3e4c89074d39c369ee464833f7367c99b425f82a78b3cf96f41fe4c2f2` (private input not uploaded to GitHub), the byte hashes were recomputed independently:

- G4 original `v1.jsonl` SHA-256 `2e1918b2c890dcf337b314692d7201a8cbdc223046322ea45953615de3144ec8`.
- G4 original `v2.jsonl` SHA-256 `9c221fa381fed4cfecc71d89e285bdb8ecc0995bfb49f8572a3177bbd4c66ac0`.
- V9 research sidecar SHA-256 `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`, unchanged from G3/G4.

A **single new research event**, nonce `dddddddd...` 64 lowercase hex and ID `44444444...` 64 lowercase hex, was appended using the **frozen original V9 V2 `append` implementation**; the original three V1 and V2 lines are unchanged byte-for-byte. The resulting canonical R60 state and hash chain were independently recomputed by a separate parser in `g6_extension_gate.py`.

| Provenance | seq | head | V1 SHA256 | V2 SHA256 |
|---|---:|---|---|---|
| Founder G4 synthetic raw input / original phone-noted minimum | 3 | `6e1d74f7860e0173b9b049487a6a89428439a987809cf363fa27503ae0b06ea1` | `2e1918b2c890dcf337b314692d7201a8cbdc223046322ea45953615de3144ec8` | `9c221fa381fed4cfecc71d89e285bdb8ecc0995bfb49f8572a3177bbd4c66ac0` |
| New G6 candidate only | 4 | **`52e1f33cf8bcf325a2cb817abe16473aa2e6a799fc76406b8cf831b912fd6d8c`** | `4eac0ebcfd5f2e1ff2efce1e2b50215fd4c511905cad34f9ce27ad07a7852b2b` | `176cb5c73c1e36f8ecd2b88a76fb8eec9db4445a43cb571d321c5e5b2880d76f` |

The candidate's third event head **equals exactly** the retained `seq=3` head. Hence the extension is a verifiable candidate based on the known historical minimum; it is not authorization, a new Ario live state, independent signed approval, or a protected `latest` floor.

## 3. Tests and exact reproducibility

The public branch `research/r63-g6-one-step-pinned-extension-20261122` adds:

- `research/r63_g5_floor_custody_ci/offline_minimum_extension/g6_extension_gate.py`: separate canonical V1/V2 audit, fixed historical seq3 pin and a strict one-event candidate policy; explicit no-automatic-promotion.
- `.../build_g6_fixtures.py`: generates deterministic synthetic seq3 prefix using the frozen V9 sidecar and demands exact independently audited G4 input SHA-256 before appending `seq=4`. No founder guest raw ZIP is uploaded.
- `.../test_g6_extension_gate.py`: **28** bounded positive/negative controls (canonical hash/commitment, prefix and append preservation, clone/fork under valid local hashes, rollback, malformed/partially written journal, forged or downgraded pin, missing phone operator assertion, extra unreviewed advance, frozen-source pin mismatch).
- `.github/workflows/r63-g6-pinned-extension.yml`: reruns fixture construction, full 28 controls and positive/fail-closed CLI contracts on Windows 2022 and Ubuntu 24.04.

**Actual GitHub Actions:** [run #45024806613](https://github.com/SepehrGhanbari/Ario/actions/runs/45024806613) **SUCCESS in both Windows and Ubuntu jobs**; each job ran **28/28 tests PASS**, validated a correct candidate and independently demanded `HOLD_PHONE_SEPARATION_NOT_ATTESTED` without explicit operator assertion. Other Implementation Regression workflow also green.

A self-contained 13-member local ZIP with V9 source, synthetic raw V1/V2 before and after, 28 tests, internal SHA256SUMS (12/12), and report was produced for user handoff; SHA256 `d08f7eb4222669582380c544cee1702ebf3f88720a0a9180ca665d04ac7e34ca`; **14,524 bytes**. It has *not* been executed on the founder's iPhone.

## 4. Outcome distinctions: acceptance vs authority

- `seq=4`, if syntactically, cryptographically and historically consistent and the founder reports separate phone storage: `CANDIDATE_EXTENDS_PINNED_SEQ3_ONLY_NOT_APPROVED_AS_LATEST`.
- A locally coherent `seq=2`: `HOLD_ROLLBACK`.
- A fully valid local `seq=4` branch built by replacing event 3 and recomputing event 4: `HOLD_FORK`.
- Supplying a “new iPhone reference” with `seq=2`, changed seq3 head or unapproved seq4: `HOLD_PIN_REBOUND_OR_DOWNGRADED`. No programmatic downgrade or automatic phone update exists.
- Missing founder-stated separate access: `HOLD_PHONE_SEPARATION_NOT_ATTESTED`.
- Extra two-event advance `seq=5`: `HOLD_UNREVIEWED_MULTI_STEP_ADVANCE`.
- **Critical honest negative control:** After building `seq=4`, a return to the original `seq=3` is still `PINNED_MINIMUM_PRESENT_NO_NEW_EVENT`, not `HOLD_ROLLBACK`, because the independently stored minimum still only says `seq=3`. **The new candidate itself has not acquired rollback protection.**

## 5. Authority boundary / what would be required next

The pinned seq3/head constants are fixed in the **reviewed research code**, which prevents a caller's untrusted pin input from lowering the baseline *when that code is trusted*. However the code and CI runner remain under GitHub publisher/control. A malicious common administrator could replace code, pinned constants and the local files and fabricate “PASS”; no external-verifier protection is established. The iPhone note was copied by the founder, separately accessible by founder report, but it was **not cryptographically read** in this experiment.

To protect `seq=4`, a separately administered verifier/custodian must independently verify the full V9-format chain extension, retain a new minimum after deliberate approval, and supply independent tamper/rollback evidence. A Sigstore Rekor historical `seq=3` inclusion does **not** assert `seq=4` or latestness; no new Rekor entry, real keys or Ario signer use happened here.

**Verdict:** `G6_LOCAL_EXTENSION=PASS`, `G6_WINDOWS_AND_LINUX_CI=28/28_EACH_PASS`, `PINNED_PHONE_MINIMUM=SEQ3_FOUNDER_REPORTED_UNCHANGED`, `G6_SEQ4=CANDIDATE_NOT_ACCEPTED_LATEST`, `EXTERNAL_SIGNED_LATEST=NOT_ESTABLISHED`, `NATIVE_V9_SIGNER=NOT_EXECUTED`, `PRODUCTION=NO_GO`.
