# R9-A — real-process atomic *local* action fence (research only)

**Date:** 2026-11-15  
**State:** `DRAFT / RESEARCH_ONLY / NO_MERGE / NO_ACTIVATION`  
**Source:** [R8 independent reproducibility, PR #185](https://github.com/SepehrGhanbari/Ario/pull/185#issuecomment-6896417546); R9-DESIGN-v0.1 (local prototype).  
**Security claim:** **LOCAL_SERIALIZATION_ONLY**. There is no independently administered witness, external side-effect adapter, authenticated search index, cryptographic trust authority or production key.

## Scope and evidence boundary

This standalone standard-library-only prototype uses **multiple real processes**:

- A checkpoint keeper **server process** accepts bounded, HMAC-authenticated requests over a POSIX `AF_UNIX` socket, with one SQLite checkpoint history and nonce replay detection.
- A coordinator **epoch process** changes the checkpoint via a compare-and-swap (CAS), then changes the local sink epoch within the same local SQLite write transaction. Crash injection (`os._exit(77)`) between the two writes intentionally leaves a mismatch and `HOLD`.
- Concurrent **action processes** check both heads while each holds a SQLite `BEGIN IMMEDIATE` lock. The epoch head, local view-only effect, unique `op_id` and receipt are serialized inside **one local database transaction**. Replaying an old receipt is not authorization.

The HMAC key is generated afresh in a disposable `0600` test file. It demonstrates protocol message verification *only*. The same test operator controls the key, sink, checkpoint, processes, labels and publication: **it is not a separate root of trust or an independent custodian**. A direct authenticated checkpoint CAS not coordinated through the sink can still cause a TOCTOU false affirmative; this negative is deliberately tested.

**The only effect in this lab is inserting a row into its disposable `effects` SQLite table** with `RESEARCH_VIEW` and scope `disposable:research-view`. There are **no external APIs, secret keys, evidence admission operations, irreversible actions, network TCP, model calls or real Ario runtime adapters**. Even for this local row, exactly-once is only supported within the assumed cooperative sink boundary; crashes and compromised database owners can break stronger claims.

## Threat-model outcomes

| ID | Adversarial or normal observation | Scope-limited expectation |
|---|---|---|
| T01 | Valid epoch and disposable local action | `APPLIED` once |
| T02 | Retry identical `op_id` | `DUPLICATE_NO_NEW_EFFECT` |
| T03 | Reuse ID with different payload | `HOLD` |
| T04 | Epoch E1 action after coordinated E2 | `HOLD_STALE` |
| T05 | E1 → E2 → E3 with same original corpus bytes | E1 rejected |
| T06 | Checkpoint server unavailable | `HOLD`, no effect |
| T07 | **Real process exit** after remote CAS, before local commit | Local E1 / checkpoint E2 → `HOLD` |
| T08 | Restore only sink DB to previous valid state | Mismatch → `HOLD` |
| T09 | Restore both DBs under one admin | **`NEGATIVE_CAPABILITY`: old E1 accepted** |
| T10 | Try `EVIDENCE_ADMISSION` or external scope | `HOLD_NO_AUTHORITY` |
| T11 | Wrong epoch digest | `HOLD_STALE` |
| T12 | Eight distinct OS processes race same action ID | Exactly one local row |
| T13 | Action and coordinated epoch transition race | Serializable local order |
| T14 | Wrong HMAC key | `HOLD` |
| T15 | Replay an identical authenticated request nonce | `HOLD` |
| T16 | Invalid type/shape, including Python Boolean as sequence | `HOLD` |
| T17 | Direct externally authenticated CAS **between local head check and effect insert** | **`NEGATIVE_CAPABILITY`: stale local effect can still commit** |

**Important:** A test that *successfully demonstrates an attack* is a successful test outcome but a **negative security result**. Passing T09 or T17 must never be presented as strong rollback resistance or global atomicity. All test labels and fixtures were designed by the same author; they are not independent, blinded evidence.

## Reproduce

From this directory, on an isolated Linux or other POSIX test environment with Python 3.10+ and AF_UNIX support:

```sh
python3 -B -m unittest -v test_r9a_atomic_fence.py
```

Each test creates its own disposable directory, generates a fresh ephemeral key, starts a real independent PID for the checkpoint server and launches actual Python subprocesses for the coordinator/action. T12 uses eight separate action processes. The runner refuses to run AF_UNIX assertions on unsupported platforms. Tests **must not** point to existing Ario ledgers, GitHub worktrees, production databases or credential files.

To identify the exact tested bytes, record Python version, OS, the Git commit, individual SHA-256 file digests and full raw test output. No test status is promoted to an implementation guarantee merely because CI reports green.

## Independence/TOCTOU limitations and R9-B decision gate

The sink `BEGIN IMMEDIATE` and receipt uniqueness make the **local** epoch/effect transition serializable against other *cooperating local sink transactions*. A standalone checkpoint CAS outside that lock is not in the same atomic transaction. T17 is the intentional counterexample. A remote verification call followed by an irreversible network request **cannot** be made atomically correct by adding another check just before the request.

Before any R9-B proposal could be accepted:

1. Define precisely which role may advance the epoch and how an external witness can reject or serialize unauthorized/out-of-band advances; pre-register a concurrent race with independent control of the witness.
2. Put at least one checkpoint log under a genuinely distinct administrator and rollback/failure domain with pinned independent identity and verified authenticated history extension. Two databases, processes, UIDs, or two machines belonging to one administrator are **not proof** of that property.
3. Perform actual rollback, fork, withheld-response, conflicting-head and key-rotation experiments with independently retained previous-head commitments. Count both false affirmative and unnecessary `HOLD` outcomes.
4. For externally visible actions, require provider-supported conditional commit, idempotency/reconciliation or a **visible** `HOLD_UNCERTAIN` result until provider-confirmed outcome. A server receipt alone never upgrades `CANDIDATES_ONLY` to admitted evidence.
5. Retain all adverse results and source hashes append-only. A Git commit under the same project administrator is version history, **not** external, censorship-resistant custody.

**Non-goals:** production merge, replacing #185, changing #133/#151, enabling a signer/trust key, automatic publication, independent witness authority or claiming that XERJ searched the intended corpus.
