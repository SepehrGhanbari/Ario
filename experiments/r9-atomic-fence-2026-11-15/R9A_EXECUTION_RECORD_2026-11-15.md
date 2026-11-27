# R9-A source-pinned execution record — 2026-11-15

**Test run class:** actual local Linux/POSIX subprocess and AF_UNIX checkpoint experiment; **NOT independently administered/attested**, not XERJ, not the real Ario M0 runtime, not production. This note does not modify R8 archives or PR #185 evidence.

## Exact new files and checksums

| Git path under `experiments/r9-atomic-fence-2026-11-15/` | SHA-256 source bytes |
|---|---|
| `r9a_atomic_fence.py` | `ed592d4ec62720bba97d0e600c0d43d64b1a4dc888c4f892f37c65f2aafbd1b0` |
| `test_r9a_atomic_fence.py` | `c382a17397331bf5a4ddd2204218ab86943bfd191a189186595cca6c92126054` |
| `README.md` | `79143c3a9b6a3837cb516f37beb9c39836100742e1b875f7277004b82c319dd8` |

Raw local execution transcript SHA-256: `c16a0eabf0e78cb5c75fe058a01365a91caf179c28db34715763ddf9369350c1`. The raw test log is included in the downloadable local R9-A artifact, **not** a third-party witness. No Git HEAD is recorded in this report until a GitHub commit actually exists.

## Environment and command

- Linux kernel: `6.18.57` (`x86_64`); Python `3.13.5`.
- `python -u -B -m unittest -v test_r9a_atomic_fence.py`
- Exit code: **0**; 17/17 author-defined test expectations met. **15 tests evaluate controlled/cooperative behavior, two tests deliberately reproduce a security weakness (T09, T17).** The outcome `ok` in those two cases indicates **the attack worked**, not that the property is secure.
- Each test used a fresh `tempfile.TemporaryDirectory()` rooted under `/tmp`, new 256-bit ephemeral test HMAC key in a mode-0600 file, one real checkpoint server child process, and separate action/coordinator subprocesses. T12 spawned eight concurrent action processes. The OS user administering all processes was the **same container administrator**.
- No actual cloud checkpoint, external API, model, wallet, network service, protected repository, permanent signer or independent host used.

## Observed falsifiers and bounds

| Experiment | Observed bounded behavior | Status |
|---|---|---|
| T01–T08 | Local transaction, idempotent retry, payload conflict, stale E1 after E2, A→B→A, offline witness HOLD, injected process crash after checkpoint CAS, sink-only rollback | PASS (cooperative boundary) |
| T09 | Restoring both sink + checkpoint SQLite files as one administrator permits an old E1 ticket to create a new local effect | **NEGATIVE_CAPABILITY (successful rollback attack)** |
| T10–T16 | No `EVIDENCE_ADMISSION` or external scope, digest/ID checks, eight real processes at most one effect, concurrent coordinated epoch advance/action, wrong HMAC key, replay nonce and malformed ticket type checks | PASS (cooperative boundary) |
| T17 | A direct *out-of-band authenticated checkpoint CAS* between the sink's remote HEAD read and local row insert allows a stale local effect to commit despite the local write lock | **NEGATIVE_CAPABILITY (successful TOCTOU attack)** |

## Non-claims

- A separately running server process **does not establish an independently controlled witness**; both databases, HMAC key and script were controlled in one administrator's test environment.
- The two negative results mean **no globally atomic epoch-and-effect guarantee** was demonstrated. The sink's single SQLite transaction only serializes *participating local sink writers*. Authorized external CAS can invalidate the remote checkpoint before the local effect commit. Runtime must not advertise cross-process/external exactly-once or fence correctness beyond that trust assumption.
- Local `APPLIED` means **one disposable SQLite row**, never external side effect or source/truth admission.
- Green tests/CI, signed local protocol messages, file hashes, and this report do not prove honest custody, source authenticity, genuine independent administration, or scientific truth.
- Original R8 30-case suite was independently replayed earlier from its exact ZIP. This R9-A run is a distinct new experiment and does not rerun R8 here.

## Next falsifiable decision gate

**R9-B NOT APPROVED.** Split observer and epoch-writer keys/capabilities; specify how the checkpoint must serialize a *real local* effect with independently controlled epoch advances, and construct an adversarial test from a separate administrative authority. Any false affirmative stale side effect must remain a failing release criterion, not be reclassified as “accepted” because the same-author test expected it. If the target is external, require its own idempotency/conditional-commit and authenticated reconciliation. Until then remain **DRAFT / HOLD / NO TRUST ACTIVATION**.
