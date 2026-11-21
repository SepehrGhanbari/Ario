# W43 — memory-mapped modification and ABA during bounded synthetic reads

**State:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / NO_TRUST_ACTIVATION / NO_PRODUCTION.

## Baseline and boundaries

W42 was merged in PR #309 as main commit `9dd4dda2784fe90e8dda0bb5142ea81167a64869`. The POSIX W38 reader currently compares pre/mid/post `fstat` identity/size/mtime/ctime and rereads an already-open FD. Windows W41 uses a held directory-relative `NtCreateFile` leaf with `FILE_SHARE_READ` only, then calls native `ReadFile`. Both improvements remain bounded and do **not** promise an atomic or authentic snapshot.

**W43 question:** can a *preexisting writable memory mapping* change file bytes during the held read and restore them before the final checks, leaving a reported read that does not match the final file? Is this different from an ordinary conflicting writable file HANDLE?

No real Ario memory, ledger, signer keys, genesis state, evidence admission, identity or production authority may be used.

## Negative controls (new, isolated tests)

1. **POSIX mapped ABA:** prepare two equal-length valid synthetic JSONL lines; prime a shared writable mapping by briefly writing/restoring line two *before* the reader's initial `fstat`, without flushing. On some Linux filesystems this leaves the mmap page dirty and subsequent stores do not advance `st_mtime_ns` / `st_ctime_ns`. Inside the existing held-FD read, perform **two actual `os.read` calls** with a mapped rewrite between them. The first W38 result is old line one + new line two. The reader's second pass obtains the same transient bytes; restore old line two immediately after the second pass and before W38's final `fstat`. The final file is old+old and the timestamp fingerprint may match all checkpoints.
2. **Windows preexisting mapping:** create a writable view, close the writable file handle, retain the view, and open the W41 read handle. Intercept **real** native `ReadFile` only to write transient replacement bytes through the preexisting view, then restore them after `ReadFile` but before the leaf path recheck. Whether the platform allows this is measured, not assumed. A refusal before any native ReadFile is not a bypass; a returned transient new image is RED; other scheduling is INCONCLUSIVE.
3. **Positive control:** unchanged synthetic receipt bytes must be returned exactly on both platforms.

In either negative test an observed bypass is deliberately recorded through `pytest.xfail("W43_VERIFIED_RED_...")`. **XFAIL is a reproduced weakness, not a successful guard.** When the mapped timestamp behavior does not satisfy the stated precondition, the POSIX probe SKIPs with a named reason rather than claiming success. Platform-specific Windows mapping interleavings may also be INCONCLUSIVE.

## Independent local prototype vs exact repository evidence

A separate Linux CPython 3.13.5 local prototype with W38-equivalent two-read and metadata-check logic accepted a transient mixed file image after mmap ABA; the final bytes and monitored `fstat` fields returned to their pre-read values. This is a **local reconstruction**, not yet proof from the exact repository W38 source. GitHub Actions execution of the test on this PR is the decisive repository-specific check; do not invent or pre-report its result.

The local prototype does not claim exploit of fixed W35 signed receipts, historical event authenticity, cross-artifact binding, or trusted admission. It checks only the bounded observation path.

## Interpretation and next decision gate

- Do not reinterpret passing CI with `xfail` as GREEN: inspect xfail messages for any reproduced bypass. 
- Do not merge diagnostic changes or patch the shared reader until Linux/Windows exact-head output and a falsifiable mitigation proposal have been reviewed.
- A double-read and local timestamps are *detection heuristics*, not proof that an adversarial writer cannot alter a shared mapping between checks.
- Consider an explicit immutability contract (writer-side atomic publish, sealed/custodied immutable content where supported, and separately retained content hash/freshness floor); each option requires its own threat-model limitations and tests. Exclusive Windows share flags alone do not necessarily revoke a preexisting writable map.
- Keep `historical_event_truth=UNKNOWN`, `evidence_admission=NOT_EVALUATED`, `cross_artifact_binding=NOT_ESTABLISHED`, `use_disposition=SUSPENDED`, `may_use=false`, and `GENESIS/TRUST_ACTIVATION/PRODUCTION=NO_GO`.

**Disposition at authoring:** DRAFT_HOLD / REPRODUCTION_PENDING_EXACT_CI.

## Phase 1 — exact repository CI evidence (initial diagnostic head)

Initial W43 head `2d9691ba2dbdd6b105ee6ed5109331cf0e664f20` in [Implementation Regression run 44944334169](https://github.com/SepehrGhanbari/Ario/actions/runs/44944334169):

- Linux Python 3.13: **1658 passed / 8 skipped / 1 xfailed / 273 subtests**. This branch introduces the one XFAIL path in `test_w43_posix_mmap_aba_torn_jsonl_not_silently_observed`, which marks acceptance of a transient mixed JSONL snapshot as `W43_VERIFIED_RED_POSIX`. The GitHub full regression's default terse mode does not display the XFAIL reason, so the follow-up focused workflow runs with `-rxs` for direct evidence.
- Linux Python 3.14 advisory: **1658 passed / 8 skipped / 1 xfailed / 273 subtests**. This is a second interpreter on Linux, not an independent filesystem or security certification.
- Windows Python 3.13: **1658 passed / 9 skipped / 0 xfailed / 273 subtests**. The first version returned normally when the W41 open was refused before `ReadFile`; it lacked an explicit SKIP reason. This was changed to a named SKIP in a subsequent diagnostic commit to avoid misinterpreting the early rejection as a demonstrated safe held-handle read.

**Initial evidence conclusion: `W43_POSIX_RED_REPRODUCED`, Windows outcome requires the focused explicit-reason replay.** No W43 mitigation has been proposed or integrated. The transient bytes are an ordinary untrusted local observation, not proved historical evidence or a signer authorization. This record is not a claim of bypassing cryptographically bound W35 receipts.
