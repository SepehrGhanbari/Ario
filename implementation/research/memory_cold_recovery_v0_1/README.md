# MCR-01 — Memory Cold Recovery v0.1

**RESEARCH_ONLY / MODEL_ONLY / HOLD / NO_REAL_KEYS / NO_LIVE_KLADJE / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.**

## Question and decision

Can Ario recover the exact cognitive-memory state after complete deletion of local memory files, and reject a recovery state older than a checkpoint already observed by an external witness?

This lab connects to the existing core.memory_snapshot.encode_cognitive_memory_snapshot / decode_cognitive_memory_snapshot APIs. It does not change them.

## Scope

Included:
- existing data-only cognitive-memory + SourceMonitoringGuard history snapshot (ario.cognitive-memory-source-history, schema v1);
- the complete synthetic JSONL event ledger used to construct that snapshot;
- a versioned checkpoint binding snapshot digest/length, ledger digest/length, generation, parent checkpoint, node count, and attribution count;
- a content-addressed, create-only archive model;
- a model-only witness receipt and nonce-bound readback adapter;
- cold recovery into fresh ConsolidationEngine and SourceMonitoringGuard candidates.

Not included:
- all Ario runtime state, WorkingMemoryBuffer, prospective intentions, model weights, user conversations, or private memory;
- actual C2SP/Sigsum wire verification, real Kladje enrollment, live log publication, or an external object-storage service;
- actual separate administrative custody or a trusted global clock.

## Important protocol distinction

Kladje is a witness, not a memory-content backup. C2SP witnesses cosign a log checkpoint after verifying consistency and persist their latest checkpoint before replying. The Sigsum log proof carries the signed tree head and witness cosignatures; the application must separately retrieve the memory capsule bytes from a content-addressed archive and bind them through a logged commitment.

The model receipt/readback in this lab is deliberately NOT C2SP wire format. It isolates the memory-side recovery contract and uses disposable Ed25519 keys in tests. A real adapter must verify the official Sigsum proof (log signature, leaf/inclusion proof, tree-head consistency, pinned Kladje cosignature) before producing an equivalent verified observation.

IPng's published Kladje description permits only /add-checkpoint; other paths redirect to its About page. Therefore direct Kladje latest-head readback is not currently available from that service. The latest_readback in this lab represents a separate independently administered monitor/readback source, not a Kladje API. Without such a source, the code returns HOLD_FRESHNESS_UNAVAILABLE when the caller asks to prove latestness. A historical valid cosignature alone proves only that a checkpoint was witnessed at some point, not that it is still the latest.

## Run

From implementation/:

    python -B -m pytest -q tests/test_memory_cold_recovery_v0_1.py

The test suite uses only synthetic events and disposable Ed25519 test keys. No network calls, log writes, Kladje traffic, real Ario keys, or production memory.

## Acceptance and negative controls

Positive:
- delete the entire local memory directory, then recover snapshot + synthetic source ledger from the content-addressed archive;
- verify exact snapshot bytes, ledger bytes, node count, source-attribution count, and checkpoint chain;
- retain historical empirical labels without restoring active empirical verification authority;
- accept only a nonce-bound readback from a pinned test monitor when require_current=True.

Negative:
- missing latest readback => HOLD_FRESHNESS_UNAVAILABLE;
- replayed readback nonce, wrong witness/monitor key, missing/tampered archive object, snapshot/ledger mismatch, checkpoint chain gap, or prior-floor rollback => HOLD.

Known RED boundary:
- test_known_red_joint_rollback_of_archive_witness_and_monitor_is_undetectable demonstrates that a fresh client with no prior floor cannot detect simultaneous rollback of the archive, witness, and readback monitor. The test passes by reproducing the attack. This is not an accepted security outcome; it proves the need for a third independently administered gossip/retention domain or a previously retained floor.

## Result interpretation

RECOVERED_CURRENT_MODEL means the synthetic test monitor signed the latest checkpoint response for the test nonce. It does not establish that the real Kladje operator, monitor, or archive is independently administered.

RECOVERED_WITNESSED_LOWER_BOUND means the supplied checkpoint has a valid model witness receipt but its latestness was not established. Do not relabel this as current.

The archive is a local test double. No production recovery, memory admission, semantic truth, trust activation, Genesis, or signer authority is established.
