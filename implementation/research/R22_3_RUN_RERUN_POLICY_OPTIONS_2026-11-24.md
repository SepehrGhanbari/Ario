# R22.3 Run/Rerun Policy Options — decision pending, no behavioral change

**Current implementation:** `latest_by_workflow` chooses the highest `(run_number, run_attempt)` for the pinned workflow and PR/SHA. The canonical Job/Check must then belong to that selected exact attempt, and the reported green status never authorizes merge or trust.

## Falsifiable characterization (synthetic)

With Run 10 / attempt 2 **failed** but re-run later, and Run 11 / attempt 1 **succeeded** earlier, the current observer chooses Run 11 and reports `REPORTED_SUCCESS_BY_LINKED_PR_RUN`, while overall `status=UNKNOWN` and `merge_authorized=false`. This is a policy consequence, **not** an established code defect.

| Candidate diagnostic policy | Example disposition | Main advantage | Main failure mode |
|---|---|---|---|
| A. Max `run_number`, then `run_attempt` (**current**) | Run 11 green for current check | Deterministic run-generation ordering | May underreport a later failed rerun of Run 10 |
| B. Latest attempt **started_at** across runs | Run 10 attempt 2 failure wins | Tracks latest activity | Timestamp completeness/semantics must be proven; stale or omitted metadata can reverse selection |
| C. Latest completed job | A completed green might win | Easy user-facing result | Dangerous: ignores a newer pending/running attempt |
| D. Any more recent contradictory rerun → separate `CONFLICT_OBSERVED` advisory or HOLD | Keep current Run 11, flag Run 10 failed | Keeps current view distinct from audit trail | Needs reliable timestamps, completeness, and definition of contradictory event |
| E. Strict all known runs/attempts must finish green | HOLD when any relevant run fails | Maximally conservative | Historical failures can block indefinitely; old runs may be deleted or omitted |

## Recommended separation — owner decision required

Keep **A** for the meaning of `CURRENT_CANONICAL_RUN_OBSERVATION` unless the owner chooses otherwise. Do **not** substitute C (latest completed job) or silently switch to B. Consider a separate **D** advisory audit: explicitly report observed later reruns and their status without overwriting current-run selection. Any missing run/attempt or unreliable timestamp must be `UNKNOWN`, not invented historical completeness.

**Open owner questions:** Is a failed later rerun of an older numbered run grounds for (1) advisory conflict only, (2) fail-closed `NOT_CONFIRMED`, or (3) a new independent check required? Which fields and visibility window define "later" and "same scope"? Does the reader need a separate `filter=all` historical check-run collector? How is >100-page completeness handled?

GitHub documentation: https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs ; https://docs.github.com/en/rest/checks/runs

No patch in PR #347 changes run selection, history admission, required checks, authority or trust. `RESEARCH_ONLY / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE`.
