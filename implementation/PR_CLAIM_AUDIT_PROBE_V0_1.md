# Ario audits Ario — PR/CI claim correspondence pilot v0.1

**Status:** RESEARCH_ONLY / READ_ONLY / NO_GITHUB_WRITE / NO_TRUST_ACTIVATION / NO_MERGE_AUTHORITY / NOT_A_SECURITY_CHECK.

Related idea: [issue #251](https://github.com/SepehrGhanbari/Ario/issues/251). This bounded pilot compares exactly one structured claim in a PR body with a supplied snapshot of the **corresponding GitHub Actions workflow run, job, and full job log**. It produces only `MATCH`, `MISMATCH` or `UNKNOWN`. It does **not** decide whether the code is correct, or whether a PR can merge.

## 1. Why this matters

**Self-Claim ≠ Self-Evidence.** A statement such as “1,140 tests passed” is a claim by the PR author. A GitHub Actions log on the same head SHA is another artifact. The two may agree, disagree, or be insufficiently linked. Even `MATCH` is a narrow observation about text and metadata, **not proof the tests are correct or independently authored**. GitHub workflow definitions, test code, PR authors, and CI evidence may share a custody domain.

This experiment is intentionally small: it does not run against all PRs, alter existing workflows or control merge eligibility.

## 2. Three-state result

- **`MATCH`** — all explicitly claimed numerical fields, Python version, invocation and job conclusion equal one unambiguous pytest summary in the **supplied** log, bound to the requested run/head/job/attempt.
- **`MISMATCH`** — a claimed field differs from the **sufficiently bound** supplied evidence. A failure can still produce `MATCH` if the claim honestly says the test job failed.
- **`UNKNOWN`** — no valid structured claim, missing/incomplete evidence, head mismatch, wrong job/run, incomplete run, wrong log digest, multiple summaries, no exact command, or other ambiguity. This is **not** a passing or failing verdict.

The tool does not call GitHub or any external service; it does not execute the PR, inspect secrets, or modify files. It has no signer, trusted timestamp, immutable external witness, provenance certification, or approval authority. Its output always lists limitations.

## 3. PR claim block (explicit opt-in)

The PR author may include one such block in the PR body. Its markers and field names are versioned; missing fields yield `UNKNOWN` rather than invented defaults.

```markdown
<!-- ARIO-CI-CLAIM-V0.1
{
  "schema": "ARIO-PR-CI-0.1",
  "head_sha": "c800b45c2c06d1bbeacaa063cca4573f0ec1d879",
  "run_id": 43949946093,
  "run_attempt": 1,
  "job_id": 133589448819,
  "python_version": "3.14.10",
  "pytest_command": "python -m pytest -q tests",
  "passed": 1140,
  "failed": 1,
  "skipped": 0,
  "subtests_passed": 121,
  "job_conclusion": "failure"
}
ARIO-CI-CLAIM-V0.1 -->
```

The claim is still author-controlled text. Duplicate blocks, duplicate JSON keys, unexpected keys, booleans in integer fields, unsupported commands or oversized inputs yield `UNKNOWN`.

## 4. Evidence input and CLI

A separate retrieval process exports the source run and job metadata plus the **full** Actions job log. The exporting process must itself be documented and reviewed; this pilot does not treat the text label `job_log_complete` as cryptographic proof of completeness.

```json
{
  "run": {
    "id": 43949946093,
    "run_attempt": 1,
    "head_sha": "c800b45c2c06d1bbeacaa063cca4573f0ec1d879",
    "event": "pull_request",
    "status": "completed",
    "conclusion": "failure"
  },
  "job": {
    "id": 133589448819,
    "run_id": 43949946093,
    "name": "python-314-differential-advisory",
    "status": "completed",
    "conclusion": "failure"
  },
  "job_log": "<FULL JOB LOG, NOT AN EXCERPT>",
  "job_log_sha256": "<SHA-256 OF EXACT UTF-8 JOB LOG>",
  "job_log_complete": true
}
```

From the `implementation/` directory, using a disposable environment without secrets:

```sh
python -B -m unittest -v tests.test_pr_claim_audit
python -B pr_claim_audit.py --pr-body /path/to/pr_body.md --evidence /path/to/evidence.json
```

The program prints exactly one JSON object to stdout. Exit 0 only means that the evaluation command completed; **exit 0 is not admission, acceptance, or approval**. Callers **must** inspect the JSON `status`. File read errors return `UNKNOWN`, not a traceback or approval.

**Important:** the exact command `python -m pytest -q tests` must appear in the job log as a CI step invocation. In later versions we can support other commands with an explicit, audited command allowlist and path provenance rather than guessing.

## 5. Real #249 CI anchor (observed externally, not attested by this tool)

The following values were read from public GitHub Actions data for [PR #249](https://github.com/SepehrGhanbari/Ario/pull/249) at head `c800b45c2c06d1bbeacaa063cca4573f0ec1d879`:

- [Run `43949946093`](https://github.com/SepehrGhanbari/Ario/actions/runs/43949946093): PR event, first attempt, overall workflow `failure`.
- Job `133589448819`, `python-314-differential-advisory`: job `failure`, Python **3.14.10**, `python -m pytest -q tests`.
- The observed terminal summary in that job log: **`1 failed, 1140 passed, 121 subtests passed in 6.08s`**.
- Other jobs on that same run, **`m0-regression` and `windows-differential-advisory`, succeeded**. Therefore a failed advisory job does not imply failure of the canonical M0 job.

The local test suite contains a **minimal synthetic log built to reproduce these public fields**; it is **not the full original GitHub job log** and must not be presented as authenticated evidence. For a real assessment, supply the complete raw log from the exact job and bind its SHA-256 to the retrieval record. A truncated excerpt must set `job_log_complete: false` and yields `UNKNOWN`.

## 6. Reproducibility and negative tests

The local tests include cases for:

- Honest `MATCH` for a fixture with the #249 summary and metadata shape.
- Changing `passed`, `failed`, subtests, Python version or job conclusion → `MISMATCH`.
- Wrong head SHA, run ID, attempt or job binding → `UNKNOWN` (not false `MISMATCH`).
- Duplicate claims/JSON keys, extra claim fields, boolean counts, tampered log digest, truncated log, duplicate summary lines, wrong command or conflicting version markers → `UNKNOWN`.
- Instructions outside the claim block are ignored as data; no approval states are emitted.
- CLI subprocess leaves its input files byte-identical; it only writes JSON to stdout.

A source mutation that blindly returns `MATCH` should make the `test_mutated_pass_count_turns_mismatch` test fail (RED). A mutation that skips head binding should make `test_wrong_run_head_is_unknown_not_mismatch` fail (RED). Archive exact mutation commands/results before calling this a mutation-verified test suite.

## 7. Open problems (do not silently promote)

1. **Evidence extraction and source authentication are not implemented.** An external, read-only adapter must fetch one PR's actual head, a specific workflow run attempt, job metadata and the full CI log and record provenance. JSON/log hashes only detect changes relative to a recorded value; self-reported hashes are not an independent trust anchor.
2. **A forged CI job can make a false claim appear to match.** The tool establishes correspondence to a supplied snapshot, not independent correctness or evidence custody.
3. **Full-suite coverage is not proven by a command string alone.** Test discovery, plugins, warnings, skips and mutable workflow files require separate auditing; `MATCH` does not imply actual full coverage.
4. **Cross-PR and rerun ambiguity:** Only one run/job/attempt is checked per claim; multiple conflicting runs are not automatically reconciled.
5. **Parser and report scope:** v0.1 accepts one canonical `python -m pytest -q tests` log summary. It does not parse arbitrary test frameworks, Github annotations, custom artifact formats, retries or multiple test commands.
6. **Research remains read-only:** no automatic PR comments, checks/status publication, webhook configuration, required-check designation, Ruleset change, core epistemic contract change, or merge.

**Next step:** request a separate reviewer to falsify the negative tests and evaluate the evidence-extraction design before adding any live connector or CI workflow.
