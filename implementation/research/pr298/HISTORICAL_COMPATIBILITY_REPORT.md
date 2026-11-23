# Historical compatibility

**All three readers agreed on the measured file.** All four existing Task histories remained `UNKNOWN`. Duplicate-ID checks and full history dictionaries matched both legacy revisions.

## Source and custody

The owner identified the Windows runtime location. The selected untracked file was nonempty and predated this investigation. It contains four Task starts, four finishes and four Workflow stage observations following their respective Task finishes. No tracked blob in the candidate tree was byte-identical, and none of the four IDs appeared as quoted literals in the pinned top-level Python test modules. These checks support classification as a historical file found in the runtime directory. They cannot establish the original writer, exclude a restored copy, or distinguish every demonstration run from operational use. No independent chain of custody was available. All synthetic experiments used separate temporary files.

The founder checkout was at a different revision with tracked and untracked local changes. Source and tests ran in a separate checkout of `da41e6818c4bdefadb19f838a962e8fe607aa1da`. No execution or recovery entry point was called on the historical file.

## Read-only procedure

1. Checked the selected path and its ancestors for symbolic links or Windows reparse points, and checked that the source was a regular file.
2. Computed streaming SHA-256 before profiling, immediately after profiling and after the comparisons. All three digests matched. File identity, length and nanosecond modification time matched at the observation boundaries. The digest values are retained in the founder's local copy.
3. Ran the pinned profiler. Its ledger opens are read-only. The SQLite scratch database used an ephemeral keyed digest of each ID. Temporary writes were confined to a dedicated scratch directory, which was empty after profiling.
4. Applied a Python audit hook during comparisons to deny write opens, audited filesystem mutation operations and process launches. The calls made zero denied attempts. Reader return values and exception messages stayed in process. Only numeric comparisons and allowlisted outcomes left the driver.

The scan completed with `OBSERVED`. No concurrent change was detected. The checks describe the intervals observed and do not establish an atomic snapshot or exclude a transient modification restored between checks. A profiler result of `UNKNOWN` must invalidate its partial counts for policy decisions.

## Differential

The streaming candidate was compared with the immediate pre-streaming commit `69d754c21218a95a4c69fe598b918a8fbdcc5ba0` and PR base `dcc9064da5e0f11e41d2048d3be1226777efe42b`. For each comparator, the driver loaded its Agent and Workflow source from Git objects. It called each read-only function for every distinct applicable ID plus one newly generated, locally verified absent ID. Legacy readers used their original whole-file implementation on this 198,993-byte sample. SHA-256 verification used streaming reads throughout.

| Per legacy revision | Comparisons | Differences |
|---|---:|---:|
| Full `inspect_task_history` result | 5 | 0 |
| `_ensure_task_id_unused` return or exception type and message | 5 | 0 |
| `_ensure_workflow_id_unused` return or exception type and message | 5 | 0 |

All four recorded tasks had a matching Workflow stage observation after `TASK_FINISHED`. Both legacy readers and the candidate classify the trailing matching event as ambiguous. All four histories and the absent-ID lookup returned `automatic_resume=False` and `write_performed=False`. A well-formed ledger can therefore yield `UNKNOWN` for a normally terminated workflow stage.

Compatibility here means the same outcomes on this file, including the inherited conservative outcome. The [resource tests](RESOURCE_AND_MUTATION_TEST_RESULTS.md) cover `STOPPED`, `COMPLETED`, complete unterminated JSON and partial final JSON on synthetic files. Other historical corpora and producers remain unmeasured.
