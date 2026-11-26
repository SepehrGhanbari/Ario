# R22.29 — TPM policy-gated signing (swtpm research model)

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

Parent #400 at c012a2a90ed3efd6061ab0de92239dcca442db36. This is an actual TPM 2.0 command-path experiment against swtpm/libtpms, a software TPM emulator, not physical hardware.

The TPM creates an ECC signing object with fixedTPM, fixedParent, sensitiveDataOrigin, sign and no userWithAuth. Its object authPolicy is PolicyAuthorize pinned to an externally generated RSA policy-authority public key. An approved policy is composed from:
1. PolicyCommandCode(TPM2_CC_Sign),
2. PolicyNV equality against the current 8-byte TPM NV counter, and
3. PolicyCpHash for the exact TPM2_Sign command parameters (the message and selected key/scheme).

The policy authority signs the resulting approved policy digest. The TPM verifies that signature and returns a verification ticket. The runtime policy session replays the same three constraints, then PolicyAuthorize verifies the approved policy/ticket before TPM2_Sign. A changed message has a different cpHash and must fail; a raw Sign without a policy session must fail; a stale counter must fail after NV increment. The fixedTPM/fixedParent attributes are checked, and a duplicate attempt is expected to fail.

The NV counter is a TPM monotonic counter, not a full external witness service. A valid authorization is bound to the exact sign command and the counter value; reusing the same token for the exact same command before advancing the counter can at most re-sign the same message. The external authorizer is a separate cryptographic role in the protocol, but in this CI fixture its private key is ephemeral and exists in the same runner/job; no real organizational separation or quorum validation is established.

Positive anti-rollback control: after generation one used NV count 1 and generation two advanced it to 3, the test owner-undefined and redefined the same counter handle with the same public definition, then incremented the new definition. swtpm returned 4, not 1; the old policy token bound to count 1 was rejected by PolicyNV. This matches TCG TPM 2.0 Architecture Rev. 1.83, §37.2.6.3: the first increment of a recreated counter must be greater than any value previously held by a counter with the same Name over the lifetime of the TPM, specifically to prevent delete/redefine rollback. This is a meaningful positive result for the tested counter semantics, not proof against TPM_Clear, firmware/platform authority, malicious firmware, device replacement, vendor deviations or physical hardware faults. Production still must pin TPM identity/epoch externally, constrain policy authority, and define recovery behavior if TPM is cleared or replaced.

swtpm is software emulation: no hardware non-extractability, secure element certification, actual TPM vendor behavior, anti-tamper, firmware boundary, real device provisioning, root-vs-platform auth isolation or Windows test is claimed. TPM key private blob files are TPM-protected blobs under the simulator's storage hierarchy, not proof that a physical device's secret cannot be extracted by invasive or firmware attacks. Policy-authority private key is ephemeral CI fixture data and is not an independent custodian.

No connection to the production Ario signer, no real keys, no external log publication, no trust activation, no production or merge. Existing R22.22–28 pins and delayed checks unchanged. Execution pending final rerun after the anti-rollback assertion was corrected.

## Technical references used

- tpm2-tools `tpm2_policyauthorize`: https://github.com/tpm2-software/tpm2-tools/blob/master/man/tpm2_policyauthorize.1.md
- tpm2-tools `tpm2_policycphash`: https://github.com/tpm2-software/tpm2-tools/blob/master/man/tpm2_policycphash.1.md
- tpm2-tools `tpm2_policynv`: https://github.com/tpm2-software/tpm2-tools/blob/master/man/tpm2_policynv.1.md
- tpm2-tools `tpm2_sign`: https://github.com/tpm2-software/tpm2-tools/blob/master/man/tpm2_sign.1.md
- tpm2-tools `tpm2_duplicate`: https://github.com/tpm2-software/tpm2-tools/blob/master/man/tpm2_duplicate.1.md
- TCG TPM 2.0 Architecture, Rev. 1.83, §37.2.6.3 NV Counter Index: https://trustedcomputinggroup.org/wp-content/uploads/TPM-2.0-1.83-Part-1-Architecture.pdf
- tpm2-tools `tpm2_nvundefine`: https://github.com/tpm2-software/tpm2-tools/blob/master/man/tpm2_nvundefine.1.md
- Ubuntu swtpm simulator package documentation: https://manpages.ubuntu.com/manpages/noble/man8/swtpm_setup.8.html
