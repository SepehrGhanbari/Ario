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

## 2026-11-21 — recovery and re-use of existing public witness work (not a new witness)

The previous generic candidates above are **not the first Ario experiments**. We inspected earlier source and original evidence to avoid duplicate work:

| Existing track | Actually previously observed | Still missing for W44 |
|---|---|---|
| W18/W19: [PR #242](https://github.com/SepehrGhanbari/Ario/pull/242), fixed archive head `33f193cdb68efdd7deff35b65db8c360378f87b5` | Real **public synthetic research manifest** accepted by official Sigsum v0.14.1 under two strict cross-operator policies (Glasklar+Google / Remora+Google). Negative tests remove required signatures or substitute a public key. | This witness proof binds the **old W18 research manifest**, NOT W44's current read bytes or a latest identity-scoped Ario ledger checkpoint. Valid inclusion does NOT convey a monotonic latest floor. |
| R08, [Issue #280 seq1](https://github.com/SepehrGhanbari/Ario/issues/280#issuecomment-7017044165) and [seq2](https://github.com/SepehrGhanbari/Ario/issues/280#issuecomment-7017059359) | Two real receipts under Sigsum *test* log policy 2/3, archived with source/proof SHA-256 and synthetic test public key. | Development test log is not Ario's real witness; a quorum count by itself doesn't establish mutually independent operators. |
| R04/R05, [PR #285](https://github.com/SepehrGhanbari/Ario/pull/285) and [Issue #280](https://github.com/SepehrGhanbari/Ario/issues/280#issuecomment-7010553337) | Actual pending OTS receipt upgraded for prior public synthetic bytes; Bitcoin-block header paths were correlated against public sources. | Independently synchronized Bitcoin Core proof and latest Ario sequence/floor still absent; a historical timestamp is not freshness or history completeness. |
| W31–W34, [Issue #293](https://github.com/SepehrGhanbari/Ario/issues/293) | Two previously posted OTS receipts, public block-header corroboration and 40/40 per OS simulated RPC tests. | **No real synchronized local Bitcoin Core was executed**. No new node installation/cloud expenditure was performed. |
| F15, [Issue #205 comment](https://github.com/SepehrGhanbari/Ario/issues/205#issuecomment-7023070284) | A third-party witness's cosignature on a Rekor **tree-head checkpoint** verified cryptographically for synthetic research. | Does not yield independently retained latest `(scope, seq, head)` for Ario; cannot be promoted into signer or memory authority. |
| R10, [PR #304](https://github.com/SepehrGhanbari/Ario/pull/304) exact source `fae07e8e3453d946a2e7928d2e67de0e8663cdd5` | SQLite/JSON durable lab with explicit crash testing; retained floor detects publisher-only rollback; **joint DB+floor rollback was not detected**. | A genuinely separate administrator must retain a non-rollbackable floor that the log publisher cannot rewrite. |
| W43/W44, [PR #311](https://github.com/SepehrGhanbari/Ario/pull/311) and this PR | W43 native Linux mmap ABA weakness and W44 conditional SHA-256/Ed25519 byte binding with synthetic keys. | A real independently authenticated W44 *subject-specific* external checkpoint is absent. |

### Exact source-pinned offline replays incorporated into W44 CI

Instead of re-uploading old proofs or submitting new data, the W44 workflow includes two new **read-only replay** jobs:

- The W19 job checks out the exact old Git commit `33f193c...`, installs the official `sigsum-verify@v0.14.1` into a disposable CI environment and runs the archived strict-policy verification script against the **already-published** W18 signed proof. The script verifies pre-pinned manifest/proof hashes and rejects removal of required cosignatures and a forged witness key. No `sigsum-submit`, registration, public POST, key generation, or new witness enrollment.
- The R10 job checks out the exact old Git commit `fae07e8...` and reruns the **original** 16 synthetic durable monitor tests, including the intentionally positive test proving the **negative security outcome** of joint same-administrator rollback. It does not treat 16 passed as anti-rollback security success.

[Initial prior W19 replay 44946851911](https://github.com/SepehrGhanbari/Ario/actions/runs/44946851911) observed both strict policies PASS and the documented weakness of the original test quorum; [W44 replay run 44946874266](https://github.com/SepehrGhanbari/Ario/actions/runs/44946874266) runs both source-pinned replays at the same PR head.

**Integration conclusion:** confirmed old external transparency proof + confirmed local W44 byte binding **cannot be composed into a real Ario custody guarantee** without a signed external record **of the actual same W44 subject and digest**, separately pinned verifier keys, a distinct-administrator monotonic floor that survives rollback, and a validated freshness/consistency rule. A proof for a *different file* must never be silently substituted. `RESEARCH_ONLY / DRAFT_HOLD / NO_MERGE / NO_REAL_KEYS / GENESIS/TRUST/PRODUCTION=NO_GO` remains unchanged.
