# Retained cognitive-memory foundation — bounded research integration

Source: #385 exact integrated head `a812be63bb053f7a50cb0d22b6cf414ce150b978` (includes #420 and #423); based on current main `5fe4be77f3418626f3fc1c96b0305f989b812e8a`. This is an opt-in, research-only library and local CLI, not a replacement for M0 or the running Ario chat loop. No new trust authority, production, keys, Genesis, external evidence admission or autonomous action is enabled.

The seven cognitive-memory core modules, original research contracts, benchmarks and regression suite are carried forward. Historical DRAFT/HOLD/NOT_ADOPTED statements in source documents describe their original scope; this integration accepts the bounded implementation as research, not the proposed authority contracts. Existing M0 CLI, workflow, governance and history are preserved. CLI research flags are exposed by a separate `python implementation/ario_memory_cli.py` entry point; six CLI test files are mechanically retargeted, and report writes use exclusive creation so input and existing reports cannot be overwritten. No implicit CLI routing or runtime adoption.

- New recovery path: bounded JSON, retained digest, atomic file replacement, combined engine/source history and no imported active verification authority.
- Raw ledger replay is recorded-only; task-finish reports cannot trigger intentions. Direct empirical and direct prospective APIs still lack independent caller authority; the bridge is a local research reader, not a hostile-input security service. Legacy pickle methods remain unsafe for untrusted input. Working-memory flush is not transactional (known expected-failure tests preserved). Joint snapshots do not include working-memory buffers or prospective registry and do not make separate bridge calls transactional. Independent custody, freshness and semantic truth not established.
- #210, #273, #381, #385, #420 and #423 source branches remain available. Integration carries the final #385 research tree's additive implementation files, not all historical branch commits or unrelated governance/CLI changes. No history deletion. Close superseded PRs only after successful main merge and retain distinct experiments.

Acceptance: exact-head normal repository CI, with original expected failures disclosed. Stop after integration; no additional speculative review loop.


## Integration correction

Initial CI run [45872367701](https://github.com/SepehrGhanbari/Ario/actions/runs/45872367701) reported one failure on all three platforms: `test_memory_r16_red.py::test_cli_memory_conflicts_small_ledger_still_works` invoked the unchanged M0 CLI rather than the new research CLI. Linux: 2144 passed, 1 failed, 7 skipped, 2 xfailed; Windows: 2142 passed, 1 failed, 9 skipped, 2 xfailed. Retarget the seventh CLI test file without changing its assertions. TXT restore run 45872367600 succeeded. Re-run normal CI; no additional experiments.


## Follow-up: #223 and #258
Freeze list-supplied source/link digest fields; reject nontext falsification conditions; reject duplicate JSON object keys at any depth in both ledger readers. Existing bounded batch ingestion and resource ceilings are retained. Source promotion deduplicates repeated evidence IDs within one assessment; exact statement binding from #424 remains required. Repeated explicit assessments may retain historical references; no independent corroboration is inferred. Bridge-level whole-file transactional replay and historic line-hash migration remain outside this correction (#227). No production/trust change. CI pending.
