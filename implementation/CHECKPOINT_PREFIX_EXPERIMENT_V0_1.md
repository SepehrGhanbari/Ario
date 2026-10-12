# Checkpoint prefix experiment v0.1

## Actual implementation and evidence

ARIO-CHECKPOINT-EXP-001 implements one conditional property: a declared synthetic ledger prefix corresponds to a checkpoint supplied by a separately preserved **test oracle**, in an externally selected scope with a supplied symbolic descriptor binding. It does not establish production independence.

Implementation: checkpoint_prefix_experiment.py. Deterministic fixtures and adversarial assertions: tests/test_checkpoint_prefix_experiment.py. The comparator uses in-memory arguments and the standard library, with no filesystem operations, signing, enrollment authority or M0 Evidence/Assessment/AuditResult adapter.

Starting source: 6c85fcabf6968da1cc9d6cf21ff6617dada0b79f. Local preservation commit: 53f1e85d810b8abece3e27b6ab658b64b95cf61c.

| Tested file | SHA256 |
|---|---|
| checkpoint_prefix_experiment.py | e17b929913623ed8027dcd08e5054a42a68a6723b00dd7780300a0622aa58e16 |
| tests/test_checkpoint_prefix_experiment.py | 7d2699cf6532ca7bd77226f9f1a5751c455f3d107cffa005c182f3d253fb117c |

Retained final targeted result: **60 passed in 0.58s, exit 0**, empty stderr. The earlier 35-case run also passed before boundary coverage was added. No full regression suite was run. This document reuses those results; new documentation checks are recorded separately in ENGINEERING_LOG.md.

## Test boundary and verdict semantics

Test control supplies Context, immutable checkpoint bytes in OracleSnapshot, symbolic descriptor bindings and a known checkpoint floor. These inputs must not come from candidate declarations or local result summaries. The oracle is frozen before mutation and built independently of the comparator. This is a test assumption and workflow, not a deployed access-control mechanism.

The attacker may replace candidate files, rewrite observations/references, recompute hashes, substitute descriptor declarations, truncate the chain or replay another ledger/epoch/branch/domain. Detection assumes that the oracle, external context and bindings remain outside candidate control. Replacement of those trusted inputs is outside this experiment's guarantees. SHA256 collision resistance is assumed; signer security is not evaluated.

| Finding | Meaning within the experiment |
|---|---|
| local_hash_validity | Recomputed record digests and predecessor links agree locally |
| prefix_correspondence | Original candidate prefix bytes, byte count and stored head digest match the admitted checkpoint |
| checkpoint_binding | Declaration exactly matches an oracle checkpoint in the external scope |
| symbolic_descriptor_binding | Descriptor agrees with the supplied identity pin and checkpoint fingerprints |
| known_checkpoint_floor | Corresponding checkpoint reaches the supplied count floor; no clock freshness or global latestness |
| oracle_evidence | Requested oracle commitment and required count-2 parent are present and nonconflicting |

property_verdict is PASS only when prefix correspondence, checkpoint binding, symbolic descriptor binding and oracle evidence all MATCH. A required MISMATCH yields FAIL; otherwise missing/unknown required findings yield INCONCLUSIVE. Known failure can coexist with UNKNOWN findings.

**Local validity and the floor are excluded from the narrow property verdict.** C2 correspondence can PASS while rollback/floor or a later invalid suffix remains visible. Consumers must inspect those separate findings.

## Strict serialization and fixture

Profile: ARIO-PREFIX-EXPERIMENT-0.1. Record objects have no profile field; their format is governed by this comparator version. Objects must use exact compact sorted-key ASCII JSON. The comparator checks exact serialization and rejects alternate bytes; it never repairs or normalizes candidate data.

Ledger records are JSONL, each terminated by LF, including the final record. No BOM, CRLF, blank record, duplicate key, unknown field or alternate whitespace is accepted. Boundaries and prefix slicing come from the original input bytes.

Exact record fields: record_id, observed_at, payload, previous_sha256, sha256. IDs are ROW-i in order. Record 0 has a null predecessor; subsequent records contain the preceding stored digest. Record sha256 hashes canonical JSON excluding only its own sha256 field, retaining previous_sha256. Digests are lowercase 64-character hex.

Payload fields: claim_id, node_id, value; successors also have lineage_from and lineage_to. All rows use claim_id=SYNTHETIC-CLAIM.

| Record | Declared observed_at | Node | Value | Declared lineage |
|---|---|---|---|---|
| ROW-0 | 2026-10-12T00:00:00Z | NODE-A | original synthetic observation | absent |
| ROW-1 | 2026-10-12T00:01:00Z | NODE-B | synthetic successor | NODE-A to NODE-B |
| ROW-2 | 2026-10-12T00:02:00Z | NODE-C | synthetic third record | NODE-B to NODE-C |
| ROW-3 | 2026-10-12T00:03:00Z | NODE-D | synthetic fourth record | NODE-C to NODE-D |

ROW-0/ROW-1 reproduce the original ARIO-ADV-XIRG-001 synthetic baseline byte-for-byte. Times, labels and lineage fields are declarations; the comparator does not authenticate their semantics.

Limits: 65536 ledger bytes, one through four candidate records, 4096 checkpoint bytes, at most eight oracle checkpoints and two symbolic bindings, nesting depth at most eight, integer tokens at most ten characters. Checkpoint counts and known floors support only integer 2 or 4; booleans are rejected. Printable ASCII context/record strings are bounded to 128 characters, payload strings to 512. Floats, NaN/Infinity, non-ASCII, invalid fields/types and noncanonical serialization are rejected.

The test module independently seals literal observations and constructs L2/L4/C2/C4 before mutating separate copies. Immutable checkpoint bytes and the frozen snapshot are retained.

## Checkpoint format and goldens

Exact checkpoint fields: profile, domain, ledger_id, epoch, branch_id, record_count, prefix_byte_count, prefix_sha256, head_sha256, previous_checkpoint_sha256, test_identity, key_descriptor_sha256, checkpoint_sha256.

Checkpoints are canonical JSON bytes **without trailing LF**. prefix_byte_count includes ledger-prefix LFs. prefix_sha256 hashes those original bytes. head_sha256 is the final record's stored digest. checkpoint_sha256 hashes the canonical body excluding itself. C2 has a null previous_checkpoint_sha256; C4 points to C2's **body digest**, not the full serialized file digest.

Fixed test scope:

- domain=SYNTHETIC_CHECKPOINT_CORRESPONDENCE
- ledger_id=SYNTHETIC-LEDGER-001
- epoch=TEST-EPOCH-001
- branch_id=TEST-BRANCH-A
- test_identity=TEST-KEEPER-A

Scope labels are opaque externally selected context and grant no domain authority. TEST-KEEPER-A is symbolically pinned to bytes TEST-KEY-A:SYMBOLIC:v0.1, SHA256 b5eb0a52fe0b4ac8eb01b1fbbb653884f83235e25cb5189246727744cbadb2d2. The substitution descriptor is TEST-KEY-B:SYMBOLIC:v0.1. Neither is a real verification key, signature or credential.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| L2 original two-record prefix | 615 | 00a9c8f968a53e987e2c90b93eecf32186612d28bb12568bc608b59c13ef4e94 |
| L4 extended four-record ledger | 1334 | 3f9bf3fa7fe9b3b71113292e4fff2671545fdcc383260a15b4cc4275e89a9e72 |
| C2 body excluding self-digest | — | 39391cd6c739caf10ea622f146c3501500ea905c20964cef05b2cc8ee4051f7e |
| C4 body excluding self-digest | — | 81b9cf87da4dd83ca86c69dc2e85041d1cf8d070c1c17d1e4df97735e9fcd606 |
| C2 full serialized checkpoint | — | 0ee1676e5c428599bf66e0a248c75be3dcbd91a63e3a58f4dc47c50d1c4e5c01 |
| C4 full serialized checkpoint | — | cfe82d497f0751202fd31bad4cb5b6db6ba3cf54c08e3c7f88ed1ab33df024a8 |

Head digests: C2 6f517155685c069af5d6f988979c71c4e1a9893b8194eb7c204e1cbba443d844; C4 8e4542172577406d577cad48bc8d25ed884710beceeb00b44e335faef2d89f60.

The scratch reference builder and independent literal test builder agreed on L2/L4 and checkpoint body digests. PowerShell Get-FileHash agreed on frozen L2/L4 files. This establishes independent test-oracle construction only, not historical truth or production independence.

## Reproduction commands

No external ledger, historical archive, signer or original evidence file is required. Use the existing environment; do not install dependencies or run the production agent. This PowerShell command creates fresh output storage and restores process-local environment settings. Pytest argv matches the verified run except for the new output path.

~~~powershell
$taskRepo = 'C:\Users\xx4773\Ario'
$taskPython = 'C:\Users\xx4773\AppData\Local\Ario\venvs\ario-tests-py313\Scripts\python.exe'
$taskScratch = Join-Path 'C:\Users\xx4773\AppData\Local\Ario\engineering-backups' ('checkpoint-prefix-reproduction-' + [Guid]::NewGuid().ToString('N'))
if (Test-Path -LiteralPath $taskScratch) { throw 'Scratch collision; stop' }
if (-not (Test-Path -LiteralPath $taskPython)) { throw 'Existing interpreter unavailable; stop' }
New-Item -ItemType Directory -Path $taskScratch -ErrorAction Stop | Out-Null
$taskSavedEnvironment = @{}
foreach ($taskName in @('PYTHONDONTWRITEBYTECODE', 'PYTHONIOENCODING', 'PYTHONPATH', 'TMP', 'TEMP')) {
    $taskSavedEnvironment[$taskName] = [Environment]::GetEnvironmentVariable($taskName, 'Process')
}
Push-Location $taskRepo
try {
    $env:PYTHONDONTWRITEBYTECODE = '1'
    $env:PYTHONIOENCODING = 'utf-8'
    $env:PYTHONPATH = Join-Path $taskRepo 'implementation'
    $env:TMP = $taskScratch
    $env:TEMP = $taskScratch
    & $taskPython -B -m pytest -p no:cacheprovider -q implementation/tests/test_checkpoint_prefix_experiment.py "--junitxml=$taskScratch\pytest.xml"
    $taskTestExit = $LASTEXITCODE
    if ($taskTestExit -ne 0) { throw "Targeted test failure: $taskTestExit" }
    git --no-optional-locks diff --check
    if ($LASTEXITCODE -ne 0) { throw 'Git whitespace check failed' }
} finally {
    foreach ($taskName in $taskSavedEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($taskName, $taskSavedEnvironment[$taskName], 'Process')
    }
    Pop-Location
}
~~~

Expected: 60 passed, exit 0; elapsed time varies. Git whitespace check must exit 0. Reproduction requires no staging, commits, production operations or reuse of old evidence directories.

Implemented call shape:

~~~text
compare_prefix(candidate_bytes, declared_checkpoint_bytes, oracle_snapshot,
               context, *, candidate_key_descriptor=None) -> ComparisonResult
~~~

Pass raw bytes and explicit test-control objects. The returned value is an experimental report only.

## Adversarial outcomes exercised by tests

| Case | Expected findings and narrow property verdict |
|---|---|
| L4/C4 | Local, prefix, binding, descriptor, oracle and floor MATCH; PASS |
| L4/C2 with known floor 4 | Prefix property PASS; floor MISMATCH |
| Early ROW-0 value rewrite, all hashes resealed | Local MATCH; C4 prefix MISMATCH; FAIL |
| Later ROW-2 value rewrite, all hashes resealed | C2 PASS with unmet floor; C4 prefix MISMATCH and FAIL |
| B descriptor substitution, including resealed declaration retaining A's label | Descriptor MISMATCH; FAIL; no manufactured conflict |
| Rollback L2/C2 | Local/prefix MATCH; property PASS; floor MISMATCH |
| Ledger/epoch/branch/domain replay against different external context | Checkpoint binding MISMATCH; FAIL |
| Missing independent C4 checkpoint | Oracle/prefix UNKNOWN; INCONCLUSIVE |
| Two different oracle-admitted C4 commitments in identical scope | conflict=true, oracle/prefix UNKNOWN; INCONCLUSIVE |
| Attacker-only C4 declaration differs from unchanged oracle | Binding MISMATCH; FAIL; conflict=false |
| Duplicate identical oracle checkpoints | No conflict; valid correspondence PASS |
| Malformed serialization, duplicate keys, invalid types/fields/counts or exceeded bounds | Relevant MISMATCH; FAIL |
| Unsupported declared/oracle profile with otherwise valid inputs | Relevant UNKNOWN; INCONCLUSIVE |
| C4 lacks independent C2 parent | Prefix/binding may MATCH; oracle UNKNOWN; INCONCLUSIVE |
| Admitted resealed C4 points to wrong C2 digest | Oracle parent binding MISMATCH; FAIL |
| Invalid hash only in ROW-3, compared to unchanged C2 | Local MISMATCH; prefix property PASS; floor MISMATCH |
| Missing candidate/declaration/oracle/context/descriptor or symbolic configuration | Relevant UNKNOWN; INCONCLUSIVE in exercised cases |
| PASS ComparisonResult reused as OracleSnapshot | Oracle UNKNOWN; INCONCLUSIVE |
| Unchanged valid checkpoint | No positive truth, admission, identity or continuity conclusion |

Oracle conflict detection compares prefix byte count, prefix digest, head digest and parent digest at identical scope/count. Attacker declarations are never added to that oracle. Metadata differences alone are not this commitment conflict. No complete cross-count/cross-branch historical inconsistency policy is established.

## Exclusions and UNKNOWN

| Result field | Fixed value |
|---|---|
| signature_validity | NOT_CHECKED |
| human_authorization | NOT_EVALUATED |
| evidence_admission | NOT_EVALUATED |
| historical_event_truth | UNKNOWN |
| entity_continuity | UNKNOWN |
| ontological_continuity | UNKNOWN |
| production_historical_continuity | INCONCLUSIVE |
| independence_basis | ASSUMED_FOR_EXPERIMENT |

Synthetic oracle "admission" is not authorized M0 evidence admission. No adapter grants REVIEW_CANDIDATE, CLAIM_TRUTH or SAME_ENTITY. HISTORICAL_CONTINUITY has not been introduced into M0. Real signatures, public-key enrollment, human authority, recovery policy, key compromise, protected persistence, clock freshness and production deployment are outside this implementation.

A matching checkpoint does not establish historical event truth, entity continuity, consciousness, ontological identity or independent production security.

## Preservation and limitations

Original evidence remains under C:\Users\xx4773\AppData\Local\Ario\engineering-backups\checkpoint-prefix-experiment-20261012-01\: frozen fixtures/checkpoints, golden-manifest.json, exact argv/environment/output, JUnit reports and final-verification.json. The original synthetic baseline is unchanged.

This continuation uses C:\Users\xx4773\AppData\Local\Ario\engineering-backups\checkpoint-prefix-preservation-20261012-01\ for new records only. The complete pre-documentation engineering log is backed up at backups\ENGINEERING_LOG.md.pre-phase-b: 30391 bytes, SHA256 b9272d484fad8f7bf1d1bdcf712ced7330d962385853a51377060c00c44b5a09. Its entire original prefix is preserved.

The 70 previously visible unrelated untracked paths remain protected. Inventory and metadata are compared during this continuation; retrospective content fingerprints were not available. Inaccessible existing pytest-cache contents were not inspected or changed. No owner secrets, real private keys, USB vault or production ledger contents are needed.

Overall independent historical-continuity conclusion: **INCONCLUSIVE**.
