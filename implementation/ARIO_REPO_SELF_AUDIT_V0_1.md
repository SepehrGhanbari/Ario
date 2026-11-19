# Ario GitHub Repository Self-Audit v0.1

Status: RESEARCH_ONLY / OFF_BY_DEFAULT / READ_ONLY / NOT_AN_ATTESTATION / NO_MERGE_AUTHORITY / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO.

This companion of Draft PR #295 samples the real Ario GitHub API from a separate advisory GitHub Actions job. It pins the exact PR HEAD supplied by the GitHub event, reads PR metadata, check-runs on that HEAD, matching pull-request workflow runs, and then re-reads the PR. If the identity or body changed, any positive-looking metadata observations are discarded.

The top-level status is ALWAYS UNKNOWN. GitHub reported success only establishes provider metadata at sampled times; it is not independently attested test execution or permission to merge. The original PR #290 offline claim/log comparator remains separate. In particular, this new probe DOES NOT inspect or verify pytest logs.

Only GitHub repository SepehrGhanbari/Ario is accepted, with strict GET-only endpoint allowlist and HTTPS, no redirects, a 400 KB body bound, strict duplicate-key rejection, and 100-result page bound. Any 403, missing evidence, inconsistent head, pagination or malformed JSON produces UNKNOWN. The temporary GitHub Actions token is scoped read-only (contents, actions, checks, pull-requests) and is not printed.

Read-only workflow: .github/workflows/ario-self-audit-lab.yml. Job: self-audit-readback-research. Runs on pull_request to exercise real provider access directly on GitHub. No new required checks, no workflow modifications to existing M0 regression, no CODEOWNERS or ruleset changes. Because the workflow executes PR-authored source, it is NOT an independent witness.

CLI from implementation directory:

    python -B ario_repo_self_audit.py --repository SepehrGhanbari/Ario --pr 295 --expected-head EXACT_SHA40

Offline tests:

    python -B -m pytest -p no:cacheprovider -q tests/test_ario_repo_self_audit.py

The already-existing adapter ario_self_audit_adapter.py connects two local claim/evidence files to the real bounded Ario agent. This NEW module adds real GitHub metadata collection; it is not an Ollama conversational attachment. Neither executable changes core memory, identity, signer, or M0 admission.

The Actions run emits one bounded JSON observation in its log and job summary. The workflow result being green only indicates that the reporting command completed; inspect the JSON reason and UNKNOWN. The owner can later disable the advisory workflow or revise this reader without changing historical evidence.
## v0.1.1 fail-closed hardening (2026-11-20)

The original reporter had a **cross-event ambiguity**: a successful push-event
`m0-regression` check could be mistaken for a successful PR-event
`m0-regression` check on the same commit. The hardening requires a unique
named GitHub Actions job whose numeric job ID and run ID are bound by its
canonical `details_url` to a PR-linked `pull_request` workflow run.
Both job and run must report completed/success; conflicting or still-running
PR jobs, invalid states, duplicate runs and incomplete pages never confirm
success. The observation field can now be
`REPORTED_SUCCESS_BY_LINKED_PR_RUN`, rather than
`REPORTED_SUCCESS_BY_GITHUB_APP`. Neither is evidence of an independent
witness or branch protection. Check-run metadata remains GitHub-reported.

This is a metadata-only improvement: no trust or production gate is
enabled, no checks are marked required, and no existing M0/agent/memory
file or original workflow is modified. All v0.1 observations remain
historical; no retroactive reinterpretation of their sampled time.
