# ARIO XERJ isolated read-only search adapter R0

Status: `RESEARCH_ONLY`, `MOCK_HTTP_TESTED`, **NOT EXECUTED WITH XERJ ENGINE**.

Files:
- `ario_xerj_readonly.py` — Python 3 stdlib client for a **dedicated** XERJ ES-compatible index. Only sends a scoped read query; search results are candidate IDs, never proof.
- `test_ario_xerj_readonly.py` — behavior tests including forged search results and provenance anomalies.
- `test_wire_contract.py` — local fake HTTP server tests of transport, no redirect and response bounds.
- `TEST_LOG.txt` — raw 40/40 self-authored unittest results.
- `ASSESSMENT_FA.md` — source-grounded Persian assessment with specific Ario integration seam and HOLD constraints.
- `RESULTS.json` and `SOURCE_MANIFEST_SHA256.json` — traceability. No private user data or third-party source code copied.

Reproduce without XERJ or dependencies:

```bash
python -B -m unittest -v test_ario_xerj_readonly test_wire_contract
```

The code does **not** create indices, install hooks, download models, run external binaries, access Ario's live ledgers, call `/_memory` or `/_decide`, or configure keys. Real upstream acceptance is a future, separately bounded R1. Search candidates are not truth or authority.

## R0 review hardening (2026-11-12)

After CodeRabbit's three findings, present-but-malformed timed_out and _shards metadata now marks results RETRIEVAL_INCOMPLETE, non-200 responses have status-specific errors, and negative HTTP controls contain valid candidate JSON with a local redirect sentinel. The tests remain author-written mocks. The absence of optional completion metadata is not proof of complete shard execution; real-XERJ verification remains HOLD.

## R03 fail-closed follow-up

See R03_RESEARCH_NOTE_FA.md. Live HTTP now requires strict completion metadata and JSON Content-Type; anomalous responses return no usable candidates. One deterministic randomized test covers 1,500 adversarial variants. Earlier R02 records are snapshotted. No live XERJ backend has been run.
