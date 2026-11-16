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
- Generator validates ZIP and TXT content; hardened consumer restores TXT; independent verifier compares every restored path and byte sequence against Git blob objects.
- GitHub Actions run #51 passed 10/10 jobs on the original hardening baseline.
- Follow-up run #78 passed 10/10 jobs after the additional path validation and expanded restore tests: Ubuntu/Windows × Python 3.11/3.12 for restore and manifest tests, plus full generator/restore/independent Git-blob roundtrip on both Ubuntu and Windows.
- Baseline restore regression suite: 27 tests; follow-up adds Windows-invalid-name and source-authenticity-label tests (29 tests PASS in isolated local Windows scratch). Fresh CI on the follow-up HEAD remains necessary.
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
