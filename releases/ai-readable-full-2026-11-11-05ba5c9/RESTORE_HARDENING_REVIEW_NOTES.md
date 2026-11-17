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
- **Confirmed on exact PR head 3626b215b1f208e99438dd20144a045a00b433b5**: the Unicode alias generator fixture passed on Ubuntu, and full pinned source generator→restore→Git-blob comparison passed on both Ubuntu and Windows. No macOS CI coverage; this policy prevents the known constructed alias but does not prove universal filesystem portability.

## Independently pinned manifest negative test and release decision

- Independent verifier verify_pinned_manifest.py does NOT import/call the restore consumer. It parses TXT records, checks payloads against a separately supplied manifest, and requires an explicit expected SHA-256. Scoped output: PINNED_MANIFEST_AND_SOURCE_BYTES_MATCH; PIN_CUSTODY_NOT_VERIFIED.
- Deliberately forged self-consistent TXT+manifest passes structural restore but fails verification against the ORIGINAL supplied pin. Changing the pin to the attacker's newly computed value would pass; external anchor custody therefore remains unresolved.
- Historical checksums.json has manifest SHA f86fb10ef3eb71dd6e3c348b3f0c9b42c88b3837ae889918c33d8f5d62fe11d8. CI uses this as a deterministic regression pin; it is not independent publication authority.
- The new generator includes the verifier and warnings in the newly built candidate ZIP; the historical checked-in RESTORE_FROM_TXT.py and old distributed files remain deliberately unchanged.
- GitHub Actions candidate artifact name: ario-05ba5c9-restore-review-candidate-unpublished.
- See RESTORE_PUBLICATION_DECISION_V0_1.md for no-overwrite release policy, reviewer gate and publication HOLD.


## Follow-up portability and producer/consumer policy parity (2026-11-17)

- **Win32 reserved-name alias:** CON .txt, COM1 .dat, AUX .log, and nested LPT2 .bin expose a naming edge because Win32 device-name checks may trim spaces from the basename portion before the extension. Restore, generator, and independent verifier now derive the reserved-name comparison key with split(".", 1)[0].rstrip(" ").upper(); original spelling is not rewritten.
- **Path-length policy parity:** all three paths now apply a 4096-byte full relative-path ceiling and a 255-byte UTF-8 component ceiling. This is a conservative policy cap, not a promise that every destination filesystem supports the full maximum once the user-selected parent directory is included.
- **Resource parity:** generator now caps file count, raw per-blob bytes, cumulative raw bytes, encoded payload bytes, manifest size, and final TXT size against the consumer's policy. It queries Git blob size before materializing each source blob and fails closed when a tracked source exceeds its configured ceiling. Raw and Base64-encoded per-record limits are distinct (64 MiB raw / 90 MiB encoded) because Base64 expansion is expected.
- **ZIP symlink semantics:** generator normalizes ZIP metadata for Git mode 120000 to regular-file mode 100644, preserving link-target bytes as ordinary file content. The README states that symlink semantics are not recreated. A real POSIX Git-symlink regression confirms that the ZIP entry is regular-file metadata and TXT restore does not create a symlink. The pinned source tree at commit 05ba5c960aaea96fc6bb80504b53b4d47e7d42f5 contains zero symlink blobs; this new test validates generic future-input behavior, not an existing item in the 204-file pinned archive.
- **Exact-head verification:** PR head 3626b215b1f208e99438dd20144a045a00b433b5. Published TXT Restore Security run [44082361685](https://github.com/SepehrGhanbari/Ario/actions/runs/44082361685) completed **10/10 jobs SUCCESS**: restore tests on Ubuntu/Windows × Python 3.11/3.12; manifest tests on Ubuntu/Windows × Python 3.11/3.12; full generator/restore/independent manifest verification/Git-blob roundtrip on Ubuntu and Windows. Implementation Regression run [44082361668](https://github.com/SepehrGhanbari/Ario/actions/runs/44082361668) also completed successfully.
- The restore workflow runs 74 test methods in each matrix cell. Linux reports 74 / OK, including the POSIX Unicode alias and symlink packaging fixtures. Windows reports 74 / OK (skipped=3); platform-specific POSIX fixtures are intentionally skipped, while Windows-specific reserved-name and source-limit tests run. CI success is not an independent human security review.
- A transient exact-head CI attempt exposed a Python syntax error in a new verifier test, then a missing-companion-file defect in the symlink test fixture. Both test-authoring defects were corrected; the cited successful run is against the corrected exact HEAD.
- **Still unresolved:** external custody/authenticity of the expected manifest pin; same-user concurrent filesystem destination races are not proven absent; macOS filesystem behavior is not directly tested; legacy checked-in RESTORE_FROM_TXT.py and already distributed historical ZIP/TXT are not retroactively repaired; no public artifact or DOI has been replaced.


## Base64 allocation-amplification defense (2026-11-16)

- Independent disposable Windows allocation probe: input 1,050,000 bytes of ASCII-white-space-separated Base64-like data reached a 43,882,417-byte Python traced-memory peak using `b"".join(payload.split())`, versus 1,050,033 bytes using `payload.translate(None, ASCII_WHITESPACE)`. This is a **resource-use amplification** even with per-record byte limits, not evidence of arbitrary code execution.
- Both hardened restore consumer and independently implemented pinned-manifest verifier now compact Base64 whitespace using bytes.translate instead of creating a list of tokens. Nonwhitespace invalid characters remain untouched and are rejected by `base64.b64decode(..., validate=True)`.
- Negative controls: bounded allocation under the ~1 MiB adversarial sample on both implementations; invalid non-whitespace character remains invalid; malformed non-UTF8 manifest is converted to controlled `VerificationError`.
- The verifier does not call the restore consumer; only the review test compares their resource behavior. Exact PR-head run 44082361685 passed all 10 jobs, and implementation regression run 44082361668 also passed. Candidate remains unpublished.


## Path-index memory amplification defense (2026-11-17)

- Audit found that a bounded TXT size and a per-path 4096-byte limit did not by themselves bound the memory cost of indexing every full path prefix. Repeatedly joining and retaining all prefixes can make stored prefix strings substantially larger than the path bytes in the input.
- Restore consumer, exporter, and independent manifest verifier now share explicit policy ceilings: maximum 128 path components, 100,000 unique indexed prefixes, and 8 MiB combined UTF-8 bytes of normalized prefix keys plus original prefix spellings. Exceeding a ceiling rejects the candidate before it can be published/restored. The exporter queries blob sizes before materializing blob content as before.
- The path-index implementation reuses the same normalized keys and original prefix strings in lookup sets where possible, rather than rebuilding a second copy of every prefix for the parent/file conflict sets.
- A separate normalized-prefix conflict check in the independent verifier was corrected: a previously recorded file at a Unicode-decomposed path must also block a child path under that NFC-equivalent prefix. The new regression verifies file-first / child-second rejection.
- New regression controls cover depth, index entry count, and aggregate index bytes in restore, generator, and manifest verifier.
- Exact PR HEAD: 771f39d522f8d6da1d7a6b28c86889f6418c505d. GitHub Actions [Published TXT Restore Security #44083268037](https://github.com/SepehrGhanbari/Ario/actions/runs/44083268037) completed **10/10 jobs SUCCESS**; [Implementation Regression #44083272246](https://github.com/SepehrGhanbari/Ario/actions/runs/44083272246) completed SUCCESS. Restore workflow reports **82 test methods / OK on Ubuntu** and **82 test methods / OK (3 platform-specific skips) on Windows**, in both Python 3.11 and 3.12 restore matrix jobs. Manifest and pinned roundtrip matrices also passed.
- Limits are explicit V1 candidate policy, not a general guarantee that all historical TXT snapshots satisfy the new bounds. macOS remains untested.



## Staged artifact publication and failed-build preservation (2026-11-17)

- Export generation now writes all files into a unique hidden staging directory under the release folder. The stage is cleaned on normal failure/exit. The final artifacts directory is not replaced until the ZIP, TXT, manifest, checksums, internal restore, and content checks have succeeded.
- If a previous artifacts directory exists, the exporter moves it to a unique backup slot, replaces the final directory with the completed stage, and removes the backup only after success. If the replacement fails, it attempts to restore the backup. This is staged, rollback-protected publication; it is not a claim of a zero-gap atomic exchange under concurrent writers.
- Repeated-build regression runs the generator twice against the same pinned Git source and confirms a byte-identical ZIP; no persistent restored-source tree is left inside artifacts.
- Failed-rebuild regression first creates a valid artifact set, then forces a late TXT-size failure. The prior ZIP/TXT remain byte-identical and no stage/backup directory remains. This guards against stale or partial artifacts being mistaken for the result of a failed build.
- Exact code/test HEAD: ba722299361ab52512190ed1a415fdee9c698e08. [Published TXT Restore Security #44084146677](https://github.com/SepehrGhanbari/Ario/actions/runs/44084146677) passed **10/10 jobs SUCCESS**; [Implementation Regression #44084146681](https://github.com/SepehrGhanbari/Ario/actions/runs/44084146681) passed. The restore suite ran **84 test methods** on Ubuntu (all pass) and Windows (all pass, 3 POSIX-only skips) with Python 3.11 and 3.12. Full generator→restore→independent-manifest→Git-blob roundtrip passed on Ubuntu and Windows.

