# Ledger budget reality report

**Decision: HOLD.** On the selected historical runtime file, the largest Task had 7 matching records and the longest decoded segment had 54,357 characters. Both experimental limits admit this sample. Neither has an established production budget.

## Historical measurement

CPython 3.13.17 on Windows ran `ledger_budget_profile.profile_ledger` from implementation commit `da41e6818c4bdefadb19f838a962e8fe607aa1da`. A local driver called the same function as the profiler CLI so it could restrict writes and compare the digest around the call. The source was a pre-existing regular file at the owner-designated runtime location. See the [compatibility report](HISTORICAL_COMPATIBILITY_REPORT.md) for provenance and the read-only checks.

| Measurement | Observed |
|---|---:|
| Total source bytes | 198,993 |
| LF-delimited physical records / logical lines / parsed event objects | 28 / 28 / 28 |
| Blank lines / malformed JSON records / partial final JSON records | 0 / 0 / 0 |
| Distinct Task IDs / distinct Workflow IDs | 4 / 4 |
| Maximum records matching a Task ID | 7 |
| Tasks above 18 / above 128 matching records | 0 / 0 |
| Physical record bytes, nearest-rank p50 / p95 / p99 / max | 314 / 41,752 / 54,358 / 54,358 |
| Decoded segment characters, nearest-rank p50 / p95 / p99 / max | 313 / 41,751 / 54,357 / 54,357 |

The profiler returned `OBSERVED`. The final record ended in LF. Raw lengths include the terminator. Logical lengths exclude it. All 28 decoded segments were ASCII, so this file supplies no measurement of multibyte UTF-8 expansion. With 28 records, nearest-rank p99 equals the maximum.

## How many events can one Task produce?

`parse_task` caps each of the action, diagnostic and criterion lists at eight. Following a normal return through `_run_task_locked` gives these counts.

| Path | Lifecycle records | Maximum |
|---|---|---:|
| A step fails | One start, steps through the first failure, every configured failure diagnostic, one finish. The failure breaks the action loop. | 18 |
| All actions succeed | One start, all steps, every declared success criterion, one finish. A failed criterion sets STOPPED and the remaining criteria are still recorded. | 18 |
| All actions succeed without criteria | One start, all steps, one finish. | 10 |

**A Workflow can bring the matching count to 19.** For an executed stage, `run_workflow` appends `WORKFLOW_STAGE_OBSERVED` with the same Task ID after the Task finishes. Both the history limit and the profiler count matching IDs across event types. The focused tests exercised 18 on a standalone success, 18 on the diagnostic failure branch, and 19 for a stage that failed goal verification. An interrupted invocation has no guaranteed finish.

**128 events.** Supported for the measured file and the tested built-in paths. A formal compatibility policy covering other writers, earlier versions, or repeated/composite identities remains `UNKNOWN`. The 129th matching event returns an explicit unknown history. It does not truncate the source. Reducing this number to 18 would reject a current Workflow case.

## What the line ceiling bounds

`iter_bounded_ledger_lines` reads at most 16,777,217 decoded characters per call and rejects a piece over 16,777,216 before passing segments to the JSON parser. The checked piece includes a translated newline when present. UTF-8-SIG decoding removes an initial BOM, universal newlines translate CRLF/CR, and `splitlines()` may split the checked piece again. This makes the profiler's largest logical segment a different quantity from the value checked by the guard.

At four UTF-8 bytes per code point, 16 Mi characters can represent roughly 64 MiB of encoded text. BOM, newline representation, decoder buffers, temporary Unicode strings, split segments and the decoded JSON object change the allocation profile. The nesting and integer limits do not bound the width of a shallow object. History inspection projects nine named fields after decoding each matching event. Observation payloads are released, while large values in fields such as `tool`, `goal` and the declared ID lists can remain live across records. There is no shared byte quota across these projected values.

**16 Mi characters.** The historical maximum and bounded benchmark establish observed headroom and demonstrate allocation costs. A deployment peak-memory target, representative multibyte history and an accepted compatibility envelope are still missing. The numeric policy is `UNKNOWN`. This investigation adds no whole-ledger cap. See the [allocation measurements](RESOURCE_AND_MUTATION_TEST_RESULTS.md).
