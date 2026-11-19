# H3.2 R0 preliminary capability boundary — 2026-11-09

**Revision inspected:** `e6ab569fec79d192a83a121f834af23e93397674` (`SepehrGhanbari/Ario`, `main` as inspected).  
**Purpose:** A falsifiable, **bounded** statement of the existing **direct M0 CLI** interface before adding a separately attributed synthetic research prototype.

## Observations of pinned source, not a runtime execution

1. [`implementation/ario_cli.py`, lines 97–120](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/ario_cli.py#L97-L120): `parse_request` accepts exactly `audit_id`, `rule_versions`, `configuration_id`, `execution_timestamp`, and `artifacts` at top level; unknown keys are rejected. The public Issue #169 H3.2 input has the top-level `cases` key. **Direct unadapted H3.2 v0.2 input is schema-incompatible** with this CLI. Prediction based on source: `ValueError` reporting unknown field `cases`; **not an executed rejection test**.
2. [`implementation/ario_cli.py`, lines 140–151](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/ario_cli.py#L140-L151) routes a decoded `AuditInput` to `AuditEngine.audit`. [`implementation/core/audit_engine.py`, lines 129–145](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/core/audit_engine.py#L129-L145) enumerates structural claim, state, lineage, retrieval, evidence, assessment, composition and observation inputs, not H3.2 display/typed-trace inputs.
3. [`implementation/ario_cli.py`, lines 122–138](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/ario_cli.py#L122-L138): the returned dict has one verdict and violations, inspector identity, hashes/basis references; it does **not** expose the five H3.2 earliest-error checks. `verdict_basis` may contain ancestry findings; do not claim it has no diagnostic content at all.
4. [`implementation/core/audit_engine.py`, lines 919–1033](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/core/audit_engine.py#L919-L1033): `_check_assessments` resolves evidence IDs and enforces prohibited reference categories and collision ambiguity. It does not use `Evidence.scope` to compare assertion/guarantee population coverage; a changed nonempty scope string with the same unique evidence ID will not by itself change this check's result. This is a source-level **counterexample to treating that check as an H3.2 semantic reasoner**.
5. [`implementation/M0_ACCEPTANCE_RECORD_V1.md`, line 50](https://github.com/SepehrGhanbari/Ario/blob/e6ab569fec79d192a83a121f834af23e93397674/implementation/M0_ACCEPTANCE_RECORD_V1.md#L50) records a structural core without an LLM semantic judge; line 197 excludes free-text semantic strength from that M0 semantic audit scope. Earlier capability audits record their **own** historical non-operationalized fixtures, not a present-day repository-wide H3.2 inventory.

The same findings and a rebuttable read-only checklist were discussed with CodeRabbit in [Issue #169](https://github.com/SepehrGhanbari/Ario/issues/169#issuecomment-6746514336). CodeRabbit independently inspected the direct CLI path and could not identify a direct five-label semantic callable in that **bounded path**. That is a code-review observation, not an executed H3.2 runtime score or a complete exhaustive audit of other services/plugins.

## Bounded status matrix

| Question | Supported current answer | Scope |
|---|---|---|
| Raw H3.2 `cases` as an M0 CLI request | **SCHEMA_INCOMPATIBLE (static)** | Only the direct M0 CLI input parser at pinned revision |
| Five specific H3.2 earliest-actor fields from direct M0 CLI | **NOT_DEMONSTRATED** | Only its current `result_to_dict` contract |
| Identifiable direct M0 `_check_assessments` semantic scope entailment | **NOT_DEMONSTRATED** | Named inspected method; ID check is not entailment |
| Repo-wide H3.2 equivalents / dynamically supplied dependencies | **NOT_EVALUATED** | No exhaustive closed-boundary inventory |
| M0 runtime H3.2 performance | **NOT_EVALUATED** | No M0 H3.2 execution or independent comparator |
| New `h32_scope_lab_v01.py` | **STANDALONE_RESEARCH_ONLY** | New isolated prototype only, NOT M0 |

A repo-wide `NOT_IMPLEMENTED` verdict **does not follow** from this limited review. Any newly identified equivalent reachable callable would change that analysis; direct evidence of a real invocation and semantic output would be required for an execution claim.

## Further R0 work before engine attribution

- Inventory tracked code and entrypoint registration beyond the direct CLI path; inspect dynamically reached functions and loaded plugin/service dependencies for equivalent semantic computations **without relying on exact H3.2 label names**.
- For each of five decisions, record a callable path, typed input, versioned semantics, earliest-event result, evidence/citation dependencies, and whether unknown history can be represented.
- Verify an actual invocation with exact input bytes and independent capture of the engine output. Separately test adapter dependencies; no mere nonce, binary hash, dummy invocation, process liveness or wrapper-computed label suffices.
- **Do not edit or retroactively grade** the original 12-case v0.2 benchmark. A future prospectively frozen evaluation must preserve its rule version, fixtures, oracle segregation, and history.

**No commit, branch, prototype result, test count, or GitHub review by itself establishes M0 semantic H3.2 performance, trust, consciousness, or comparative superiority.**
