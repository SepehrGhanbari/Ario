# R63 G4/G5 — Peer-SID Sandbox and independent latest-floor custody gate

**2026-11-21 · RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / GENESIS=NO_GO / TRUST_ACTIVATION=NO_GO / PRODUCTION=NO_GO**

## 1. Why the two next gates are separate

**G4:** A server observes the actual OS peer token on a named-pipe connection, rejects self-reported SID spoofing, then uses a valid synthetic frozen V9-style V1/V2 journal. The earlier [G4 native Windows CI](https://github.com/SepehrGhanbari/Ario/actions/runs/44939990366) passed. The original G3 TCP receiver did not provide this guarantee. The founder's **G4 fresh Windows Sandbox run still has not been supplied**. A new guest-only package and native Windows PowerShell 5.1 compatibility CI were prepared; their results are separate from the earlier CI.

**G5:** A publisher can rewind a self-consistent V1+V2 pair, and can delete the local uncertainty flag. A separate verification domain must retain **at least** the last accepted `(epoch,seq,head,receipt_digest)` without granting the publisher reset/delete access. Signed attestations and independent nonrollback/consistency checks must accompany each accepted transition.

## 2. New G4 founder Sandbox source and evidence contract

New branch `research/r63-g4-guest-external-floor-20261121` adds:
- `research/r63_g4_peer_ci/Invoke-G4PeerIdentityGuest.ps1` — **CI/Guest mode only**. Requires elevated Windows GH ephemeral CI or `WDAGUtilityAccount` inside a fresh Sandbox, checks exact SHA256 of original frozen V9 sidecar, uses only 3 new synthetic local nonadmin accounts + one disposable `C:\Users\Public\ArioR63G4_...` test directory, with writer journal Modify, readers Read & Execute, SYSTEM/Administrators Full Control. Does not run the real V9 signer or use production policies.
- `pack_g4_evidence.py` + `audit_g4_evidence.py` — archive raw `v1.jsonl`, `v2.jsonl`, the server-side observed peer-SID log and a source-fingerprinted report before deleting ephemeral test state. Reconstruct all three V2 events and verify raw v1/v2 and report agreement independently. Neither archive nor reported SID events establishes external administrative independence.
- `test_audit_g4_evidence.py` — **8** offline positive and tamper-negative controls: valid case, broken checksum, forged authenticated response, wrong SID, incomplete archive, invalid server logs and altered chain.

Private chat-only Windows Sandbox package prepared, not posted publicly, because its WSB includes machine-specific host folder paths. It must be launched manually in a **new** Sandbox; no autorun, no networking, no clipboard, no vGPU, source and Python read-only, evidence export only into existing Documents export directory.

**Do not call this G4 guest accepted merely because the earlier Actions run was green.** Acceptance needs exact guest zip/report/log plus independent raw-byte audit and verified cleanup.

## 3. G5 signed monotonic floor — evidence and explicit limitation

`research/r63_g5_floor_custody_ci/custodian_floor_demo.py` and `test_custodian_floor_demo.py`: **Ed25519** independent *test-key* signing and SQLite monotonic compare-and-swap in a synthetic “remote” custodian. Receipts cover `domain,epoch,seq,head,previous_receipt`, signed with the custodian test key, and chain to the previous receipt. A pinned test public key verifies them; stale/fork/gapped proposals fail; missing remote state, tampered signatures, old receipts or local chain rollback fail closed. It uses exact frozen V9 V2 source SHA256 `c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd`, never a live actor key.

Fourteen unit tests include a deliberate **counterexample**: if the same administrator can replace both remote storage and the verifier's trusted public-key pin, forged historical state can pass. This is not an external witness. CI Windows checkout requires LF-preserved frozen source; no relaxation of SHA pin.

**Crucial scope:** SQLite in the test process is NOT a remote machine; all credentials and files are under a common test administrator. Ed25519 validity only proves the signature relative to the supplied public key. `INDEPENDENT_LATEST_FLOOR=NOT_ESTABLISHED`.

## 4. Independent custody decision: Sigstore Rekor vs actual authoritative floor

As of **2026-11-16**, Sigstore's public instance narrowed accepted entry types and recommends `hashedrekord` or Rekor v2 for new integrations: https://blog.sigstore.dev/rekor-public-instance-hardening/

Rekor is a **genuinely externally administered transparency log**, capable of providing independently checkable inclusion/consistency evidence for published *synthetic* checkpoints; the Ario publisher does not administer Sigstore. However, Rekor's official architecture explicitly says transparency logs **witness events rather than store the business's authoritative latest state**. Its search index is not a cryptographic guarantee of complete query results. Even an included, independently signed record proves **that this checkpoint appeared**, not that there is no newer approved checkpoint. Official specification: https://github.com/sigstore/architecture-docs/blob/main/rekor-spec.md

Therefore:
- A verified **Rekor inclusion + signed log checkpoint** may support `EXTERNAL_HISTORICAL_COMMITMENT`, **never by itself** `INDEPENDENT_LATEST_FLOOR`.
- An acceptance-grade **custodian** MUST be managed by a party/domain whose administrative credentials the publisher/claimant cannot reset, with immutable log and monotonic CAS, its own signing key not accessible by the publisher, a publisher-bounded API that cannot lower accepted floors, and read-only verifier retrieval.
- A verifier MUST pin the custodian's independently provisioned public key and a minimum accepted floor **outside publisher control**, compare signed `epoch,seq,head,previous_receipt` to the on-disk V2 prefix, require nonstale authoritative last head and independent receipt, and HOLD on network loss, equivocation, age failure, digest mismatch, fork or missing predecessor. It must not trust a floor supplied by the same claimant.
- Test both local attacker rollback (can delete V1/V2/flag) **and** independent operator boundary. Windows separate user-SIDs on a machine whose local administrator can reset both is not the latter.
- Do not use real Ario signer, real credentials, laptop TPM/keys, Genesis, production or Rulesets in these tests.

**No external latest-state custodian has been provisioned or activated. No public Rekor upload made for this phase.** Any actual Sigstore upload should use only disposable synthetic data and a test key, preserve signed inclusion/checkpoint evidence, and require a separate latest-floor mechanism before acceptance. A truly independent custodian requires provisioned credentials and authority **not available to this chat or the repo**.

## 5. Next acceptance tests

1. Green native WinPS5.1 G4 guest-controller CI (not merely the old pwsh7 run), source pinned and independent raw evidence audit;
2. Founder guest ZIP/report and raw SID trace audit; keep old G3/G4 failures intact;
3. Select a real separate custodian operator, prove its independence by rights/SID/account/credential evidence, publish a **synthetic** signed checkpoint, verify original signed receipt and actual external inclusion (and fresh signer pin);
4. Verify remote retained max floor across independent guest restart and deliberately rewind or delete all local V1/V2/flag, plus auth-loss, refusal, fork, replay, stale head, and operator rollback;
5. Only after G1–G5 positive and negative controls consider native V9 synthetic signer integration. **No automatic trust activation.**

**Verdicts:** `G4_OLD_WINDOWS_CI=PASS`; `G4_FOUNDER_GUEST=NOT_EXECUTED`; `G5_SIMULATED_SIGNED_FLOOR=UNIT_TESTED`; `G5_REAL_ADMIN_INDEPENDENCE=NOT_ESTABLISHED`; `REKOR_EXTERNAL_LATEST=NOT_ESTABLISHED`; `NATIVE_V9_SIGNER=NOT_EXECUTED`; `PRODUCTION=NO_GO`.
