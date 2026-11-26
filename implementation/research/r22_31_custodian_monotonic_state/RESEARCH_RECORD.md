# R22.31 research record — custodian monotonic state machine

**RESEARCH_ONLY / SYNTHETIC_KEYS / NO_REAL_TPM / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_MERGE.**

Parent: R22.30 PR #409, exact source head fba551689eacd686380c54104fbe8452fc7830e1.

## Source finding

The R22.30 embedded custodian_gate.py validates the request against a signed anchor and appends the nonce to a JSONL file. It does not update the anchor or record an authoritative current epoch/head/storage-root state after approval. Thus the anchor remains epoch 7 after a 7→8 approval. A second request with a different nonce but the same epoch-7 predecessor can pass the same checks. This is a deterministic state-machine gap.

The nonce check and append also occur without an inter-process lock, leaving a check-then-append race for concurrent requests. This is a source-level finding; this record does not claim a live exploit against any production system.

## R22.31 prototype

A separate prototype is added at implementation/research/r22_31_custodian_monotonic_state/custodian_state.py. It uses:
- signed initial anchor;
- signed per-transition receipt;
- append-only hash-chained JSONL journal;
- exclusive flock around replay, validation and commit;
- fsync of the journal and containing directory;
- epoch/head/storage-root state advancement;
- idempotent recovery of an exact request after commit but before response delivery.

The new workflow is read-only with respect to repository contents and runs synthetic keys in a disposable Ubuntu runner. No real TPM, private user key, Ario signer, external publication, or production resource is used.

## Explicit evidence boundary

The prototype receives storage_root_sha256 as a caller-supplied request field. It marks this as CALLER_SUPPLIED_UNATTESTED; it does not validate a TPM quote or prove that the value came from the TPM. The custodian key and journal remain accessible to the runner administrator, so independent custody and rollback resistance are NOT_ESTABLISHED. This work only repairs and tests the local state-machine semantics.

## Test acceptance

- Single-step transition accepted.
- Distinct second transition against the consumed epoch rejected.
- Exact retry returns the original receipt/signature with no second journal entry.
- Post-commit crash recovery returns the durable receipt.
- Concurrent distinct requests for one epoch have exactly one winner.
- Journal tampering is detected.
- Unattested storage-root provenance is explicit.

## Execution

Pending dedicated CI run on the branch. Prior R22.30 results remain unchanged and are not re-counted.
