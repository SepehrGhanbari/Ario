# W39 — native Windows ancestor-rename race probe

**Status:** RESEARCH_ONLY / DRAFT / NO_MERGE / NO_REAL_KEYS.

## Goal
Precisely examine the unclosed Windows ancestor-directory race left by W38's read-only public synthetic W35 receipt guard. No extension of trust, genesis, signer, production, memory, or evidence authority.

## Source evidence
- Base `main` at `3d2e17374359eb28778fbd74ec520215c0bb2a6b`.
- Reader: `implementation/research/w38_receipt_fd_guard.py`, blob `175462932cbc3f0d89d69318e2faa01f625b6284`.
- W38's `_read_windows` checks ancestor paths one at a time by native `CreateFileW`, closes each handle, and then opens the final file with `FILE_FLAG_OPEN_REPARSE_POINT`. It rejects final reparse points and compares the opened final object path with the requested lexical pathname. Those checks do not by themselves pin the identities of all ordinary parent directories throughout the operation.

## Controlled experiment
`test_win32_regular_parent_swap_at_leaf_open_is_not_misreported_as_safe` intercepts just the Win32 `CreateFileW` invocation that would open the receipt leaf. It renames the already-checked regular directory to a saved name and renames a second **ordinary directory** into the original name. No symlink/junction, administrative privilege, remote system or real secrets needed. It then calls the original Windows API.

If the reader returns the replacement directory's bytes, the test calls `pytest.xfail` with **W39_VERIFIED_RED**: a captured vulnerability, *not a security pass*. If the reader refuses the race, the test passes. If it cannot trigger the rename, it explicitly skips as untested rather than fabricating a result.

The second test checks normal exact bytes on Linux and Windows. All mutations stay inside pytest's temporary directory. No actual W35 proof hash is modified or promoted. A swapped public receipt still must pass W35's immutable SHA-256 pins to produce `VERIFIED_SYNTHETIC_INCLUSION`.

## Interpretation
- **VERIFIED:** only if hosted Windows runner shows the injected native API path and its resulting xfail/acceptance; Linux runs must skip the Windows probe.
- **NOT_ESTABLISHED:** general Windows race closure, live adversary scheduling, a real authorization bypass, in-place concurrent content stability, file hardlink origin, or rollback freshness.
- **Next possible correction:** Windows directory-relative native NT handles (`NtCreateFile` with `RootDirectory`) or another independently reviewed equivalent; do not claim a check/re-check-by-path sequence is atomic.

No changes to the W38 runtime reader in W39. This PR is a diagnostic research branch; do not silently merge a known vulnerability assertion or enable trust.
