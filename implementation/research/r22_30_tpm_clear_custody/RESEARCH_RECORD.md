# R22.30 — TPM_Clear, device identity and custodian-gated recovery

**RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.**

Parent: R22.29 PR #401, source head `13cd0bf6128075def37763a3f097011c617d3174`. This is a new software-TPM experiment using `swtpm`/libtpms and tpm2-tools. It is not a physical TPM test.

## Question

Can a TPM owner reset/clear the Storage hierarchy, replace the TPM, or retain platform-managed state while causing Ario to silently accept an old identity or generation? The experiment separates three logical roles:
- publisher: produces the synthetic recovery request;
- TPM/platform administrator: controls platform hierarchy and can execute TPM_Clear;
- custodian: owns a separate UID-protected signing key and a signed anchor of device EK fingerprint, storage-root fingerprint, epoch and last confirmed synthetic checkpoint.

## TPM_Clear behavior under test

TCG TPM 2.0 Library Part 1 Architecture v185 (2026-03-12), §§10.3–10.8 and 11.4, states that platform controls can manage hierarchies and change PPS/SPS/EPS; TPM2_Clear is authorized by Platform or Lockout authorization unless disableClear is set; platform authorization can re-enable clearing. TPM2_Clear flushes SPS/EPS hierarchy objects, deletes NV indices without TPMA_NV_PLATFORMCREATE, resets owner/endorsement/lockout auth and policies, and replaces the Storage Primary Seed (SPS). It does not list EPS replacement as part of TPM2_Clear. EKs are derived from EPS, while storage root keys are derived from SPS. Thus the model expects the same EK public identity after TPM_Clear but a different Storage Primary Key. Platform-created NV survives; owner-created NV is removed.

This distinction is essential: an EK fingerprint alone is not an epoch/freshness signal. The signed custodian anchor therefore binds EK identity + SPS-derived storage-root identity + monotonic epoch + previous checkpoint digest. A reset on the same TPM is detected as same EK / changed storage root. A replacement TPM is detected as a different EK.

## Test plan

1. Set synthetic Platform, Owner, Lockout and Endorsement hierarchy auth values.
2. Create and increment separate Owner-created and Platform-created NV counters.
3. Create an EK and an Owner Storage Primary Key; record their public-key SHA-256 fingerprints.
4. Set disableClear. Confirm Lockout-authorized TPM_Clear is rejected. Have Platform authorization re-enable TPM_Clear, then clear the TPM.
5. Verify EK fingerprint is stable, SPS-derived storage key changes, pre-clear owner context is unusable, owner-created NV disappears, platform-created NV and its value survive, and Owner/Endorsement/Lockout auth values reset.
6. Start a second fresh swtpm state and verify its EK fingerprint differs (replacement-device model).
7. Run a synthetic custodian policy under a separate Unix UID. Its signed anchor binds the original EK, storage root, epoch 7 and previous checkpoint. It permits only a single-step explicit recovery to epoch 8 on the same EK, with changed storage root, exact previous checkpoint and fresh 256-bit nonce.
8. Verify custodian rejection of nonce replay, replacement EK, skipped epoch, stale previous checkpoint and unchanged storage-root identity.
9. Record the expected RED boundary: the CI runner can use root/sudo to read the custodian key. UID separation is not independent administrative custody.

## Expected security interpretation

A same-device TPM_Clear is not silently treated as continuity: it requires a custodian-signed explicit recovery transition and epoch increment. A replacement TPM is rejected against the original anchor. Platform authority remains stronger than ordinary Owner authority and can re-enable Clear; therefore TPM policy/NV alone cannot establish sovereignty against the platform/firmware administrator. The custodian's key and anchor must be outside that administrator's control in a real deployment.

The separate UID is only a local process/permission control. The runner's root can read its key and modify local files. The custodian in this CI job is therefore a **simulation**, not an independent custodian. No hardware EK certificate chain, attestation quote, PCR measurement, manufacturer trust, secure boot, TPM_Clear on a physical device, TPM firmware update, platform reset, device replacement in hardware, or physical non-extractability is established. The synthetic EK fingerprint is an identifier only, not proof of genuine hardware. The test does not connect to Ario's signer or ledger and does not authorize any checkpoint.

## References

- TCG TPM 2.0 Library Part 1: Architecture, Version 185 (2026-03-12), especially §§10.3–10.8 and 11.4: https://trustedcomputinggroup.org/wp-content/uploads/Trusted-Platform-Module-2.0-Library-Part-1-Architecture_Version-185_pub.pdf
- TCG TPM 2.0 Library current specification landing page: https://www.trustedcomputinggroup.org/resources/documents/tpm-library-specification
- tpm2-tools `tpm2_clear`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_clear.1/
- tpm2-tools `tpm2_clearcontrol`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_clearcontrol.1/
- tpm2-tools `tpm2_createek`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_createek.1/
- tpm2-tools `tpm2_nvdefine`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_nvdefine.1/
- tpm2-tools NV attribute names: https://tpm2-tools.readthedocs.io/en/latest/man/common/nv-attrs/

## Execution status

Final execution verified on 2026-11-26; see the appended run record below. No real key, public log, merge, trust activation, production or change to R22.22–29 evidence.

## Final verified execution — 2026-11-26

[GitHub Actions run 45841590621](https://github.com/SepehrGhanbari/Ario/actions/runs/45841590621), exact source/script commit `e32a6334f8f6639bd664fcfe00bb8def761624b9`, job 139984380104 SUCCESS. The run emitted **27 PASS assertions** and one explicit expected RED boundary. Verified: lockout TPM_Clear is blocked when disableClear is set; platform authority can re-enable Clear; platform-authorized TPM_Clear succeeds; EK fingerprint stays stable while SPS-derived storage-root fingerprint changes; old storage context is invalidated; owner NV disappears while platform-created NV survives with value intact; Owner/Endorsement/Lockout auth values reset; a fresh replacement simulator has a different EK; the publisher UID cannot directly read the custodian key; a signed same-device recovery to epoch 8 is approved; nonce replay, replacement EK, skipped epoch, stale previous head and unchanged storage-root are rejected. The expected RED is explicit: runner root can read the custodian private key, so UID separation is not independent custody.

Evidence artifact: `r22-30-tpm-clear-custody-evidence`, ID `15129270513`, ZIP SHA-256 `8fce527c42b0788509760ef753a00aa45f7ea11f72e4b197f07ba6ae557c772a`, 958 bytes, expires 2026-12-26T14:42:15Z. Metadata only; artifact bytes were not independently downloaded/rehashed. Earlier failed setup attempts are retained in Actions history; the final successful run is the only run counted as passing. [Implementation Regression run 45841590585](https://github.com/SepehrGhanbari/Ario/actions/runs/45841590585): M0 regression SUCCESS; Python 3.14 and Windows differential advisory jobs SKIPPED.

Interpretation: TPM_Clear does not preserve Storage hierarchy continuity; same-device EK identity remains stable, while the Storage Primary Seed-derived root changes. A device identity fingerprint alone is therefore insufficient to represent the owner/storage epoch. The simulated custodian binds both fingerprints, epoch and previous checkpoint and requires an explicit one-step recovery. This is a useful protocol control in swtpm, not proof of hardware identity or an independent custodian. The local custodian private key/anchor remain root-readable and mutable; no manufacturer EK certificate chain, attestation quote, PCR evidence, secure-boot measurement, physical TPM, external custodian, Ario signer integration, real checkpoint signature, trust activation, production or merge is established. Existing R22.22–29 pins and delayed checks unchanged.
