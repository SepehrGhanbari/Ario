# MEM-OBS-01 — Lovable V2 HTML admission gate: independent source review (2026-11-22)

Status: RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_PRODUCTION.

## One question
Does the supplied Lovable Evidence-Gate V2 HTML prevent a record author from obtaining an unearned SUPPORTED / ACCEPTED display state after ingest?

## Evidence
- Original Lovable HTML, preserved byte-for-byte in lovable-v2-original.html: SHA-256 002bb0be35b4e2e5a5e4bb140f3de14a192fb482e1e743b27158bb541577e788.
- Original Lovable Node VM test (not copied here): SHA-256 92f0aa202d73bb840bb0edcd16016d3cb67c68ded56e07b3f4b9048e0ff1c7d0. It reported seven focused PASS plus six in-memory scenario outputs. Its script uses a mocked DOM in Node, not a real browser test.
- Revised research-only HTML in ario-memory-observability-demo-v2-reviewed.html: SHA-256 619a082e633689ce0c357c2c964a282a1a55e85ce3e7e0d56e94b46f3eddb850.
- Focused Node VM regression test_lovable_v2_reviewed_node_vm.js: SHA-256 4d4f043e4a15c104856e2a941bc6715f1a87cb86125595781fa92c70f45140ef.

## Two independent RED probes on the Lovable V2 source
1. The status getter was originally declared configurable:true. After ingesting a RECORDED event, Object.defineProperty(record, "status", {value:"SUPPORTED"}) succeeded and render() displayed SUPPORTED. The original positive suite checked public setter assignment and only a pre-ingest override, not this post-ingest case.
2. The HTML card template interpolated untrusted ID, concept, source ID and parent ID into innerHTML without escaping. A record with an injected HTML-like ID produced unescaped markup in the constructed card. This is a markup-injection construction finding, not demonstrated script execution in a real browser.

Additional bounded failure: plain-object conceptIndex mishandled "__proto__" as an inherited key.

## Local correction (reviewed HTML only)
- Set status descriptor configurable:false, preserving only CONTESTED/REVISED diagnostic transitions (NO authorized SUPPORTED/ACCEPTED admission).
- Treat every ingestRecord argument as an untrusted record specification; reject a status-bearing prebuilt record with HOLD_UNAUTHORIZED_STATUS_AT_INGEST.
- Escape record-derived HTML text and attributes; use Object.create(null) for the concept index.
- Correct status-domain taxonomy: core schema EpistemicStatus = UNKNOWN / UNSUPPORTED / CONTRADICTED / CONTESTED / REVISED. SUPPORTED and legacy ACCEPTED are separate NodeEpistemicStatus labels in memory_consolidation.py.
- Avoid calling a resettable in-memory journal "immutable".

## Reproduction
Run from this directory with Node.js (no npm packages needed):

    node test_lovable_v2_reviewed_node_vm.js

Directly executed before upload: PASS for bounded fake-empirical, fake-witness, status setter, post-ingest redefine, prebuilt spoofing, missing provenance, AI self-narrative, escaped HTML metadata, "__proto__" concept, conflict, revision lineage, rollback and no support/acceptance. This Node VM harness uses a mocked DOM; it does not prove browser-wide security or real external witness authority.

## Limits
Code already running in this same JS realm can still directly modify window.journal and can render arbitrary HTML. An upstream trusted-source admission path, independently administered custodian, immutable event log and true source authentication are NOT established. No actual Lovable project, Ario runtime, key or production deployment was modified. The original V2 file remains available as unedited evidence.

Related: Draft PR #319; Notion MEM-01 case https://app.notion.com/p/41f09e730a098193bf37c4ddc57ac87a.
