# Restore hardening and reproducibility review — review only

## Restore hardening
- Fail-closed staged restore validates header/footer record count, commit, tree, total bytes and manifest digest token.
- Every record validates payload length, SHA-256 and Git blob SHA-1.
- Rejects POSIX traversal, Windows drive/UNC/backslash paths, reserved device names, trailing dots/spaces, colon, Windows-invalid filename characters (`<>\"|?*`, controls U+0000–U+001F), duplicate and case-colliding paths.
- Rejects non-canonical path spellings, invalid UTF-8 path strings, case-colliding directory components, and file/directory path conflicts.
- Publishes only after complete validation; failed restores clean their staging directory and do not publish a partial destination.
- Git symlink blobs are materialized as regular files, never filesystem links. Safe against link creation but not semantics-preserving.

## Manifest V3
- `papers/creation-without-sovereignty/2026-11-11/PUBLIC_PACKAGE_FILE_MANIFEST_V3.json` is a review candidate built from exact Git blob objects at source commit `2e7f83c6c7518012bed7fedfb12103ce9b7222ea`.
- V2 remains unchanged as historical record.
- Four V2 entries are corrected; their prior byte counts and hashes match an LF-to-CRLF transformation, while V3 records exact Git blob bytes, SHA-256 and Git blob SHA-1.
- Canonical builder and unit tests: `scripts/build_public_package_manifest_v3.py` and `scripts/test_public_package_manifest_v3.py`.
- CI verifies generated V3 against the committed Git blob, avoiding checkout newline conversion.

## End-to-end artifact verification
- Generator uses pinned release source commit `05ba5c960aaea96fc6bb80504b53b4d47e7d42f5`.
- Generator path validation now rejects the same Windows-invalid characters and control characters as the restore consumer; `test_make_export_path_policy.py` exercises invalid Git paths on POSIX and is skipped on Windows, where those filenames cannot be created.
- Generator validates ZIP and TXT content; hardened consumer restores TXT; independent verifier compares every restored path and byte sequence against Git blob objects.
- GitHub Actions run #51 passed 10/10 jobs on the original hardening baseline.
- Follow-up run #78 passed 10/10 jobs after the additional path validation and expanded restore tests: Ubuntu/Windows × Python 3.11/3.12 for restore and manifest tests, plus full generator/restore/independent Git-blob roundtrip on both Ubuntu and Windows. The latest follow-up PR-head run is recorded separately above.
- Restore regression suite: 29 test methods. The added generator-path parity regression also passes on Ubuntu; its POSIX-only fixture is skipped on Windows. The latest PR-head GitHub Actions run `43923055510` passed all 10 jobs, including the restore and manifest matrices and full Ubuntu/Windows artifact roundtrip.
- The run #57/#63 attempts exposed authoring defects in the added tests and generator initialization (literal escaped newline and missing RESERVED/path-set initialization). Those defects were corrected; run #78 is the successful verification of the corrected code.
- The pinned release artifacts were downloaded and independently rechecked locally: ZIP integrity, all 204 Git blob SHA-1/SHA-256 entries, and TXT consumer restoration all passed.

## Remaining limitations
- TXT contains a manifest SHA-256 token but not the manifest bytes; matching header/footer values do not independently authenticate the digest against a manifest. A future format revision or independently supplied manifest is still needed.
- Successful consumer output is `RESTORE_STRUCTURAL_PASS_AUTHENTICITY_UNKNOWN` (replacing misleading `RESTORE_VERIFIED`). Internal hash and record agreement is NOT authentication or external manifest verification; no producer-identity or truth claim is made.
- Symlink semantics are not preserved by restore; symlink blobs become regular files.
- V3 is a review candidate; no external DOI or Zenodo record has been replaced or republished.
- No claim of full source-selection reproducibility: private-source selector material remains unavailable/UNKNOWN.

## Repository boundary
- No main edits, merge, trust activation, Ruleset or key changes were performed.
- Main has since advanced six commits beyond the original review base; the review branch is intentionally not rebased automatically.

## Resource-bounded intake follow-up (research candidate; 2026-11-16)
- **Reproduced before fix in disposable Windows scratch** at base HEAD `f83b76b`: a 1 MiB ignored header and 1 MiB unused record JSON field were silently accepted; a forged `payload_bytes=1099511627776` (1 TiB) reached a huge `f.read` request and raised `MemoryError`, not a controlled `SnapshotError`. No user file/destination was exposed, and no heap-size claim is inferred.
- Proposed default bounds: input file 384 MiB; entire header 16 KiB with 4 KiB per header line; record header 64 KiB; footer 512 bytes; file count 10,000; raw tracked total 256 MiB; raw/payload per record 64 MiB; path UTF-8 4096 bytes. Reject declarations and framing before large reads; check cumulative raw count; consume at most one byte when checking for trailing data.
- **Independent local follow-up**: 38/38 unittest methods PASS on Windows (29 original, 9 new resource controls). The three reproduced bad inputs now raise `SnapshotError` and clean staged output; an ordinary valid synthetic archive still restores. Source + tests are a *candidate* pending exact-HEAD CI.
- Compatibility anchor: published snapshot commit `05ba5c960aaea96fc6bb80504b53b4d47e7d42f5`, 204 files, 16,183,258 raw tracked bytes, largest tracked file 2,857,981 bytes, full TXT 17,751,878 bytes. Exact-head Ubuntu/Windows generator→restore roundtrip must pass before treating the candidate as compatible with that snapshot.
- These are V1 **consumer policy caps**, not permission to reinterpret old snapshots. Larger future archives require a separately reviewed explicit limits policy. Neither resource bounds nor blob digests prove external source authenticity, prevent same-user filesystem interference or authorize deployment.

## Duplicate-key JSON provenance guard (2026-11-16)
- **Independent RED reproduction** on exact previous HEAD `b836ebec233cc2baae72e5df4588a5161b2a73c6`: a synthetic record header containing two JSON `path` keys (`../unsafe.txt` then `valid.txt`) was accepted by Python `json.loads` last-wins and restored `valid.txt`. This did **not** demonstrate a directory traversal, but did demonstrate ambiguous provenance-sensitive metadata being silently accepted.
- **Candidate GREEN:** reject duplicate JSON object keys using `object_pairs_hook` at every depth; reject `NaN`/non-JSON constants with `parse_constant`; reject dot-only path before staging. Five additional negative unittest cases: duplicate `path`, duplicate `sha256`, nested duplicate, nonfinite constant, dot-only filename.
- **Independent scratch result:** original 38 tests + five added = 43/43 PASS on Windows; the prior duplicate-`path` reproducer now raises controlled `SnapshotError` with no restored destination. Exact-head GitHub CI and full pinned roundtrip pending. This strictness is an explicit review-candidate behavior for the published V1 consumer, not a retroactive claim about all historical snapshots.

## Unicode-normalization path alias guard (2026-11-16)
- **Independent RED reproduction** on Windows against earlier candidate: `é.txt` and `e\u0301.txt` are different byte strings but have the same Unicode NFC comparison key; both were accepted and restored as two files on NTFS. Potential equivalence on normalization-insensitive filesystems (e.g., some macOS configurations) is a portability threat model, **not empirically demonstrated here on macOS**.
- **Conservative candidate policy:** preserve each original path spelling and bytes, but compare full paths *and all directory components* by `NFC(casefold(path))` for collision rejection. Apply exactly the same check in generator and restore consumer; do not silently normalize or merge files.
- **Windows local GREEN:** `python -B -m unittest -q test_restore_from_txt.py test_make_export_path_policy.py`: **48 tests OK / 2 POSIX-only skips** (46 PASS). Added two NFC-collision rejection controls and one positive distinct-name control for the consumer; generator's new POSIX-only Git fixture checks rejection of same-NFC source names. `unicode_path_probe.py` formerly accepted two files; now rejects them before publication.
- **Linux/POSIX generator fixture execution and exact-head pinned artifact roundtrip must be confirmed in GitHub Actions**. No macOS CI coverage; this policy prevents the known constructed alias but does not prove universal filesystem portability.
