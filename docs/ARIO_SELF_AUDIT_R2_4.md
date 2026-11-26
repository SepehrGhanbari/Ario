# Ario Self-Audit R2.4 — adversarial verification of pinned CI log evidence

Disposition: RESEARCH_ONLY / PASS_BOUNDED DESIGN / NO_REAL_KEYS / NO_TRUST_ACTIVATION / NO_PRODUCTION / NO_AUTOMATIC_MERGE.

## Objective

Connect the R2.3-D transport result to a local Self-Audit verifier. The verifier consumes the existing R2.3-D output directory, not a newly downloaded copy, and checks the report plus six saved raw log files against fixed observations. It is offline and requires no token.

## Pinned scope

- Repository: SepehrGhanbari/Ario
- Workflow run: 45460415487
- PR #366 head: c91300a3e4430ddbb4f60ab5fb23513be23d3b1e
- Expected merge checkout in all three logs: bb49574475f6e4c4bf9a740c4bbb986a603a4cd0
- Job IDs: 138681144591 (M0), 138681144245 (Python 3.14), 138681144844 (Windows)

The fixed SHA-256 and byte-length pins are recorded in docs/self-audit-r2-4-evidence/OBSERVED_LOG_PINS.json. The local verifier refuses a report that attempts to replace those pins.

## Checks performed by R2.4

1. Strictly parse the R2.3-D report; duplicate JSON keys and non-finite values are rejected.
2. Require the exact repository, run ID, checkout, job IDs, sample order, file names and safety flags.
3. Require the expected API redirect (302) followed by storage response (200) for each sample.
4. Read each raw log as a bounded regular file; reject symlinks, special files, observed changes during read and oversized content.
5. Compare every raw file's length and SHA-256 to a fixed per-job pin, not a digest supplied by the report.
6. Parse the log without executing it. Require the expected fetch ref, git log -1 output, runner OS, Python marker, pytest command and exact observed summary.
7. Require the two raw samples for each job to match.
8. Always keep execution attestation, source custody, freshness, correctness and PR-exclusive association NOT_ESTABLISHED; never grant merge, memory or trust authority.

## Actual observed log pins

| Job | Job ID | Bytes | SHA-256 | Reported summary |
|---|---:|---:|---|---|
| M0 regression | 138681144591 | 22,782 | def5b16d547b34ed2fe14fb31a1068cb105d91291a783f821ebfd6bae2c181b4 | 1715 passed, 7 skipped, 2 warnings, 359 subtests |
| Python 3.14 differential | 138681144245 | 24,017 | 48dd555debd9377944b0380f3a7d00dd11208b31881c34f743af55b255991763 | 1715 passed, 7 skipped, 2 warnings, 359 subtests |
| Windows differential | 138681144844 | 24,059 | 5d5a634095767b714b62e29961b7380e5209fce43938529d1b6361c8de406045 | 1714 passed, 8 skipped, 2 warnings, 359 subtests |

The two samples for each job had identical raw bytes. The R2.3-D report records the same per-job hashes and byte lengths. The GitHub job-log connector was queried again; both reads were identical per job. The three logs each include the expected checkout SHA in the fetch ref and git log -1 output, and each contains the exact pytest command and summary above.

## Adversarial tests

The focused offline suite contains 19 tests. It exercises:

- one-byte raw-log tampering;
- attempts to re-pin a tampered file in the report;
- a different checkout SHA even if the test fixture digest is recomputed;
- appended or substituted fabricated success summaries;
- swapped job logs and wrong job/run IDs;
- altered API/storage event chains;
- report attempts to upgrade execution attestation or enable merge/memory/trust;
- duplicate JSON keys, missing evidence, BOM removal and symlink paths;
- a valid six-sample baseline.

Linux local execution: 19/19 PASS (Python standard library only). Windows execution of R2.4 itself remains untested. A dedicated read-only GitHub Actions workflow runs the same focused suite on the PR.

## Metadata boundary

GitHub's job-list response associates the three job IDs with run 45460415487, gives the expected job names, and reports each as completed/success. A commit-run lookup for PR #366's head SHA returns run 45460415487 among the pull-request-triggered runs. PR #366 is merged. This still does not prove an exclusive run-to-PR association, independent custody, runner integrity, freshness, or test correctness; the report preserves these as NOT_ESTABLISHED.

## How to run on Windows

Extract the companion ZIP into a new directory and double-click RUN_SELF_AUDIT_R2_4.cmd. It first runs the 19 synthetic adversarial tests, then asks for the path to the R2.3-D output folder. No token is requested. The original files are read-only; a new R2.4_VERIFICATION_REPORT.json (or numbered successor) is written alongside them.

## Safety and limitations

The verifier is a bounded checker for one historical run, not a general GitHub log validator. It does not execute log content or contact GitHub. The pins and verifier are distributed together and are not signed; a hostile party able to replace the verifier package can replace its pins. The GitHub runner and API remain the upstream source for the logs. Matching raw bytes plus matching textual claims are not a cryptographic execution attestation. No runtime, memory, ledger, signer, governance, historical evidence, or production path is modified.

PASS_BOUNDED is a local correspondence result only. It is not a proof of correctness or authorization.
