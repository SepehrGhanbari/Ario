# Restore hardening and reproducibility review — review only

## Restore hardening
- Fail-closed staged restore validates header/footer record count, commit, tree, total bytes and manifest digest token.
- Every record validates payload length, SHA-256 and Git blob SHA-1.
- Rejects POSIX traversal, Windows drive/UNC/backslash paths, reserved device names, trailing dots/spaces, colon, duplicate and case-colliding paths.
- Rejects non-canonical path spellings and invalid UTF-8 path strings.
- Publishes only after complete validation; never overwrites an existing destination.
- Git symlink blobs are materialized as regular files, never filesystem links. Safe against link creation but not semantics-preserving.

## Manifest V3
- `papers/creation-without-sovereignty/2026-11-11/PUBLIC_PACKAGE_FILE_MANIFEST_V3.json` is a review candidate built from exact Git blob objects at source commit `2e7f83c6c7518012bed7fedfb12103ce9b7222ea`.
- V2 remains unchanged as historical record.
- Four V2 entries are corrected; their prior byte counts and hashes match an LF-to-CRLF transformation, while V3 records exact Git blob bytes, SHA-256 and Git blob SHA-1.
- Canonical builder and unit tests: `scripts/build_public_package_manifest_v3.py` and `scripts/test_public_package_manifest_v3.py`.
- CI verifies the generated V3 against the committed Git blob, avoiding checkout newline conversion.

## End-to-end artifact verification
- Generator uses the pinned release source commit `05ba5c960aaea96fc6bb80504b53b4d47e7d42f5`.
- Generator validates ZIP and TXT content; hardened consumer restores TXT; independent verifier compares every restored path and byte sequence against Git blob objects.
- GitHub Actions run #45 additionally passed the review-baseline snapshot roundtrip: 280 Git blobs / 94,812,023 bytes, exact paths and bytes, executable modes checked.
- GitHub Actions run #51 passed 10/10 jobs: restore matrix (Ubuntu/Windows × Python 3.11/3.12), manifest builder matrix (same), and generator roundtrip on Ubuntu and Windows.
- Run #51 predates the latest additional path-validation regression cases; a follow-up run is pending.

## Remaining limitations
- TXT contains a manifest SHA-256 token but not the manifest bytes; matching header/footer values do not independently authenticate the digest against a manifest. A future format revision or independently supplied manifest is still needed.
- Symlink semantics are not preserved by restore; symlink blobs become regular files.
- V3 remains a review candidate; no external DOI or Zenodo record has been replaced or republished.
- No main changes, merge, trust activation, Ruleset or key changes.
