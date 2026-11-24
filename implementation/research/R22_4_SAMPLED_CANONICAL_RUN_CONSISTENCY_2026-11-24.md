# R22.4 — Canonical run sample consistency and observed Check filtering

**Research only. Baseline #347:** `eced1c9ca3c3e3a4a0d0d22dd2f5fb237ca348c3`. **PR #348** is Draft/HOLD, stacked on #347. No merge, keys, trust activation, memory admission or production.

## 1. Real read-only Check Runs API observations

GitHub documents default `filter=latest` and optional `filter=all`: https://docs.github.com/en/rest/checks/runs?apiVersion=2022-11-28

Using pinned commit SHAs and `per_page=100`, the initial GitHub connector response bodies reported:

| PR | SHA | default | explicit latest | explicit all |
|---|---|---:|---:|---:|
| 347 | eced1c9ca3c3e3a4a0d0d22dd2f5fb237ca348c3 | 19 | 19 | 20 |
| 344 | 75426fad2337a604339ddc202a73af6272e04fe9 | 22 | 22 | 23 |
| 337 | 491a22a89899a6a12c5b4c46d37983e69afad05a | 21 | 21 | 21 |

Reported counts matched returned record lengths. Explicit all contained an additional successful Vercel Preview Comments Check Run: ID 138508305830 on #347; ID 138007767965 on #344. The canonical m0-regression Check IDs were identical across the three views on each SHA. A second sample gave latest/all counts 22/23, 22/23, 21/21 respectively, with the same omitted Vercel IDs, app ID 8329, completed/success. The #347 count increased between observations; the observations are non-atomic and connector bodies do not establish independent origin or pagination-header completeness.

This establishes an observed difference between views, not a false-green canonical CI case, not complete history, and not a justification for switching selection to filter=all. No URL allowlist change. The reader now explicitly discloses default latest filtering and that reported arrays are initial samples, not full attempt history.

## 2. RED: observed older canonical run drift ignored

The previous `_run_snapshot` projected only the highest (run_number, run_attempt) PR-linked canonical run. Earlier canonical runs were validated but omitted from the comparison, while the output still reported their initial metadata.

Tests-only commit `2b32ce88cd2be8a2617531b2df4745f2425cbbf9` on #348: [Implementation Regression 45413311421](https://github.com/SepehrGhanbari/Ario/actions/runs/45413311421). Linux 3.13 observed **5 failed, 2039 passed, 7 skipped, 2 warnings, 273 subtests passed**. All five failures are targeted synthetic controls: an older same-scope canonical run enters a rerun, finishes a failed rerun, disappears, is added, or changes path in the final run sample. The selected green Run 10 remains unchanged; the original implementation still reports `REPORTED_SUCCESS_BY_LINKED_PR_RUN` despite the observed change.

This is a sampled-evidence consistency gap, not proof of false execution success or unauthorized merge. The older run can change independently of the selected run. Two controls establish that stable older failure and presentation-only changes are not selection failures.

## 3. Bounded correction

Code commit `b197c3300b838f4b2544898f538ecaa76921bed0`: compare normalized binding fields for all returned canonical workflow runs linked to the pinned PR and head, order independently. A differing sampled set or binding field returns the existing `RUNS_CHANGED_DURING_OBSERVATION` reason and `NOT_CONFIRMED`; initial positive diagnostic arrays are discarded by the existing error path.

Keep the current-run selection rule unchanged. Stable failures in earlier run numbers do not override the selected run. Unrelated workflows and PRs are not added to the canonical comparison. New tests: `implementation/tests/test_r22_4_sampled_run_consistency.py`. No additional GETs, timestamps, retries, history collector, or vocabulary changes.

**Trade-off:** this deliberately returns UNKNOWN when observed nonselected canonical evidence changes, even if the selected run remains green. It cannot detect unobserved changes, missing historical attempts, ABA, later mutations or internally consistent replay. Full historical completeness and chronology of reruns remain unestablished. No claim of atomicity or authority. Exact-head CI required before claiming GREEN.

**Governance:** RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.
