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
