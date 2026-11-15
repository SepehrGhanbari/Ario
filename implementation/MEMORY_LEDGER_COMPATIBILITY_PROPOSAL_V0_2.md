# Ario memory ledger compatibility & resource budgets — v0.2 candidate

**Status:** PROPOSED / RESEARCH-ONLY / NOT ADOPTED / NOT ACTIVATED / NO MERGE.  
**Date:** 2026-11-15. **Base:** Draft #225 head c5eedf0f7847da0fa336d0295b503aae6b7c48c1.  
**Relates:** #209, #210, #216, #217, #222, #223, #224, #225, #227.  
**Scope:** One bounded candidate change to memory-consolidation ingestion; no new truth, trust, signing, admission or identity authority.

## 1. Source-grounded observations and what is not proven

- Existing \`implementation/ario_agent.py\` emits \`TASK_STARTED\`, \`STEP_OBSERVED\`, \`TASK_FINISHED\` as newline-terminated JSONL; in a three-event synthetic example, the memory prototype records three hashes but constructs only one semantic node. **Ingested events != semantic claims produced.**
- \`implementation/ledger_observation_adapter.py\` declares 8 MiB ledger, 64 KiB per line and 5000 event limits and refuses incomplete JSONL lines; it cannot establish a historical source's independent truth or custody.
- The #210 prototype calculated \`sha256(raw_line.strip())\`; #222/#225 use \`sha256(raw_line)\`. A newline-terminated record produces different identifiers. A successful local hash match is **not source authentication**.
- Current memory stream entry has no event-count/serialized-byte budget, while the file reader permits a 16 MiB snapshot. The stream has a nested scan of prior nodes and remains bounded **only as configured by the candidate budget**; this is not a proof of linear CPU or fixed RAM use.
- No real personal ledger was read, re-signed, migrated or modified in preparing this proposal.

## 2. Versioned identity and provenance policy (proposal, not adoption)

1. \`legacy_trimmed_sha256_v0_1\`: historical draft #210 line digest, hashing \`raw_line.strip()\`, **never** reinterpret as a raw-byte digest.
2. \`raw_line_sha256_v0_2\`: #222+ byte-exact hashing, including LF/CRLF; consistent in kind with the observation adapter's record hash.
3. Require \`digest_scheme\` alongside **any export** or persisted reference. The module currently emits only a hash tuple; this proposal does **not** silently change that public schema. Until approved and implemented, consumers must not guess the scheme or assume continuity.
4. A legacy resolver, if needed, must be separate, explicit, source-byte witnessed, and must report \`UNKNOWN\` if the source bytes are unavailable or ambiguous. No silent rewrite of old records.
5. Claim status remains legacy \`ACCEPTED\` (structural ingestion only, not \`SUPPORTED\` or external truth). Versioned \`RECORDED/UNASSESSED\`, node-ID versioning, \`negates\` compatibility, collision handling and timestamped semantic revisions remain **HOLD in #216**.
6. No creation of new cross-type lineage authority. No reduction in evidence admission requirements, and no release/trust activation.

## 3. Candidate resource contract and escape hatches

| Boundary | Candidate default | Proposed behavior / limit |
|---|---:|---|
| Each call to \`ingest_event_stream\` | 5000 event items | reject event 5001 with \`ConsolidationError\` and restore state |
| Retained event hashes per engine instance | 5000 unique digests | reject new hash at cap, but accept idempotent replay |
| Serialized JSON value per event | 64 KiB | reject above limit before adding event to state |
| Sum of compact serialized events per stream call | 8 MiB | reject above limit, restore state |
| File byte snapshot | existing 16 MiB | retain existing cap; separate from compact serialized byte cap |
| Completed JSONL records | final LF mandatory; CRLF accepted | reject incomplete final line or blank record before memory update |

These values are *candidates*, borrowed where useful from the existing adapter, **not authorized universal limits**. Direct stream \`json.dumps\` is not a hard bound on peak heap allocation or recursive serialization work. Bounded event count plus a 5000-node scan can still be costly; CPU/time benchmarks and cancellation controls remain required before adoption. A 16 MiB file may be rejected because its 8 MiB *compact serialized* stream budget is exceeded—an intentional candidate restriction requiring compatibility review.

The existing \`ingest_event_stream\` / \`ingest_ledger_file\` integer return values are unchanged and count accepted **records**, not semantic nodes learned. A future, separately reviewed metrics API should report seen/accepted/skipped/reinforced counts without claiming all events express meaningful facts. No new substantive mapping from \`STEP_OBSERVED\` or \`TASK_FINISHED\` to truth is allowed here.

## 4. Planned controlled RED/GREEN acceptance

- 3 events under a monkeypatched per-call limit of 3 **pass**; a 4th causes a controlled, atomic fail.
- 2 stored hashes across separate calls **pass** under a monkeypatched cap of 2; 3rd causes rollback. Old nodes and hash set stay byte- and value-equal.
- Oversized serialized event and batch produce controlled errors and leave preexisting state unchanged.
- LF/CRLF complete JSONL **pass** preserving exact raw byte hashes; unfinished final line **rejects** with no partial state.
- Blank-record and duplicate-key JSONL **reject**, legitimate nested JSON **passes**.
- Realistically shaped 3-event synthetic agent log remains 3 ingested / 1 semantic node; report this known limitation, not three learned memories.
- Original tests, stacked RED controls, Linux/Windows CI on the exact new commit and independent review remain required. A green CI while the old node-ID strict XFAIL persists is not proof of a fixed ID contract.

## 5. HOLD decisions requiring explicit owner adoption

- Any production event/byte budget or expansion of storage; incompatibility with old logs and caller contracts.
- Structural \`ACCEPTED\` vs \`RECORDED/UNASSESSED\` and the reserved possibility of \`SUPPORTED\` only from separately authorized evidence.
- Stable SemanticNode ID v2 and potential aliases of \`("a:b","c")\` versus \`("a","b:c")\`.
- Historical hash-reference translation; no silent migration, and no claim that every prototype-generated reference exists in production.
- Bitemporal validity, source-monitoring guard, durable memory custody, indefinite retention and user deletion policy.

**End state:** this document and candidate code are intended solely for review in a stacked Draft PR. Preserve original Git blobs and commits. Do not merge, deploy or activate security/trust controls because the tests pass.
