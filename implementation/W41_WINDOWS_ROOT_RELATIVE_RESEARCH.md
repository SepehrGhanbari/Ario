# W41 — stable Windows directory HANDLE / RootDirectory research

**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE; not trust activation.

## Problem and separate historical evidence

W39 [Draft PR #302](https://github.com/SepehrGhanbari/Ario/pull/302) reproduced a native Windows **ordinary directory** replacement at the final CreateFileW. W38 returned the substitute file bytes; W39 recorded this as **RED/xfailed**, not a passing security control. No pinned W35 proof, real Ario key or event truth was bypassed.

## Proposed bounded correction

- Retain W38's POSIX descriptor-relative reader unchanged. Delegate the Windows branch to the new `research/w41_windows_root_relative.py`, confined to synthetic public receipt and local JSONL observation inputs.
- Start from an existing local drive root; reject UNC/device/ADS and ambiguous trailing-space/dot paths rather than silently falling back.
- Open each single directory component with `NtCreateFile` using `OBJECT_ATTRIBUTES.RootDirectory` set to the **held previous directory HANDLE**. Require `OBJ_DONT_REPARSE`, `FILE_OPEN_REPARSE_POINT`, and reject opened reparse or incorrect directory type from native handle metadata. Open the final regular leaf relative to the retained parent handle, never by its unchecked full pathname.
- Compare opened leaf's final native canonical path to the requested lexical pathname **before and after** a bounded read. A directory renamed out of the nominated path before the final open must be refused instead of silently returning replacement bytes.
- Maintain W38's 16MiB guard cap and the unchanged fixed W35 proof pins, `may_use=false`, and `SUSPENDED`. W40 JSONL manifests remain local observation, not an authenticated history or evidence-admission authority.

## Falsification test

`tests/test_w41_windows_root_relative.py` reproduces **the same ordinary parent swap as W39**, but hooks the **final NtCreateFile** instead of the old CreateFileW. It requires a real native interception, observed replacement of ordinary directories, and a reported refusal. If the native hook never executes, the test must fail (no false green). A rename that cannot run is SKIP/NOT_TESTED; not proof. Other Windows cases cover normal exact bytes, size cap and unsupported path spellings. Existing Windows W38 and W40 tests must still pass.

## Important restrictions and unknowns

The Windows implementation calls an NT native API, which requires **actual Windows CI and external source review**. A normal CI pass alone is not a proof of arbitrary concurrent renames, alternate mount paths, filter drivers or hardlink provenance. `GetFinalPathNameByHandleW` normalization can vary with volumes and file systems; unsupported inputs fail closed. Concurrent **in-place writes** still do not produce a verified atomic historical snapshot; volume root namespaces and drive-letter remapping are not independently attested. No real keys, signer, trust, identity, memory admission, Genesis or production activation.

Sources: Microsoft Learn `NtCreateFile`, `OBJECT_ATTRIBUTES`, `GetFinalPathNameByHandleW`; status of specific returned fields must be tested and pinned to exact GitHub CI logs.

**Do not merge until the native Windows race test proves a triggered refusal and the full Linux/Windows suite passes.**


## Exact-head native Windows CI — actual W39 replay

[Implementation Regression run 44939412453](https://github.com/SepehrGhanbari/Ario/actions/runs/44939412453) was executed on the candidate head `fd95ae36511c766014ee8119277cf8f8aa53fdfa`:

- **Windows Python 3.13: 1653 passed, 7 skipped, 2 warnings, 273 subtests passed.** All three new W41 Windows tests ran and passed; the Windows-only W39-style interception is not marked xfail or skip. A true PASS of the race test requires that the hooked **native NtCreateFile** observed the leaf-component open, the ordinary parent was renamed/replaced, and the W41 reader returned an exception instead of bytes.
- **Linux Python 3.13: 1655 passed, 5 skipped, 2 warnings, 273 subtests passed.** W41's three Windows-only tests are explicitly skipped; the existing POSIX W38 tests continue to pass.
- **Linux Python 3.14 differential: 1655 passed, 5 skipped, 2 warnings, 273 subtests passed.**
- [Published TXT Restore Security run 44939412467](https://github.com/SepehrGhanbari/Ario/actions/runs/44939412467): **all 10 jobs successful**.

**Interpretation:** The exact W39 ordinary-directory rename at the final native open was **rejected** in the tested Windows runner. This resolves the specific earlier red test *for this profile and host*. It does not prove full concurrency immunity or historical provenance.

**Open scientific limits:** adversarial native filesystem reparse filter drivers, alternate volume mapping, Win32 case/8.3 alias resolution, post-read file edits, concurrent in-place content writes and file hardlinks are not exhaustively tested. The source remains read-only, synthetic/prospective and nonauthorizing. Check current-base CI after any documentation-only changes and never call this a production trust guarantee.
