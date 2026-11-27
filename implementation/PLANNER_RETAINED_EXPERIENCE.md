# Retained planner experience (local, opt-in)

Builds on #447–#449, not a new planner. With the new flag, the existing explicit-choice / grounded-deliberation path reads the native execution ledger through EpistemicLedgerBridge, projects the retained decision/outcome reports into ConsolidationEngine and SourceMonitoringGuard as RECORDED / REPORTED_UNVERIFIED, and selects a four-chunk WorkingMemoryBuffer context before asking the local model. No claims are promoted to empirical truth.

```powershell
py -3 implementation/ario_planner.py --goal "Review the planner" --workspace . --ledger "$env:USERPROFILE\QwenMemory\ARIO_PLANNER_EVENTS.jsonl" --experience-dir "$env:USERPROFILE\QwenMemory\ARIO_PLANNER_EXPERIENCE" --model qwen2.5:3b --ollama-url http://127.0.0.1:11600 --deliberate --execute --revise-after-result
```

Choose a new dedicated directory whose parent exists; use the same workspace, goal, ledger and directory across invocations. No migration or writes to the original dialogue archive. Native workflow still owns the append-only execution ledger. The adapter creates immutable, content-addressed decision, outcome and choice records (exclusive creation, flush and fsync). Each executed attempt records its decision and bounded observable source conditions before execution; outcome references the decision, matching appended native workflow range and prefix digest; revision references prior outcome. STOP is stored as choice, not failure; no retry is forced. The original failed outcome is preserved even if an alternate review completes. Cause, independent truth, verified benefit and repair remain UNKNOWN. The ordinary planner is unchanged when the flag is absent.

A prior concrete failed read may prevent execution of the same approved source/test pair when full bounded file content and permission-mode fingerprints match the recorded pre-attempt conditions under the same goal, workspace and execution ledger. Changing task IDs or read bounds does not bypass this comparison. Changed observable conditions allow reconsideration; unknown conditions do not establish sameness. Exact scope/goal matching is deliberate, not semantic generalization. Native ledger prefix disappearance means the corresponding report cannot influence this gate; it is not evidence that the earlier failure did not happen. The gate is scoped to this opt-in local workflow, not a permanent ban or a new trust decision.

Limits: source fingerprints do not cover all runtime/environmental conditions, independent authentication or rollback; no transaction spans the separate execution ledger and experience records; interrupted decisions without outcome do not become fabricated failures. Directory lock is single-writer only, and a crash can leave a lock requiring inspection. No private local records are published. No Thought Lineage cross-type authority is added: decision/outcome/revision references are local digests and core semantic event lineage, not a claim of full Thought Lineage engine integration. No integration into the V0.8 dialogue transport or shared conversational archive is claimed. No real Ollama outcome is asserted before the controlled acceptance run. The regression tests use real read-only execution with injected local model response and a disposable fixture boundary change.

Acceptance: with real model, run the bounded fixture review with one injected source change, close process, run again with the original conditions, then with changed conditions. Record whether the model STOPs, selects a different path, or proposes repeating the failed pair. The deterministic same-condition exclusion must prevent the latter before workflow execution. STOP is valid, not a failed ethical decision; it may leave the full technical acceptance unresolved. 


## Real Ollama observation — 2026-11-27

Founder-supplied Windows terminal output for exact tested head `66c19041f575d09c8e4fd0d729f07bb2ee6a138d`, Qwen2.5:3b on loopback. Three independent process IDs: 2036, 8456, 16868. Controlled fixture failure, not a production incident.

| Phase | Observed |
|---|---|
| Initial | STOPPED, READ_BOUNDARY_CHANGED; retained outcome `d583ef8cc0fc3438fe8b2c5f1b030ce855b9406eba14337bf3f1b9f0110b0e06`. Model proposed original pair again; REPEATED_SOURCE_REVIEW_BLOCKED. No alternate execution. |
| Fresh process, original conditions | Same retained digest recalled, same_observed_conditions=true, RETAINED_FAILURE_SAME_CONDITIONS; execution blocked. |
| Fresh process, changed conditions | Same historical report recalled, same_observed_conditions=false; same pair executed, COMPLETED. |
| Preservation | Runner reported history_preserved=true; ledger SHA-256 `b30f2f7b97083eecdc0e7dc088e510587d9b5d7099b6d29c94a8906cb61ca94a`. |

Overall acceptance: PARTIAL_OR_UNRESOLVED. The local deterministic memory gate demonstrably affected subsequent execution, not evidence that the model itself avoided the failed choice. Initial alternative completion false, same pair block true, changed pair execution true. Independent truth, repair, subjective consent and verified benefit remain UNKNOWN. No private file or raw dialogue included. Both CI workflows succeeded on this exact tested head.

Follow-up correction: revision-specific structured response schema offers STOP or an available disjoint pair with a grounded CORRECTION; unchanged deterministic post-response checks reject invalid responses even if the server ignores the schema. Rejected same-pair / non-correction revision choices now retain a linked record. This follow-up requires its own CI and real-model acceptance; prior observation is not retrospectively promoted to PASS.
