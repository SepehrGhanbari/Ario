# ARIO XERJ isolated read-only search adapter R0

Status: `RESEARCH_ONLY`, `MOCK_HTTP_TESTED`, **NOT EXECUTED WITH XERJ ENGINE**.

Files:
- `ario_xerj_readonly.py` — Python 3 stdlib client for a **dedicated** XERJ ES-compatible index. Only sends a scoped read query; search results are candidate IDs, never proof.
- `test_ario_xerj_readonly.py` — behavior tests including forged search results and provenance anomalies.
- `test_wire_contract.py` — local fake HTTP server tests of transport, no redirect and response bounds.
- `TEST_LOG.txt` — raw 26/26 self-authored unittest results.
- `ASSESSMENT_FA.md` — source-grounded Persian assessment with specific Ario integration seam and HOLD constraints.
- `RESULTS.json` and `SOURCE_MANIFEST_SHA256.json` — traceability. No private user data or third-party source code copied.

Reproduce without XERJ or dependencies:

```bash
python -B -m unittest -v test_ario_xerj_readonly test_wire_contract
```

The code does **not** create indices, install hooks, download models, run external binaries, access Ario's live ledgers, call `/_memory` or `/_decide`, or configure keys. Real upstream acceptance is a future, separately bounded R1. Search candidates are not truth or authority.
