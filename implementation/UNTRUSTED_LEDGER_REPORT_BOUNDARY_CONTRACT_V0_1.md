# Ario Research Contract — Untrusted Ledger Report Boundary v0.1 (2026-11-17)

**DRAFT / HOLD / RESEARCH_ONLY / NOT_ADOPTED / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO**

Source: current #210 head `6235df45444f112c3a7a699d5c96cac85a4e5b66`.
RED historical test-only #266 head `c1f4fddfbd14fa432edd391727d5afb16ce05acb`.
This stacked branch makes a **research proposal**, not a production security authorization.

## 1. Observable vulnerability and precise scope

The old `EpistemicLedgerBridge.ingest_agent_ledger` parsed `STEP_OBSERVED` from a local JSONL file. On self-declared `status=COMPLETED`, it called `SourceMonitoringGuard.record_empirical_observation(..., exit_code=0, stdout=serialized_report, execution_lock=serialized_report)`. It then put `SUPPORTED` on the semantic node. The guard classified the caller-provided values `VERIFIED_EMPIRICAL`, without independent attestation of execution.

The exact-head synthetic #266 test includes an absent `file_fingerprint` target. Prior [PR CI #44138405955](https://github.com/SepehrGhanbari/Ario/actions/runs/44138405955) showed **two real expected failing assertions on Linux and Windows**, with 1,228 other passes + 121 subtests each. This proves **untrusted replayed event bytes were granted epistemically stronger labels** in this research bridge. It does **not** prove live production access, external attack reachability, or compromise of a signer.

## 2. Proposed minimal v0.1 boundary

### Inbound: read-only and unauthenticated

- A ledger event may report `COMPLETED` or `FAILED`; these are observations of bytes, not proof of tool execution.
- The bridge creates `SourceType.LEDGER_REPORT` and `VeracityState.REPORTED_UNVERIFIED`, tied to the SHA-256 of the raw line (after existing whitespace normalization). The record has **no `EmpiricalProvenance`**, and its `SourceAttribution` constructor refuses any forged `VERIFIED_EMPIRICAL` label or provenance for this type.
- The semantic memory node starts `NodeEpistemicStatus.RECORDED` regardless of self-reported execution status. Repeated identical reports do not promote it.
- Explicit conflicting assertions on the same tool/target still follow the existing `CONTESTED` branch.

### Outbound: retain separation

- Existing promotion requires an `EMPIRICAL_OBSERVATION/VERIFIED_EMPIRICAL` attribution; `LEDGER_REPORT` cannot satisfy that condition.
- `filter_working_memory_candidates(require_verified=True)` does not admit ledger reports.
- The preexisting `record_empirical_observation` API remains available **for separately authenticated execution paths** but this prototype **does not authenticate callers of that API**. A caller with direct access to it could still self-certify by supplying metadata. **This is an outstanding trust-boundary issue.**
- Existing `ACCEPTED` nodes and historical event bytes are not rewritten. This is a change in **future replay interpretation in this research branch**; compatibility of persistent downstream data and behavior requires separate evaluation under Issue #216.

## 3. Falsifiers, negative and positive controls

1. A synthetic file-fingerprint claim about a nonexistent file cannot become `SUPPORTED` or `VERIFIED_EMPIRICAL` simply via replay.
2. A forged JSONL field `veracity_state=VERIFIED_EMPIRICAL`, `source_type=EMPIRICAL_OBSERVATION` cannot override the replay boundary.
3. A `FAILED` self-report is `RECORDED`, not automatically a contradiction.
4. `SourceAttribution` round-trips the new type/state and refuses a `LEDGER_REPORT` dressed as verified.
5. `evaluate_claim_promotion` cannot use a lone `LEDGER_REPORT` as its empirical support; `require_verified` excludes it.
6. A proper `TASK_STARTED` becomes `RECORDED`; truly conflicting recorded observations still become `CONTESTED`, preserving existing functionality.
7. Existing direct empirical API has its old behavior; this verifies non-breaking research change but **does not establish source authentication**.
8. All ledger files stay byte-for-byte unchanged. The original two RED tests and their failure logs remain in #266.

## 4. Issues NOT solved by this patch

- The direct `record_empirical_observation` API has no process/isolation authority enforcement. Do **not** connect it to an untrusted caller. Hashing a value provided by its author proves nothing about real execution.
- `TASK_FINISHED` may still trigger an intention in the registry based on replayed status; the bridge returns triggers, not an action execution guarantee. Consumer action authorization is **UNKNOWN**, and must be investigated separately before any privileged sink is connected.
- Semantic entailment of text, trusted source custody, independent witnesses, de-duplication of real-world sources and forged historical ledgers remain **UNKNOWN**.
- `SUPPORTED` and legacy `ACCEPTED` meanings elsewhere in Ario are unchanged. Issue #216 still governs status naming and historical migration.
- This branch is not a live integration, not an approved memory contract, not a policy acceptance and not safe for production.

## 5. Required external review

Review both #266 (historical RED) and the proposed stacked patch, with exact SHAs and CI evidence. Examine collision/append-only behavior, canonical SHA semantics, source type parsing, hard-coded direct API bypass, `TASK_FINISHED` intention risk, and positive functionality. Do not recommend merge or activation before independent review and #216 governance decision.

## خلاصهٔ فارسی

کد قدیمی صرفاً با خواندن یک ادعای موفقیت در دفتر رویداد، به آن برچسب شاهد تأییدشده می‌داد. در اصلاح پژوهشی، دفتر رویداد فقط **گزارش ثبت‌شده** است؛ برای «تأیید مستقل اجرا» باید مسیر امن دیگری ساخته و آزمایش شود. این تغییر هنوز به حافظهٔ اصلی وصل نیست و تاریخچهٔ گذشته پاک نشده است.
