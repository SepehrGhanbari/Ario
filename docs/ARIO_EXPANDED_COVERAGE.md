# Ario expanded verification coverage — research-only

The existing verified-release launcher and exact R1.4 source are preserved. A separate read-only tool, `scripts/ario_verify_coverage.py`, covers checkout raw file bytes and local Zenodo record files. Use a separately trusted copy of this package; do not execute code from the directory under inspection. No installation hooks, no runtime integration, no execution of inspected content, no write to input directories.

## Checkout

```
python -I -B scripts/ario_verify_coverage.py checkout --directory "PATH_TO_ARIO_CLONE"
```

Default pinned commit `d12d511e0ae1a19560a13dadaafb77a700fd20ef`, tree `d101d77191f4df34538c8385538655fc053e4616`: 456 regular tracked files, 96,284,142 bytes, 81 directories, according to the public repository tree read through the GitHub connector on 2026-11-24. No special modes or case-insensitive path collisions were observed in that tree. The tool retrieves the commit and recursive tree from the fixed GitHub API origin, rejects a truncated response, checks the pinned root and reconstructs every Git tree object ID. For each expected regular file it recomputes the Git blob SHA-1 object ID from raw bytes. No local Git metadata or configuration is executed or trusted. Extra paths (including untracked files and ignored outputs) are reported and prevent a clean match; root `.git` is excluded entirely. Line ending conversion, modified worktrees and missing paths can legitimately fail the exact-byte check. This is not a Git history, executable mode, Git LFS materialization, or atomic filesystem snapshot check. Git object IDs are SHA-1, not independent SHA-256 attestation; no collision-resistance guarantee beyond that format. Symlinks and reparse points in inspected paths are refused. Ancestors of the selected root, OS, runtime and TLS store are environmental assumptions.

To select a different version explicitly, pass `--commit FULL_40_HEX_COMMIT`. For this option the tree ID is obtained from the live GitHub commit response, not independently pinned in the verifier. Unsupported objects (submodules, symlinks), excessive sizes, malformed or truncated metadata cause UNKNOWN. The default fixed pin does not silently move with main.

## Zenodo DOI records

```
python -I -B scripts/ario_verify_coverage.py doi-catalog
python -I -B scripts/ario_verify_coverage.py doi-check --directory "PATH_TO_LOCAL_DOI_FILES"
python -I -B scripts/ario_verify_coverage.py doi-check --directory "PATH_TO_LOCAL_DOI_FILES" --record 24136175
```

The allowlist is the 15 record IDs already in the accepted R1.4 bibliography: 23259916, 23326995, 23375350, 23375401, 23376521, 23376577, 23441596, 23600820, 23651704, 23771218, 24041161, 24054535, 24136175, 24230572, 24343618. This is coverage of known listed records, not automatic discovery of every future deposit. The catalog reads metadata, verifies exact record ID and DOI (not a concept DOI), and lists names/sizes/MD5. Catalog success is METADATA_ONLY (exit 3), never a byte-match claim. A record with unavailable or unsupported metadata remains UNKNOWN.

Place files already downloaded by the user under `PATH_TO_LOCAL_DOI_FILES/<record-id>/<exact-filename>`. The check hashes local bytes, streams each official record file from the fixed Zenodo HTTPS content endpoint, checks byte count and metadata MD5, and compares the two SHA-256 digests. Metadata MD5 alone is not acceptance. Extra local DOI files outside the server's file list are not covered. No redirects followed; inaccessible content, concept DOIs, unsupported naming or framing, and files beyond limits (512 MiB/file, 2 GiB/record) remain UNKNOWN. No credentials sent. A missing required local file is REJECTED. The tool does not map a Zenodo deposit to a Git commit or establish DOI-to-GitHub equivalence, identity, or independent custody. Network timeouts are per blocking operation, not a global deadline.

Exit 0 only for exact matched scope, exit 2 rejected, exit 3 unknown or metadata-only. Do not interpret any result as permission to execute. No remote repository mutation or trust activation. No write to local examined files. The original verified release launcher still covers the three pinned 204-file release assets, not arbitrary historical exports.

## Evidence

Linux: 25 new offline tests plus 11 existing launcher tests passed (36 total). Synthetic network fixtures test orchestration, not real HTTPS. The actual current GitHub tree inventory was independently read via the connector; the expanded tool's direct GitHub API and one Zenodo metadata attempt returned UNKNOWN in this environment. Actual checkout and Zenodo byte checks and Windows behavior remain unvalidated. User-supplied earlier Windows output for the unchanged three-file launcher reported ALL_SELECTED_RELEASE_ASSETS_MATCH, exit 0, all three expected SHA-256 values. This is not evidence for the expanded modes. No claim of independent reviewer approval or production readiness.

Run offline tests from `scripts/`: `python -B -m unittest -v test_ario_verify_coverage test_ario_verified_release`.

## Subsequent Windows validation (2026-11-24)

Owner-supplied results: the pinned checkout matched 456/456 raw files, 96,284,142 bytes, no extra paths and no reported problems. All 79 record/file entries across the 15 listed Zenodo records matched separately retrieved HTTPS content by SHA-256. The bulk downloader `python -I -B scripts/run_doi_bulk.py` creates a fresh output directory in the current directory and repeats the DOI byte check; its GitHub mapping separately compares Git SHA-1 blob ID and size (54 mapped, 25 without a match in the pinned tree). No direct GitHub SHA-256 match is asserted. See [combined closeout](verification-coverage-evidence/README.md) and the public result copies. The earlier limitations above on live validation describe the earlier Linux run.

The fixed default remains the tested pre-admission commit, not the new `main`. For later commits use `--commit` with the exact desired full commit SHA, from a separately trusted verifier checkout. Raw checkout bytes require no checkout newline conversion (e.g. `git -c core.autocrlf=false checkout --detach FETCH_HEAD`). The verifier does not treat a normal clone or download as an execution trigger.
