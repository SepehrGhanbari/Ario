# A15 v0.5 — experimental Custodian broker and combined branch research tree

**Disposition: RESEARCH_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_MERGE / NO_TRUST_ACTIVATION / NO_PRODUCTION.**

## Source provenance and branch relationship

This *new*, additive research branch is created from PR #338's exact head at the time of branching:
`9a12f5ee872a210cee22f492f754e986da26fdbb` (v0.4 OS-principal feasibility work).
The divergent #334 head is `91e2bb45f9cc19d57465bab3414ed210286688c4`. To build an executable **combined working tree**, this branch copies the exact blob content of #334's new evidence-generator file, Claude delta test file, and updated v0.3 CI workflow. The commits are **not cherry-picked**, and #334 is not merged or rebased. This is a source-tree compatibility lab, not reconciled Git ancestry. Both parents remain Draft/HOLD.

## Experimental scope

- Python 3.12 standard library only; no network provider, real key, signer, external write, deployment or production action.
- Linux-only Unix-domain-socket broker, running under a disposable **Custodian UID distinct from the Gate UID**. The Custodian-owned installation directory is not Gate-writable; private SQLite ledger is directory mode 0700, owned by Custodian; socket belongs to Custodian with restrictive group access; the server checks the connecting peer UID using Linux SO_PEERCRED before reading a request. Linux root/CI coordinator provisions accounts; Gate is unprivileged. Only Custodian runs the broker and writes its ledger.
- Request schema is a single bounded (at most 4096-byte) line containing exactly `v=1, run_id, attempt_id, choice_json, claimed_status`. Strict JSON duplicate-key and size rejection. No arbitrary code/text-command dispatch; no actions.
- Custodian **independently recomputes** a strict, canonical ASCII subset of the frozen `a15_procedural_choice_v0_1.js` decision policy from original `choice_json`; does not trust claimed ACCEPT/DECLINE, reason, PID or child hashes. Tests cover selected rule equivalences; full language equivalence across every possible input has *not* been established.
- For a caller-declared ACCEPT that is permitted under the procedural policy, the broker records `INERT_RECORDED_UNATTESTED_ORIGIN`: it still has `origin_attested=false`, `execution_authorized=false`, `provider_receipt=UNKNOWN`, `causal_sender=UNKNOWN`, `independent_custody=NOT_ESTABLISHED`. A claimed verdict mismatch is labelled `EVIDENCE_CONFLICT_GATE_CLAIM`. No action or trusted evidence is promoted.
- A Custodian-owned SQLite journal (`journal_mode=DELETE`, `synchronous=FULL`) uses `BEGIN IMMEDIATE` and a unique `run_id|attempt_id` key with monotonic sequence and chained SHA-256 checks. A repeated identical request retrieves a **local-only previous receipt** without appending a new event; conflicting reuse is rejected. Full chain and SQLite integrity are checked at startup. This is local crash durability, not independent historical custody.
- Synthetic crash injection at `BEFORE_COMMIT` rolls back the in-flight transaction; `AFTER_COMMIT_BEFORE_REPLY` simulates a lost response after a durable commit, and retry returns the same event. Tests include concurrent duplicate requests, restart, tampering, corruption and truncation.
- **Unresolved RED:** replacing the SQLite DB with a valid *earlier copy* under common administrator control is not detected by local hashes; the old high-water head is gone. External rollback resistance requires a separately retained, monotonic checkpoint under independently administered control.

## Executable verification

- `python -m unittest discover -s implementation/tests -p test_a15_custodian_broker_v0_5.py -v`: deterministic cross-platform policy, replay, crash, corruption, and **expected RED rollback** tests. A passing RED-reproduction test means the weakness is observable.
- `sudo -n bash implementation/research/a15_v05_linux_separated_broker_lab.sh`: Linux end-to-end disposable accounts, Gate-to-Custodian socket, SO_PEERCRED peer check, kernel filesystem denial, durable ledger, crash-before/after commit, replay/lost reply and duplicate concurrency. It must not reuse pre-existing accounts, and cleans only accounts it created.
- `.github/workflows/a15-v05-custodian-combined.yml`: on Ubuntu and Windows, rerun all frozen G0/G1 (56), historical v0.2 (22), original v0.3 (21), unique Claude delta tests (5), S9 exploit RED control (1), and v0.4 durability/origin RED controls (2): **107 JavaScript tests per OS when green**. It also runs the Python ledger core tests on each OS, and runs the real local Linux two-UID broker/probe job on Ubuntu.
- Historical #338 Linux and Windows OS-principal ACL tests are a separate baseline. The **new** v0.5 Windows named-pipe IPC, token-based client identification, service SID/SCM installation, ACL and end-to-end broker flow are **NOT IMPLEMENTED**; a Python ledger core pass on Windows is not an authenticated Windows broker integration.

## Acceptance gates still on HOLD

1. Integrate and independently review a Windows service-boundary broker + named-pipe peer-token verification, including Gate denial of process termination, service configuration changes and ledger mutation.
2. Add a separately administered custodian/checkpoint whose floor/head cannot be rolled back by the same founder/host administrator.
3. Bind user origin, preference, authorization and renewal to externally inspectable evidence; a self-declared envelope or unkeyed hash never authenticates intent.
4. Test full implementation concurrency (multiple broker **instances**, rather than only simultaneous clients on one server), power-loss semantics across storage hardware, disk-full/partial writes, secret/capability scope, and emergency fail-closed recovery.
5. Obtain independent threat-model/security review and a separately observed operational trace before any production consideration.

**No results in this file claim S9 solved, independent custody achieved, user intent proven, trusted evidence admitted, or trust/signer/production activated.**

## v0.5.1 journal-safety addendum (CUST-08 G-RED1/G-RED2 patch, Draft PR #346, HEAD a5f5e8652542beb54caa9a97ff0ea6da5168af5c)

- G-RED1: an existing custodian.sqlite3 that is smaller than a SQLite container header (100 bytes, magic bytes "SQLite format 3" + NUL), is not a SQLite database, or lacks the events schema now fails closed on reopen; it is never silently re-initialized into a fresh GENESIS ledger. A missing file remains the explicit-first-boot case. Local hashes still cannot prove authentic history: valid-prefix rollback of a well-formed ledger stays undetectable here and requires the external retained (seq, hash) checkpoint (residual RED, honestly preserved).
- G-RED2: replay receipts now return event_hash (hash of the replayed historical event; head_hash keeps this original-receipt meaning for idempotent retries) together with point-in-time chain_head_seq / chain_head_hash read inside the same serialized transaction; the chain tip may advance after the read (no lease). Fresh-commit responses include the same chain-head fields. The chained-hash core and verify() are unchanged.
- Added additive regression tests: test_gred1_zero_and_one_byte_ledger_fail_closed_no_rebirth, test_gred1_first_boot_provisioning_stays_allowed, test_gred2_replay_separates_event_from_chain_head. All 12 existing core tests, preserved REDs and the Linux two-UID lab are untouched; execution_authorized stays false and origin_attested stays false everywhere.
- Cross-enrollment dedup namespace (Vibe F1) and group-writable socket-parent mode guard (Vibe F2) are deliberately NOT patched in this bounded step (handoff ordering: secondary, after the two REDs).
