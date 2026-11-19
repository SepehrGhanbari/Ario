# AEC Interchange Adapter v0.1 — prototype

**Status:** experimental, synthetic fixtures only; not a trusted transport protocol.

## Purpose

Validate a small external envelope and map explicit source/parent declarations to existing Ario Reference and ObservationRecord primitives. This is an adapter experiment, not a second evidence ontology, evidence aggregator, truth engine, identity service, or admission authority.

## Envelope

Required fields: schema_version, message_id, sender_id, scope, observation_id, source_id, source_type, and record_version. Optional field: parent_ids.

- schema_version: only major version 1 is accepted.
- sender_id and source_id: declarations, not authenticated identities or sources.
- scope: declared context, not authorization.
- parent_ids: declared parent message IDs; absence means ancestry UNKNOWN.

Unknown fields are rejected in v0.1 to avoid silently misinterpreting semantics. Limits: 16 KiB encoded message, 16 top-level fields, 128 UTF-8 bytes per identifier, 64 parent references and at most 16 entries in the flat parent list.

## Result semantics

- ACCEPTED_FOR_LOCAL_REVIEW means local structural checks passed and an observation declaration was mapped. It does not mean admitted evidence, supported claim, trusted sender, or true proposition.
- REJECTED means a local validation rule failed.
- ancestry_completeness=UNKNOWN when parent references are absent.
- ancestry_completeness=DECLARED_ONLY when parent IDs are supplied. This does not establish completeness or authenticity.
- source_authentication, evidence_independence, and claim_assessment remain UNKNOWN.
- truth_authority is always NONE.

No independent roots are inferred from agent count, message count, parent count, signatures, hashes or successful parsing. No confidence or majority consensus is computed.

## Threat model and limits

Covered structurally: malformed fields, unsupported major version, oversized messages, oversized identifiers, duplicate/self parent references, excessive parent lists, and replay against a caller-supplied seen_message_ids set.

Not solved: a sender can omit ancestry, lie about sender/source identity, fabricate parent IDs, or replay under a fresh ID. There is no trusted key registry, trusted clock, durable replay store, network transport, or independent observation channel. A declared parent chain is not proof of completeness.

The flat parent list is not a recursive graph verifier. MAX_GRAPH_DEPTH is a conservative bound on the declared parent-list length, not a claim that a multi-message ancestry graph has been traversed or verified.

## Mapping

- source_id/source_type becomes one Reference in ObservationRecord.provenance_refs.
- Each supplied parent ID becomes a Reference with type AEC_MESSAGE.
- No Claim, Evidence, or Assessment is manufactured: the envelope does not supply enough authenticated semantics.
- No existing M0/EAG/EAC behavior or schema is modified.

## Tests

From implementation/: python -m pytest tests/test_aec_interchange.py

The synthetic suite covers valid mapping, unknown/declared-only ancestry, unsupported versions, malformed input, replay within supplied caller state, size limits, sender non-authentication, and the invariant that message count does not become independence or truth.

## Decision gate

Compare this adapter with current EAG/EAC and external interchange standards before extending it. Reject or narrow it if it duplicates existing functionality. Any future authentication, persistence, trust policy, confidence aggregation, or network behavior requires separate design and explicit review.
