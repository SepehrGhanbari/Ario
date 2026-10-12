# ARIO-TB-002 — Independent Historical Witness Experiment v0.1

**State:** BOUNDED SYNTHETIC IMPLEMENTATION CANDIDATE — not deployed; no authority activated.
**Base repository:** `SepehrGhanbari/Ario`, PR #63 merge `8ec2392742cb477a2abb781b5af5314490bbd8ac`.
**Owner-approved scope:** new module, new tests, new document only; no changes to M0/core, existing comparator, existing ledger, signer, or trust-anchor contract.

## 1. Research question

Can a candidate-controlled ledger with a recomputed, locally valid hash chain be shown to differ from one or more **test-controller-frozen** synthetic witness commitments? What conclusions still cannot follow if custodianship is only declared, or if the attacker also controls the reference commitments?

The experimental property is conditional byte/hash correspondence, **not independent historical authentication**. Distinguish ledger integrity, prefix correspondence, witness-to-witness agreement, trust-anchor enrollment, custody independence, chronology, real event truth, and entity/ontological continuity.

## 2. Relationship to existing Ario implementation

- `checkpoint_prefix_experiment.compare_prefix(candidate_bytes, declared_checkpoint_bytes, oracle_snapshot, context, *, candidate_key_descriptor=...)` remains the **only** ledger/checkpoint validator in this experiment.
- `independent_witness_experiment.verify_witnesses()` makes **two separate calls** to the existing comparator using independently supplied, controller-frozen per-witness reference objects.
- It does not combine witness checkpoints into one oracle, and it does not modify the comparator's narrow `property_verdict`.
- `WitnessComparisonReport` is **not** a typed M0 Evidence, Assessment, AuditResult, authenticated witness, or grant of any power.
- All input data, identities, keys, timestamps, provenance, and witness copies are synthetic. Symbolic test descriptors are not cryptographic keys.

## 3. Model and artifact semantics

### 3.1 WitnessEnvelope

Frozen dataclass fields: role, witness_id, custody_domain_label, checkpoint_bytes, optional count-2 parent bytes, snapshot_reference, capture_sequence, declared_provenance, test_control_digest.

`test_control_digest` is an ordinary SHA256 checksum over fixed-format test metadata and digests; it is **not** a signature. `seal_test_envelope()` is strictly a fixture helper and must not be used for authority enrollment. An attacker who can replace both envelope and test-controller reference can manufacture a matching digest.

### 3.2 WitnessControl

- `anchors`: exactly two controller-frozen envelopes of distinct roles and witness IDs.
- `context`: externally selected checkpoint comparator scope.
- `symbolic_bindings`: up to two symbolic test identity-to-descriptor bindings.
- `known_floor`: `None`, 2, or 4, a test-controller record-count floor, **not a trusted timestamp**.
- `laboratory_isolated_roles`: a **controller-declared assumption** of experimental isolation; no operating-system, hardware, or administrative boundary is created.

### 3.3 WitnessCase

- Candidate ledger bytes and two or fewer presented witness envelopes.
- The frozen `WitnessControl` snapshot described above.
- Candidate symbolic descriptor, bounded attacker-capability description.
- Explicit `compromised_witness_roles` and `controller_compromised` indicators supplied by the **test controller**. They record attacker capability; they do not detect compromise.

### 3.4 WitnessComparisonReport

Stores role-labeled per-witness fields: snapshot_integrity, checkpoint_correspondence, scope_binding, witness_identity_claim, checkpoint_floor, local_hash_validity, descriptor_binding, experimental_oracle_evidence, authenticity, and original comparator verdict.

Also stores cross_witness_commitment_relation, candidate_history_relation, known_floor_relation, aggregate_verdict, conflict_detected, custody_independence, attacker capability, and stable reason codes.

The following are explicitly non-authorizing and permanently unresolved by this experiment:

| Field | Value |
|---|---|
| `cryptographic_witness_authenticity` | `NOT_CHECKED` |
| `historical_custody_independence` | `NOT_ESTABLISHED` |
| `human_authorization` | `NOT_EVALUATED` |
| `evidence_admission` | `NOT_EVALUATED` |
| `historical_event_truth` | `UNKNOWN` |
| `entity_continuity` | `UNKNOWN` |
| `ontological_continuity` | `UNKNOWN` |
| `production_historical_continuity` | `INCONCLUSIVE` |

For explicitly compromised controllers/witnesses, `independence_basis=COMPROMISED_BY_SCENARIO` and custody_independence is `UNKNOWN` even when the commitments correspond. Otherwise the independence basis is only `ASSUMED_FOR_EXPERIMENT`, never VERIFIED.

## 4. Commitment equivalence versus metadata equivalence

Two witnesses can have the **same ledger prefix** but different `test_identity` and different predecessor checkpoint body digests. Comparing their raw serialized checkpoint bytes or count-4 `previous_checkpoint_sha256` values would falsely report historical conflict.

TB-002 instead compares, within identical ledger/epoch/branch/domain and count:

1. Prefix byte count.
2. Prefix SHA256 and stored head record digest.
3. **Semantic content** of the parent count-2 checkpoint (if the child is count-4).
4. Each child-parent digest edge must match **its own** parent serialized checkpoint body.

Distinct witness metadata alone must not manufacture a content conflict. This narrower equivalence still does not prove that the declared observation occurred. Malformed, missing or unsupported parents must not produce false `AGREE`.

## 5. Status precedence

**Scoped per-witness:** `MATCH`, `MISMATCH`, `UNKNOWN` reflect each returned comparator finding. Missing witness yields `UNKNOWN`; candidate-declared provenance never overrides the frozen control reference.

**Across witness commitments:**
- `AGREE`: comparable semantic historical commitments are equal.
- `CONFLICT`: comparable frozen commitments differ.
- `UNKNOWN`: noncomparable scope/count, unresolved parent, or missing response.

**Aggregate:**
- `INVALID_INPUT`: malformed bounded experimental wrapper, ambiguous role/enrollment, unsupported control configuration, or comparator not installed.
- `UNRESOLVED_CONFLICT`: incomparable accounts within the same controlled scope/count and a definite frozen witness contradiction; never majority-vote.
- `DEFINITE_DISCREPANCY`: observed contradiction with at least one specified frozen laboratory reference, role declaration or known floor. This does not identify which account is historically true.
- `CONDITIONAL_CORRESPONDENCE`: two available role-bound declared responses pass their separate comparator property checks, snapshot binding matches, and their **controlled historical commitments** agree. Does not assert valid real custody, event truth or latestness.
- `INCONCLUSIVE`: insufficient evidence for the above scoped observations.

The whole result must be read, not just the aggregate. For example: locally invalid final record can coexist with a valid earlier prefix; or an old prefix can match while failing a separately supplied floor. An aggregate diagnostic is not a new inference rule for global truth.

## 6. Pre-registered 20 adversarial scenarios

| ID | Attack/control | Expected bounded observation |
|---|---|---|
| TB-01 | Unmodified four-record candidate; two frozen synthetically independent witnesses | Two scoped PASS; semantic `AGREE`; conditional correspondence |
| TB-02 | Rewrite first record and recompute candidate hashes | Local chain MATCH but frozen checkpoint prefix MISMATCH |
| TB-03 | Rewrite third record while one witness binds earlier C2 | Early C2 may MATCH while C4 MISMATCH; no truth inflation |
| TB-04 | Roll back to L2 and supply known floor=4 | Prefix MATCH but floor MISMATCH |
| TB-05 | Remove floor | Floor UNKNOWN; absence alone not rollback proof |
| TB-06 | B response missing | A finding retained; B UNKNOWN; aggregate INCONCLUSIVE |
| TB-07 | Different frozen same-scope same-count historical commitment | `CONFLICT`; unresolved without selection by ordering |
| TB-08 | A candidate match; B discrepancy | Both findings retained, witness conflict not voted away |
| TB-09 | Two witness roles claim same custody group | No independent-source inflation; custody UNKNOWN |
| TB-10 | Change witness B's declared identity | Declared ID and frozen snapshot mismatch, no enrollment |
| TB-11 | Replay under an incompatible external ledger scope | Scoped binding not PASS; no conditional correspondence |
| TB-12 | Candidate manufactures and self-seals a replacement checkpoint | Self-checksum cannot overwrite controller anchor |
| TB-13 | Use favorable old comparison report as witness checkpoint bytes | Wrong artifact kind rejected |
| TB-14 | Same historical prefix with different per-witness metadata/parent hashes | Semantic `AGREE`; no fabricated content conflict |
| TB-15 | Duplicate keys, invalid/missing profile, malformed or oversized checkpoint | No conditional correspondence; bounded error classification |
| TB-16 | Reverse presented witness order | Exact same role-labeled report |
| TB-17 | Candidate, both witnesses and test controller compromised | Conditional local agreement possible; independence/truth unestablished |
| TB-18 | Witnesses collude on false event text | Agreement possible, historical event truth UNKNOWN |
| TB-19 | Well-formed checkpoint with forged custody label | Prefix observation separate from custody mismatch/authenticity UNKNOWN |
| TB-20 | Attempt to use witness report as M0 truth/entity identity evidence | No adapter, no authority/evidence admission, ontology UNKNOWN |

Additional wrapper cases check repeated-call determinism and duplicate/unenrolled roles.

### Frozen fixtures

The test module independently rebuilds the published two-record and four-record synthetic baseline. It asserts:

- L2 SHA256: `00a9c8f968a53e987e2c90b93eecf32186612d28bb12568bc608b59c13ef4e94`
- L4 SHA256: `3f9bf3fa7fe9b3b71113292e4fff2671545fdcc383260a15b4cc4275e89a9e72`

Witness B has its own symbolic metadata and count-2 parent checkpoint, reflecting the same original prefix; this intentionally changes B's serialized checkpoint body hash without changing what historical bytes its commitment refers to.

## 7. Bounded execution

- No real signing or trust-root enrollment; no filesystem or network access in the implementation or tests.
- Max two controlled witnesses, two presented responses, max 4096 checkpoint bytes each, max 65536 candidate bytes, restricted labels, explicit floor profile 2/4/None.
- Use existing strict checkpoint comparator for canonical JSON/record chain/full checkpoint validity. The witness analyzer contains only a narrowly scoped extraction of checkpoint commitments, including self-checksum verification, for comparing *historical content*, not full ledger validation.
- No mutation of original fixtures, runtime ledgers, evidence, backups, M0 core, signer or approval records.

## 8. Integration and reproducibility

The patch consists of these **three new files only**:

1. `implementation/independent_witness_experiment.py`
2. `implementation/tests/test_independent_witness_experiment.py`
3. `implementation/INDEPENDENT_HISTORICAL_WITNESS_EXPERIMENT_V0_1.md`

Copy them into an existing local Ario clone **only after checking that the destination files do not already exist and after owner-approved reconciliation of the current HEAD**. Preserve all previously untracked files and historical evidence. Do not automatically commit or push.

Recommended PowerShell validation, from repository root with existing Python venv, using a NEW unique scratch path and disabled cache/bytecode:

```powershell
$repo = "$HOME\Ario"
$py = "$HOME\AppData\Local\Ario\venvs\ario-tests-py313\Scripts\python.exe"
$scratch = Join-Path "$HOME\AppData\Local\Ario\engineering-backups" ("tb002-repro-" + [Guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $scratch) { throw 'scratch collision' }
New-Item -ItemType Directory -Path $scratch -ErrorAction Stop | Out-Null
$before = @{}
foreach ($v in @('PYTHONPATH','PYTHONDONTWRITEBYTECODE','TMP','TEMP')) {
    $before[$v] = [Environment]::GetEnvironmentVariable($v, 'Process')
}
Push-Location $repo
try {
    $env:PYTHONPATH = Join-Path $repo 'implementation'
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:TMP = $scratch
    $env:TEMP = $scratch
    & $py -B -m pytest -p no:cacheprovider -q implementation/tests/test_independent_witness_experiment.py "--junitxml=$scratch\pytest.xml"
    if ($LASTEXITCODE -ne 0) { throw 'TB-002 targeted regression failed' }
    git --no-optional-locks diff --check
    if ($LASTEXITCODE -ne 0) { throw 'Git whitespace check failed' }
} finally {
    foreach ($v in $before.Keys) { [Environment]::SetEnvironmentVariable($v, $before[$v], 'Process') }
    Pop-Location
}
```

**Validation honesty:** A separately written compatibility shim of the publicly inspected v0.1 comparator API was used only in the assistant's sandbox for early algorithmic validation; its code is *not in the deliverable*. This does **not** substitute for the required integration run with the actual checkout's `checkpoint_prefix_experiment.py`. No tests have been executed on the user's Windows computer for this TB-002 version. Exact sandbox results and package SHA256 belong in the handoff report; do not claim GitHub CI, integration PASS, historical independence or production readiness from the shim run.

## 9. Acceptance and release gates

- All 20 named scenarios must pass in the actual Ario checkout, along with the existing checkpoint tests.
- Run `git diff --check`, inspect the staged path list if an owner-approved local commit is planned, and preserve untracked files.
- No historical evidence, current M0/IRG code, signer or trust-authority code may change.
- If any scenario fails with the real comparator, record the exact failure and stop rather than weakening expectations.
- Additional independent review of the threat model is desirable before claiming research validation. No production witness enrollment, remote push or merge is permitted by this patch.

## 10. Unresolved research questions

1. How could independent custody be authenticated without trusting a candidate-supplied reference?
2. How could protected checkpoint time, fork detection and freshness be established under controlled clock and revocation assumptions?
3. What happens if one or both witnesses are compromised or collude with the candidate?
4. How can root enrollment, rotation and dispute resolution remain contestable rather than creating an infallible authority?
5. What evidence, if any, would justify conclusions about historical events rather than merely registered bytes?

**Governing non-equivalence:** `CONSISTENCY != CORRESPONDENCE != AUTHENTICITY != INDEPENDENCE != TRUTH != CONTINUITY`.
