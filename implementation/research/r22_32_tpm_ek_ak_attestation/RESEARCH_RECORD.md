# R22.32 — TPM EK/AK binding, Quote and storage-object certification

**RESEARCH_ONLY / SOFTWARE_TPM / SYNTHETIC_LAB_CA / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.**

Parent: R22.31 PR #411, exact head `39ebaf8c5f043471f09fa56eeedce673ee00085d`.

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


## AK TPMT_PUBLIC identity extension — 2026-11-26

The R22.32 harness now also reads the persistent AK public area back from the TPM, captures its raw TPMT_PUBLIC and Qualified Name, independently recomputes the AK Name, and checks the expected restricted RSA signing attributes (fixedTPM, fixedParent, sensitiveDataOrigin, restricted, signEncrypt). This closes the earlier asymmetry where the storage-primary Name was recomputed but the AK Name was only captured from tpm2_createak output.

Dedicated R22.32 workflow on the R22.33 integration branch: [run 45857398519](https://github.com/SepehrGhanbari/Ario/actions/runs/45857398519), source head `6050263e6075415d5261b876c61a2d9cf5c8a30f`, **SUCCESS: 26/26 PASS**. Environment: Ubuntu 24.04; tpm2-tools 5.6-1build4; swtpm 0.7.3-0ubuntu5.24.04.1; OpenSSL 3.0.13. Evidence artifact [ID 15135289752](https://github.com/SepehrGhanbari/Ario/actions/runs/45857398519/artifacts/15135289752).

This is still software-TPM evidence with a synthetic lab CA, not OEM EK or physical hardware attestation. The AK public area check strengthens the Name binding but does not establish hardware non-extractability, manufacturer identity, independent custody, firmware trust, or rollback resistance.
