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


## Exact source reproduction and final verification — 2026-11-26

Dedicated CI [run 45848502455](https://github.com/SepehrGhanbari/Ario/actions/runs/45848502455), source commit `540bd4f4962c7e0db94215373b871bcf40de59b2`, SUCCESS on CPython 3.13.18 and OpenSSL 3.0.13: **8/8 tests PASS**.

The eighth test extracts the exact embedded custodian_gate.py heredoc from the unchanged R22.30 source shell script, creates a synthetic signed epoch-7 anchor, and submits two distinct valid-format requests with different nonces and different storage-root claims, both requesting 7→8 from the same previous head. The exact R22.30 gate approved both requests, emitted two epoch-8 approvals, appended two nonce entries, and left the signed anchor unchanged. This reproduces the source-level state-machine gap against the exact parent implementation, not a copied approximation.

The seven R22.31 prototype tests passed: single transition, second distinct request rejected, exact retry returns byte-identical receipt/signature, post-commit crash recovery, same-nonce/different-request rejection, journal tamper rejection, and eight-way concurrent requests with exactly one epoch winner.

Earlier failed workflow attempts are preserved in Actions history: the first exposed a Python string-escaping error in the reproducer; the second exposed a test fixture that incorrectly inherited setup state. Both were corrected. Only final run 45848502455 is counted as passing.

Boundaries remain: caller-supplied storage-root data is explicitly UNATTESTED; software-only synthetic keys; root-readable custodian key; same-runner journal; no TPM quote, AK/EK binding, physical TPM, independent custodian, external rollback floor, trust activation, production, or merge.

## 2026-11-26 — valid-prefix rollback counterexample and precise evidence boundary

The prior wording “detects journal tampering/truncation” was too broad. Source inspection of `custodian_state.py` shows that the loader rejects byte-level record tampering and an incomplete final record, but a complete-record tail deletion (including deleting the entire journal) leaves a valid shorter prefix. Because the signed initial anchor remains unchanged and there is no independent retained floor, replay cannot know that a later record ever existed.

Added `test_expected_red_valid_prefix_rollback_is_not_detected_without_external_floor`: it commits a synthetic 7→8 transition, removes the complete journal, then submits a second distinct 7→8 request. The prototype accepts it. This is an **expected RED counterexample**; the test harness passes because it successfully reproduces the documented weakness. It is not a security pass and does not claim anti-rollback protection.

Dedicated CI [run 45853039157](https://github.com/SepehrGhanbari/Ario/actions/runs/45853039157), exact branch head `19d78881138451a0b75404f96a0d78a8d3155034`, completed SUCCESS: **9 tests passed** on CPython 3.13.18 / OpenSSL 3.0.13. The nine comprise seven original prototype controls, one exact-source reproduction of the R22.30 defect, and this expected-RED valid-prefix rollback reproduction. The workflow artifact path was corrected; evidence artifact `r22-31-custodian-monotonic-state-evidence`, ID `15133349967`, 543 bytes, was uploaded successfully.

The local state-machine repair remains bounded: it prevents duplicate epoch consumption while the journal is intact and detects record corruption, but cannot detect restoration of an older valid journal prefix by an administrator who controls the journal. Closing that boundary requires an authenticated floor retained outside the runner's administrative domain. A second same-domain file or another local simulation would not establish that independence. No trust activation, production, real keys, or merge occurred.


## 2026-11-26 — prevent destructive path aliases in the R22.31 CLI

A source review found a concrete local data-loss case: before this correction, a caller could set `--response` to the journal path. The process would durably append the signed transition, then `atomic_write(response, receipt)` would replace the journal with the receipt object. Similar aliases could overwrite the signed anchor or cause the response signature to overwrite the response bytes.

Added `validate_distinct_paths(args)` before opening/creating the lock file. It rejects aliases among all nine input/output paths. `Path.resolve(strict=False)` detects lexical and symlink aliases; `os.path.samefile` additionally detects existing hard-link aliases. This is a deterministic caller-path guard, not a defense against a hostile process racing filesystem changes after validation.

Three regressions verify: response→journal is rejected before journal creation; response-signature→anchor is rejected without changing anchor bytes; and response/response-signature must be distinct. Existing expected-RED rollback control remains unchanged.

Dedicated CI [run 45853154583](https://github.com/SepehrGhanbari/Ario/actions/runs/45853154583), head `3eea8bcd642762912c4a3d4b00c1169275d4d0ad`, SUCCESS: **12/12 tests PASS** on CPython 3.13.18 / OpenSSL 3.0.13. This count includes the expected-RED valid-prefix rollback reproduction and exact-source R22.30 regression; neither is a claim that those vulnerabilities are prevented. The three new path-alias tests pass by confirming rejection before mutation.

No Sigsum call, new witness, external publication, real key, TPM, trust activation, production promotion, or merge was performed.
