# Research record — 2026-11-26

**RESEARCH_ONLY | GENESIS = NO_GO | no merge or production authority.**

## Scope and origin
Experiential memory (incoming messages and generated responses), not the entire repository. Founder proposed an internal cumulative message counter and hash chain, independent consenting metadata-only witnesses, and optional periodic OpenTimestamps/Bitcoin anchoring. First detect tampering; later investigate recovery. Do not prescribe Ario's general decision after discovering missing memory. MEMORY ≠ TRUTH; CLAIM ≠ PROOF; REVISION ≠ ERASURE; UNKNOWN IS VALID.

## Preserved artifacts (SHA-256 calculated from received ZIPs)

| Artifact | SHA-256 | Recorded local unittest rerun |
|---|---|---|
| ario-anti-rollback-phase2.zip | `9c1133b7e4a2105f77efb5cf559179bc4aad6cf9ca2a0c5468280f35e0f96cc3` | 42/42 |
| ario-anti-rollback-phase3.zip (A) | `86453b9d30c29ee2d2b6da720c02bf66110f4e79cf211ca1d5346accece9cfe4` | 60/60 |
| ario-anti-rollback-phase3(1).zip (B) | `d0520351365d1dc6ef693d00d290de4f8f6b296d37feb3c129b1ced1ff4ebd98` | 59/59 |

A/B designate independent candidates, not rankings. Original archives and execution log are retained locally; this issue records their identifiers and findings, not a binary upload or source commit. Test counts above are from the archived local rerun record, not GitHub CI. B's digest matches its supplied report. Model-exploration figures below are from bundle reports, not fresh reruns in this publication.

## Findings
- Phase 2: cumulative counter and hash chain, metadata-only portable SQLite witness, offline OTS mock. Reported expanded checker: 19,041 states / 101,932 transitions; 3 pre-fix regressions, final 42 tests passed. No authenticated networking, actual Bitcoin proof, or latestness guarantee.
- Phase 3-A: durable recording before model invocation and output release on reference path; input/output payload bytes in SQLite, partial streams, interruption, delivery uncertainty, idempotent retries; no exactly-once delivery/tool execution or production confidentiality. Safe-gateway model reported 32 states / 44 transitions.
- Phase 3-B: distinguish creation, recording, processing, output recording, delivery and external confirmation; mainly hash retention. Assessment distinguishes INCOMPLETE, UNCERTAIN, UNKNOWN, VERIFIED_RELATIVE; latter is conditional on supplied transcript, witness match and asserted measurer/witness independence, not global completeness or truth. Replaced gateway self-report is not evidence. Reported honest model 52 states / 151 transitions; weaker model with bypass 152 / 754 (unsafe); classifier survey 19,440 observations, zero violations of specified guards. Different abstraction sizes do not rank solutions.

## Shared impossibility boundary
A valid nine-message history is indistinguishable from one where a tenth message bypassed every observable recording path and no independent trace survived. An administrator controlling model, gateway, OS, storage and witnesses can restore a coherent snapshot or bypass capture. Global capture completeness remains UNKNOWN; independent surviving evidence may establish an omission but cannot rule out all other omissions. Hashes neither recover content nor establish truth. Physical/device independence, authenticated networking, real keys, actual Bitcoin anchoring, physical power-loss durability and integration with Ario remain unestablished. Two devices alone do not establish independent administration.

## Phase 4 — proposed research, not approved architecture
Preserve both source candidates and regression suites separately. Investigate combining durable capture A with B's independent relative assessment; encrypted recoverable payload separate from witness metadata; trust boundaries, key custody and recovery, witness identity/reset detection, quorum/freshness, bypass/rollback/replay/crash/concurrency and privacy tests. No claim of independence without evidence. Physical two-device trial deferred to approximately 2026-12-01, contingent on authorized Desktop Commander access and device availability; synthetic data only.

This research is distinct from the evidence-admission/legacy-ID work in #216, #381 and #385; related boundary #81. No code changes, history rewrite, merge, signer activation, real keys or production deployment authorized by this record.

Local research record: ARIO_MEMORY_RESEARCH_RECORD_2026-11-26.md; archive: ARIO_MEMORY_RESEARCH_ARCHIVE_2026-11-26.zip; rerun log: ario-memory-research-test-log-2026-11-26.json. Source-bundle reproducibility instructions: RUNNING.md and TEST_RESULTS.md in each ZIP; model reports: PHASE3_MODEL_RESULTS.json (A), MODEL_RESULTS.json (B).

## Publication status
This record reproduces the research issue. The binary ZIP artifacts are not present in this branch at the time of this publication; their SHA-256 digests have been rechecked against the three local originals. See existing discussion #280 for independent rollback evidence and #216 for separate memory admission semantics. No PR was opened. The original archives remain unchanged.
