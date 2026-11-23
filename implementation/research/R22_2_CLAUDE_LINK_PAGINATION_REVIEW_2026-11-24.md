# R22.2 — Independent Claude Review Handoff: REST Link Pagination Fail-Closed

**Disposition:** LIMITED FIX / DRAFT / HOLD / RESEARCH_ONLY. Target: PR #337 head `491a22a89899a6a12c5b4c46d37983e69afad05a` (stacked on #335, parent #333). This review branch is **not** main. No automatic merge, trust activation, keys, signer or production.

## Provenance and independence

An independent Claude account with **no GitHub/Notion connection** reviewed a 13-source-file offline handoff, verified Git blob SHA-1 and SHA-256 against its manifest, and returned `CLAUDE_INDEPENDENT_REVIEW.md`, `test_r22_1_pagination_cache_rate_limit.py` (241 synthetic cases), `PROPOSED_FIX.patch` and `TEST_RESULTS.md`. Its environment only had Python 3.12.3 and a hand-built pytest stand-in, **not real pytest**; the reported 182 / 225 / 16 / 241 / 189 counts from that runner are not independent pytest validation.

The maintainer then independently inspected the uploaded ZIP, reproduced the initial **225 pass / 16 fail** on the unchanged #337 source using **real pytest 9.0.2, Python 3.13.5**, applied the offered patch to a scratch copy only, and ran the 241 independent cases plus 4 original focused test files and the 7 new regression cases. Scratch result: **430 passed / 0 failed** with real pytest. This verifies the modelled defect and the bounded correction; it is not an assertion about GitHub production service behavior.

## Finding F1 — Link next-page indicator dropped

`implementation/ario_repo_self_audit.py` GET transport verified `total_count == len(records) <= 100` for Check Runs, Workflow Runs, and Jobs, but did not inspect the HTTP `Link` response header. If a synthetic response claimed `total_count == len(records)` yet supplied `Link: <...>; rel="next"`, the old reader returned a complete-looking dictionary and permitted a reported CI success. The independent suite reproduced this with **16 failing cases** on unchanged #337.

**GitHub official REST pagination guidance** explicitly states that `Link` response headers advertise additional pages: https://docs.github.com/en/rest/using-the-rest-api/using-pagination-in-the-rest-api?apiVersion=2022-11-28

**Correction:** The reader now rejects `Link` relations containing `next` with `PAGINATION_NEXT_LINK_PRESENT` before parsing the response body. No paging, retries, token, writer, or API allowlist expansion. Four positive attack variants plus three benign controls were added to `implementation/tests/test_ario_repo_self_audit.py`; the independent 241-case offline test file was additionally run, but **not copied wholesale into this PR** because it is an externally generated wider test suite rather than the minimal R22.2 regression patch.

**Limits:** The contradictory `Link`+matching-count response is a tested synthetic input; its reachability against real GitHub is **UNKNOWN**. A missing `Link` header is not proof of absence of stale caching or historical omissions. The regex deliberately follows the supplied narrow proposal and fails conservatively; it does not implement a general RFC 8288 Link parser.

## Other independently reviewed tracks — not fixed in R22.2

- **Cache:** Two internally consistent replayed stale responses can evade sequential sampling. No cache/conditional headers or independent time/freshness oracle; UNKNOWN. `Cache-Control: no-cache` would not prove atomic freshness. No speculative header was added.
- **Rate limit / transport:** Claude's deterministic synthetic cases returned UNKNOWN for 403/429/5xx/3xx, timeout, truncation, incomplete body and primary/secondary throttling; rate-limit headers are discarded, lowering diagnosability. No blind retry added.
- **Concurrency:** Reruns/changes visible to a later recheck are rejected in modelled cases. Events after the final relevant read, PR ABA, both-final-read replay, PR revision after its final identity read and slow final response remain non-atomic residuals.
- **Normalized projections:** Selected Check Run and canonical run identity and attempt fields are covered in the tested model. Strict enum values, empty `pull_requests`, and other noncanonical records may force conservative UNKNOWN. GitHub's actual contract for these exceptional values still requires verification.
- **Open policy question:** `(run_number, run_attempt)` orders the newest run number before a later rerun of an older run. Do **not** silently reinterpret this policy in a pagination fix; separate owner/governance decision required.

## CI and scope

Previous R22.1 CI on #337 (`45070971895`, `45070971896`, `45070971924`) was reported successful and was separately read by the original reviewer; it is not proof about this follow-up branch. This R22.2 PR must obtain its own same-head Linux/Windows CI; **do not call it green until runs finish**.

**Governance:** `RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE`. #333/#335/#337 are unchanged Draft/HOLD. `MEMORY != TRUTH`; `CLAIM != PROOF`; `UNKNOWN` remains valid.

## Independent review deliverable summary

The independent reviewer reported: Track A GREEN_WITH_LIMITS; B UNKNOWN; C GREEN_WITH_LIMITS; D GREEN_WITH_LIMITS; E GREEN_WITH_LIMITS; F UNKNOWN (pytest unavailable). Review artifacts were received as a four-file ZIP in chat on 2026-11-24; their source work is preserved with this provenance and the bounded findings above. Full independent artifact bytes are not represented by this shortened report.
