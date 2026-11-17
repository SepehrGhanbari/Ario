# FC-E04 v0.3 — eliminate check-to-execute gap in source-pinned W9 loader

**2026-11-17 | Research-only | intended existing Draft PR #242 | `research/consensus/`**

## Evidence and boundary

- Earlier W9 source: current pinned Git blob SHA-1 `f795065ce06d88c2ca017270f5036eb028029220`, plus its exact **SHA-256 `bd515b470fd51186f6e44f5320dd69fa73a1bce325b12301b9b276163d5e33d3`**; W9 existing module **not modified**.
- Original v0.2 loader: verifies the bounded W9 path's file bytes and then asks `importlib` to load code **from the path again**. In a disposable temporary directory, a test hook replaced the local W9 source **between** the verified read and path loader, using only a benign marker variable. **Observed:** hook invoked, and dynamically loaded module contained marker `FC_E04_CHANGED_AFTER_CHECK=True`. This reproduces a local **TOCTOU check-vs-execution defect**; it is NOT a remote or deployed Ario exploit.
- v0.3 fix: verify bounded W9 bytes against BOTH pinned hashes, then `compile(raw, ..., 'exec')` and `exec` **the same immutable byte object** in an uncached ModuleType namespace. Never ask a path loader to reopen the source after verification; no import bytecode cache created by this loader.
- v0.3 preserves prior bounded SHA on rejected input and 128-digit JSON integer cap from v0.2. It changes only an isolated research module, *not* production or historical code, or W9 itself.

## Tests performed

- Local disposable ChatGPT scratch, **Python 3.13.5**, `python -B -m unittest -q test_fc_e04_v0_3_regression test_fc_e04_v0_3_resource_guards test_fc_e04_v0_3_loader_binding`: **60/60 PASS** (42 inherited policy/lineage controls, 12 resource guards, 6 loader-binding controls); exit 0. Full output in adjacent test log.
- Separate **v0.2 RED** path-swap reproduction: `POST_HASH_LOADER_CALLED=True`, `EXECUTED_MODIFIED_SOURCE=True`, expected no second read = RED. The replacement was created and executed solely in a throwaway temporary directory with a benign flag; **no authorized user device or source file was modified**.
- v0.3 test `test_01_post_hash_loader_path_swap_has_no_effect` detects any regression to the path-reopening loader; five additional loader controls verify pinned SHA-256 + Git blob, tampering, byte bounds, cache-free load, and same-image stage behavior.

## What this does NOT establish

- No independent validation of the source's true real-world origin; a pinned digest authenticates **local byte identity only**.
- No independent/externally held custody, no proof two declared roots are unrelated, no statistical independence, no claim evidence/relevance truth, no memory admission or action permission.
- No GitHub upload/CI/review yet confirmed for v0.3; these are **local** results. Await exact HEAD review after a separately verified additive upload.

## GitHub plan (NOT EXECUTED)

- Target: **existing Draft PR #242**, branch `research/consensus-sprint-20261116`, in **`research/consensus/` only**, with additive filenames in this package. Do not create another PR, rewrite W9/earlier tests/old evidence, or merge into main.
- Before upload: fetch live branch HEAD, check paths for collision. Upload exactly the four new files and this report, then fetch exact Git blobs and confirm. Run these specific tests in the research checkout, check CI status on exact HEAD, obtain independent negative review, append findings to #216 without assuming protected semantics approval.

**Decision:** `FC-E04-v0.3 LOCAL_PASS / INDEPENDENT_REVIEW=NOT_ESTABLISHED / #216=HOLD / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO`.