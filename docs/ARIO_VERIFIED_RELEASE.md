# One-command Ario release verification (research-only)

This is a proposed independent entry point for the 11 November 2026 204-file release. It does not modify the accepted R1.4 verifier or the historical ZIP/TXT. Use a trusted, separately obtained copy of the launcher and verifier. A clone or browser download is deliberately **not** configured to execute programs. A Git clone's object-integrity checks alone do not attest the publisher or the complete working tree.

## Usage

Python 3.10+; standard library only. From the trusted checkout/package root:

```sh
# Automatically download and verify all three assets in a fresh directory.
python -I -B scripts/ario_verified_release.py download --directory .
# Automatically check the three release assets already present in the checkout.
python -I -B scripts/ario_verified_release.py
# Check already downloaded files in a chosen directory without writing to it.
python -I -B scripts/ario_verified_release.py check --directory /path/to/downloads
# Download or verify only a selected known asset.
python -I -B scripts/ario_verified_release.py download --directory . --asset ario-full.zip
```

`--directory` must be an existing directory. The default check directory is `releases/ai-readable-full-2026-11-11-05ba5c9` within the trusted launcher's checkout, not the current working directory. For checking an untrusted checkout, use a separately trusted launcher and explicitly select the checkout's release directory. An ordinary clone is not a verification trigger. Do not execute code from a received archive.

The launcher checks the reviewed R1.4 source SHA-256 before writing a private temporary copy for isolated execution. It downloads selected allowlisted assets from the fixed GitHub publication commit, requests identity encoding, rejects unsupported framing, and uses the exact R1.4 CLI on each local asset. The launcher requires its complete expected live-match result including repository, commit, registry pin, asset, size, digest and exit code. An unverified caller-supplied reference cannot satisfy the gate. Download creates a new directory, never overwrites existing files, and returns that directory as accepted only after all selected assets pass. On a normal failure it removes only the newly created download directory; interruption, cleanup failure, or hostile local changes can leave unaccepted data. Do not use an unfinished directory. Check mode makes no modifications to input assets.

Exit 0: `ALL_SELECTED_RELEASE_ASSETS_MATCH`; 2: `REJECTED`; 3: `UNKNOWN`. Unknown, failed, or interrupted runs must not be treated as successful. Matching describes the bytes read; reverify before later use if files are mutable. The trusted launcher, runtime, OS and TLS trust store are assumptions. The network download has blocking-operation timeouts, not a global deadline; the R1.4 child has a 90-second process timeout. The helper covers exactly these three release assets, not arbitrary versions, the whole clone, DOI file equivalence, independent publisher identity, or independent pin custody. No restore, execution of received data, production activation, keys, signing, or memory changes.

## Evidence for this proposal

Linux/Python 3.13: eleven offline test methods passed, including real CPython HTTP body decoding with synthetic socket input, rejection of altered verifier source, wrong child results, failure cleanup and preservation of existing files. Mocked successful child responses are tests of orchestration only, not live evidence. The live download attempt for the manifest returned UNKNOWN because HTTPS was unavailable in the execution environment. No fresh Windows or end-to-end HTTPS success is claimed for the launcher. R1.4 itself has the separately recorded prior Windows live verification of all three published assets. The accepted R1.4 source is byte-identical to the reviewed pin `fac354c46e8fc8ce68edf6202980aa974ab3f0319cfe0e8272b5c688330b432b`.

Run focused tests from `scripts/`: `python -B -m unittest -v test_ario_verified_release`.

## Subsequent Windows validation (2026-11-24)

The owner-supplied Windows terminal result for the unchanged launcher reported `ALL_SELECTED_RELEASE_ASSETS_MATCH`, exit 0, all three exact SHA-256 values and `HTTPS_GITHUB`. The earlier unavailable-HTTPS observation above is historical. See [combined closeout](verification-coverage-evidence/README.md). This does not authorize execution or restore of the received archive.
