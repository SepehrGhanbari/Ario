# R22.33 — proof-carrying TPM-attested custodian transition

**RESEARCH_ONLY / SYNTHETIC_VERIFIER_FIXTURES / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.**

Parent: R22.32 PR #414, branch head 5f7e1f8ffc3835f00447f67489785a30a6cc6e58, itself stacked on the latest R22.31 PR #411 head 39ebaf8c5f043471f09fa56eeedce673ee00085d.

## Research question

Can the default custodian transition entrypoint refuse an arbitrary caller-supplied storage-root hash and require a verifier-signed receipt that cryptographically binds:
- the enrolled EK SubjectPublicKeyInfo fingerprint;
- the raw TPM storage-object Name and its derived root fingerprint;
- the custodian's current epoch/head and a one-step recovery transition;
- the fresh attestation challenge;
- the AK identity, Quote and CertifyCreation evidence digests; and
- a short validity window?

R22.31 proved the local monotonic state-machine behavior but explicitly accepted storage_root_sha256 as CALLER_SUPPLIED_UNATTESTED. R22.32 independently exercised EK/AK, storage Name, CertifyCreation and Quote mechanics in swtpm, but did not connect those outputs to the R22.31 transition request. R22.33 adds the strict gate-side receipt contract and state-transition binding.

## Protocol

1. issue_challenge.py verifies the signed R22.31 anchor and replays the journal while holding the custodian lock. It emits a random 256-bit nonce and signs a challenge containing the current EK identity, previous storage root, current epoch/head, proposed next head, recovery reason, policy identifier, issue time and expiry.
2. A verifier is expected to validate the actual TPM evidence against the challenge and sign an exact-schema receipt with its own key.
3. The verifier public key is pinned in verifier-pin.json; the pin file is canonical and signed by the custodian key.
4. The default custodian_state.py entrypoint verifies the custodian-signed challenge, verifier-key pin, verifier receipt signature, expiry, exact field bindings, evidence-manifest digest, and both AK/storage TPM Name derivations from the exact TPMT_PUBLIC bytes. It checks the storage-primary profile and the AK restricted-signing attributes.
5. Before any transition, the wrapper also checks that the configured custodian private key matches the public key used to verify the anchor, pin and challenge; a mismatch is rejected before the legacy gate can commit a receipt.
6. The gate independently derives:
   - device_ek_sha256 = SHA256(EK SubjectPublicKeyInfo DER);
   - storage_root_sha256 = SHA256(raw TPM Name bytes).
7. The transition nonce is derived from the signed challenge nonce and canonical verifier-receipt hash. This makes the R22.31 journal idempotency key bind the exact signed evidence receipt, not merely a caller-chosen nonce.
8. Only after preflight verification does the wrapper pass a normalized base request to the preserved R22.31 monotonic state machine. It then emits an outer custodian-signed transition bundle containing the challenge, verifier receipt, normalized request and inner custodian receipt.

The outer bundle is the authoritative R22.33 result. The inner R22.31 receipt intentionally retains its historical CALLER_SUPPLIED_UNATTESTED label because the legacy state-machine function does not itself verify TPM evidence; consumers must verify the signed outer bundle and both nested signatures.

## Default-entrypoint enforcement

The original R22.31 implementation is preserved unchanged as custodian_state_legacy.py. Existing R22.31 tests now explicitly target that legacy path. The default custodian_state.py is a strict wrapper around R22.33 and rejects a bare caller-supplied request. The legacy script remains present only for historical regression and comparison; it is not the default entrypoint.

## Adversarial acceptance matrix

The R22.33 tests exercise:
- valid signed challenge, pinned verifier receipt, derived TPM identity fields, and one committed transition;
- rejection of a bare request at the default entrypoint;
- caller substitution of EK identity or storage-root hash;
- AK and storage TPMT_PUBLIC mutation, wrong Name derivation, and missing storage/AK object attributes;
- mismatched custodian private/public key pair rejected before commit;
- malformed AK SubjectPublicKeyInfo DER rejected even when its claimed hash is updated;
- wrong verifier key, tampered verifier signature, tampered challenge signature, and invalid verifier pin;
- invalid TPM Name algorithm and a storage-root hash not derived from the exact Name bytes;
- evidence-manifest mismatch for Quote/CertifyCreation evidence;
- expired/future receipt and mismatched challenge hash/nonce;
- request nonce not derived from the exact signed receipt;
- exact retry returning the same signed custodian receipt and bundle without another journal record;
- a different signed receipt for an already consumed challenge being rejected as stale;
- bundle-output path alias rejection; and
- challenge issuance from the replayed current state without mutating the journal.

The preserved R22.31 suite is also run to ensure its 18 historical state-machine tests still pass against the explicitly named legacy implementation.

## Evidence boundary and remaining work

This stage tests the custodian-side receipt contract and enforcement, not the verifier implementation. Test receipts are signed by synthetic verifier keys and contain synthetic evidence digests. The R22.32 software-TPM run remains separate evidence. Its harness now also captures the AK TPMT_PUBLIC and independently recomputes the AK Name while checking restricted-signing attributes. R22.33 test fixtures exercise the same AK/storage TPMT_PUBLIC-to-Name contract, but the R22.32 raw evidence bundle is not yet exported and independently re-verified by the receipt signer.

Therefore this stage does not claim:
- that the verifier signing key is independently held or inaccessible to the runner administrator;
- that a real OEM EK certificate or manufacturer trust chain was validated;
- that a physical TPM, hardware AK non-extractability, firmware, Secure Boot or a real event log was verified;
- that the synthetic PCR 23 policy is a real platform approval policy;
- that the R22.32 evidence has been wired end-to-end into the receipt signer;
- independent custody, external rollback-floor enforcement, Ario signer integration, Genesis, trust activation, production or merge.

The next research task is to implement the verifier that consumes the actual R22.32 evidence artifacts, verifies the TPM signatures and challenge, and only then signs this receipt schema. Its key must subsequently move to a separately administered custodian before any independence claim is made.

## Execution

Pending dedicated GitHub Actions run on the exact R22.33 branch head. No test count is claimed until the final workflow and logs are inspected.
