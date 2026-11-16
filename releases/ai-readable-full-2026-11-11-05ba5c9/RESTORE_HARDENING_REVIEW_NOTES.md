# Restore hardening proposal — review only

- Fail-closed staged restore validates header/footer count, commit, tree, total bytes and manifest digest token.
- Every record validates payload length, SHA-256 and Git blob SHA-1.
- Rejects POSIX traversal, Windows drive/UNC/backslash paths, reserved device names, trailing dots/spaces, colon, duplicate and case-colliding paths.
- Publishes only after complete validation; never overwrites an existing destination.
- Git symlink blobs are materialized as regular files, never filesystem links. Safe but not semantics-preserving.
- Manifest limitation: TXT contains a manifest SHA-256 but not manifest bytes. Header/footer equality does not prove that digest belongs to a manifest. Future format must embed or independently supply the manifest.
- The generator should read the hardened canonical restore source; its duplicate embedded implementation has been removed in the proposed patch.
- ZIP timestamps fixed for deterministic packaging.
- GitHub Actions run #3 passed on ubuntu-latest and windows-2022 with Python 3.11 and 3.12 (four matrix jobs). This verifies the focused restore regression suite on those runners, not a full artifact roundtrip.
- No main changes, merge, trust activation, Ruleset or key changes.
