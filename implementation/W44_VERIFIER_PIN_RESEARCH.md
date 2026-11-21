# W44 — conditional byte binding to a verifier-retained checkpoint

**RESEARCH_ONLY / DRAFT_HOLD / NO_MERGE / NO_SIGNER / NO_TRUST_ACTIVATION / NO_PRODUCTION**

## Goal and baseline

W43 [Draft PR #311](https://github.com/SepehrGhanbari/Ario/pull/311), [targeted CI 44944668608](https://github.com/SepehrGhanbari/Ario/actions/runs/44944668608), confirmed a Linux mmap ABA case in which W38 returned a mixed old/new JSONL image despite before/mid/after metadata and repeated matching reads. W43 is not merged. W44 branches from W42 main SHA 9dd4dda2784fe90e8dda0bb5142ea81167a64869, without using the W43 draft as its base.

**Narrow question:** if a verifier already retains a checkpoint and verification key outside the file writer's authority, does the acquired byte image match those pinned bytes? Checking a local digest cannot *create* the external independence it assumes.

## Design contract

- SignedPin contains artifact_id, sequence, byte_length and sha256, signed as a domain-separated canonical payload using ephemeral Ed25519 test keys.
- VerifierAnchor contains the expected artifact_id, **exact** retained sequence, SHA-256 checkpoint hash of that payload, and an **already trusted** public key.
- A signed pin with an older sequence, ahead of the floor, or the same sequence but a different digest is refused. Exact equality to the retained floor is required; this is not an append-only chain or an authorized floor-advance mechanism.
- Pin format, expected checkpoint hash and signature are checked *before* W38/W41 bounded reading. Read bytes must match both the pinned length and SHA-256. All mismatches and bounded read refusals yield UNKNOWN.
- The only positive status is **PIN_MATCH_ONLY**, *not* ACCEPTED, TRUSTED, EVIDENCE or TRUE. Every response sets may_use=false, historical_event_truth=UNKNOWN, custody_independence=NOT_ESTABLISHED, evidence_admission=NOT_EVALUATED.
- The public probe does **not** accept a caller-selected reader: it calls W38/W41 directly. Tests monkeypatch the private imported read function for fault injection only. A compromised verifier runtime can still bypass any same-process check.

**Conditional premise:** the verification key and floor must actually originate outside the file writer's administrative control and survive rollback/restart. A dataclass called VerifierAnchor, a separate folder/process under the same OS user, a self-controlled GitHub repository, or a self-signed hash **does not** prove independence.

## Synthetic negative and positive controls

| Scenario | Expected |
|---|---|
| Exact bytes under fixed checkpoint | PIN_MATCH_ONLY, still may_use=false |
| Valid equal-size JSONL overwritten on same inode | UNKNOWN / INPUT_DIGEST_MISMATCH |
| Forged pin signed with attacker's key | UNKNOWN / CHECKPOINT_SIGNATURE_UNTRUSTED |
| Writer-controlled new pin against retained anchor | UNKNOWN / CHECKPOINT_NOT_AT_VERIFIER_FLOOR |
| Valid signed old pin after verifier floor advanced | UNKNOWN / CHECKPOINT_NOT_AT_VERIFIER_FLOOR |
| Equivocation at exactly the same sequence | UNKNOWN / CHECKPOINT_NOT_AT_VERIFIER_FLOOR |
| Unacknowledged future sequence | UNKNOWN / CHECKPOINT_NOT_AT_VERIFIER_FLOOR |
| Absent/malformed anchor or pin, wrong artifact or byte length | UNKNOWN |
| Attacker owns content **and** signing key **and** anchor | Can pass local pin match; still custody_independence=NOT_ESTABLISHED |
| File modified immediately after a successful check | Previous match is not continuing immutability; a new check rejects |
| W43-style two-native-read POSIX mmap ABA | UNKNOWN despite any transient W38 image |
| Windows writable mmap preexisting at read | Refused read or mismatched digest, not false byte admission |

Local Linux CPython 3.13.5 scratch prototype with a reconstructed W38-equivalent reader: **16 passed / 1 Windows-only skipped**. This is **not** execution against GitHub's exact source tree. Exact-source Linux, Windows, and advisory Python 3.14 CI results must be verified at the final PR head.

## What this cannot prove

- A real external custodian, independent administrative domain, key non-extractability, a durable external floor, crash/rollback resistance, or witness signature provenance.
- Historical event truth, signing time, time freshness, original event order, cross-artifact binding, real evidence admission or signer authorization.
- Filesystem-wide atomicity or ongoing immutability; the underlying file can change after validation.
- Identity of an OS file with the same bytes, beyond the artifact_id that the verifier's floor claims to bind.
- Anything about independent custody if an adversary can replace **both** the verifier public key and the retained checkpoint/floor.

**Next independent-custody phase:** experimentally move an append-only checkpoint and a separate (sequence, head) floor into a truly separate administrative authority, check trusted public-key enrollment, crashes, deletion, rollback, stale responses, key rotations and equivocation. Synthetic-only until independently authorized; do not publish original Ario data or activate trust.

**At authoring: W44_RESEARCH_PROBE / INDEPENDENCE_NOT_ESTABLISHED / DRAFT_HOLD.**

## Candidate **real** external anchoring for a later, separately authorized phase

These are not deployed in W44 and do **not** supply a live independent Ario witness:

1. **OpenTimestamps** (https://opentimestamps.org/): can commit a digest using public calendar servers and eventually Bitcoin-backed attestations verified against the chain. An inclusion/timestamp proof can support a past existence claim *after confirmation*; a timestamp alone does **not** identify the newest valid (sequence, head), and the verifier still needs a retained floor, verified attestation and checkpoint identifier. Temporary/unconfirmed calendar receipts are not blockchain confirmation.
2. **Sigstore Rekor / verifiable transparency** (https://docs.sigstore.dev/logging/overview/; https://github.com/sigstore/architecture-docs/blob/main/rekor-spec.md): log inclusion, signed checkpoints and consistency monitoring can provide externally observable tamper-evidence for supported registered artifacts. The verifier must verify inclusion and required consistency under independently distributed log keys. A self-submitted hash or unsigned assertion of inclusion is not enough; service admission requirements and public exposure must be examined before use.
3. **Merkle-log verification principles** from RFC 9162 (https://www.rfc-editor.org/rfc/rfc9162.html): inclusion and consistency are different claims, and neither alone establishes truthful event content or that the verifier was shown the globally latest head.

The next practical experiment requires a **genuine separately administered service and a verifier floor not controlled by the original log writer**, with a proof that can be independently validated and retained across process restarts. Do not publish real Ario material, generate permanent trust keys, or treat a mere public-hosting account as an independent witness without a separate authorization and threat model.
