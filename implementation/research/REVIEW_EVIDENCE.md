# Review evidence consolidation

Research candidate based on Ario main `c7088b69d170df09fa196a1ac1adc7d84e444752`, inspected 2026-11-21. The offline reader compares a V1 declaration with two supplied observations. A coherent input yields `metadata=CONSISTENT`. Its gate remains `HOLD`, execution attestation remains `UNKNOWN`, and the command exits 1 on every evidence outcome. The founder retains the decision on any later research merge. [Governance](../../GOVERNANCE.md)

## Historical audit

| Revision | Comparison with the starting main | Disposition |
|---|---|---|
| [#133 at 1209e357c1d573234bd76e01d5dd88093305d02a](https://github.com/SepehrGhanbari/Ario/pull/133) | 11 unique commits, 293 behind, conflicting. Proposed a live Action, path-based routine eligibility and governance changes. Its candidate unit job passed 13 tests. Its trusted-main job failed during discovery. [Jobs](https://github.com/SepehrGhanbari/Ario/actions/runs/41666031249) | Supersede the software proposal. Preserve policy discussions, citations, commits and failed runs. Recommend closure after owner review of the successor. |
| [#151 at 2261ac66ce12215b0dd0f02696be2146f1fd83f6](https://github.com/SepehrGhanbari/Ario/pull/151) | Stacked on #133, 34 unique commits versus main, 293 behind. Improved record parsing, bot IDs, PR/run/attempt/checkout binding, mutable readback and redirect handling. 81 candidate unit tests passed. The trusted-main job again failed. [Jobs](https://github.com/SepehrGhanbari/Ario/actions/runs/42375243016) | Supersede the operational candidate and preserve its regression archive. The offline reader retains selected contracts. Closing the old PR remains an owner decision. |
| Starting main | The historical workflow, script and gate tests are absent. Existing bounded JSON, typed GitHub ID matching, pytest log parsing and versioned readback probes already cover parts of the same problem. The existing Implementation Regression workflow discovers this candidate's tests on Ubuntu and Windows, including canonical Python 3.13. | Reuse those primitives and existing CI. The candidate adds no GitHub collector, permissions, path-based authorization or required check. |

The historical source locations below refer to `.github/scripts/review_evidence_gate.py` unless marked as workflow lines. [Pinned #133 source](https://github.com/SepehrGhanbari/Ario/blob/1209e357c1d573234bd76e01d5dd88093305d02a/.github/scripts/review_evidence_gate.py) · [Pinned #151 source](https://github.com/SepehrGhanbari/Ario/blob/2261ac66ce12215b0dd0f02696be2146f1fd83f6/.github/scripts/review_evidence_gate.py)

| Status | Evidence or defect | Observed result and scope of correction |
|---|---|---|
| VERIFIED | #133 L33, valid browser CRLF | Expected a valid V1 record. #133 raised GateError. #151 and this candidate accept CRLF and LF. |
| VERIFIED | #133 L33–35, incomplete second opener | Expected an ambiguous record to be rejected. #133 accepted the first record. Count marker-like openers before parsing the complete block. |
| VERIFIED | #133 L37, duplicate JSON field | Expected rejection, even for equal values. #133 accepted the record. Reject duplicate members at every object level. |
| VERIFIED | #133 L47, boolean schema version | Expected an integer. #133 accepted a boolean. Retain the exact-integer check from #151. |
| VERIFIED | #151 L143–150, PR association database ID | Changing only the association's ID left its number unchanged and passed the historical binding function. Require both IDs on the same unique association. |
| VERIFIED | #151 L145–149, repository ID type | A float numerically equal to the expected repository ID passed the comparison. Require a positive JSON integer for each matched ID. |
| DISPROVED | The failed #151 job executed the gate script and then failed there | The checkout selected main and unittest discovery raised `ImportError: Start directory is not importable: '.github/tests'` before the script step. The script also is absent on starting main. [Failed job](https://github.com/SepehrGhanbari/Ario/actions/runs/42375243016/job/128411370459) |
| VERIFIED | Names and review text have limited meaning | #133 L102–108, L125–139 accepted identity evidence based on names. #151 L121–124, L339–390, L472–519 added bot and execution checks. The reader checks a distinct bot ID/login/type and the native review state and PR URL. A COMMENTED review stays COMMENTED. A self-review cannot count as that distinct reviewer. |
| VERIFIED | Incomplete or inconsistent supplied evidence | Missing RED, incomplete pages, stale head/base, wrong suite/app/workflow/attempt/job, changed comments, unresolved threads or an unreadable capture produce UNKNOWN. A single canonical Linux job cannot establish complete CI coverage. |
| UNKNOWN | Independent evaluator identity, deleted evidence before first read, complete historical custody and merge-time freshness | Two identical snapshots can share omissions or be fabricated. An authenticated GitHub Actions App ID is shared across workflows. A quoted pytest result cannot authenticate who executed code. A fresh read can become stale before merge. |
| NOT_EXECUTED | Privileged PR execution, publication of Check Runs, actual merge, ruleset or signer changes | This experiment uses local fixtures and ordinary project CI. It does not run a privileged evaluator. |

## Current protection and archived experiments

GitHub’s effective-rules response and public rules page both list active rulesets 24782645 and 27201221 for main. The former requires one approval and Code Owner review. The latter requires a PR and the strict up-to-date `m0-regression` check from GitHub Actions App 15368 and restricts deletion and non-fast-forward updates. The public branch response reports `protected: true`. The classic-protection details endpoint requires authentication, and the public ruleset payload omits bypass actors. Actual bypass membership remains UNKNOWN from this read. CODEOWNERS names the founder as sole owner. The offline experiment adds no reviewer requirement. [Effective rules](https://api.github.com/repos/SepehrGhanbari/Ario/rules/branches/main) · [Branch](https://api.github.com/repos/SepehrGhanbari/Ario/branches/main) · [CODEOWNERS](../../.github/CODEOWNERS)

| Archived lab | What the published record established | Remaining boundary |
|---|---|---|
| [R1i](https://github.com/SepehrGhanbari/ario-relay-webhook-sandbox-20261112/blob/157ba9a131deab67f188675c06bdd81dd775e1f7/evidence/r1i/2026-11-13/R1I_FINAL_LAB_REPORT.md) | Separate evaluator exercised one fixture. A genuine old-head App success did not satisfy the new head. | Single owner controlled lab infrastructure. Independent signer custody remains unproved. |
| [R1j](https://github.com/SepehrGhanbari/ario-relay-webhook-sandbox-20261112/blob/4cfd7a3b70a5575e4ba29651396c7e4e2d3d5512/research/r1j/NO_REPOST_RECONCILIATION_V1.md) | Ambiguous write outcome led to read-only reconciliation and a final PR reread. | The API reads and an eventual merge are separate operations. |
| [R1k](https://github.com/SepehrGhanbari/ario-relay-webhook-sandbox-20261112/blob/2e09b6ff68d65f53529dc9cdb6001ad8a93360d7/research/r1k/CRASH_RECOVERY_AND_MULTIHOST_GAP_V1.md) | Competing processes sharing one journal obtained one reservation. | Two journals could both reserve. |
| [R1l](https://github.com/SepehrGhanbari/ario-relay-webhook-sandbox-20261112/blob/1e8cbdc4ea9e871db580c55f50b48567fe8b4675/research/r1l/SHARED_COORDINATOR_ATOMICITY_V1.md) | Clients using one transactional database serialized reservations. | Independent primaries could both succeed. |
| [R1m](https://github.com/SepehrGhanbari/ario-relay-webhook-sandbox-20261112/blob/efad4a4ee10917a0cd774b9f39db3fcb8534d7b2/research/r1m/TWO_INDEPENDENT_RUNNERS_REF_CAS_V1.md) | Two hosted VMs contended for a lab ref and a third job checked the outcome. | Sandbox refs and common operator control establish neither immutable retention nor independent authority. |

## Run and interpret

From `implementation`, run `python -m research.review_evidence pin.json first.json last.json`. Use Python 3.13. The fixture builders `PIN` and `observation()` in [the tests](../tests/test_review_evidence.py) are executable input examples. Each input is a bounded UTF-8 JSON file. Declare the PR number, PR database ID, head repository ID and expected head/base SHAs separately in the pin.

Each observation contains the PR, its observed filename list, review/comment/thread collections and the declared RED/GREEN runs. Collections carry nodes, total count and a final-page indicator. The thread collection includes the parent PR database ID. Runs carry the observed check suite, attempt job list, canonical job log and merge checkout commit. RED includes a complete compare response projection from its revision to GREEN. A RED checkout with an older base also needs its base comparison. The reader is scoped to Ario's Implementation Regression workflow and the canonical Linux job. It does not classify file sensitivity or authenticate collector assertions.

Two captures must agree. Missing or rate-limited reads must be represented as missing data or an error, never replaced with empty successful collections. The reader recognizes explicit historical Major/Critical labels as blockers. It does not infer the meaning of arbitrary prose or verify that a claimed RED failure was caused by a specific patch. A deleted review predating both observations may be invisible. Verifying production authority would require a separately controlled issuer, execution provenance, protected retention and a decision bound to the then-current revision. A smallest next *research* experiment is to compare independent, read-only collections of one public PR across one ordinary head update and retain both raw responses and errors. It cannot establish independent custody.

## Reproduce the contract results

From the repository root, run the following Python with Python 3.13 and locally available, pinned historical Git objects. It copies only the historical module and the current test module into a temporary directory. Both historical modules have an import-safe main guard. These comparisons call only their local parser and binding functions.

```python
from pathlib import Path
import shutil, subprocess, sys, tempfile

for revision, classes in [
    ("1209e357c1d573234bd76e01d5dd88093305d02a", ["RecordContract"]),
    ("2261ac66ce12215b0dd0f02696be2146f1fd83f6", ["RecordContract", "AssociationContract"]),
]:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "research").mkdir()
        source = subprocess.check_output(["git", "show", revision + ":.github/scripts/review_evidence_gate.py"])
        (root / "research/review_evidence.py").write_bytes(source)
        shutil.copy("implementation/tests/test_review_evidence.py", root)
        subprocess.run([sys.executable, "-B", "-m", "unittest", "-v",
                        *["test_review_evidence." + name for name in classes]], cwd=root)
```

Linux Python 3.13.5 historical output, abridged:

```text
#133: valid LF ok; CRLF ERROR; duplicate field FAIL; second opener FAIL; bool version FAIL
Ran 5 tests
FAILED (failures=3, errors=1)
#151: five record checks ok; valid PR association ok; changed PR ID FAIL; float repository ID FAIL
Ran 8 tests
FAILED (failures=2)
```

Candidate command from `implementation`: `python -B -m unittest discover -s tests -p test_review_evidence.py -v`. The same historical fixtures and the full-reader, readback and CLI controls passed locally. The Draft PR records the final revision, hosted jobs, skips and execution evidence.
