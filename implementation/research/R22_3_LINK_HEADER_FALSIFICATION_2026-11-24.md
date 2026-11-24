# R22.3 — Independent falsification of Link-header parser (#344)

**Scope:** research-only, no keys, no trust activation, no production, no automatic merge.  
**Baseline:** PR #344 at `75426fad2337a604339ddc202a73af6272e04fe9`.  
**Fix branch:** `research/r22-3-link-header-parser-20261124`, stacked on #344; #344 and ancestors remain unmerged.

## Sources and the falsified claim

The original #344 reader used `NEXT_LINK.search(link)` across the **entire** HTTP header value. This is not equivalent to parsing the `rel` link parameter defined by RFC 8288 §3 and §3.3: https://www.rfc-editor.org/rfc/rfc8288.html.

The 26-file R22.3 offline handoff was inspected and its initial source manifest pinned 12 GitHub source files. A real local Python 3.13 pytest run on the unchanged reader reproduced **198 passed / 5 failed** in six handoff test modules. Four cases had a well-formed Link value with no `next` relation but the old substring regex incorrectly raised `PAGINATION_NEXT_LINK_PRESENT`:

1. `rel=next` appears only inside the target URI query, while the actual relation is `last`.
2. `rel=next` appears only in `title`, while the actual relation is `last`.
3. `rel="next-foo"` is not the separate `next` relation.
4. `rel="not-next"` is not the separate `next` relation.

The fifth handoff case expected `<URI>` **without a rel parameter** to be accepted. This expectation is **not valid under RFC 8288 §3.3**, which requires the rel parameter. The fail-closed `UNKNOWN` disposition is retained and now classified as `PAGINATION_LINK_INVALID`. The original handoff fixture is not silently rewritten to manufacture a fifth success.

## Bounded correction

`implementation/ario_repo_self_audit.py` now parses bounded Link fields, distinguishing angle-enclosed URI, semicolon-delimited parameter names and values, quoted strings with escapes, comma-separated link-values, and repeated header fields. It detects the exact `next` relation token (including a quoted multi-token `rel`) and raises `PAGINATION_NEXT_LINK_PRESENT`. Malformed, duplicate-rel, overlong, or ambiguous Link fields are rejected with `PAGINATION_LINK_INVALID`.

The reader **does not dereference link targets** or expand its fixed URL allowlist. It still rejects incomplete bounded JSON response collections, retains no-retry behavior and non-atomic observation semantics. This parser is deliberately conservative rather than a general-purpose RFC 8288 implementation: some unusual otherwise legal headers can return UNKNOWN.

`implementation/research/guard_v2_manual_report.py` REST reason vocabulary now includes the new `PAGINATION_LINK_INVALID`, retaining the R21a AST-derived allowlist contract.

## Negative controls

New `implementation/tests/test_r22_3_link_header_parser.py` checks valid unrelated rel names, URL/query/title false matches, commas and semicolons inside URI/quoted-string, quoted-pair escapes, exact next in multiple links or headers, uppercase NEXT, malformed/duplicate rel, excessive headers, oversize header, and a missing rel. The expected behavior for malformed evidence is fail-closed UNKNOWN.

A scratch copy of the corrected reader ran **219 focused tests with real pytest PASS** on the 4 original Guard/Self Audit modules, the Run/Rerun characterization module, and the new parser test module. This test set excludes the one RFC-invalid handoff assertion. GitHub CI on the **exact final PR head** must be checked separately; the first push CI failed because the new quoted-escape *test fixture* lacked an escape at runtime, and the test was corrected in the next commit. This is recorded, not hidden.

## Unresolved / not silently changed

- **Run/Rerun:** current max `(run_number,run_attempt)` is a defensible current-check policy, but a later failing rerun of an older numbered run can be a separately relevant contradictory observation. See `R22_3_RUN_RERUN_POLICY_OPTIONS_2026-11-24.md`. No policy change.
- **Check Runs:** GitHub documentation says `filter=latest` is default for the check-run list; this is not proof of all historical checks. Source: https://docs.github.com/en/rest/checks/runs
- **API shapes:** `run.path` with `@ref`, PR `body: null`, and nonstandard states can trigger conservative UNKNOWN; no endpoint-specific positive evidence to justify relaxing fields. Preserve null-vs-empty distinction if changed later.
- **Freshness:** sequential PR/Check/Run/Job/PR/Check/Run GETs cannot detect changes occurring after their last relevant sample, ABA or replay of coherent stale responses. `SAMPLED_NOT_ATOMIC`, overall UNKNOWN and merge authorization false remain mandatory.

**No successful test establishes independent execution attestation, custody, historical truth or trust activation.**
