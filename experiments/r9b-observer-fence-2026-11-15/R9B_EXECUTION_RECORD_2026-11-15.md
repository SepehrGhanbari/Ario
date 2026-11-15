# R9-B execution record — 2026-11-15

**Result classification:** `SOURCE_REPLAYABLE_DEVELOPMENT_CONTROLS / 19_EXPECTED_OUTCOMES / 1_NEGATIVE_CAPABILITY / NO_INDEPENDENT_CUSTODY / DRAFT_HOLD`.

## Frozen execution scope

- Local POSIX/Linux container, `Python 3.13.5`, standard library only; no network TCP, cloud services, production credentials, signer, real Ario ledger, external provider, or real action sink.
- Standalone executable: `r9b_fenced_sink.py`; actual child process for the observer; real subprocess for each CLI action/epoch operation. Each test creates a fresh `TemporaryDirectory`, scratch SQLite databases and a new `0600` 32-byte HMAC key. This suite did **not** use independent operating-system administrations; all resources were controlled by the executing user/container administrator.
- Full command: `python3 -B -m unittest -v test_r9b_fenced_sink.py`, exact stdout/stderr in the local `full_19_run.log` (retained in the downloadable ZIP, not Git-tracked). **19 tests, 81.181 seconds, return code 0.**
- Additional focused stress: five fresh invocations of `test_14_action_epoch_race_serialized_at_observer` each returned `OK`; exact output in local `race_stress.log` (in downloadable ZIP). A first attempt of the shorter suite was terminated by the tool's 90-second envelope partway through test 08; it is a *harness-timeout*, NOT a successful run, and the raw `test_run_01.log` was retained.
- The T18 interleaving is forced at the client-call boundary using the real running observer process and a separately authorized CAS operation. It demonstrates deterministic ordering in the protocol, **not** a separate-host or byzantine test.

## Tests and observations

| ID | Result | Evidence-limited interpretation |
|---|---|---|
| B01 | PASS | One local `RESEARCH_VIEW` effect committed at current epoch |
| B02 | PASS | Same operation ID does not append a second local row |
| B03 | PASS | Same ID with different payload rejected |
| B04 | PASS | Privileged CAS before reserve makes old local head stale; hold/no effect |
| B05 | PASS | Persistent reservation after process kill prevents direct privileged epoch CAS |
| B06 | PASS | Outstanding reservation blocks unrelated actions and epoch changes |
| B07 | PASS / UNCERTAIN | Process death after local commit, before observer FINALIZE: local row exists and no finished receipt is claimed; pending requires reconciliation |
| B08 | PASS / HOLD | Process death between observer CAS and local epoch commit: mismatch blocks effect |
| B09 | PASS | Stale epoch after coordinated advancement refused |
| B10 | PASS | ABA/older ticket refused despite repeating corpus name |
| B11 | PASS / HOLD | Observer unavailable refuses to add effect |
| B12 | PASS / HOLD | Restoring only local SQLite DB is detected as head mismatch |
| B13 | PASS | Eight real action clients compete; only one local row |
| B14 | PASS | Competing action and coordinated epoch advance serialized at observer interface; repeated five additional runs |
| B15 | PASS / HOLD | Wrong HMAC key fails observer authentication |
| B16 | PASS / HOLD | Unsupported evidence admission, external scope and boolean sequence refused |
| **B17** | **PASS AS A TEST; NEGATIVE_CAPABILITY AS SECURITY** | **Same administrator restores both SQLite DBs; old E1 looks valid again and an old ticket writes a new local effect. The security control FAILS against a privileged shared admin.** |
| B18 | PASS | Authorized epoch CAS *after HEAD and before RESERVE* causes stale reservation rejection; zero effect |
| B19 | PASS / HOLD | Reused authenticated request nonce rejected |

A passing expected-outcome test is not a statement that the capability was achieved. B17 is the explicitly preserved attack, not an exception to hide. B07 is an uncertain result, not verified exactly-once.

## Differences from R9-A and remaining failure surfaces

**R9-A T17:** R9-A read checkpoint HEAD under local SQLite lock but allowed a separate observer CAS before local effect write; it could apply an effect on stale epoch. R9-B gives the observer a durable `PREPARED` effect reservation, and puts both the observer epoch CAS and reservation under that observer's SQLite `BEGIN IMMEDIATE`. B05 and B18 exercise both orderings: when CAS wins first, reserve fails; when reserve wins, CAS fails. This **closes the tested RPC-level interleaving**, subject to observer availability and administrators not mutating the databases outside the protocol.

**Still unresolved by design:** a compromised/shared root can edit or roll back both databases and HMAC material. A crash after local insert but before FINALIZE yields a durable pending reservation; this is **not** externally atomic and can deadlock progress without independently justified reconciliation. All operational claims are limited to a local scratch SQLite row, not a real provider, evidence admission, money, network or irreversible act. No independent admin/witness tested.

**No production activation:** This artifact grants no trust or signer authority and cannot justify merging #185, #212, #133 or #151. Any future observer with genuinely separate administration must be independently audited, must support consistent identity/commit-history checks, and must run byzantine/rollback/withheld-response tests. To approach real external exactly-once, an actual destination must offer conditional commit or provable idempotency plus separately verified reconciliation. No such destination was connected.

## Source identity and auditability

Run-local SHA-256 (the exact GitHub Git blob hashes will be recorded on the PR after upload):

- `r9b_fenced_sink.py` → `1bf5297b8934c3b60a5cc8adc057bd89037d4247dd405d1158c3ff97693350b1`
- `test_r9b_fenced_sink.py` → `5646378cdbb42d90b6dee2311c9e9572ad78da34eaf08ed1f40fb110bdd61214`
- `README.md` → `029a4beb2c769267b47398a3582e74b8d67a6f29d03c733556c5bc8be3ab5fbd`

No raw test log has been included in the Git PR because its run environment labels are disposable; raw logs and a manifest are retained in the accompanying standalone ZIP. This markdown file itself is the issue-visible reproducibility summary, not an externally authenticated witness record.
