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


## 2026-11-26 — strict JSON ledger parsing and typed sequence validation

Source audit found three parser-boundary weaknesses in the R22.31 prototype:
1. Python's default JSON decoder accepts duplicate object keys and silently keeps the last value.
2. Journal records were hashed after decoding but the stored JSONL line was not required to be canonical, allowing noncanonical encodings of the same decoded object.
3. `record["sequence"]` was compared with an integer request epoch using equality only; JSON `8.0` compares equal to Python integer `8`.

Implemented:
- a duplicate-key-rejecting object-pairs hook for signed anchors, requests and journal records;
- canonical-byte enforcement for the signed anchor;
- exact single-line canonical JSONL enforcement for every journal record;
- explicit integer-only sequence validation, rejecting bool and float values before equality comparison.

Six regression tests cover duplicate keys in anchor/request/journal, noncanonical signed anchor and journal record encodings, and a float-valued sequence with a recomputed valid record hash. Existing path-alias regressions and expected-RED rollback control remain intact.

Dedicated CI [run 45854444069](https://github.com/SepehrGhanbari/Ario/actions/runs/45854444069), exact tested head `0229727e6b297a1fd13e598f79940c32c2524ca0`, completed SUCCESS: **18/18 tests PASS** on CPython 3.13.18 / OpenSSL 3.0.13. Evidence artifact `r22-31-custodian-monotonic-state-evidence`, ID `15135810639`, 702 bytes.

The same-domain valid-prefix rollback RED remains unresolved by design; no local parser change can create an independent floor. No Sigsum call, new witness, external publication, real key, TPM, trust activation, production promotion, or merge occurred.


## 2026-11-26 — owner-admin rollback threat-model disposition

**Disposition: ACCEPTED_RISK / OUT_OF_SCOPE under the owner's declared current operating model.**

The owner reports that they are the only trusted administrator of the Ario repository and its associated research environment. This is an owner-provided assumption, not an independently verified access-control inventory. Under that model, deliberate rewriting of every local state source by the same trusted owner is not treated as an adversarial security requirement. We will not create additional same-domain processes, files, mock custodians, or repeat the Sigsum test merely to simulate independence.

The expected-RED valid-prefix rollback test remains in the suite as an explicit boundary demonstration. It is not a blocker for the narrow R22.30 duplicate-epoch correction, and it is not evidence that the prototype resists a hostile administrator.

**Still NOT CLOSED:** compromise or theft of the owner's GitHub account, credentials, or execution device; compromise by another administrator not included in the declared model; and any deployment that requires resistance to a hostile owner. Those threats require a genuinely out-of-band owner-held floor or an independently administered custodian. They cannot be solved by another file or process under the same authority.

The existing R22.22I 2-of-4 external test-witness floor is not a floor for R22.31: its signed tree head predates this R22.31 state and does not commit to this journal or branch. Reusing it as though it did would be a false binding. No new Sigsum publication, witness test, external call, key, merge, trust activation, or production action was performed.

The R22.31 valid-prefix rollback finding is therefore **closed as an accepted scope limitation for the current owner-operated research prototype**, not as a cryptographic fix. The original same-epoch defect remains addressed by the R22.31 state-machine correction; PR #411 remains open/Draft pending its normal integration path.


## 2026-11-26 — superseding correction: administrator inventory is incomplete

**This section supersedes the immediately preceding ACCEPTED_RISK / OUT_OF_SCOPE disposition.**

The owner has clarified that at least one additional administrator exists and may have relevant administrative capability. Therefore the prior assumption that the owner is the sole trusted administrator is false and must not be used as the threat model.

Current disposition: **OPEN / NOT_ASSESSED — administrator inventory and authority boundaries are not yet established.** The previous same-domain valid-prefix rollback result remains a valid technical observation, but it cannot be closed as an accepted risk on the basis of sole-owner administration.

The connected GitHub integration confirms that its authenticated account has admin permission on this repository. Its current tool surface does not expose a complete collaborator/admin roster; the permission-check action can check a named GitHub login, but no second login has yet been supplied or identified. Thus the existence, identity, exact role, and effective authority of the additional administrator remain unverified here. Do not infer the administrator roster from commit authors, PR reviewers, workflow actors, or the repository owner field.

Next required evidence: enumerate repository administrators and any organization/enterprise owners through an authorized GitHub settings view or a named-user permission check; then map their effective access to repository settings, branch/ruleset changes, Actions/workflow secrets, deployments, external witness accounts, and any independently retained recovery floor. Determine whether the additional administrator can alter both the state and the evidence used to verify it. No access removal or security-setting mutation is authorized by this note.

No new Sigsum publication, witness test, key, merge, trust activation, or production action was performed. PR #411 remains open/Draft.


## 2026-11-26 — final direct-access inventory correction (owner screenshot)

**This entry supersedes the immediately preceding statement that a second administrator exists.** The earlier wording was a misinterpretation of the owner's question; the owner has now supplied the actual GitHub Settings → Collaborators screenshot.

Observed directly in the screenshot for `SepehrGhanbari/Ario`:
- Direct access: **0 collaborators**.
- GitHub UI states: **"Only you can contribute to this repository."**
- Manage access states no collaborators have been invited.

Cross-checks from the connected GitHub account:
- Repository owner: `SepehrGhanbari`; authenticated account has `admin`.
- Authenticated account has no organization memberships.
- The active `Protect main` ruleset lists only user ID `104393545` (SepehrGhanbari) as its explicit bypass actor; the second active no-bypass baseline lists no bypass actors.
- The earlier `Mrxxir = read` permission result is not evidence of collaborator status; the repository is public, and the owner's Collaborators page explicitly shows zero direct collaborators.

**Disposition for the question asked:** No second human collaborator/admin with direct repository access is present in the supplied current access view. The earlier "another administrator exists" note is withdrawn. No further search for a fictional second admin is warranted.

**Remaining distinction:** this does not prove that the owner's account/device is uncompromised, nor does the Collaborators page enumerate GitHub App installation permissions, Actions credentials, deploy keys, or external service credentials. Those are separate machine/credential access paths, not evidence of another human repository administrator. The connected integration shows one GitHub App installation on the owner's user account; its effective repository permissions were not exposed in the returned installation metadata. No claim is made that this app is a second human admin.

No collaborator removal, ruleset change, key rotation, new Sigsum test, merge, trust activation, or production action was performed. The R22.31 same-domain rollback behavior remains a distinct owner-account-compromise / credential-custody boundary; it must not be conflated with a nonexistent second direct collaborator.


## 2026-11-26 — final disposition: no second human repository administrator

The owner-provided current GitHub Settings → Collaborators screenshot shows **0 collaborators**, **"Only you can contribute to this repository"**, and no invited collaborators. This is consistent with the connected GitHub account being the repository owner/admin, having no organization memberships, and being the only explicit bypass actor in the active `Protect main` ruleset. The old `Mrxxir` account is not a collaborator; the repository is public and the earlier `read` result did not imply write access.

**Decision:** the threat scenario "a second human repository administrator deliberately rewinds the Ario repository/journal" is **NOT APPLICABLE to the currently observed access configuration**. Stop treating a second human admin as an unresolved blocker; do not build a mock admin, repeat Sigsum, or add another same-domain process for this scenario.

This is not a cryptographic rollback fix. The expected-RED valid-prefix rollback test remains as a documented boundary for a different threat: compromise of the owner's GitHub account/device or an automated credential/app with write authority. One GitHub App installation is visible on the owner's account, but its effective repository permissions were not exposed in the available installation metadata; it is not evidence of a second human administrator and remains a separate machine-credential audit item only if that threat is in scope.

No collaborator removal, ruleset change, key rotation, new witness test, merge, trust activation, or production action was performed.

## R22.33 descendant compatibility note — 2026-11-26

The historical R22.31 caller-supplied gate has been moved unchanged to `custodian_state_legacy.py` in the R22.33 descendant branch. The existing R22.31 tests now explicitly target that legacy path so the original 18-test state-machine result remains reproducible. The default `custodian_state.py` path is replaced by a strict wrapper that rejects requests unless they carry a custodian-signed, unexpired challenge and a receipt signed by a verifier key pinned by a custodian-signed pin file. The legacy implementation is retained for comparison only; it is not the default entrypoint.
