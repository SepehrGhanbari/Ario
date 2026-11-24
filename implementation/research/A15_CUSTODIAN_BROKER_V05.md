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

## v0.5.2 provisioning/recovery addendum (CUST-08-R3, same Draft PR #346)

On top of the confirmed G-RED1/G-RED2 fixes at HEAD 4b96de82fac3995037a5ee9a2b81b9182386d6cd. Post-Grok handoff (2026-11-24) asked for explicit local provisioning and recovery separation covering exactly the three residual REDs Grok exercised on #346: (1) unlink vs first boot, (2) well-formed empty DB replacement, (3) valid-prefix restore. Implemented as a bounded research patch on the same Draft branch: commit 72cdb6b635f3e03ffec289ce6054f7df5e7e39aa (broker + tests + lab) and 5401717a588fb177ac29248dce506bb43a1a58a8 (lab self-review fix).

**Design: the locally retained expected floor.** A scoped sidecar file, `custodian.floor.json` in the state directory (format `a15-custodian-floor-v1`, JSON with exact keys `format`, `ledger`, `expected_seq` (int >= 0, not bool), `expected_hash` (64 lowercase hex, or the literal GENESIS at seq 0), bound to the ledger base name). Written atomically (tmp + flush + fsync + os.replace) at explicit provisioning (`expected_seq=0, expected_hash=GENESIS`) and refreshed after each durable commit, best effort: a lost floor write is a documented crash window, and the next open reconciles a DB-ahead floor forward to the verified chain head. The floor is a local guard under the SAME administrator; it is explicitly NOT an authenticated independent custody witness and no response or document in this step claims independent custody.

**Explicit separation in `Journal`:**

- Recovery mode (default `Journal(state_dir)`, and `serve` without flags): never bootstraps. A missing ledger fails closed (HOLD). Never re-provisions: `provision=True` is additionally refused while any ledger file or retained floor exists.
- Explicit provisioning (`Journal(state_dir, provision=True)` / `serve --provision`): allowed only when neither a ledger nor a retained floor exists; refused over any existing file ("deleting it is an explicit operator decision"). A legitimate empty first boot is operator-authorized, not implicit.
- Recovery verification order: G-RED1 byte-level preflight (unchanged) -> events schema check (unchanged) -> full `PRAGMA integrity_check` + hash-chain `verify()` (unchanged) -> floor reconciliation. The floor never weakens an existing check.
- Fail closed when the retained floor survives: (a) ledger missing; (b) well-formed zero-row replacement (ledger head behind floor); (c) valid-prefix rollback (head behind floor); (d) the floor-row hash diverges from the retained `expected_hash` (an extended replacement chain cannot ride a stale floor).
- Deliberate HOLD when the expectation is missing/ambiguous: no floor file, unparseable, wrong format tag, wrong ledger name, wrong key set, or bad hash shape -> ValueError, no implicit adoption, never a new chain. Recovery behaviour is documented rather than silently resetting history.
- G-RED2 receipt semantics unchanged: `event_hash` vs `chain_head_seq/chain_head_hash` separation kept; legacy `head_hash` keeps its original-receipt meaning; `execution_authorized=false`, `origin_attested=false`, `independent_custody=NOT_ESTABLISHED` everywhere.

**Preserved RED (deliberately unsolved):** the same administrator rolling back the ledger AND the floor together remains locally undetectable; a local marker, flag, or CLI argument is not an authenticated independent witness. Superseded test `test_host_admin_valid_prefix_rollback_remains_undetectable_RED` (DB-only rollback) is replaced by `test_r3_joint_rollback_of_ledger_and_floor_remains_undetectable_RED` (joint rollback stays RED; DB-only rollback is now detected and covered by `test_r3_db_only_prefix_rollback_fails_closed_with_retained_floor`). Closing joint rollback requires a separately administered external (seq, hash) authority: acceptance gate #2 stays HOLD.

**Tests (16 core; all 15 prior tests preserved with intent, first-boot openings switched to explicit provisioning):** new controls `test_r3_db_only_prefix_rollback_fails_closed_with_retained_floor`, `test_r3_wellformed_empty_replacement_fails_closed`, `test_r3_missing_ledger_fails_closed_and_provision_refused_while_floor_kept`, `test_r3_missing_or_ambiguous_floor_holds_instead_of_new_chain`, `test_r3_stale_floor_after_commit_crash_recovers_to_durable_head` (positive crash window: durable commit, lost floor write, forward reconciliation to the verified head), `test_r3_joint_rollback_of_ledger_and_floor_remains_undetectable_RED`. Crash-injection harness explicitly provisions; interruption around initialization (provision crash before the first floor write) yields an empty ledger without a floor, which HOLDS on reopen by construction.

**Linux lab:** first start is an explicit `--provision`, every restart is recovery mode, and a new end-of-lab control asserts `EXPLICIT_PROVISION_REFUSED_ON_EXISTING_LEDGER=PASS` (`serve --provision` over the live ledger must exit nonzero without binding), alongside the existing crash/lost-reply/peer-UID/kernel-ACL controls.

**Not claimed:** S9 solved, independent custody, external witness, Windows authenticated IPC, F1/F2 fixes (still deferred secondary tasks). No merge, no rewrite of historical source, no trust activation.
