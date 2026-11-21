# W38: Bounded receipt path opening under symlink/TOCTOU substitutions

**Research only. No ledger or M0 mutation; no trust, key, signer, Genesis or production activation.**

## Narrow scope and threat model

W37 reads four hard-pinned, public W35 test receipt files using its original `read_bounded_regular` helper. The pre-patch `Path.is_symlink()`/`Path.is_file()` checks and later `Path.open()` were separate operations. In a deterministic, synthetic local substitution, replacing a checked file with a symlink at `Path.open()` made that function read bytes from an outside file (RED). Those bytes still cannot become a verified W35 receipt unless they match the fixed SHA-256 pins; the observed problem was the file-read boundary, not an Ario trust escalation.

## Candidate and platform coverage

- W37 delegates its existing `read_bounded_regular` function name to `research/w38_receipt_fd_guard.py`; other receipt logic, proof/key/policy pins, ledger observers and result authority fields are unchanged.
- On POSIX with `O_NOFOLLOW`, `O_DIRECTORY` and `dir_fd`, walk **each absolute path component using the previous directory descriptor**. Open the final leaf using `O_NOFOLLOW|O_NONBLOCK`, validate `fstat` as regular, and read at most cap+1 bytes through the already-open file descriptor. The short window between pathname checks and a separate file open is eliminated for symlink components in this walk. This is not atomic snapshotting of file contents under concurrent writes.
- On Windows use `CreateFileW(FILE_FLAG_OPEN_REPARSE_POINT)` for the final leaf, inspect the opened handle attributes with `GetFileInformationByHandleEx(FileAttributeTagInfo)`, precheck ancestor directory reparse points, then compare the opened object's canonical final path with the lexical path via `GetFinalPathNameByHandleW` before bounded `ReadFile`. There is **no Windows `dir_fd` equivalent** in this implementation; swapping/replacing an ancestor concurrently between path checks and leaf open is **NOT_PROVEN_CLOSED**, and no claim of full Windows TOCTOU safety is made.
- Any unsupported POSIX no-follow support or invalid/linked/nonregular file is rejected; the caller reports `INVALID_OR_UNVERIFIED_RECEIPT` instead of granting authority. No arbitrary filesystem paths are authorized by hash equality alone.

## Deterministic tests / known exclusions

New focused tests cover: regular byte and CRLF preservation; exact cap and oversized input; invalid caps; symlink leaf and symlink parent refusal; missing/directory refusal; deterministic POSIX file and directory substitution **at the `os.open` call itself** (injection, no thread-timing dependency); FIFO nonblocking refusal; hardlinks allowed but **not** considered origin-proof. Symlink tests may be skipped on Windows installations without link-creation privileges. The native Windows branch requires actual Windows CI; local POSIX tests do not establish Windows security.

Existing W37 receipt checks, synthetic inclusion proof, Windows Git CRLF restoration and exact fixed file SHA-256 pins are unchanged. `W35` proof is not bound to real Ario event bytes. Successful W37 observation keeps `historical_event_truth=UNKNOWN`, `cross_artifact_binding=NOT_ESTABLISHED`, `evidence_admission=NOT_EVALUATED`, `use_disposition=SUSPENDED`, `may_use=false`, and `trust_activation/genesis/production=NO_GO`. Receipt path hardening does **not** address the separate ledger adapter's path and content observation races.

## Research disposition

Require exact-head Linux and Windows CI, source/implementation review of the native Windows handle calls, and independent mutation attempts before merging to `main`. Preserve the old code and RED evidence in Git history. This phase makes no claim about live external log freshness, historical completeness, stable file content under concurrent writes, Windows ancestor race closure, or hostile hardlinks.


## Actual cross-platform CI (candidate commit e8c338e)

The exact-head PR [Implementation Regression run 44936106437](https://github.com/SepehrGhanbari/Ario/actions/runs/44936106437) completed successfully:
- Linux (Python 3.13): **1634 passed, 2 skipped, 2 warnings, 227 subtests passed**.
- Windows (Python 3.13): **1631 passed, 5 skipped, 2 warnings, 227 subtests passed**. The additional three skips are POSIX-only tests (two descriptor-open race injections, one FIFO test); Windows symlink leaf/parent and regular-handle tests are included in the passing subset.
- Python 3.14 differential advisory: SUCCESS (full implementation regression).

These observations validate this host matrix, **not** a general proof against Windows concurrent ancestor replacement. In particular, the Windows branch still opens ancestors by pathname and checks their attributes before final leaf opening, so that concurrent interval must be treated as a separate unresolved risk.

API references: [Python os.open dir_fd](https://docs.python.org/3.13/library/os.html#os.open), [Microsoft CreateFileW with OPEN_REPARSE_POINT](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew).
