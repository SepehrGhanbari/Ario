# Ario audits Ario — strict complete-line Python version extraction v0.8

**Status:** RESEARCH_ONLY / DRAFT / HOLD / NO_MERGE / PRODUCTION=NO_GO / TRUST_ACTIVATION=NO_GO. Additive, offline diagnostic sidecar. v0.1–v0.7 historical files remain unchanged. The final verdict is always `UNKNOWN`.

## Source and independent-review provenance

Hallaaj evaluated **author-reported excerpts** of v0.7, not the independently fetched exact source or independently run tests (`NOT_RUN` for both). Hallaaj reasonably recommended replacing `finditer` substring recognition by strict complete-line version recognition, without upgrading evidence authority. Ava separately read the original Git blob `3ba8f7dba680b2db2add8ee6bd28a7c01b5e07ad` at PR #257 HEAD `31cfc0d37cd12adfde12e270c399bfdb187ff6d1` and reproduced two counterexamples against the actual CPython source:

1. **False diagnostic positive:** A synthetic log contains only `Some test deliberately prints: Python 3.13.18` in place of a legitimate setup version line. v0.7 extracts the substring and returns `claim_correspondence=MATCH` for a matching synthetic claim (but final `status=UNKNOWN`).
2. **False diagnostic downgrade:** A valid `Successfully set up CPython (3.13.18)` setup line plus irrelevant `Documentation: Python 3.12.0 is EOL` leads v0.7 to misclassify the two versions as conflicting.

## Scoped patch, without changing custody or claims

v0.8 copies the v0.7 offline logic unchanged **except** version recognition. After v0.1's bounded timestamp and ANSI-prefix stripping, it recognizes only full lines matching either:

- `Python X.Y.Z` (the legacy source-form full-line marker); or
- `Successfully set up CPython (X.Y.Z)` (the observed `actions/setup-python` marker).

It collects the **set of all recognized version values**. Empty set or more than one distinct value ⇒ `UNKNOWN`. Repeated identical values are not a contradiction; conflicting full-line values are rejected. It neither takes the first nor last arbitrarily. Unrelated version substrings embedded in other lines are ignored.

**Important remaining limitation:** A forged *whole* `Python X.Y.Z` line, or a forged setup-python line, could still be emitted as untrusted log text and accepted by the *format parser*. v0.8 does NOT establish the producer, custody, authenticity or correct execution. `source_delivery=UNVERIFIED`, `execution_attestation=NOT_ESTABLISHED`, and final `status=UNKNOWN` are unchanged. A self-recomputed SHA-256 of a forged log does not prove source origin. No self-asserted `source_integrity` field is introduced.

## Validation plan and admission criteria

The new tests include v0.7 RED reproductions, v0.8 GREEN counterexamples, actual GitHub Actions setup/pytest excerpt, legitimate version-line duplicates, conflicting recognized version-lines, unrelated version mentions, unknown pytest count categories, duplicate count keys, mismatched claim, bad log hash and fake complete-line provenance. Preserve the entire v0.2–v0.7 historical test suite. A CI green check is not an independently authenticated execution attestation; verify results on the exact commit if code is published.

**Decision:** Keep the sidecar research-only. No merge, no deployment, no trust activation, no new API credentials or workflow changes. Stronger assertions require independent source review and a source/custody proof distinct from the log's own content.
