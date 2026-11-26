# R22.32 — TPM EK/AK binding, Quote and storage-object certification

**RESEARCH_ONLY / SOFTWARE_TPM / SYNTHETIC_LAB_CA / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.**

Parent: R22.31 PR #411, exact head `1dba8ae472d0a0c8d02ab575eb62878fa705f897`.

## Research question

Can Ario replace the caller-supplied, explicitly UNATTESTED storage-root fingerprint in R22.31 with evidence whose provenance is tied to TPM-generated objects and signed attestation data?

This is a software-TPM interoperability experiment using `swtpm`, `libtpms`, `tpm2-tools`, and OpenSSL. It does not use a physical TPM.

## Important protocol distinction

An AK is not generally expected to carry a manufacturer-issued X.509 certificate. The TPM 2.0 credential activation protocol is the appropriate binding test:

1. The verifier creates a random secret and uses the EK public key plus the AK Name to make a credential.
2. The TPM activates that credential using the EK and AK handles.
3. Recovery of the exact verifier secret demonstrates that the AK is associated with the TPM that possesses the corresponding EK.

The harness therefore tests `MakeCredential/ActivateCredential`, rather than inventing a mandatory AK certificate chain.

## What the harness exercises

1. Generate a TPM-profile EK in `swtpm`.
2. Issue a short-lived EK X.509 certificate using a synthetic local lab CA, validate its chain, and compare the certificate SPKI with the TPM EK public key.
3. Reject the EK certificate under an unrelated CA.
4. Create an AK and perform MakeCredential/ActivateCredential; compare the returned secret byte-for-byte.
5. Attempt to activate the TPM-1 credential on a second independent `swtpm` state with a different EK and AK; expect rejection.
6. Create an Owner-hierarchy storage primary and capture the TPM-computed Name and Qualified Name.
7. Use `TPM2_CertifyCreation` with a fresh verifier challenge to attest the currently loaded storage object and its TPM-generated creation record. Verify the signature, object Name, creation hash, AK Qualified Name, attestation type and qualifying data. Independently recompute the object Name from the marshalled `TPMT_PUBLIC` bytes and check fixedTPM/fixedParent/sensitiveDataOrigin attributes.
8. Quote PCR 23 with a separate fresh challenge. Independently recompute the expected PCR extension, verify the quote signature and nonce, and test rejection under a wrong AK, wrong nonce, tampered signature, and post-quote PCR change.

The storage-root identifier emitted by this harness is the SHA-256 of the TPM Name bytes, explicitly named `TPM_STORAGE_PRIMARY_NAME_SHA256`. It is not silently equated with the earlier R22.30 caller-supplied storage-root fingerprint. A future adapter must define and validate the exact mapping before using it in a custodian transition.

## CertifyCreation versus Certify

The Ubuntu runner's packaged `tpm2_certify` does not expose a qualifying-data option, while `tpm2_certifycreation` does. The harness therefore uses `TPM2_CertifyCreation` with a fresh challenge. It proves that the loaded object is associated with TPM-generated creation data and signs the object Name and creation hash. This is not the same statement as `TPM2_Certify`; the attested Qualified Name is not claimed to be signed here. The Qualified Name is captured separately, while the object Name is independently recomputed from the raw `TPMT_PUBLIC` structure. The binary verifier parses `TPMS_ATTEST` directly because the runner's `tpm2_print` version cannot render the Creation attestation type.

## EK certificate and AK identity boundaries

The certificate chain in this experiment terminates at a generated lab root. It tests X.509 path validation and EK SubjectPublicKeyInfo matching only. It is **not** an OEM/manufacturer EK certificate, a TCG certification, or proof of genuine hardware. No vendor trust anchors are installed or inferred.

The AK is bound to the EK through credential activation. The AK public key is then used to verify Quote and CertifyCreation attestations. This is not a manufacturer-issued AK X.509 certificate.

## PCR and measured-boot boundaries

PCR 23 is used as an application-defined synthetic measurement target. The experiment proves that the quote binds a fresh nonce and the PCR digest returned by the software TPM. It does not validate UEFI Secure Boot, firmware measurements, a PC Client event log, reference integrity manifests, or a real boot chain. A valid PCR quote alone does not mean the measured state is approved; a verifier still needs a policy and trusted reference measurements.

The script reads PCR values after the quote and checks them against the quote digest. A later PCR extension is expected to make verification against the new values fail.

## Explicit non-claims

- No physical TPM, OEM EK certificate, manufacturer trust chain, hardware AK non-extractability, or real device identity.
- No firmware, Secure Boot, event-log replay, RIM policy, or operating-system integrity claim.
- No independently administered custodian, external rollback floor, or resistance to a runner administrator.
- No Ario signer, ledger, real key, Genesis, trust activation, production, merge, or changes to R22.22–31.
- The lab CA key and both simulator states are disposable runner-local material.

## References

- TCG EK Credential Profile for TPM Family 2.0, Level 0, Version 2.7 (2026-03-19): https://www.trustedcomputinggroup.org/resources/documents/http-trustedcomputinggroup-org-wp-content-uploads-tcg-ek-credential-profile
- TCG TPM 2.0 Library Part 1: Architecture, Version 185 (2026-03-12), especially attestation and PCR attestation: https://trustedcomputinggroup.org/wp-content/uploads/Trusted-Platform-Module-2.0-Library-Part-1-Architecture_Version-185_pub.pdf
- TCG TPM 2.0 Library Part 3: Commands, Version 185 (2026-03-12), TPM2_CertifyCreation and TPM2_Quote: https://medias.cdn.trustedcomputinggroup.org/production/Trusted_Platform_Module_2_0_Library_Part_3_Commands_Version_185_pub_87a5c10230.pdf
- tpm2-tools `tpm2_makecredential`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_makecredential.1/
- tpm2-tools `tpm2_activatecredential`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_activatecredential.1/
- tpm2-tools `tpm2_quote` and `tpm2_checkquote`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_quote.1/ and https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_checkquote.1/
- tpm2-tools `tpm2_certifycreation` and `tpm2_verifysignature`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_certify.1/ and https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_verifysignature.1/
- TCG PC Client Reference Integrity Manifest Specification v1.1r11 (2024-04-26): https://www.trustedcomputinggroup.org/resources/documents/tcg-pc-client-reference-integrity-manifest-specification

## Execution status

Dedicated exact-head CI on the restacked branch: [run 45854078266](https://github.com/SepehrGhanbari/Ario/actions/runs/45854078266), source commit `498e3620362cdea1940377c15be3edc611fcd19f`, **SUCCESS: 24/24 PASS**.

Repository Implementation Regression on the same exact head: [run 45854078244](https://github.com/SepehrGhanbari/Ario/actions/runs/45854078244), **SUCCESS**.

Environment: tpm2-tools 5.6-1build4, swtpm 0.7.3-0ubuntu5.24.04.1, OpenSSL 3.0.13, Ubuntu 24.04.5.

The 24 passing assertions cover:
- synthetic EK certificate chain, pinned lab root, wrong-root rejection and EK SPKI matching;
- AK-to-EK MakeCredential/ActivateCredential and rejection on a second independent simulator;
- TPM Name recomputation from TPMT_PUBLIC, required storage-object attributes, and mutation rejection;
- nonce-bound TPM2_CertifyCreation signature, signer, object Name and creation-hash checks, including wrong-challenge and substituted-object rejection;
- PCR 23 recomputation, binary Quote challenge/signer/selection parsing, TPM signature/PCR-digest validation, and rejection of wrong nonce, wrong AK, altered signature and changed PCR.

Evidence artifact: [R22.32 TPM attestation evidence](https://github.com/SepehrGhanbari/Ario/actions/runs/45854078266/artifacts/15134911715).

The earlier pre-restack run 45853404250 also passed 24/24; it is retained as historical evidence. The run above is the final exact-head result after the feature branch was updated to the latest R22.31 PR #411 head.

This remains software-TPM interoperability evidence, not proof of physical-device or manufacturer identity.

## R22.32 addendum — exact NV contents attestation (2026-11-26)

**New bounded question:** Can the exact 32-byte storage-root claim be carried inside a TPM NV index and returned in a fresh, AK-signed `TPMS_ATTEST_NV`, with the NV index Name independently recomputed from its public area?

**Implementation:** Added `verify_nv_attestation.py` and extended `run_swtpm_attestation.sh`. The harness writes the SHA-256 of the TPM storage-primary Name into a 32-byte NV index, reads it back, obtains `TPM2_NV_Certify` using the already credential-activated AK, verifies the signature with `tpm2_verifysignature`, and independently checks the attestation type, qualifying data, AK Qualified Name, NV index Name, offset and exact contents. The NV Name is recomputed from the TPM2_NV_ReadPublic YAML fields (handle, nameAlg, attributes including TPMA_NV_WRITTEN, empty authPolicy and dataSize).

**Adversarial controls:** wrong challenge, substituted content, substituted NV handle, and substituted AK Qualified Name must be rejected. The same TPM owner then overwrites the NV index with a fresh random 32-byte value and obtains a second valid attestation. The old attestation must not validate against the new value, and the new attestation must not validate against the old value.

**Interpretation:** A valid NV_Certify signature authenticates the bytes currently stored in the specified NV index at attestation time. It does **not** prove that the bytes were correctly measured from an external filesystem, that the owner chose an honest value, that the NV index cannot be rewritten, or that a prior valid state cannot be restored after TPM Clear/redefinition. This is therefore a `TPM_NV_ATTESTED_CLAIM`, not a `TPM_MEASURED_ROOT`, an immutable floor, or independent custody. The explicit owner-rewrite positive is included to prevent overclaiming.

**Source references:** tpm2-tools documents `tpm2_nvcertify` as attesting NV index contents and identifies the NV index/owner hierarchy authorization options: https://tpm2-tools.readthedocs.io/en/stable/man/tpm2_nvcertify.1/ . The TPM 2.0 specification defines `TPMS_NV_CERTIFY_INFO` as index Name, offset and NV contents: https://trustedcomputinggroup.org/wp-content/uploads/Trusted-Platform-Module-2.0-Library-Part-2-Structures_Version-185_pub.pdf . TPM Names for NV indices are derived from the NV public area; the Name changes when dynamic attributes such as TPMA_NV_WRITTEN change: https://trustedcomputinggroup.org/wp-content/uploads/Trusted-Platform-Module-2.0-Library-Part-1-Architecture_Version-185_pub.pdf .

**Initial execution status:** parser-only synthetic validation passed positive exact-content, wrong-content and wrong-challenge cases locally. Exact software-TPM CI is pending for the new commit. No physical TPM, OEM certificate, real key, external custodian, anti-rollback guarantee, trust activation, production or merge is claimed.

### 2026-11-26 — R22.32 NV attestation validation correction

- Moved the alternate-root fixture creation before the wrong-content negative control; the negative control now uses an existing 32-byte file.
- Added an explicit `expect_reject` wrapper that requires a verifier `REJECT` line, preventing unrelated errors (such as a missing fixture) from being counted as a valid negative.
- Added `implementation/tests/test_r22_32_nv_attestation.py` for NV public Name recomputation, written-state and handle checks, exact field acceptance, challenge/content/signer/offset/trailing-byte negatives, and Bash syntax/order checks.
- Exact TPM simulator execution remains **NOT_RUN**: the R22.32 workflow file is branch-local and absent from `main`; no current-head TPM workflow run exists. The generic Implementation Regression workflow will run the new parser tests.

### 2026-11-26 — R22.32 NV attestation first-run failure and correction

- Dedicated TPM workflow run **45857424209** executed on exact head `ae553dac0ccf04578cb8156064d33088f7753f63` and failed **before** invoking `tpm2_nvcertify`: the verifier rejected the zero-length NV authorization-policy representation emitted by `tpm2_nvreadpublic`. The workflow log is the evidence; no NV attestation PASS is claimed for that run.
- Generic Implementation Regression run **45857424187** reported **8 failed, 2100 passed, 8 skipped, 273 subtests passed**. The eight new parser tests all stopped while parsing their synthetic NV YAML fixture because the fixture encoded literal backslash-n sequences instead of line breaks. Existing-suite results remain separate from the new test failures.
- This commit accepts only explicit empty-policy representations (blank, zero-length forms) and rejects non-empty policy material; it also prints the public NV metadata in the research workflow log for audit.
- The synthetic fixture now uses actual newline characters. Exact TPM NV_Certify remains pending a fresh current-head workflow run.

### 2026-11-26 — R22.32 NV public-name format and test assertion correction

- The exact-head TPM workflow **45857768346** reached the real `tpm2_nvreadpublic` output. It reported NV Name `000b79a2c7d47eac1193512b3b1363f972df127b6507b61ec09dc6c0e513de792fd9` and attributes `0x20060006`. Independent recomputation from handle, SHA-256 nameAlg, attributes (including WRITTEN), empty authPolicy and size 32 produced the identical Name. The parser then failed because tpm2-tools 5.6 emits a `name:` field and omits an empty `authorization policy` field. The TPM2_NV_Certify command had not yet run.
- The generic regression workflow **45857768351** reported **1 failed, 2107 passed, 8 skipped, 273 subtests passed**. The sole failure was a test's expected wording (`Qualified Name`) differing from the verifier's actual `qualifiedSigner` rejection; the wrong-signer case itself was rejected correctly.
- This correction requires the TPM-reported NV Name to match the independently recomputed Name, accepts omission of the policy field only in conjunction with that match, adds a mismatched-reported-Name negative, and corrects the test assertion.
- **Correction to prior workflow note:** the earlier statement that the branch-local workflow could not run was premature. It did trigger on the exact branch head; run 45857768346 is the evidence. The earlier NOT_RUN statement is superseded by these run results.
