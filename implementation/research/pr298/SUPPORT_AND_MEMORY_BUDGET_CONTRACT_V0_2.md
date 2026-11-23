# PR #298 — v0.2 Historical Support & Memory Benchmark Contract

**Status:** `RESEARCH_ONLY / REVISE / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`  
**Supersedes the experimental target interpretation in:** [v0.1](SUPPORT_AND_MEMORY_BUDGET_CONTRACT_V0_1.md). Historical v0.1 remains unchanged.  
**Measured regression to address:** Codex peer review of `65b85759f5d6d6c096e78f7fd2c29bf281ec2c40` (Windows 10, CPython 3.13.17).  
**Source of measurement:** owner-supplied `PR298_PEER_REVIEW_65b8575.md` and `PR298_RSS_WINDOWS.json` (locally reported; not an independently re-run Windows measurement here).

## 1. Counterexample, not a passing resource gate

The same synthetic 128-record, 134,217,728-byte JSONL ledger (each physical record exactly 1,048,576 bytes) produced:
- Direct `inspect_task_history` invocation: **152.66 and 152.81 MiB** peak working set (two fresh Windows processes).
- Original `ario_agent.main --inspect-task-id` with a counting sink that discarded text: **347.95 MiB** peak working set in one fresh process; reported serialized output length 133,166,145 characters.
- The latter **DISPROVES** the proposed <=256 MiB whole-process target **for the old CLI reporting path on this synthetic benchmark**. Do not hide the failure by excluding serialization from the same benchmark, raising the target without evidence, or reclassifying the synthetic case out of scope retroactively.

The direct function, the CLI including JSON production, and the terminal/consumer are distinct accounting domains. A terminal, pipe or file consumer's own buffering is outside the Python process; **the CLI's serialization and stdout writes are inside the target**.

## 2. Two workload populations, explicitly distinct

**Writer-backed development history:** a normal current bounded Agent invocation emits <=18 events for one Task, <=19 if a Workflow stage event shares the Task ID; names of allowed tools are short. A 4-MiB request-file cap **does not imply a 1-MiB maximum JSONL record**: Codex produced a valid 1,048,683-byte request whose output record was 1,048,732 bytes. The 1-MiB profile is a measured stress benchmark condition, **not** an asserted generator invariant.

**Adversarial synthetic resource benchmark:** 128 records with one Task ID; each complete physical JSONL record <=1,048,576 **UTF-8 bytes including newline**; `STOPPED` history with large projected fields (including `tool`) that the current reader accepts. One standalone reader, local regular file, stable bytes, no uncoordinated external writers. This benchmark may be reachable through separately authored or restored histories; it is not claimed to be a normal current CLI writer output. Its source total can be >=128 MiB. No global ledger size limit is introduced.

**Other / historical:** the owner-designated 198,993-byte ASCII runtime sample still has zero legacy-result differences. Other writers, atypical giant fields, and near-16-Mi-decoded-character records remain `UNKNOWN` for universal support. The 16 Mi-character line guard and 128 matching-record limit are unchanged.

## 3. Exact accounting and acceptance

**Trial objective (NOT a verified universal guarantee):** peak **256 MiB whole-process working set/RSS** in a fresh reference Python 3.13 process on both Windows and Linux, including `inspect_task_history`, `ario_agent.main --inspect-task-id`, JSON serialization and stdout writes to a **write-only counting/discard sink**.

- The old full-document `json.dumps` before `print` duplicated up to ~133 million output characters in memory. The proposed fix uses `JSONEncoder(ensure_ascii=False, sort_keys=True).iterencode` to send fragments directly to stdout, ending with one newline, without changing report fields, statuses or exit codes.
- Preservation criterion: for tested reports, emitted UTF-8 bytes **must exactly equal** legacy `json.dumps(report, ensure_ascii=False, sort_keys=True) + "\n"`; never truncate an output or declare a partial history complete. Output size itself remains large and may burden receiving consumers.
- **256 MiB not yet verified for the new fix on Windows or Linux.** Re-run Codex's *same pinned synthetic input and counting sink* after the candidate code change, with fresh processes, same Python version/OS where possible. On Linux use comparable fresh-process peak resident memory; report any different semantics of counters.
- The earlier `tracemalloc <64 MiB` fixtures (128 × 64-KiB projected fields and one multibyte 1-MiB observation) establish **only their two limited cases**; never infer global RSS bounds from them.
- Any >256 MiB fresh-process peak on this defined synthetic benchmark is **REVISE**. Results at <=256 MiB for one benchmark may justify `BENCHMARK_PASS`, not production certification or guaranteed safety for other inputs.
- A separate `subprocess.run(capture_output=True)` memory concern remains out of this serialization change.

## 4. Required next gate

1. GitHub CI for exact new SHA on Linux+Windows (full suite + byte-identity / bounded-fragment CLI regressions); no silent differences.
2. Independent repeat of Windows peak working set using the owner's Codex driver (`PR298_RSS_REVIEW.py`) on an isolated checkout pinned to new SHA, plus Linux peak RSS if available. **Do not use or modify the owner's historical file.**
3. After benchmark verification, decide whether the <=256 MiB objective is an acceptable **reference-profile target**, while acknowledging unlimited total unrelated ledger history and no hard aggregate retained-field limit.
4. Peer review of the latest implementation (our own testing and prior Codex participation are **not** third-party independent acceptance).

**Verdict until those steps:** `REVISE / DRAFT / HOLD / NO_MERGE`. No trust/signer/Genesis, ruleset, production or merge activation.
