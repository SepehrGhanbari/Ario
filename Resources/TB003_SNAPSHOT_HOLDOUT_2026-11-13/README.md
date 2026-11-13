# TB-003 Snapshot-Custody: proposed alternative semantics and blind-test protocol

**Research-only, 2026-11-13. Nothing here changes the existing TB-003 contract or source code.**

Linked research review: [#198](https://github.com/SepehrGhanbari/Ario/issues/198), [#196](https://github.com/SepehrGhanbari/Ario/issues/196), [#129](https://github.com/SepehrGhanbari/Ario/issues/129), and [Draft PR #197](https://github.com/SepehrGhanbari/Ario/pull/197).

This experiment distinguishes two questions:

- **H_E (existing path observation):** does a supported, acyclic laboratory custody path connect a capture custodian and nominated holder? An off-path transfer does not automatically disprove that a past path existed. Current TB-003 tests intentionally accept some short off-path fanouts.
- **H_S (new proposed snapshot-final model):** given a complete, exclusive-token synthetic transfer log and a specific snapshot sequence, is the declared holder the *unique final custodian*, after every in-scope transfer has been applied? If not, return mismatch/unknown and never advertise final holder certainty.

These are alternative tasks, not a proven defect in the old evaluator. Under H_S we also require complete transfer history (separate from control/source completeness), both witnesses' custody exposure, and separate source/admin independence verdicts.

**Bounded witness-B rule for v0.1:** Witness B has a single declared LAB capture and direct hold by P2, without transfer events. Both the reference oracle and evaluation adapter reject any challenge that supplies `other_witness_custodians` other than `["P2"]`. Therefore this pilot cannot claim to evaluate arbitrary two-witness custody histories; a later version must add explicit B-transfer events and separately adjudicate them. The future hidden holdout must obey this restriction or be preregistered as a new schema.

## Files

- [PREREGISTRATION.md](PREREGISTRATION.md): definitions, falsifiers, planned blind experiment, expected directions, and failure criteria.
- [reference_oracle.py](reference_oracle.py): pure-stdlib *proposed* H_S decision procedure for bounded synthetic cases. Its labels are NOT real-world ground truth.
- [blind_runner.py](blind_runner.py): read-only historical TB-003 evaluator adapter; consumes challenge cases without importing expected labels.
- [public_controls.json](public_controls.json): **18 OPEN development cases**. These were constructed by our own research process; NOT a blind holdout.
- [test_reference_oracle.py](test_reference_oracle.py): fixed asserted outcomes for the public controls.

## Public controls and execution

```sh
python -B test_reference_oracle.py
python -B blind_runner.py public_controls.json
```

The second command fetches pinned public source from GitHub, then verifies SHA256 and Git blob SHA1 before running in memory. For a network-free test, pass `--source-file` pointing to an **exact-byte matching** evaluator snapshot. It does not require private credentials or alter the user's local repository. It emits observed outcomes only; no answer-key file is loaded. Do **not** call these controls a blind validation.

For each input, compare H_S reference outputs to old evaluator output **as a difference in semantics**, not automatically an existing code failure. This package does not make M0 evidence, certify identities, prove an event happened, or activate signer/trust/production.

## Critical methodological correction

CodeRabbit observed that PR #197's control C07 used P2, who also held witness B, confounding whether the compromise was off-path for witness A. The new public cases use **P4** as an exclusive target to remove that specific confound. The historical C07 observation remains retained unchanged. [Independent critique](https://github.com/SepehrGhanbari/Ario/pull/197#issuecomment-6855474526).

**HOLD:** no changes to old tests, protected implementation, source artifacts, provenance authority, governance, archives, or main. This PR is a research proposal pending reviewer and owner governance checks.
