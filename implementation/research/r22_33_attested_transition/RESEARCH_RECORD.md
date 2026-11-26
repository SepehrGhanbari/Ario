# R22.33 — proof-carrying TPM-attested custodian transition

**RESEARCH_ONLY / SYNTHETIC_VERIFIER_FIXTURES / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.**

Parent: R22.32 PR #414, current head 40eccd4692c765255f628a7e0e993b0057867b52, stacked on the latest R22.31 PR #411 head 1dba8ae472d0a0c8d02ab575eb62878fa705f897.

## Research question

Can the default custodian transition entrypoint refuse an arbitrary caller-supplied storage-root hash and require a verifier-signed receipt that cryptographically binds:
- the enrolled EK SubjectPublicKeyInfo fingerprint;
- the raw TPM storage-object Name and its derived root fingerprint;
- the custodian's current epoch/head and a one-step recovery transition;
- the fresh attestation challenge;
- the AK identity and Qualified Name;
- TPM2_NV_Certify index Name, exact 32-byte contents, AK signer, fresh nonce, attestation and signature digests;
- challenge-derived nonces for NV_Certify, CertifyCreation and PCR Quote; and
- Quote and CertifyCreation evidence digests;
- a short validity window?

R22.31 proved the local monotonic state-machine behavior but explicitly accepted storage_root_sha256 as CALLER_SUPPLIED_UNATTESTED. R22.32 independently exercised EK/AK, storage Name, CertifyCreation and Quote mechanics in swtpm, but did not connect those outputs to the R22.31 transition request. R22.33 adds the strict gate-side receipt contract and state-transition binding.

## Protocol

1. issue_challenge.py verifies the signed R22.31 anchor and replays the journal while holding the custodian lock. It emits a random 256-bit nonce and signs a challenge containing the current EK identity, previous storage root, current epoch/head, proposed next head, recovery reason, policy identifier, issue time and expiry.
2. A verifier is expected to validate the actual TPM evidence against the challenge and sign an exact-schema receipt with its own key.
3. The verifier public key is pinned in verifier-pin.json; the pin file is canonical and signed by the custodian key.
4. The default custodian_state.py entrypoint verifies the custodian-signed challenge, verifier-key pin, verifier receipt signature, expiry, exact field bindings, evidence-manifest digest, and both AK/storage TPM Name derivations from the exact TPMT_PUBLIC bytes. It checks the storage-primary profile and the AK restricted-signing attributes.
5. It recomputes the NV index Name from the pinned handle, nameAlg, attributes and dataSize using the same public-area encoding as the R22.32 verifier. It requires the NV index to use the exact 32-byte SHA-256 profile, empty authPolicy and offset zero. The NV contents must equal the storage-root hash derived from the storage TPM Name, and the NV qualifiedSigner must equal the enrolled AK Qualified Name.
6. Before any transition, the wrapper also checks that the configured custodian private key matches the public key used to verify the anchor, pin and challenge; a mismatch is rejected before the legacy gate can commit a receipt.
7. The gate independently derives:
   - device_ek_sha256 = SHA256(EK SubjectPublicKeyInfo DER);
   - storage_root_sha256 = SHA256(raw TPM Name bytes).
8. The transition nonce is derived from the signed challenge nonce and canonical verifier-receipt hash. This makes the R22.31 journal idempotency key bind the exact signed evidence receipt, not merely a caller-chosen nonce.
9. Only after preflight verification does the wrapper pass a normalized base request to the preserved R22.31 monotonic state machine. It then emits an outer custodian-signed transition bundle containing the challenge, verifier receipt, normalized request and inner custodian receipt.

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
- evidence-manifest mismatch for NV_Certify, Quote and CertifyCreation evidence;
- NV index Name recomputation, exact index handle/attributes/size, empty authPolicy, offset zero and contents-to-storage-root binding;
- NV_Certify signer binding to the AK Qualified Name;
- NV, CertifyCreation and Quote nonce derivation from the same custodian challenge;
- expired/future receipt and mismatched challenge hash/nonce;
- request nonce not derived from the exact signed receipt;
- exact retry returning the same signed custodian receipt and bundle without another journal record;
- a different signed receipt for an already consumed challenge being rejected as stale;
- bundle-output path alias rejection; and
- challenge issuance from the replayed current state without mutating the journal.

The preserved R22.31 suite is also run to ensure its 18 historical state-machine tests still pass against the explicitly named legacy implementation.

## Evidence boundary and remaining work

This stage tests the custodian-side receipt contract and enforcement, not the verifier implementation. Test receipts are signed by synthetic verifier keys and contain synthetic evidence digests. The R22.32 harness now captures EK/AK, storage TPMT_PUBLIC and Names, NV public metadata and contents, NV_Certify, CertifyCreation, PCR Quote, and a SHA-256 evidence manifest in an optional public evidence bundle. It also supports domain-separated NV/creation/quote nonces derived from a supplied R22.33 challenge nonce. The R22.32 CI exercises this path with a fresh per-run random nonce and checks the derivation formulas. That CI nonce is not itself a custodian-signed challenge, and the exported raw bundle is not yet consumed by a separate verifier to produce the signed receipt.

Therefore this stage does not claim:
- that the verifier signing key is independently held or inaccessible to the runner administrator;
- that a real OEM EK certificate or manufacturer trust chain was validated;
- that a physical TPM, hardware AK non-extractability, firmware, Secure Boot or a real event log was verified;
- that the synthetic PCR 23 policy is a real platform approval policy;
- that the R22.32 evidence has been wired end-to-end into the receipt signer; the R22.32 CI nonce is a per-run test vector, not a signed custodian challenge;
- independent custody, external rollback-floor enforcement, Ario signer integration, Genesis, trust activation, production or merge.

The next research task is to implement the verifier that consumes the actual R22.32 evidence artifacts, verifies the TPM signatures and challenge, and only then signs this receipt schema. Its key must subsequently move to a separately administered custodian before any independence claim is made.

## Execution

Dedicated exact-head R22.33 workflow [run 45861166209](https://github.com/SepehrGhanbari/Ario/actions/runs/45861166209), source commit `d19af7e6380a54677fb6f927fbd66cb30bbdc862`, **SUCCESS: 40/40 R22.33 tests**. The same run completed the preserved R22.31 legacy state-machine suite: **18/18 PASS**.

Repository Implementation Regression on the same exact head: [run 45861166197](https://github.com/SepehrGhanbari/Ario/actions/runs/45861166197), **SUCCESS**. Evidence artifact: [R22.33 test logs, ID 15137653237](https://github.com/SepehrGhanbari/Ario/actions/runs/45861166209/artifacts/15137653237).

R22.32 software-TPM CI with AK/storage usage-role separation, NV_Certify, public evidence export and a per-run nonce derivation cross-check: [run 45860968609](https://github.com/SepehrGhanbari/Ario/actions/runs/45860968609), **41 PASS assertions**. Raw evidence artifact: [ID 15138756624](https://github.com/SepehrGhanbari/Ario/actions/runs/45860968609/artifacts/15138756624).

The R22.32 CI nonce is generated by the runner as a per-run test vector; it is not itself a custodian-signed challenge. R22.33 tests verify the signed-challenge and derived-nonce rules independently, but the raw TPM evidence has not yet been consumed by a separate verifier to produce a verifier-signed receipt. That end-to-end verifier and independent key custody remain the next step.
