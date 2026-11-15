# AEC-Bench v0.2 — 120-case design and adapter contract

**Status:** design specification only. No v0.2 execution, measured outcome, hidden-set result, or adapter conformance is claimed.

## 1. Purpose and falsifiability

AEC-Bench evaluates whether a system preserves evidence lineage, distinguishes integrity from authenticity, handles scope and schema constraints, and avoids upgrading claims beyond their evidence. The benchmark is designed to expose failures in Ario as well as in baselines. It is not a leaderboard for a preferred architecture.

The v0.1 pilot is retained unchanged as a historical smoke corpus. v0.2 is a separately versioned study. Do not silently change v0.1 fixtures or expected labels.

## 2. Audit findings against v0.1

The v0.1 runner is a pilot, not a validated evaluator. Direct inspection identified these limitations to resolve before scoring v0.2:

1. The candidate policy returns UNKNOWN for most non-conflicting claim labels; the v0.1 minority-supported fixture expects CONTESTED, but the implementation does not derive that disposition from the fixture's SUPPORTS/UNSUPPORTED combination.
2. Agent deduplication and source-root deduplication are different operations. A repeated agent can relay multiple records; distinct agents can share a root; a single agent can cite multiple roots. These dimensions must not be collapsed.
3. Schema validation currently checks only the major-version string equals "1". It does not validate supported minor versions, required fields, unknown critical fields, or downgrade compatibility.
4. The v0.1 expected root count is a synthetic oracle annotation. It is not evidence that a real-world root is independent or authentic.
5. The v0.1 hash flag is a fixture boolean, not cryptographic digest verification or source authentication.
6. The v0.1 baselines are toy policies, not full implementations of PROV-O, TMS/ATMS, RAG, EviGuard, or DerivAudit.

These findings are design constraints, not post-hoc changes to v0.1 results.

## 3. 120-case public development corpus

Use 10 orthogonal failure families × 12 variants = 120 deterministic cases. Each family must contain at least:
- 3 positive/control cases;
- 3 negative/adversarial cases;
- 3 boundary/partial-information cases;
- 3 paired counterfactual cases differing in exactly one controlled feature.

| Family | Cases | Required variation |
|---|---:|---|
| Lineage dependence | 12 | shared root, shared ancestor, independent roots, unknown root, mixed fan-out |
| Relay/replay identity | 12 | duplicate message, duplicate agent, same agent/multiple roots, distinct agents/same root, replay window |
| Claim disposition | 12 | support, contradiction, explicit refutation, mixed evidence, no evidence, minority evidence |
| Scope | 12 | exact scope, narrower scope, broader scope, disjoint scope, unknown scope, temporal scope |
| Schema/version | 12 | supported version, unsupported major, supported/unsupported minor, downgrade, missing required field, unknown critical field |
| Integrity/authenticity | 12 | valid digest, invalid digest, missing digest, valid digest/unknown signer, authenticated source, altered payload |
| Temporal provenance | 12 | event order, late arrival, stale evidence, clock uncertainty, supersession, invalid chronology |
| Revision/history | 12 | append-only revision, correction, erasure attempt, fork, merge, superseded assertion |
| Composition/dependencies | 12 | shared premise, incompatible premises, partial overlap, circular dependency, transitive support, composition firewall |
| Uncertainty/abstention | 12 | missing ancestry, conflicting evidence, insufficient evidence, UNKNOWN preservation, abstention calibration, forced-choice pressure |

Each case has a stable ID, family, input fixture, expected disposition(s), oracle rationale, mutation target, and pair-group ID where applicable. Every expected label must be reviewable independently of the implementation under test.

### Split policy

- Public development: 120 cases, fully visible, used for debugging only.
- Public validation: a separately generated, version-pinned set, not used to tune the candidate policy.
- Hidden test: independently authored and held by a reviewer or separate custodian; never commit its fixtures, expected labels, hashes that enable brute-force reconstruction, or per-case outputs to the public repository before evaluation.
- Publish only the hidden-set protocol, custodian role, aggregate metrics, and a post-evaluation disclosure schedule. A hash commitment may be published only if the custodian can demonstrate it does not leak fixture content and the commitment is timestamped before submissions.
- Any exposure of hidden cases invalidates the hidden status and requires a newly authored set.

## 4. Typed record contract

Every adapter maps its native representation into a common, loss-minimizing envelope:

- `record_id`: stable record identifier;
- `assertion_id`: assertion being evaluated;
- `claim_polarity`: SUPPORTS | CONTRADICTS | REFUTES | UNKNOWN;
- `source_id`: source/agent identity, explicitly not treated as a root;
- `root_ids`: zero or more declared provenance roots;
- `parent_record_ids`: explicit derivation edges;
- `scope`: typed scope object, not an opaque string;
- `schema_version`: parsed semantic version plus declared compatibility range;
- `digest`: algorithm and digest value, or absent;
- `authentication`: VERIFIED | UNVERIFIED | FAILED | NOT_APPLICABLE, with evidence reference;
- `event_time`, `observed_time`, `recorded_time`: separate optional timestamps;
- `revision_of`: optional prior record reference;
- `status`: SUPPORTED | CONTRADICTED | CONTESTED | UNKNOWN | REJECTED, with reason codes.

Adapters must preserve native identifiers and raw payload references. Missing fields remain missing; they must not be synthesized as positive evidence. Unsupported native concepts must be represented as unmapped/unknown, not silently discarded.

## 5. Adapter targets and honest comparison boundaries

Implement adapters only when a real, pinned implementation and reproducible invocation exist.

| Target | What can be compared | Required qualification |
|---|---|---|
| W3C PROV-O / PROV constraints | Entity/activity/agent lineage mapping and constraint validation | A vocabulary/constraint mapping is not a truth or authenticity engine |
| TMS / ATMS | Justification/dependency graphs, assumption sets, contradiction and retraction behavior | Specify the exact implementation; "TMS/ATMS" is a family, not one executable |
| RAG/memory systems | Retrieval citation lineage, source deduplication, revision and abstention behavior | Pin model, prompt, corpus, retrieval config and decoding; stochastic outputs require repeated trials |
| EviGuard | Only the exact public paper/repository implementation identified and pinned | Do not infer capabilities from the name alone |
| DerivAudit | Only the exact public paper/repository implementation identified and pinned | If no reproducible implementation exists, report NOT RUN; do not create a straw-man substitute |

For every adapter, record repository/DOI, immutable commit or release, license, runtime, dependencies, invocation, configuration, input/output schema, mapping losses, deterministic/stochastic status, and independent reproduction instructions. If a named target cannot be located or run, preserve it in the matrix as NOT AVAILABLE / NOT RUN with the reason.

## 6. Metrics (report separately)

1. Provenance-root count accuracy on cases with fully specified oracle roots.
2. Lineage-edge preservation and missing-edge detection.
3. Claim-disposition macro-F1 and per-class precision/recall.
4. Scope violation detection and false rejection rate.
5. Schema acceptance/rejection accuracy by compatibility class.
6. Integrity-vs-authenticity confusion matrix.
7. Temporal ordering accuracy, with uncertain clocks excluded from strict ordering claims.
8. Revision/history preservation and unauthorized-erasure detection.
9. Composition false-positive rate on incompatible dependencies.
10. UNKNOWN precision/recall and abstention rate on insufficient-evidence cases.
11. False independence inflation rate.
12. Unsupported claim promotion rate.

Report denominators, excluded cases, confidence intervals where appropriate, and per-family breakdowns. Do not collapse metrics into a single score. Do not rank systems when adapter coverage or task mappings are materially unequal.

## 7. Execution and governance gates

Before any result is called benchmark evidence:
1. Freeze v0.2 protocol, public fixtures, oracle rationale, adapter versions and environment.
2. Have an independent reviewer inspect expected labels and paired counterfactuals.
3. Run all public tests against the exact commit SHA and retain raw machine-readable outputs.
4. Verify each adapter with a round-trip or mapping-loss test.
5. Run hidden evaluation under the custodian's control.
6. Publish all failures, exclusions, missing adapters, and deviations alongside aggregate results.

A passing unit test proves only that code matches its test assertions. It does not prove source authenticity, truth, real-world independence, security, privacy, consciousness, or architectural superiority.

## 8. Explicit non-claims

AEC-Bench v0.2 does not establish that Ario is superior, that declared provenance roots are authentic, that an assertion is true, or that a benchmark adapter is equivalent to a full product. No production service, signing infrastructure, trust registry, private oracle, or core Ario runtime is changed by this design document.
