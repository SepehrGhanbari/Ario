# R22.25 — independent keeper protocol (model only)

RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

Parent: R22.24 PR #391, head 4ded7d16f60fc32d202567d2f018f1574ac5deaf. This PR does not alter the scanner, retained recovery kit, delayed 24h/7d workflow, or any prior pin.

## Threat boundary

Publisher, GitHub repository, CI artifacts, and both publisher relays may collude and roll back together. The proposed recovery path therefore has two separately administered roles:
1. Custodian: stores content-addressed checkpoint bytes, maintains an append-only generation head with atomic compare-and-swap, and signs receipts using a key never present in publisher/GitHub.
2. Witness transparency log: records every signed receipt in order; a production adapter must verify inclusion proofs and the latest quorum-cosigned tree head before exposing the complete receipt chain.

The verifier requires the custodian's latest receipt to equal the latest receipt in the verified witness chain. It retrieves each checkpoint by digest, validates canonical bytes, signature, scope, sequence, predecessor hash, cursor monotonicity, target-tree monotonicity and append-only match manifest. Growth of the sampled tree requires a separately verified consistency proof. A missing keeper or witness, unavailable old object, mismatch, gap, fork, rollback, match deletion, or unverified transition => HOLD. No fallback to GitHub, relay, local digest, or old checkpoint.

## Implementation in this PR

protocol.go defines the receipt/checkpoint formats, interfaces, and cold recovery verifier. CustodianWriter is a contract only: a real implementation must keep its signing key, monotonic head, and authorization outside GitHub. VerifiedWitnessLog is also a contract: an adapter must verify complete inclusion proofs and a current quorum-cosigned head; returning an unverified list is not sufficient. The test harness uses ephemeral Ed25519 keys and in-memory services only. No external account, credential, service, or actual independent admin is provisioned.

## Adversarial cases

- publisher repository and two relays revert while custodian/witness remain current;
- either custodian or witness alone rolls back;
- previous floor rejects rollback for a returning client;
- both external services roll back together: a fresh client without a prior floor cannot detect this (explicit passing boundary test); requires a third independent gossip/witness domain;
- deletion, corruption, replay, fork, sequence gap, signature forgery, missing match, target shrink/conflict, unverified target growth;
- concurrent compare-and-swap writers: exactly one wins;
- custodian or witness outage: fail closed.

Target growth while the scanner is paused is represented by chained receipts and proof-verifier contract; the Go test uses synthetic consistency-proof fixtures, not a live Sigsum proof. Repeated real runner crashes, live keeper API, actual independent administrator, and actual witness-log adapter are NOT_ESTABLISHED. This is protocol/model evidence only, not proof of operational independence.

No real keys, no public test-log submission, no external publication, no merge, no trust activation, no production. R22.24 remains unchanged.

## Verified model execution — 2026-11-26

[Run 45827781576](https://github.com/SepehrGhanbari/Ario/actions/runs/45827781576), source dd5f338aaa3f39a2b830246818af5591b3383dde: SUCCESS. Seventeen Go test functions passed under normal execution and race detector. Includes real test-double CustodianWriter CAS with two concurrent proposals (exactly one signed receipt wins), three chained checkpoint generations with two target-tree growth transitions, append-only match preservation, publisher+two-relay rollback, independent custodian-only and witness-only rollback detection, stale prior-floor/fork detection, deletion/corruption/replay/signature/gap/outage rejection. The explicit dual-external-rollback test passes by demonstrating the boundary: a fresh client with no prior floor accepts the old state if both custodian and witness are rolled back together. No actual external keeper, witness adapter, independent admin, provider, service credential, live source consistency proof, public-log write, or real key exists. The keeper/witness are in-memory test doubles; the CustodianWriter and VerifiedWitnessLog are deployment contracts. No actual operational independence is established. R22.24 and delayed readback jobs remain unchanged. Research HOLD; no merge, trust activation, or production.
