# M0 Evidence Ancestry Guard — architectural contract proposal v0.1

**Status: ARCHITECTURALLY CLEARED WITH AVA C1-C5 / LOCAL CANDIDATE IMPLEMENTED AND TESTED / AWAITING FINAL AVA REVIEW.**
**Prepared:** 2026-10-14. **Issue:** https://github.com/SepehrGhanbari/Ario/issues/75.
**Verified local baseline:** main at 700130a48fd222d8905f145598212b60f6ff303f.
**Scope:** exclusion of unsupported evidentiary promotion and one fixed supplied-record predicate. No positive independent-source authority.

Owner directly adopted Ava's conditional clearance on 2026-10-14. This revision incorporates its C1-C5 before any schema, engine, CLI or test changes. Implementation may proceed only within section 12. No commit is authorized. The owner explicitly made the clearance clarifications binding; other attached documents remain reference proposals.

## 1. Observed baseline and preserved RED evidence

SHA256 of actual working-file bytes; source/test paths are relative to implementation/:

| File | SHA256 |
|---|---|
| core/schema.py | 17a97ec6716d986cd20bf7c0077258608598f0980a1f4d6b315ee5ba334e128a |
| core/audit_engine.py | f5452ddb921e0597d5667d734bf1acf16e199c5bda0e548132be6fe9ae057732 |
| ario_cli.py | 16316e83d1feb53183467a96ab83f3ddc8c13eaba408359420dea59b1c9ce81c |
| tests/test_m0_regression.py | 3266915a483f63261a87e072e618175bec62e15466727aed562882605d9884f0 |
| tests/test_runtime_cli.py | d278676e04e62f350787636040f7212c8068f5afce13735facf6cad6d2ac894e |

Root AGENTS.md: 21081fcea4dc091139f24c01a400c925c1c41453e5f706736f9b3912fc0decb1. Original 53,103-byte ENGINEERING_LOG.md: 8a926d4d4dae3597feebbf05d81aaa503e9bcf7a33b445bd2ef2da154f10a455.

Complete evidence and verified backups:
C:\Users\xx4773\AppData\Local\Ario\engineering-backups\issue-75-phase-b-20261013-01\

Actual pre-patch execution preserved there:

- 18 complete synthetic input fixtures, canonical bytes and hashes in scratch/red-fixtures.json.
- 34 real baseline calls: two standalone and sixteen cases under each of BASE and DECLARED_F11_F15. Characterization exit 0; this is characterization, not security acceptance.
- Hidden ancestry and explicit retrieval/temporally resolved lineage returned structural PASS. C0 remained UNSUPPORTED and C1 UNKNOWN; no Claim truth status was changed.
- Two proposed acceptance sentinels: 2 tests, 2 failures, 0 errors, exit 1. Both expected fail-closed results and observed PASS.
- Direct result evidence was forbidden. Multi-hop observation wrappers did not receive equivalent ancestry checking. Duplicate Evidence mapping retained UNKNOWN; duplicated independent observation IDs retained EVIDENCE_INFLATION.
- No real summarizer, authenticated independent observation, production ledger, key, or admission authority was exercised.

| Complete input | SHA256 |
|---|---|
| hidden ancestry | 4a9f2bd2d97b830f122f0ed8016e972a7fe4a56d6c4d7dd7f2d11d12f994cfae |
| declared retrieval | 5950f1b36c0f1c4e50619c2e1604a8d6e267a012a7187b1519cdaa8a95507d76 |
| resolved declared lineage | e7c51f1ab2ff3d20678413dd741ed54899926efe806e377d3d921bdbeb72f270 |

Full results: scratch/baseline-audit-results.json, SHA256 c76f46ea291ebc15e355b829d290f44b2aa771e053e53b39b52a9145f770df2e. Exact argv/cwd/environment/exits/stdout/stderr: scratch/red-baseline-execution.json, SHA256 e11341de8c9406d45745c9b55d3390076fc843bf2298dabb6d929a215f80f334. Those artifacts are the exact verdict evidence. Results are reused because the five source/test files remain byte-identical to verified backups; no new test execution is claimed.

Phase A separately inspected remote 97d249e36764401c7e234fee7e97b0b317302128. Matching relevant blobs does not make that remote commit the local HEAD.

## 2. Existing commitments and exact gap

Observed: Evidence carries opaque observation references and a caller independence label. Assessment lacks typed target/use. _check_evidence receives neither Claims nor retrieval ancestry. _check_assessments accepts a unique Evidence ID. That join proves reference availability, not use-specific eligibility.

Preserve M0_STRUCTURAL_CORE_DESIGN_V1.md, M0_PRE_REGISTRATION_V1.md, M0_F11_F15_SECURITY_CONTRACT_V1.md, architecture/CROSS-IRG_INTEGRITY_V1.md, EA-0.1 and ARP-0.1. The latter two are specifications without positive admission authority. No candidate-dossier conversion or admission adapter is proposed.

Separate five dimensions: structural validity; resolution of submitted ancestry; known use incompatibility; independent-support eligibility; proposition truth. Resolution may expose a prohibited path. It cannot establish exhaustive historical ancestry, authenticated origin, independent support, or truth. Bit-identical submitted inputs from a fabricated and an independently observed source must be classified identically.

## 3. Proposed typed inputs — LOCAL CANDIDATE IMPLEMENTATION

~~~python
class EvidenceUse(str, Enum):
    RECORD_DESCRIPTION = "RECORD_DESCRIPTION"
    INDEPENDENT_TARGET_SUPPORT = "INDEPENDENT_TARGET_SUPPORT"

@dataclass(frozen=True)
class SupportTarget:
    subject_reference: Reference
    property_id: str

@dataclass(frozen=True)
class ObservationRecord:
    observation_id: str
    record_version: str
    target: SupportTarget | None = None
    declared_use: EvidenceUse | None = None
    provenance_refs: tuple[Reference, ...] = ()

# Append optional fields; preserve legacy construction/loading.
Assessment.target: SupportTarget | None = None
Assessment.requested_use: EvidenceUse | None = None
AuditInput.observations: tuple[ObservationRecord, ...] = ()
~~~

ObservationRecord is a submitted structural declaration, not an admitted witness. provenance_refs means immediate information parents, not administrative association. record_version is the supported declaration profile M0-EAG-OBSERVATION-0.1, not a historical revision credential. Unsupported nonempty profiles remain unresolved; malformed types are decoding/construction errors. New string identifiers are nonempty and bounded to 128 UTF-8 bytes, compared exactly without case/whitespace/suffix/Unicode normalization.

Identity is (reference_type, reference_id) within one immutable supplied invocation. A second object with the same key is ambiguous even if equal or similarly versioned. Differing versions cannot select a winner. Equal text IDs across distinct well-typed kinds are not automatically ambiguous. Untyped/ambiguous lookup remains unresolved; existing AuditResult/Composition text-ID protections retain precedence. No Reference snapshot fields or cross-invocation continuity are added. A future version-aware identity scheme needs a separate contract.

INDEPENDENT_TARGET_SUPPORT requires an exact supplied CLAIM and explicit property_id. Claim has no proposition body; that token cannot itself establish semantic compatibility. RECORD_DESCRIPTION has only the fixed property below. Missing target/use never defaults to either. Every relied-on Observation target/use must exactly match the Assessment, and cited Evidence resolves uniquely.

Existing Claim statuses and Evidence fields remain unchanged. condition_evaluation, assessment_basis, evidence_level, scope and independence labels remain caller declarations; they cannot authorize a rule or widen its target.

## 4. Registry, directed ancestry and inventory — LOCAL CANDIDATE IMPLEMENTATION

Index actual supplied Claims, Observations, Evidence, Assessments, prior AuditResults, CompositionRequests and summaries present in supplied results. CompositionParticipantResult bindings do not instantiate additional AuditResult definitions: resolve them against uniquely supplied prior results under existing F15 rules. References in artifacts_examined do not instantiate objects. Historical content references do not become ObservationRecords.

| Declaration | Directed treatment: child -> information parent |
|---|---|
| Evidence.observation_refs | Evidence -> each observation |
| ObservationRecord.provenance_refs | Observation -> every declared parent |
| RetrievalEvent source/retrieved | retrieved -> source; restriction-only |
| Evidence.derivation_reference resolving to content artifact | Evidence -> artifact, with all type/collision checks |
| TRANSFORMATION procedure reference | Procedure metadata; never a primary witness; ID collision checks remain |
| Assessment.admissible_evidence_refs | Assessment -> Evidence for feedback detection |
| target/producer/request/admin metadata | Binding/association, not inferred information ancestry |
| generic LineageEdge/history/provenance text | Existing temporal rules only; no invented support edges |

Attach RetrievalEvent dependencies only when retrieved_reference exactly matches a reachable child's canonical typed key. A different well-typed key with the same text ID is a separate endpoint, not implicit ancestry or automatic ambiguity. If an endpoint is actually unsupported/untyped/ambiguous, keep that unresolved; never cast it to a favorable kind. Existing forbidden-result ID protections still apply. Retain every exactly attached retrieval dependency; a shorter parent declaration cannot erase it. A declared typed information edge remains inspectable when transformation semantics are unknown. Unknown relation roles must not be guessed from similarity or temporal connectivity.

Traverse all branches; separate completed and active states; use deterministic memoization/cycle detection. Never infer missing parents, favorable kinds, source authenticity or closure completeness. Repeated references do not create sources; duplicate definitions remain ambiguous. Shared resolved content roots cannot be counted as independent plurality under fresh IDs.

Apply the current forbidden-reference/ID firewall before favorable resolution. A differently typed ID matching a supplied forbidden artifact stays restricted. Explicit forbidden reference types remain forbidden without a supplied matching object, consistent with current direct rules. An unrelated unsupported Claim does not globally taint a bounded description.

Extend artifacts_examined with every guard-evaluated target, cited Evidence identity, Observation identity, parent, derivation, and relevant retrieval/procedure reference, including unresolved endpoints. Preserve the full chosen two-field identity. Inventory completeness reports supplied/evaluated inputs, not exhaustive historical disclosure. Do not introduce significant snapshot fields and silently discard them.

~~~mermaid
flowchart LR
    A["Assessment: exact target/use"] --> E["Evidence wrapper"]
    E --> O["ObservationRecord"]
    O --> P["All declared information parents"]
    P --> G["Mandatory type/collision/ancestry checks"]
    G --> D["Fixed supplied-record presence"]
    G --> U["Independent support: UNKNOWN"]
~~~

## 5. Uncertainty, determinism and bounds — LOCAL CANDIDATE IMPLEMENTATION

Separate findings:

- Ancestry: TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT or UNKNOWN. Traceable means submitted dependencies resolved, never exhaustive or authenticated ancestry.
- Requested-use disposition: NOT_EVALUATED, RECORD_DESCRIPTION_ONLY, KNOWN_INADMISSIBLE or UNKNOWN.
- Literal record presence: MATCH, NOT_EVALUATED or UNKNOWN; no underlying proposition follows.
- Source authentication/independent origin: UNKNOWN in v0.1.

Missing nodes, ambiguous identities, unsupported profiles/kinds, conflicting bindings, cycles and exhausted budgets cannot generate positive support. Preserve specific failures from other branches. Unknown transformation semantics leave equivalence, transformation accounting and substantive support UNKNOWN; they do not erase declared edges or forbidden ancestors.

Literal presence does not require fidelity: a supplied record may be present despite unknown transformation semantics. Report presence MATCH separately from Evidence eligibility. An unresolved ancestry path potentially hiding forbidden composition remains fail-closed for the ordinary Evidence/Assessment request even if presence MATCH is reported. Missing transformation accounting does not mean the target is absent, and cannot authenticate independent origin.

Proposed limits: 4,096 indexed object occurrences; 16,384 dependency-reference occurrences; depth 64. Count before deduplication; traverse iteratively; emit UNKNOWN when a limit prevents required resolution. Preserve established violations and never call truncation complete. Callers cannot increase limits. These are review candidates, not measured capacity guarantees. JSON ingestion and total input memory remain outside this traversal guarantee.

Identical typed inputs yield identical findings/order. Order new findings by assessment and canonical typed references using a stable sort. Existing artifacts_examined retains supplied order; entire-output equality under arbitrary permutations is not promised. No cross-request mutable cache.

## 6. Requested-use policy and sole positive predicate — LOCAL CANDIDATE IMPLEMENTATION

For INDEPENDENT_TARGET_SUPPORT:

- Exact typed target or current-Assessment feedback can establish self-confirmation and incompatible independent-support use. CLAIM C0 ancestry offered for distinct CLAIM C1 remains UNKNOWN: Claim has no proposition body or trusted equivalence relation. Do not infer equivalence from ancestry, wording, similarity, status or a property label. An UNSUPPORTED status alone is not an inspection ban.
- Reachable result/request/summary ancestors remain forbidden through wrappers.
- Disjoint submitted roots, names, hashes, empty parents, ROOT/COMPLETE and INDEPENDENT declarations cannot establish independence.
- Even a fully resolved benign graph yields eligibility UNKNOWN without a separately approved authority. No positive independent-support GREEN exists in v0.1.

RECORD_DESCRIPTION is not a blanket exemption. Proposed sole positive predicate:

| Binding | Exact requirement |
|---|---|
| requested_use | RECORD_DESCRIPTION |
| Assessment.rule_version | M0-EAG-RECORD-PRESENCE-0.1 |
| property_id | SUPPLIED_RECORD_PRESENT |
| Assessment.scope | SUPPLIED_INPUT_RECORDS_ONLY |
| Target | Exactly one supplied CLAIM or OBSERVATION |
| Cited records | Unique Evidence, matching Observation target/use and all mandatory guard requirements |

The engine-owned predicate is only "the nominated typed record is uniquely present in this supplied invocation." Presence MATCH may remain visible when another guard requirement fails. Positive disposition is RECORD_DESCRIPTION_ONLY, never ADMITTED, INDEPENDENTLY_ESTABLISHED or Claim SUPPORTED.

No quotation accuracy, faithful source preservation, executed transformation, authentic attribution, event occurrence, historical existence, entity continuity, ontology or consciousness follows. Caller strings TRUE/SUPPORTED are not engine conclusions. A lossy record may satisfy its own presence predicate without supporting the original proposition.

Target metadata describing a record's own presence is not a dependency cycle; an explicit self-parent is. Ordinary Evidence cannot use AuditResult/CompositionSummary/CompositionRequest even for description. Preserve native F15 LOCAL_RESULT_SUMMARY for its existing bounded result description.

Quotation equality/fidelity, source equivalence and TRANSFORMATION_ACCOUNTING are NOT IMPLEMENTED here. They need separately fixed comparison predicates. This narrows addendum AG-17/18: presence and declaration inspection can be controls, but "passes as accurate quotation" or "admitted transformation account" is not established. Ava must approve this literal predicate or defer positive description Assessments; implementation cannot substitute a free-text bypass.

## 7. Classification precedence — LOCAL CANDIDATE IMPLEMENTATION

Preserve the current aggregate algebra: violations, including UNKNOWN, imply FAIL; empty primary input retains UNKNOWN. No new aggregate UNSUPPORTED or truth/admitted verdict.

| Supplied finding | Diagnostic |
|---|---|
| Reachable forbidden kind/ID under existing Evidence-position rules | COMPOSITION_FORBIDDEN |
| Duplicate same-typed definitions or actually ambiguous lookup | UNKNOWN; no favorable object chosen; benign distinct-kind equal IDs allowed |
| Directed cycle/feedback | UNKNOWN; retain applicable existing SELF_VALIDATION_CYCLE |
| Exact typed target/current-Assessment self-confirmation | EVIDENCE_INADMISSIBLE |
| Shared root presented as independent plurality | EVIDENCE_INFLATION |
| Missing binding/required endpoint, unsupported profile or budget limit | UNKNOWN |
| Benign independent-support graph lacking admission authority | UNKNOWN |
| Fixed presence predicate satisfying guards | No new violation; RECORD_DESCRIPTION_ONLY |

Not first-finding-wins: preserve specific and unknown failures across branches. Forbidden plus missing sibling retains COMPOSITION_FORBIDDEN and UNKNOWN. An ambiguous node cannot choose a favorable definition; other unique branches remain inspectable.

Retain current direct F11/F15 diagnostics, assessment result-ID collision UNKNOWN, and specialized optional classifications. Do not replace them with a blanket alias. Lossiness alone is not a ban. Failed support never establishes that the target proposition is false.

## 8. Mandatory versioning and reporting — LOCAL CANDIDATE IMPLEMENTATION

Propose inspector M0-1.2 and mandatory M0-EAG-0.1 alongside unchanged M0-REF-GUARD-1.0. Recheck collisions before implementation. Every verdict_basis names caller rule versions and both mandatory guards. Caller omission cannot disable guards; specialized optional rules keep their versioned behavior.

Preserve AuditResult/CLI JSON field sets. Proposed per-request findings are a canonical JSON appendix within verdict_basis, prefixed "Evidence ancestry findings: ":

~~~json
{"assessments":[{"ancestry":"TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT","assessment_id":"A1","property_id":"SYNTHETIC_PROPERTY","reasons":["NO_INDEPENDENT_ADMISSION_AUTHORITY"],"record_presence":"NOT_EVALUATED","requested_use":"INDEPENDENT_TARGET_SUPPORT","source_authentication":"UNKNOWN","target":{"reference_id":"C1","reference_type":"CLAIM"},"use_disposition":"UNKNOWN"}],"candidate_ancestry":"TRACEABLE_WITHIN_SUPPLIED_SNAPSHOT","candidate_use":"NOT_EVALUATED","claim_truth":"UNKNOWN","entity_continuity":"UNKNOWN","independent_admission_authority":"NONE","mandatory_guards":["M0-REF-GUARD-1.0","M0-EAG-0.1"],"profile":"M0-EAG-0.1","report_complete":true}
~~~

This is reporting, not a credential. Legacy missing fields are null/UNKNOWN; no favorable synthesis. Candidate-only inspection explicitly reports use NOT_EVALUATED. CLI verifies both current-inspector mandatory markers and preserves findings through serialization. Missing guard reporting is a fail-closed CLI error. Canonical appendix format is an explicit review decision, not existing implemented behavior.

## 9. Legacy compatibility and frozen F10

Optional new fields preserve legacy construction/loading; unknown JSON keys remain rejected. Legacy Assessment missing target/use becomes unresolved in M0-1.2, not implicit support or description.

Standalone candidate inspection may retain structural PASS with use NOT_EVALUATED. Caller INDEPENDENT does not establish origin. Known forbidden ancestry is screened; opaque legacy references do not fabricate ObservationRecords.

Do not edit frozen M0_PRE_REGISTRATION_V1.md or historical acceptance/results. Original F10 expectations remain historical. The opaque F10 fixture cannot demonstrate successor eligibility; record successor behavior as explicit migration.

Static review: 97 M0 test definitions, 16 CLI methods; not executed counts. Two legacy support PASS controls need intentional migration: test_f11_a_real_evidence_reference_remains_admissible and test_f11_false_positive_control_allows_evidence_ids_containing_keywords. Strengthen test_f10_assessment_with_declared_admissible_evidence's weak absence-only assertion with explicit successor verdict/use checks while documenting frozen historical expectations. Update inspector/profile assertions explicitly. Preserve benign keyword IDs and append-only CLI ledger behavior.

## 10. Proposed acceptance and validation — NOT EXECUTED AFTER REPAIR

| Case | Required successor behavior |
|---|---|
| Frozen hidden-ancestry legacy Assessment | UNKNOWN / FAIL; no target/use inferred |
| Bound C0 -> O1 -> E1 offered for distinct C1 | UNKNOWN; no semantic equivalence or automatic inadmissibility inferred |
| Multi-hop/mixed-transform wrappers; all independence labels | No promotion through labels or representations |
| Result/summary/request at any hop | Mandatory forbidden ancestry |
| Distinct IDs sharing a resolved root | No independent plurality; applicable inflation |
| Duplicate same-typed IDs or conflicting versions | UNKNOWN; no newest-version choice |
| Missing nodes; unsupported profile/kind | UNKNOWN required resolution |
| Self/long cycle; target/Assessment feedback | Bounded failure |
| Forbidden branch plus unresolved branch | Both findings; no early accept |
| Omitted F11/F15 declarations | Both mandatory guards still execute/report |
| Closed apparent root; forged labels/hash/completeness | Independent eligibility UNKNOWN |
| Same text in unlinked sources | No similarity ancestry or independence proof |
| Unrelated unsupported Claim plus bounded presence | No global contamination |
| Lossy record's own supplied presence | Bounded presence possible; no fidelity/truth inference |
| Description replayed under stronger use/property/scope | No widening |
| Unknown fidelity, uniquely supplied target | Presence may MATCH; stronger property UNKNOWN |
| Result used as description Evidence | Still forbidden; native F15 summary preserved |
| Legacy missing fields; bad type/enum/extra CLI key | Unresolved legacy; malformed protocol rejected |
| Each graph limit/fanout/shared subgraph | Deterministic bounded failure |
| Every target/graph endpoint | Included in artifacts_examined |
| Identical repeated input; direct API/CLI | Stable findings and preserved bindings |
| Empty primary; candidate-only; benign IDs | Existing bounded behavior/limits preserved |
| Stripped guard marker; scratch ledger append | Fail-closed reporting; complete ledger prefix preserved |

After Ava clearance, rerun applicable real-engine RED sentinels before patch, preserve inputs, add successor cases, implement only approved paths, then run targeted M0, CLI and adversarial checks and one full authorized tracked regression suite. Existing Python, -B, PYTHONDONTWRITEBYTECODE=1, disabled pytest caching, and scratch-confined TMP/TEMP/ledgers. Save exact commands/counts/exits/hashes/results. Fix only demonstrated in-scope failures.

Actual local GREEN/full-suite results are recorded in section 14. No accurate-quotation result, positive admission or production-security conclusion is established.

## 11. Addendum disposition and Ava decisions

Addendum SHA256: 76cb82d82c9b177cd6dffe22be1135742c1f925df8089ac6697f0f67026db13e. Resume SHA256: 9ef7899e30a78b4b726dd4de0bdd5b23c0d26485bae21ca42b085dea1c9aa3f7. Their remote state/quoted execution do not replace verified local facts.

D1 separation, D3 declarations-versus-trust, D4 no positive authority and D5 mandatory version/migration are incorporated. D2 is narrowed to two uses and literal presence. Accurate quotation and transformation accounting are deferred.

Ava conditionally approved D1-D6. Owner adopted that clearance; the following decisions are binding with C1-C5:
1. Conservative boundary: positive independent support remains UNKNOWN.
2. Exact target/use and invocation-local identity; no authenticated revision/proposition semantics.
3. Fixed SUPPLIED_RECORD_PRESENT predicate, or defer positive descriptions.
4. Directed edges, all-branch precedence, candidate-only scope, inventory and limits.
5. Explicit successor migration without editing frozen F10 expectations.
6. Canonical findings appendix, or equally bounded reporting within authorized paths.

Trust-root authentication, reviewer/admission authority, semantic support and historical continuity remain separate protected decisions. Procedural approval of this patch supplies none.

## 12. Exact paths, preservation and stop gate

| Authorized path | Proposed change |
|---|---|
| implementation/M0_EVIDENCE_ANCESTRY_GUARD_SPEC_V0_1.md | This review proposal |
| implementation/core/schema.py | Typed target/use, ObservationRecord and optional fields |
| implementation/core/audit_engine.py | Observation inventory, bounded resolver, guard, fixed predicate, reporting/version |
| implementation/ario_cli.py | Strict new decoding, both profile checks, same output field set |
| implementation/tests/test_m0_regression.py | Actual RED/GREEN cases and explicit migration tests |
| implementation/tests/test_runtime_cli.py | Serialization/profile/adversarial and scratch ledger checks |
| ENGINEERING_LOG.md | Append actual scope/results/preservation |

Six originals have byte-identical SHA256-verified backups in the retained backups/ tree. Preserve the log's complete original prefix. Original RED evidence, backups, 71 pre-existing unrelated untracked paths and runtime/cache contents are protected. Path-set verification is not retrospective content fingerprinting. Two cache directories produce access warnings; do not inspect or modify them.

The seven listed paths may now change within this clarified contract. Frozen contracts, governance, signer, production ledger, original evidence, keys, USB, staging, commit, remote and branch mutation remain forbidden.

**CONDITIONAL GATE CLEARED BY OWNER-ADOPTED AVA REVIEW.** Implement only these clarified boundaries. Any necessary deviation or new authority returns to review. Independent historical continuity remains INCONCLUSIVE; event truth and entity/ontological continuity remain UNKNOWN.

## 13. Binding implementation clarifications — owner-adopted Ava clearance

Clearance source: ARIO_Issue75_Ava_Architecture_Clearance_2026-10-14.md, SHA256 f48c396926a37d608d163e26fb469b2e2dadfbe607f027fbf3c7baaef01f34d8. Reviewed pre-revision spec SHA256 c322f8476e11d8f227767be19762d3c0fb4c3978d1642beffcc5d96a839b39e4 is preserved byte-for-byte. Local main remains the verified 700130a... baseline; the review's reported remote state is not reconciled by a Git operation.

C1 canonical class mapping: Claim=CLAIM; ObservationRecord=OBSERVATION; Evidence=EVIDENCE; Assessment=ASSESSMENT; AuditResult=AUDIT_RESULT; CompositionRequest=COMPOSITION_REQUEST; supplied nested CompositionSummary=COMPOSITION_SUMMARY. Participant bindings are references, not new result definitions. Exact typed lookup never falls back to text-ID-only. Different canonical kinds may share text IDs; direct and reachable result/request/summary anti-laundering ID restrictions remain unchanged.

C2: distinct C0/C1 ancestry is UNKNOWN for independent support, not inferred semantic identity. EVIDENCE_INADMISSIBLE requires exact demonstrable self-confirmation of the typed target or current Assessment, or an existing applicable direct rule. No semantic matching is introduced.

C3: preserve old RED evidence. Add fully typed direct-engine and CLI inputs with populated Observation/Assessment target/use, including C0-to-distinct-C1, exact target feedback, two observation wrappers around a forbidden result, mixed forbidden/missing parents, and strict presence MATCH. Run with optional F11/F15 absent. Schema/input scaffolding may precede the policy RED run so these fields decode, but the policy must still be pre-guard; record that intermediate revision explicitly and do not call rejection of unknown fields a laundering reproduction.

C4: observations alone count as primary candidate input. No Assessment means requested use NOT_EVALUATED, regardless of Observation.declared_use. Candidate-only opaque legacy references or unresolved declarations do not establish eligibility; report ancestry UNKNOWN, without inventing objects or treating that diagnostic alone as a support-use violation. Screen known reachable forbidden kinds/IDs from all supplied Evidence/Observation roots. Occurrence-budget failure produces UNKNOWN/FAIL because required screening cannot complete. Duplicate/cyclic/unsupported declarations remain unresolved; no candidate source gets authenticated. Canonical evaluated Claim/Observation/Evidence/Assessment identities and relevant endpoints (including missing parents) are inventoried in supplied order, without using inventory mentions as definitions.

Depth counts dependency edges from each traversal root: root depth 0, depth 64 permitted, depth 65 unresolved. Guard object/edge limits count occurrences before deduplication. Traversal caches may not bypass depth at deeper paths or transfer one Assessment's self-dependence finding to another target.

C5/D6 reporting profile: append exactly one final canonical JSON object between newline-anchored delimiters:
BEGIN = "\nEvidence ancestry findings: "
END = "\nM0-EAG-0.1-FINDINGS-END"
Serialize with sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False; escaped strings cannot insert raw delimiters. Parse the complete framed tail and verify canonical JSON plus engine-owned profile and mandatory_guards values, not caller-spoofable substring matches. Existing result/CLI field sets remain unchanged.

Appendix fields include profile, mandatory_guards, independent_admission_authority=NONE, candidate_use=NOT_EVALUATED, candidate_ancestry, assessments, report_complete, claim_truth=UNKNOWN and entity_continuity=UNKNOWN. Each Assessment reports exact bounded target/use, ancestry, record_presence and use_disposition; free-form condition/basis never appears as an engine support conclusion.

The appendix is capped at 65,536 UTF-8 bytes including delimiters. Caller strings that cannot be represented within the new 128-byte identifier bounds are not truncated into substitute identities; report null/UNKNOWN and fail any requested use. On appendix overflow, emit a fixed bounded fallback with report_complete=false, report_limit_exceeded=true, assessments=[], use UNKNOWN and retained established violation codes; add UNKNOWN and force FAIL. Never present omitted positive findings as complete. This cap applies to the guard appendix, not entire legacy verdict_basis, inventory, JSON ingestion or process memory.

Presence MATCH may coexist with forbidden/unresolved ancestry and aggregate FAIL. Positive RECORD_DESCRIPTION_ONLY requires all exact approved bindings and guard requirements. TRUE/SUPPORTED/INDEPENDENT caller strings cannot change Claim status or become admission conclusions. Candidate-only and presence PASS do not establish independent evidence authentication.

Required positive/negative controls include benign same-text/different-kind IDs and retrieval keys, duplicate same-typed definitions, existing forbidden-result aliases, multiple targets sharing graph facts, all limits, deterministic framing/escaping/overflow, inventory, and native F15 summary preservation. Frozen F10 and historical evidence remain untouched.

## 14. Actual local implementation and validation — 2026-10-14

This is an uncommitted local candidate on main at 700130a48fd222d8905f145598212b60f6ff303f. No publication or release is implied. Owner-adopted Ava C1-C5 were incorporated before the schema/input scaffold; historical design/evidence snapshots remain in verified backups. This validation record supersedes the earlier prospective test-plan statements, not frozen M0 contracts.

Actual RED: four fully typed fixtures and eight direct-engine/CLI calls under M0-1.1 pre-guard policy; four expected failures, zero errors, exit 1. The four shipped eag_red tests separately reproduced four assertion failures (151 deselected), exit 1. Their populated target/use and two-wrapper/mixed-branch inputs genuinely reached the pre-guard policy. Two initial harness codec errors are preserved separately and are not valid RED evidence.

Actual GREEN: the same four frozen typed fixtures replayed unchanged for eight direct-engine/CLI calls, with exact result parity and unchanged input objects. Distinct C0-to-C1 support remained UNKNOWN; exact self-confirmation was inadmissible; wrapped forbidden ancestry remained COMPOSITION_FORBIDDEN; forbidden plus missing kept both diagnostics. No independent source or Claim truth was authenticated.

Targeted M0/CLI final: 159 passed in 6.17s, exit 0 (132 M0 tests, 27 CLI tests). Full tracked regression: 566 passed and 92 subtests passed in 12.15s, exit 0, from an exclusively scratch-confined byte-verified export of 32 tracked Python files and 15 tracked test modules. Existing untracked signer/tests, runtime data, caches and historical evidence were not copied into that export.

Initial targeted validation had 154 passed/1 failed: an edge-budget fixture omitted the Assessment reference in its accounting. The corrected candidate-only boundary tests exactly 16,384 versus 16,385 repeated parent declarations without changing the intended limit. Focused review found missing ancestor target/use validation; its regression produced 1 failure/2 passes before the guard fix. Reporting regressions produced 2 failures/3 passes before fixes. All subsequent regressions passed in the final 159-test and full-suite runs. No assertions were weakened to admit independent support.

The final guard validates every reachable Observation's target/use outside intrinsic graph caching. Missing/ambiguous forbidden endpoints preserve COMPOSITION_FORBIDDEN plus ancestry UNKNOWN. Canonical findings validation rejects ADMITTED and authenticated-source states; reporting is never a credential.

Exact commands, environments, source hashes, fixtures, complete AuditResults, JUnit and execution outputs are under the continuation-20261014-01/scratch directory in the retained Issue #75 backup root. Named records: typed-red-results.json; typed-module-red-execution.json; targeted-first-green-execution.json; review-defect-red-execution.json; reporting-red-execution.json; targeted-final-green-execution.json; typed-green-results.json; full-regression-execution.json; full-tracked-export-manifest.json; final-verification.json.

Five original test definitions were explicitly migrated; 35 M0 and 11 CLI tests were added. The frozen F10 preregistration and existing historical records remain unchanged. Observation-only candidates are primary input with use NOT_EVALUATED. Supplied-record presence can MATCH despite a separate failing guard; source authentication, claim truth and entity continuity remain UNKNOWN.

Limitations: submitted ancestry can be omitted or fabricated; the guard cannot prove external source independence or exhaustive history. Invocation-local typed identity is not historical revision authentication. Quotation fidelity, transformation accounting and positive evidence admission remain unimplemented. The traversal/report limits do not bound the entire legacy input parser, result inventory or process memory. Cache-access and Git newline warnings are retained without permission/configuration changes. No production security or consciousness claim follows.

NO_COMMIT, NO_PUSH, NO_MERGE, NO_RESET, NO_UNAPPROVED_PATH_CHANGES. Stop for Ava's final review; overall independent historical continuity remains INCONCLUSIVE.
