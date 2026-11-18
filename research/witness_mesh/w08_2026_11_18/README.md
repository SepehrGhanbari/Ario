# Ario Witness W08 — Offline read-only signature/trust boundary audit

No private keys, no signing, no network, no changes to Ario, no trust activation.

## Reproduce

Requirements: Python 3.10+ and Python package `cryptography`.

In this directory, run:

```bash
python -m unittest -v test_w08
```

The supplied `fixture_w22_excerpt.json` is a literal excerpt copied from the pre-existing PUBLIC SYNTHETIC W22 signed notes in `SepehrGhanbari/Ario` (branch `research/consensus-sprint-20261116`, Git blob `6aaf4b53e4f1e3e88556fcfbbbfddaef3445da8e`). The complete original Git file is not bundled. No witness-generated signature is bundled or verified. An existing note signed by the **log's own key** is not a witness cosignature.

`w08_signed_note_gate.py` checks strict format and existing Ed25519 log signature only. A correct signature is **never** treated as evidence of independently authenticated public key, external operator custody, latest-world freshness, source completeness, or authority. All results carry `status=HOLD_NO_EXTERNAL_TRUST` and `authority=NONE`.

`evidence/` records initial and corrected tests, final observations and upstream W07 regression. `SOURCE_MANIFEST.json` stores hashes for all files except itself. `REPORT_FA.md` explains limits in Persian.

*Important:* W27 already implemented a bounded synthetic cosignature/v1 verifier with 28/28 tests. This W08 is a limited, independently authored note parser and downgrade/fork/origin-confusion probe, **not** a replacement or new real witness audit.
