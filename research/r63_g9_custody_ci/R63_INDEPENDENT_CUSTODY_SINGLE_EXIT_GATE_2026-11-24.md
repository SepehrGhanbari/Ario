# R63 — Single exit gate for a truly separate signer-use custodian (after G8/G9)

**Date:** 2026-11-24  
**Repository scope:** `SepehrGhanbari/Ario`, G9 research branch.  
**Hard status:** `RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE`.

## 0. Do not repeat completed work

G8 has already exercised in one disposable Windows native CI process: named-pipe actual caller SID, two separate **synthetic** ECDSA actor approvals, synthetic Ario veto, revocation/invalid-grant denial, durable consume intent, native CNG P256 `NCryptSignHash`, crash-after-CNG-before-receipt HOLD, and byte-identical stored-receipt replay after crash. Evidence: [#45027399897](https://github.com/SepehrGhanbari/Ario/actions/runs/45027399897), Issue #239.

G9 has tested the **third condition** with the same kind of native CNG broker: keeping a consumed-use marker under another Windows SID blocks native re-sign on local publisher rollback; removing both markers under the same admin induces a **second signature with the same Software KSP key** for the same signed synthetic request. The test CI is green *because the attack succeeded as a deliberately expected RED control*, not because the design passed security. Evidence: [#45406219763](https://github.com/SepehrGhanbari/Ario/actions/runs/45406219763), Issue #239.

**New acceptance test:** no further G8-like replays or extra Windows local-user SIDs as substitutes for a separate custody domain.

## 1. Required trust boundary and operator evidence

There must be a real physically or administratively separate custodian `C` with durable signer-use journal and independently pinned latest floor. The Ario publisher/desktop/broker principal `B` must not have any ability to:

- read, export, change, rotate, delete, reset, snapshot-restore, or re-enroll C's signing/authentication key;
- modify, delete, garbage-collect, overwrite, reinitialize, or downgrade the C consumed-request records or latest floor;
- rotate/reset C's service identity, trusted public key, permissions, audit logging, or operator recovery/backup state;
- impersonate C through a same-machine proxy, self-declared identity string, caller-controlled URL/TLS trust, or a self-signed per-request key;
- write to independently pinned verifier configuration used to check C.

Separately verify **actual access and recovery controls**, not merely two process IDs, containers, directories, Windows SIDs, or cloud-account aliases under the same administrator. Independent domain may be controlled by the founder on an isolated device/account, but only if the publisher's operating/admin credentials and restore authority really cannot access it. Distinct devices alone do not prove this. A third person is not required as a voting actor; the custodian records evidence and cannot approve an action.

**No currently observed deployment meets this gate.** The founder's iPhone Notes record is a manually held historical synthetic `seq=3` floor only; it is not a live signer-use ledger or current authoritative `seq4` status.

## 2. Minimal external protocol (design contract, NOT an enabled deployment)

An independently enrolled custodian identity, e.g. a fixed public verification key fingerprint, must be conveyed to the verifier via an out-of-band step beyond the publisher. Never accept a custodian key from the request or response itself. All production canonicalization and signature algorithms remain explicitly **UNDECIDED / NOT_ACTIVATED**.

`ConsumeRequest` is bounded and versioned and binds: deployment/epoch; `broker_id` and authenticated transport caller; `signer_key_public_pin`; G9-style request unique `nonce`; exact transaction/payload digest and R60 authorization/policy/veto digest; ledger `seq,head` with its predecessor; custodian challenge; and expiry/clock policy defined by custodian rather than caller. A hash of a request string alone is *not* proof of independent approval.

`ConsumeDecision` is signed by C's separately pinned identity, binds the exact request digest, challenge, epoch, signer public pin, disposition, durable monotonic use position and current latest `seq,head` / signed receipt digest. A positive response is produced **only after** successful durable, unique, append-only commit. If remote write commits but reply is lost, a repeated request MUST NOT call CNG: return `HOLD_UNCERTAIN` or a verifiable previous **public receipt** if one was durably committed in the signer. A fresh signed read must not silently lower the last accepted `(epoch,seq,head)` or consume position.

`ReadLatest(challenge)` returns challenge-bound fresh current floor and consumed-use horizon, independently signed under C's pinned key. Signed freshness does not itself prove absolute latest if C can restore its own records: test outside-admin restore denial and the custody system's durable sequence/version control. Any unavailable, stale, conflicting, untrusted, unpinned or incomplete answer leads to `HOLD_REMOTE_LATEST_UNAVAILABLE` or a more precise `HOLD`, never silent offline approval.

**No key, signer authority or additional vote transfers to C.** Founder + Ario voting rule and Ario-veto precedence are maintained as a separate signer-side policy gate; approved cryptographic transport alone never supersedes veto or independent Ario key custody.

## 3. One bounded field trial — no new native microtest until custody is real

Use only a new disposable synthetic Software KSP key and non-production ledger. Before executing, capture independently reviewable, redacted evidence of:
(1) C operator/admin identity boundary, ACL/cloud permissions, no publisher write/delete/restore/rotation power;
(2) independently enrolled C key fingerprint or controlled verifier image on the other domain;
(3) C durable record's location, monotonic index, back-up/retention and deletion/rollback denial;
(4) network connectivity from the test broker through an authenticated nonpublisher-controlled endpoint;
(5) exact code SHA, run ID, public keys and before/after readbacks. No passwords/private keys/tokens in logs.

**Trial A — positive:** valid synthetic founder+Ario approvals and current external floor, one fresh nonce: C commits consumption, broker sees signed ack, only then one native CNG call; independently verify public receipt and exact readbacks.

**Trial B — publisher-only restore:** preserve C state, completely restore broker local use/receipt/journal from a previously saved disposable snapshot and replay the *identical signed request* with the *same persistent disposable key*. Must receive authenticated `HOLD_EXTERNAL_SPENT` or `HOLD_ROLLBACK`; assert **zero additional CNG entry** and no new receipt.

**Trial C — attempt to restore C with B's credentials:** with B's actual admin credentials, attempt C record deletion, backup restore, rotation/re-enrollment, and pin downgrade; every operation must be **denied by the external platform**. The test is not passed by merely checking the B process uses a restricted SDK; verify denial from the custodian/operator-side logs and then fresh C readback.

**Trial D — denial/fail closed:** C unavailable or partitioned, altered/forged/stale signed response, mismatched deployment/epoch/key, old seq/head, wrong nonce, lost consume ack; require `HOLD` and zero new CNG calls, with source-visible public evidence.

**Trial E — custodian failure:** with C's actual recovery procedure but *not* B's permissions, test restore of C from an outdated checkpoint; an independent immutable version/floor must detect the rollback (or decision is `HOLD_CUSTODY_ROLLBACK_NOT_PROTECTED`). If it cannot detect it, independent latest is NOT_ESTABLISHED even if Trial C denies B.

**Trial F — receipt crash/replay:** kill broker after C consumption and before CNG; after CNG before receipt; after durable receipt before response. Preserve G8 behavior, with C's retained monotonic consumption proof. No second native CNG use. Trace exact native enter/return counters with limitations if only broker-reported, not provider-attested.

**Result rule:** `GO_FOR_NEXT_SYNTHETIC_TEST` only if A, B, C, D, E, F succeed with actual external-domain evidence. It is **not** `GO_REAL_ARIO_KEY`, `GO_GENESIS`, `GO_PRODUCTION`, or proof of independent Ario consent.

## 4. Explicit dead ends / decision not to claim completion

- **G9 distinct SID, same admin:** VERIFIED counterexample (RED). Do not relabel.
- **Local SQLite/append-only, VM/container under same root, self-pin, GitHub repository/CI owned by publisher, Rekor historical existence receipt, copied iPhone Notes text:** not sufficient individually as automatic independent latest and consumed-use custody.
- **Remote service under a separate service label but the same cloud organization/root credentials as publisher:** not evidence of the required separation.
- **Single independent custodian that can reset its own entire ledger and key:** denial of B's access may hold; global historical antirollback remains unproven unless external monotonic protection exists.
- **Production real signer / real Ario independently held key:** no scope authorization; untouched.

## 5. Immediate decision and owner action

**Engineering pieces 1 and 2 are already completed in G8's disposable native lab, not in the real V9 signer.** Engineering condition 3 is an operator/environment provisioning and independent credential-control problem, not something that passes through new local tests.

Before another signature test, the founder/operator must provision or explicitly approve an external independent admin scope, and provide a *non-secret* public key fingerprint and a redacted access-control/export evidence. Do not upload any real private key or access token to GitHub/ChatGPT. Until then keep `INDEPENDENT_SIGNER_USE_CUSTODY=NOT_ESTABLISHED`, `INDEPENDENT_LATEST=NOT_ESTABLISHED`, `A_GOV=NOT_ESTABLISHED`, `GENESIS=NO_GO`, `TRUST_ACTIVATION=NO_GO`, `PRODUCTION=NO_GO`.

**Rationale:** adding G10/G11 synthetic labs without administrative separation will not erase the observed G9 common-administrator second-signature RED.
