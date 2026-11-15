# Ario — V1↔V2 Memory Migration Decision Matrix (Proposal v0.1)

**Issue:** #216. **Status:** PROPOSED / UNAPPROVED / NO MIGRATION / NO TRUST ACTIVATION.  
**Date:** 2026-11-15. **Evidence base:** first Draft memory prototype #210; Draft #229 proposed digest labels; Draft #230 cross-component RED; Draft #231 LF framing correction; separate shared input-contract proposal. No existing core code, archives or history changed by this decision matrix.

## 1. The owner decision is architectural, not a code formatting change

| Option | Mechanism | Pros | Blocking risks | Proposal |
|---|---|---|---|---|
| A — In-place upgrade | Rewrite old \`ACCEPTED\`, IDs and hash refs | Simple-looking current API | Violates revision≠erasure, ambiguous aliases, old \`negates\` references, false admission | **Reject** |
| B — Sidecar V2 | Keep immutable V1 and opt-in separate, versioned V2 projections | Honest backcompat, reversible view, explicit UNKNOWN | Needs mapping provenance, authorization, read-only migration fixtures | **Recommend for independent review** |
| C — No migration | Keep V1 with historical limitations | No immediate history risk | Continuing ambiguous status and node IDs; cannot claim V2 guarantees | **Valid HOLD fallback** |

No alternative has been approved. A PR with green CI is not an owner decision.

## 2. Split recording from assessment

V1 historical \`NodeEpistemicStatus.ACCEPTED\` came from **structural ingestion** of caller-supplied text. It is NOT a witness, verdict, admissible Evidence, or independently supported fact. A V2 candidate needs two axes:
- \`record_state\` with at least \`RECORDED\` or an explicit not-recorded/unknown reason.
- \`assessment_state\` initially \`NOT_EVALUATED\` or \`UNKNOWN\`. \`CONTESTED\` can reflect an explicitly scoped conflict; \`SUPPORTED\` is unavailable without separately authorized, authenticated, versioned assessment and its admission criteria.

A local hash, replay count, CI, model agreement, or claim salience **never** automatically performs \`NOT_EVALUATED → SUPPORTED\`. Any V2 assessment authority needs a separate trust/governance decision, not this proposal.

## 3. Identity test vectors (draft only)

V1 prototype key: \`"SEM-" + sha256((concept + ":" + assertion).encode("utf-8")).hexdigest()[:16]\`. A delimiter collision:
- \`("a:b","c")\` and \`("a","b:c")\` both hash the input string \`"a:b:c"\` and get **the same** V1 key.
- Candidate V2 input encoding: UTF-8 bytes of JSON array \`[concept,assertion]\` using \`ensure_ascii=False, separators=(",",":")\`, no implicit trimming or Unicode normalization. Prefix \`SEM-v2-\` followed by the **full** 64-hex-character SHA-256. The two pairs produce distinct candidate keys. This is a **proposed deterministic encoding**, not a claim that SHA is a proof of identity or a standardized canonical JSON format.
- Unicode normalization policy, type requirements, maximum size, versioned encoding name and stable public serialization MUST be explicitly decided before adoption. Semantically equivalent spelling ≠ automatic identity. If an alias is ambiguous, return \`UNKNOWN\` rather than choosing based on recency, confidence or salience.

## 4. Source-byte digest versioning

| Scheme | Byte transform | Interpretation |
|---|---|---|
| \`legacy_trimmed_sha256_v0_1\` | \`sha256(raw_line.strip())\` | Historical prototype reference; NOT byte-identical to complete JSONL line |
| \`raw_line_sha256_v0_2\` | \`sha256(raw_line)\` | Byte-exact source line including LF/CRLF, **not** custody or external authenticity |
| unspecified | none | Return \`UNKNOWN\`; never assume either scheme |

A source-hash crosswalk needs (scheme tag, exact source bytes or independently warranted copy, context and timestamp, translation method and review decision). Even a complete digest match is not a declaration that an event happened or that its proposition is true.

## 5. Proposed append-only sidecar record fields

\`migration_version\`, \`legacy_id\`, \`v2_id\`, \`legacy_digest_scheme\`, \`v2_digest_scheme\`, \`source_reference\`, \`normalization_version\`, \`mapping_status\`, \`review_source\`, \`review_timestamp\`, and \`ambiguity_reason\`. Each proposed field is a *candidate schema*, not a guaranteed existing source.

Required behavior:
- A one-to-one **verified projection** may be offered as a versioned *view*, not an in-place mutation.
- A one-to-many V1 alias stays \`AMBIGUOUS/UNKNOWN\`. Any \`negates\` pointer to it remains \`UNKNOWN\` until independently scoped evidence disambiguates the target.
- Lost bytes, missing legacy digest scheme, uncertain provenance, contradicted references or unresolved timestamps produce \`UNKNOWN\`, not fabricated lineage.
- Any private-data archival/erasure needs a separate data-governance contract; append-only metadata does not automatically justify indefinite retention of source content.

## 6. Preregistered V2 gate / potential falsifiers

| Probe | Success condition |
|---|---|
| Two colliding V1 delimiter pairs | Same V1 ID, distinct V2 candidate IDs |
| V1→V2 crosswalk with 2 targets | \`UNKNOWN\`, no chosen target |
| V1 \`ACCEPTED\` with unsupported input | V2 \`RECORDED/NOT_EVALUATED\`, never auto-\`SUPPORTED\` |
| \`negates\` points to ambiguous V1 ID | Unresolved; no guessed V2 mapping |
| LF vs CRLF vs trimmed hash | Distinct tagged digests preserved; old references unchanged |
| No surviving source bytes | \`UNKNOWN\`, no invented digest provenance |
| Repeated or colluding claimed source | No independent assessment or evidence admission inferred |
| Old archive snapshot check | Byte-for-byte unchanged (hash before/after) |
| Legitimate unambiguous case | Resolve in an opt-in view without rewriting V1 |

The included *pure Python test vectors* check deterministic encoding and ambiguous-map outcomes; they **do not** exercise any approved runtime V2 implementation, because none exists.

## 7. Explicit decision needed before production

1. **Approve / reject / revise** Option B *in principle*. No silence-as-approval.
2. Freeze V2 identity encoding and Unicode handling only after corpus/collision review.
3. Define exact compatibility maps, read-only visibility, archived back-reference handling and \`negates\` behavior.
4. Specify separate authorized Assessment promotion and user privacy/retention rights.
5. Preserve old issue/test identifiers, including the \`T-CONS-04\` decay vs anti-self-citation naming collision, with versioned alias documentation.
6. Obtain independent scientific/security review with falsifiers and explicit owner adoption **before any implementing/merging or activating PR**.

**Current verdict: DESIGN CANDIDATE / HOLD. This document cannot confer truth, identity, trust, signing or governance authority.**
