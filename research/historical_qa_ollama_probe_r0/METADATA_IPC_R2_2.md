# RIO-01 R2.2 — metadata-only subprocess research boundary

RESEARCH_ONLY / SYNTHETIC_ONLY / DRAFT / HOLD / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE

This prototype starts a real separate Python process (Python -I -B in tests).
The child reads one disposable synthetic JSONL archive against an externally
provided SHA256 pin, performs an exact historical lookup, and replies with
one JSON metadata receipt. No quote, HTML, original question or path is
returned through the supported stdout protocol.

Test command from repository root:

    python -B -m pytest -q implementation/tests/test_historical_metadata_ipc_worker_r2.py

Only operation METADATA_LOOKUP_ONLY is supported. The command requires
--research-synthetic-only. A filename starting RIO01_SYNTHETIC_ is required
to reduce accidental use of real archives; a filename is NOT an authenticity
test, so do not rename real archives and feed them to this prototype.

The tests reproduce: real subprocess separation; no reply bytes crossing
stdout/stderr; rejection of model/tool/display operations, duplicate keys,
multiple JSON messages, stale archive pins and malformed/oversize inputs.

LIMITATIONS: With the same OS account, the caller can usually read the source
file, debug the worker or launch modified code. Python -I is not an OS
sandbox or an independent source custodian. No independent account, ACL,
process identity attestation, trusted external hash, quorum, nonce/floor,
anti-replay mechanism or cross-process integrity proof is established.
The existing display endpoint is deliberately NOT part of this worker;
any display HTML could otherwise be copied or parsed and reintroduced
into a model prompt. Consumer-side no-reentry remains HOLD.

Research-only status after successful CI: METADATA_ONLY_IPC_REPRODUCED;
INDEPENDENT_CUSTODY_NOT_ESTABLISHED; LIVE_ARIO_NOT_CONNECTED.
Archive/source content remains unverified as factual truth.
