# M0 F11/F15 Non-Optional Reference Firewall — Security Contract V1

**Status (verified 2026-10-13):** the M0-1.1 reference firewall is implemented on `main` (introduced in commit `700130a48fd222d8905f145598212b60f6ff303f`); GitHub Actions regression passed at `97d249e36764401c7e234fee7e97b0b317302128`. This records bounded implementation and test evidence, not a claim of comprehensive security assurance.

**Pinned baseline:** `8ce95148636e2e65915c055c667573514c8d19a1`.

**Change discipline:** exact five paths only, with untracked assets/ledgers/backups untouched.

## 1. Scope and threat model

The existing deterministic M0 inspector accepts caller-declared `rule_versions`. Previously, omitting `M0-F15-1.0` let an `AUDIT_RESULT`, `COMPOSITION_REQUEST`, or `COMPOSITION_SUMMARY` be wrapped as an `Evidence.observation_refs` or `Evidence.derivation_reference` and yielded structural `PASS` in some cases. A caller may also mislabel an ID which matches a supplied prior audit result.

The caller cannot be allowed to disable the **reference-type boundary** merely by omitting an optional version declaration. This contract does **not** establish real-world evidence authenticity or eliminate unrelated unsupported rule declarations.

## 2. Versioned engine-owned mandatory invariant

- The M0 inspector on `main` reports `inspector_version = M0-1.1` (prior M0-1.0 remains recoverable at the pinned Git commit).
- The engine enforces the new nonoptional baseline `M0-REF-GUARD-1.0` whenever it audits primary artifacts, independent of caller-declared `rule_versions`.
- Evidence observation and derivation references of typed kinds `AUDIT_RESULT`, `COMPOSITION_REQUEST`, and `COMPOSITION_SUMMARY` MUST NOT be accepted as ordinary observations/derivations. Violation: `COMPOSITION_FORBIDDEN`.
- Even a differently typed evidence reference with an **exact ID** equal to a supplied prior audit result, supplied composition summary, or current composition request MUST NOT silently pass. Violation: `COMPOSITION_FORBIDDEN`.
- Assessments must not accept an explicitly forbidden reference type as admissible evidence, regardless of caller version list. Violation: `COMPOSITION_FORBIDDEN`.
- If an assessment evidence ID collides with a supplied prior-result/summary/request ID, that cross-kind ambiguity stays unresolved as `UNKNOWN` in violations (therefore aggregate FAIL) even when F15 is omitted. A known prior result ID without a matching evidence object remains `EVIDENCE_INADMISSIBLE` under legacy F11-off behavior.

## 3. Compatibility and constraints

- F11 and F15's existing versioned specialized classifications, composition-summary generation and admissibility checks otherwise retain their declared-version behavior.
- The F15 summary writer is **not** activated solely by the mandatory reference-type firewall. If F15 is omitted, unsupported requests stay fail-closed with `UNKNOWN` and produce no authorized summary.
- `UNKNOWN` must remain a valid epistemic state. It is not upgraded into positive evidence. Existing aggregate FAIL-on-violations behavior is not silently changed.
- Benign references whose IDs merely contain tokens such as `AUDIT`, `PASS`, `VERDICT` are not rejected on substring matching.
- `AuditResult.rule_versions` and CLI field `rule_versions` continue reporting **caller-declared** versions; they MUST NOT misrepresent the new mandatory invariant as caller-declared.
- Every verdict_basis (PASS, FAIL, UNKNOWN) names the declared version list and engine-enforced mandatory guard. A PASS is bounded structural checking only, **not** proof of historical truth, authenticated witness provenance, identity, or consciousness.
- Existing immutable audit records and historical source remain untouched. Changing inspector behavior is signaled by its explicit v1.1 identifier, not by rewriting past results.
- CLI output keeps the existing JSON field set and append-only ledger behavior. It fails closed if an M0-v1.1 result lacks its mandatory scope statement.

## 4. Original acceptance requirements (historical plan, not a completion record)

1. Exact hashes of each original tracked source and test from pinned commit are checked before any patch.
2. Two sentinel new tests run *before* engine edits, demonstrating failing security invariants; stage must report two expected assertion failures, not errors.
3. At least 15 newly added regression and CLI tests run after repair, including negative and benign controls.
4. Full tracked M0/CLI/TB suites run from an isolated scratch export of the pinned commit; no live edits, no commits, no pushes.
5. Additional red-team characterization can be rerun **with updated baseline expectations**; tests that encode the old vulnerability as expected behavior must not be called passing security tests after the fix.
6. On any mismatch stop, preserve scratch and outputs. Seek separate owner approval before any branch publication or merge.

## 4a. Observed main-branch evidence (2026-10-13)

- The five-path implementation change was introduced by commit [`700130a48fd222d8905f145598212b60f6ff303f`](https://github.com/SepehrGhanbari/Ario/commit/700130a48fd222d8905f145598212b60f6ff303f); the original pinned baseline remains identified above.
- On `main` at [`97d249e36764401c7e234fee7e97b0b317302128`](https://github.com/SepehrGhanbari/Ario/commit/97d249e36764401c7e234fee7e97b0b317302128), `implementation/core/audit_engine.py` declares `INSPECTOR_VERSION = "M0-1.1"` and `ALWAYS_ON_FIREWALL_VERSION = "M0-REF-GUARD-1.0"`; its evidence and assessment checks apply the reference-type guard without requiring callers to declare F15.
- GitHub Actions [Implementation Regression run 38398626666](https://github.com/SepehrGhanbari/Ario/actions/runs/38398626666) completed successfully on that `main` commit, reporting **520 passed, 92 subtests passed**. This is evidence for the executed test suite only.
- The original acceptance requirements above remain historical requirements; this status update does **not** independently establish that every pre-patch red sentinel, scratch-export step, or red-team characterization was performed exactly as specified. Those particulars remain unverified here.
- This documentation correction changes no engine, CLI, tests, historical ledger, or immutable artifact; it does not establish provenance authenticity, real-world truth, or comprehensive security.

## 5. Limits

This is a **type and reference-ID firewall** scoped to the supplied record set. It does not authenticate objects or chronology independently. Caller omission of historical records remains outside the guard's knowledge. Rule-version declarations for other features remain optional as contracted elsewhere. Higher-level authorization, lineage and epistemic semantics are not altered.
