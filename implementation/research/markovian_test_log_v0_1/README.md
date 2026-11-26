# Ario synthetic C2SP log — Markovian research witness v0.1

**RESEARCH_ONLY / SYNTHETIC_ONLY / NO_REAL_KEYS / NO_PRODUCTION / NO_TRUST_ACTIVATION.**

## Purpose

Prepare a small public C2SP transparency log that Markovian Protocol can manually pin and cosign. It reuses the already-created encrypted Ario Kladje research identity:

- Origin: \`github.com/SepehrGhanbari/Ario/kladje-test-v1\`
- Existing encrypted key: \`%USERPROFILE%\\Ario-Kladje-Research-v1\\research-log.private.pem\` on Windows
- No new identity or key is generated.

The same origin/key can later be submitted to Kladje once the Witness Network testing-list enrollment is accepted. Markovian pinning is manual and independent of that list.

## What is published

The public bundle contains only:
- \`capsule.json\`: three fictional synthetic memory records;
- \`entries\`: newline-delimited synthetic log leaves;
- \`checkpoint\`: the log-signed C2SP tlog-checkpoint note;
- \`vkey.txt\`: the C2SP Ed25519 verifier-key line;
- \`manifest.json\`: hashes and public metadata.

The encrypted private key is read locally and never copied into the output directory, ZIP, GitHub, or email. The passphrase is prompted without echo. The script does not generate or replace a key.

## Commands on the desktop test PC

Install the dependency if needed:

    python -m pip install cryptography==46.0.4

From the repository root, run:

    python implementation/research/markovian_test_log_v0_1/markovian_test_log.py prepare

This reads the existing encrypted research key at its default path and creates:
- \`%USERPROFILE%\\Ario-Markovian-Test-v1\\\`
- \`%USERPROFILE%\\Ario-Markovian-Test-v1.zip\`

The command prints the exact vkey line and public checkpoint hashes. It sends no network request.

Verify offline:

    python implementation/research/markovian_test_log_v0_1/markovian_test_log.py verify

Append a second synthetic leaf only after the first checkpoint has been published and Markovian has cosigned it:

    python implementation/research/markovian_test_log_v0_1/markovian_test_log.py append

The append command signs a larger checkpoint and keeps the previous checkpoint in the local history folder. It sends no network request.

## Publication and witness sequence

1. Prepare and verify the bundle locally.
2. Share only \`Ario-Markovian-Test-v1.zip\` with the project maintainer for publication at the fixed public raw-GitHub URLs.
3. Send Markovian the exact \`vkey\` line and public \`checkpoint\` URL (and \`entries\` URL for independent root reconstruction).
4. Wait for Colin/Markovian to confirm that the origin/key is manually pinned.
5. Only then run:

       python implementation/research/markovian_test_log_v0_1/markovian_test_log.py submit

The submit command first reads the witness's public checkpoint. It checks the witness cosignature against the operator-published Markovian witness vkey, checks that the witness's current root is a prefix of the local log, computes the RFC 6962 consistency proof, and sends one \`add-checkpoint\` POST. It does not retry automatically. A 404 is reported as \`HOLD_ORIGIN_NOT_PINNED_BY_MARKOVIAN\`; a 409 requires a fresh manual review rather than blind retry.

After a successful response, the script verifies the returned cosignature and writes \`checkpoint.cosigned\` plus \`witness-cosignature.txt\`. These files contain public evidence only.

## C2SP formats and limits

- Log verifier key: signed-note vkey, Ed25519 signature type \`0x01\`.
- Checkpoint: C2SP tlog-checkpoint note.
- Witness cosignature: C2SP tlog-cosignature/v1, Ed25519 signature type \`0x04\`.
- Submission framing: C2SP tlog-witness \`POST /add-checkpoint\`.

The test witness vkey is pinned from Markovian's operator-published \`/about\` page, not learned from the log:
\`markovianprotocol.com/witness+41b8827f+BJKLl8rBYM0oUxSaWh9rjTldTprEpYj/SWVIGgacA9XC\`.

A cosignature means the witness checked the checkpoint signature and append-only consistency at the time of signing. It does not establish that the synthetic records are true, that Ario memory is semantically correct, or that the witness and log are under independent global administration.

## Test

From the repository root:

    python -m pytest -q implementation/tests/test_markovian_test_log_v0_1.py

No live network request, Markovian submission, Kladje request, real Ario signer key, personal memory, or production state is used by tests.
