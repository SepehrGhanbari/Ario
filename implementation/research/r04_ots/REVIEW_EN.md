# Ario R04 OpenTimestamps — independent research review

**State: `DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO`.** This is an additive research archive, not a new signer, time source, memory admission path or operational checkpoint custodian.

## Claims worth falsifying

1. The archive includes the **exact original 613-byte synthetic JSON** (SHA256 `c37da68d045da9c85a90dc679857c017ed0bbd1454e51d9033ef9a48e799a68a`) and the **549-byte pending OTS receipt** (SHA256 `5b7fc36d470560adbc8fd4620436451ea43ea0578bf50e7ca6104ce0280c3bf6`). The receipt is encoded as base64 for safe text-only storage; decode to obtain its original binary bytes. Compare against [earlier issue #280 base64](https://github.com/SepehrGhanbari/Ario/issues/280#issuecomment-6990276287), not only against constants in our verifier.
2. The real original submission requested timestamps from Alice, Bob and Finney public calendars using `opentimestamps-client==0.8.0`. Three `PendingAttestation` paths are present. A separate live check on 2026-11-18 still yielded pending at all calendars.
3. The **offline** `audit_archive` checks byte identity and conservative fixture fields. It **does not parse or cryptographically verify an OTS Merkle path or Bitcoin block**. Never treat `EXACT_ARCHIVED_BYTES_MATCHED` as finality.
4. `compare_external_floor` is a pure toy comparison. A lower `last_seq` compared with an authentic externally retained floor is rejected; if one publisher can replace both history and floor, rollback is **not** detected. Equal seq/hash is **not** a freshness proof; higher seq without a consistency proof is held.
5. Self-claimed signatures, a verified digest, and three calendar URLs do not demonstrate administrator independence, witness nonextractability, complete history, authenticity of history data or trusted event time.

## Reproduction

```bash
python implementation/research/r04_ots/verify_r04.py
cd implementation && python -m pytest -q tests/test_r04_ots_archive.py
```

Archive verification works with Python standard library and does not require networking. For optional online CLI status checking, supply `--ots /path/to/ots` to the verifier after independently validating the executable and its Bitcoin data source. Its output is separately tagged `OTS_CLI_REPORTED_SUCCESS_SOURCE_NEEDS_REVIEW`, **not** evidence admission.

Reconstruct the binary proof with Python:

```python
import base64
from pathlib import Path
p = Path("implementation/research/r04_ots")
(p / "synthetic_checkpoint_r04.json.ots").write_bytes(
    base64.b64decode((p / "synthetic_checkpoint_r04.ots.b64").read_bytes())
)
```

Then use the [official OTS client](https://github.com/opentimestamps/opentimestamps-client) with `ots info`, `ots verify -f <json> <json.ots>`, and `ots upgrade -n <json.ots>`. Preserve original bytes before a non-dry-run upgrade; do not claim confirmation based on calendar self-reporting. Official docs distinguish early pending receipts from Bitcoin proof and recommend a Bitcoin Core node for independently checking a finalized timestamp.

## Independent review challenges

- Mutate checkpoint bytes, proof bytes, floor seq/hash, and claimed witness operator.
- Re-run with verified source pins and independent Bitcoin data, documenting block height and time **only when confirmed**.
- Demonstrate genuine **separate administrative custody** and monotonic checkpoint persistence before treating the floor as external. Two processes or two cloud endpoints under a shared operator are not independent.
- Test response loss, crash, stale/forked checkpoints, revoke/rotate and witness rollback with synthetic keys and offline data before discussing any trust activation.

No main merge, production signer, live memory writer, Genesis changes, or protected architecture decisions are included.
