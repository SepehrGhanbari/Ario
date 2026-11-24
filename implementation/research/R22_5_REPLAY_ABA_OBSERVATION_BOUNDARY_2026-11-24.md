# R22.5 — Cache, replay and ABA: observation boundary

**RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.** PR #349 is Draft/HOLD, stacked on #348 pinned at `c7cc8ccdece383492312b23968abad119e5b5920`.

## Threat model and executable experiment

The experiment uses the actual GitHubReadOnly.get_json decoder, a synthetic opener and bounded HTTP response objects; no live network, credentials, real clocks, or writes. A separate mutable World tracks hidden state and an initial snapshot. The test compares the full returned transcript (URL, HTTP status, ordered header pairs and raw JSON bytes) and observer output. This models delivery semantics, **not a demonstrated compromise of GitHub, TLS, or an actual intermediary**.

- Stable baseline: seven GETs, coherent green linked PR run, no hidden changes.
- ABA: PR body changes after first PR sample, then returns to original before the second. Event log records A→B→A; wire transcript is identical to stable baseline.
- Final replay: a rerun begins just before final Check GET; both final Check and Run responses come from the old snapshot. Hidden live attempt=2, in progress. Wire transcript is identical to baseline.
- Full replay: rerun starts before the first request; all seven responses are old. Same transcript and result.
- Aged cache: final replay with Age=120. Header differs, but the current decoder discards it; result remains identical. This does not prove a particular cache is stale or misbehaving.
- Positive detection controls: visible PR mutation, visible rerun and a 304 response all yield NOT_CONFIRMED. The simulated 304 exercises the status guard, not actual urllib HTTPError behavior.
- All tested paths retain status UNKNOWN, merge_authorized=false, trust_activated=false, memory_updated=false, execution_attestation=NOT_ESTABLISHED.

## Proof boundary

For deterministic observer O and transcript T, O(T) must be the same for each hidden history producing T. A stable history H0, ABA H1 and replay histories H2/H3 can yield identical T. Thus the observed equality cannot distinguish these histories. More reads do not guarantee resolution when the delivery path can repeat old evidence or a mutation occurs between samples. This is a model-relative non-identifiability result, not a general impossibility claim about all possible external observations.

RFC 9111 §5.1: an Age header indicates the response was not generated or validated by the origin for the request; absence of Age does not establish origin contact. §5.2.1.4 no-cache requests prefer successful validation of stored responses. ETag/304 identify representation equivalence, not a gap-free event journal. See https://www.rfc-editor.org/rfc/rfc9111.html and https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api . A compliant cache's reuse is not necessarily malicious or stale; TLS and origin semantics are outside this synthetic model. No blanket rejection of Age, arbitrary wall-clock threshold, forced nonce query, conditional requests, or cache-control policy change is introduced.

## RED and bounded correction

Tests-only commit `e1ac3085f8c07f1c3507e94d067d395b3e9b8d61`. [Push CI 45417119878](https://github.com/SepehrGhanbari/Ario/actions/runs/45417119878), Linux job 138526252873: 8 failed, 2051 passed, 7 skipped, 273 subtests. Seven characterization/detection controls passed; eight explicit-output-contract cases failed on missing fields. This is a reporting gap, not a newly proven authorization vulnerability. The bridge previously omitted workflow_freshness in its output.

Self-audit output now always includes source_freshness=NOT_ESTABLISHED and history_continuity=NOT_ESTABLISHED. Bridge output includes ci_source_freshness and ci_history_continuity fixed to NOT_ESTABLISHED; ci_sample_freshness is SAMPLED_NOT_ATOMIC only when the observer reports that exact sample statement and linked CI success, otherwise NOT_CONFIRMED. Neither external claims nor sample success upgrade the source/history fields. Two additional bridge tests cover overstated claims and pending CI. No behavioral changes to run selection, URL allowlist, retries, transport cache handling, or existing REVIEWABLE_ONLY meaning. Additive research schema fields only; downstream strict consumers need review. Full CI on final exact head is required.

## Next experiment, not deployed

A separate research witness could retain a monotonic sequence and previous digest, binding repository/PR/head, event identity and observation scope. A verifier with independently retained (sequence, digest) floor should reject replay/rollback, gaps, conflicting same-sequence records and stale checkpoints. A nonce tied to a current receipt can prove responsiveness under a specified custody model, not completeness of unrecorded GitHub events. Witnesses must actually observe the event stream and be outside the publisher's rollback control; shared-admin storage or a self-asserted clock cannot establish this. Missing observation, journal omission, or unavailable independent custody remains UNKNOWN. Reuse existing Ario witness/custody research rather than constructing a redundant authority system.

No keys, production, signer, memory admission, trust activation, main changes or merge.
