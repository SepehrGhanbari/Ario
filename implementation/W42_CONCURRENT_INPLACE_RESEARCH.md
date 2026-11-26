# W42 — simultaneous in-place mutations of synthetic receipt/JSONL data

**Phase 1: negative controls / reproduction only**. DRAFT / RESEARCH_ONLY / HOLD.

## Source and precise question

At main `d60688c68a746a48881897050adb7c7063d6c6aa`, W38's POSIX reader obtains `fstat` once before reading but does not validate file metadata after reading. W41's Windows leaf `NtCreateFile` currently passes `FILE_SHARE_READ|FILE_SHARE_WRITE|FILE_SHARE_DELETE` even for the file handle.

Question: can a local actor change *the same inode/file identity* during the active read while the local reader reports an ordinary `OBSERVED` JSONL manifest or accepted receipt bytes?

## Controlled synthetic diagnostics

- POSIX: read a two-record JSONL using **two real `os.read` calls** on one descriptor, with a fixed-length in-place write and flush/fsync between them. The synthetic result is line 1 from the old content, line 2 from the new content, neither the original all-old nor final all-new file. The baseline test marks `W42_VERIFIED_RED_POSIX` as an expected failure **only if** that mixed manifest was accepted.
- Windows: hold an actual writable `r+b` handle open while invoking W41's read-only helper. A successful read during the writer-handle conflict is `W42_VERIFIED_RED_WINDOWS`; no bypass of fixed W35 cryptographic pins is claimed. A second test injects a new writer open at the native `ReadFile` hook and demands the write be refused: it should be RED on baseline and GREEN only after correction.
- Uncontended bytes must remain exact; the entire experiment is local and uses synthetic temporary content only.

## Intended correction and acceptance gate

For POSIX, revalidate `fstat` identity, byte count, size and change timestamps after the read; re-read the same held descriptor and demand identical bytes/metadata. If any evidence of mutation is observed, raise a specific fail-closed error; W40's adapter maps it to `UNKNOWN`. This detects tested mutations, **not** an atomic snapshot guarantee.

For Windows, keep the W41 held-parent `RootDirectory` algorithm, but reduce the **file leaf** `ShareAccess` to `FILE_SHARE_READ`. File writer conflicts must lead to a refused open. Parent directories retain their original share modes for W39 rename tests.

A passing focused suite plus exact-head full Linux/Windows/Python 3.14 CI is required. Cross-process shared memory/file mapping, kernel file-system filter writers, timestamp ABA/restoration, malicious privileged writes, and historical source provenance remain NOT_TESTED or NOT_ESTABLISHED.

No code, signer, trust, genesis, identity, memory admission or production changes are authorized by a passing test.


## Phase 2 — bounded correction candidate and unchanged RED probes

The baseline W42 PR commit `9b25eee8757ebdaf1b6355cb3ed7c360df6eb5ba` is the unmodified W38/W41 runtime + newly added diagnostic tests. On real GitHub CI (run 44942236535), the Linux tests observed a torn JSONL and recorded `W42_VERIFIED_RED_POSIX` as an xfail, while Windows recorded a pre-existing-writer xfail and **failed** `test_windows_new_writer_blocked_while_leaf_handle_held` because a competing writer opened during the held leaf `ReadFile` operation. This is a real negative-control failure, not an authorization bypass.

The correction in the following commit leaves those tests **byte-for-byte identical**:
- POSIX `_read_posix` now checks `fstat` identity/size/write/change times both after the first read and after a second read on the same opened FD. The two reads must agree byte-for-byte. Otherwise fail closed with `CONCURRENT_MODIFICATION_DETECTED`. This detects the tested two-read write window but cannot guarantee absence of all races (ABA, malicious timestamp manipulation, unsupported mounts).
- Windows W41 `NtCreateFile` restricts **only the final regular leaf** to `FILE_SHARE_READ`. It fails when an existing writer is incompatible and blocks a newly opened writer that requests write access during the reader-handle lifetime. Existing directory HANDLE sharing remains unchanged, preserving the W39 rename replay.
- All outcomes remain research-only. The observer maps unsafe reads to UNKNOWN; valid W35 pins, ledger event parser, and downstream epistemic states are not modified. Mandatory exact-head Windows+Linux full CI and targeted mutation replay still apply.

Residual limitations: preexisting writable memory maps and file-system filter writes may not obey ordinary sharing; POSIX uncooperative writers can perform ABA between checks; this is **not proof of globally atomic disk content**, a stable event chronology, external freshness, or source custody.


## Phase 3 — exact-source RED/GREEN results and limits

**Baseline RED (before runtime changes):** [Implementation Regression 44942236535](https://github.com/SepehrGhanbari/Ario/actions/runs/44942236535) at `9b25eee8757ebdaf1b6355cb3ed7c360df6eb5ba`:
- Linux CPython 3.13: **1656 passed / 7 skipped / 1 xfailed / 273 subtests**. The POSIX two-real-read same-inode write recorded `W42_VERIFIED_RED_POSIX` because the resulting two-record mixed JSONL was accepted as OBSERVED.
- Windows CPython 3.13: **1 failed / 1654 passed / 8 skipped / 1 xfailed / 273 subtests**. The test `test_windows_new_writer_blocked_while_leaf_handle_held` failed with `['WRITER_OPENED_WHILE_READER_HELD']`. The existing writable-handle conflict was separately an xfail. This failed CI is preserved and not reported as PASS.

**Bounded correction:** source commit `174bcec886139fe86475916994dfb9dea55a6571`; unchanged diagnostic test Git blob `3f5ad1e2eab028fdd9ec9ef79d010725621f1c26`:
- [Implementation Regression 44942451503](https://github.com/SepehrGhanbari/Ario/actions/runs/44942451503) **SUCCESS**. Linux CPython 3.13 **1657 passed / 7 skipped / 2 warnings / 273 subtests**; Windows CPython 3.13 **1656 passed / 8 skipped / 2 warnings / 273 subtests**; Python 3.14 advisory **1657 passed / 7 skipped / 2 warnings / 273 subtests**. No W42 xfails/failures; positive W38/W41/ledger regression tests preserved.
- [Published TXT Restore Security run 44942451558](https://github.com/SepehrGhanbari/Ario/actions/runs/44942451558) runs independently; its result must be verified before integration, not assumed from implementation CI.

**Interpretation:** The previously reproduced POSIX mixed-byte acceptance and Windows conflicting-writer opening were blocked in the tested synthetic scenarios. POSIX metadata+double-read and Windows `FILE_SHARE_READ` do not establish atomic snapshots in the presence of all filesystem/privileged/remote/memory-mapped actors, timestamp ABA, or external custodial freshness. GitHub branch protection, trust and event authenticity stay separate.
