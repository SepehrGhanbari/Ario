# R22.32 — TPM EK/AK binding, Quote and storage-object certification

**RESEARCH_ONLY / SOFTWARE_TPM / SYNTHETIC_LAB_CA / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.**

Parent: R22.31 PR #411, exact head `2ccf6033d87e69fe70a6b459d02f78cbf02efc5f`.

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
7. Use `TPM2_Certify` with a fresh verifier challenge to attest that the exact storage object is loaded. Verify the signature and check the attested object Name, Qualified Name, AK Qualified Name, attestation type and qualifying data.
8. Quote PCR 23 with a separate fresh challenge. Independently recompute the expected PCR extension, verify the quote signature and nonce, and test rejection under a wrong AK, wrong nonce, tampered signature, and post-quote PCR change.

The storage-root identifier emitted by this harness is the SHA-256 of the TPM Name bytes, explicitly named `TPM_STORAGE_PRIMARY_NAME_SHA256`. It is not silently equated with the earlier R22.30 caller-supplied storage-root fingerprint. A future adapter must define and validate the exact mapping before using it in a custodian transition.

## EK certificate and AK identity boundaries

The certificate chain in this experiment terminates at a generated lab root. It tests X.509 path validation and EK SubjectPublicKeyInfo matching only. It is **not** an OEM/manufacturer EK certificate, a TCG certification, or proof of genuine hardware. No vendor trust anchors are installed or inferred.

The AK is bound to the EK through credential activation. The AK public key is then used to verify Quote and Certify attestations. This is not a manufacturer-issued AK X.509 certificate.

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
- TCG TPM 2.0 Library Part 3: Commands, Version 185 (2026-03-12), TPM2_Certify and TPM2_Quote: https://medias.cdn.trustedcomputinggroup.org/production/Trusted_Platform_Module_2_0_Library_Part_3_Commands_Version_185_pub_87a5c10230.pdf
- tpm2-tools `tpm2_makecredential`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_makecredential.1/
- tpm2-tools `tpm2_activatecredential`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_activatecredential.1/
- tpm2-tools `tpm2_quote` and `tpm2_checkquote`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_quote.1/ and https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_checkquote.1/
- tpm2-tools `tpm2_certify` and `tpm2_verifysignature`: https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_certify.1/ and https://tpm2-tools.readthedocs.io/en/latest/man/tpm2_verifysignature.1/
- TCG PC Client Reference Integrity Manifest Specification v1.1r11 (2024-04-26): https://www.trustedcomputinggroup.org/resources/documents/tcg-pc-client-reference-integrity-manifest-specification

## Execution status

Pending dedicated GitHub Actions execution on the exact branch head. No result is counted until the final source revision's workflow and job logs are inspected.
