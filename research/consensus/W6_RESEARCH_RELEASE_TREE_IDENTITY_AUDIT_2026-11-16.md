# W6 — Source-identity audit of Ario's 14 November research corpus

**Date:** 2026-11-16. **Finding:** `VERIFIED_META_DEFECT / TREE_METADATA_ONLY_FAIL / NO_FILE_COVERAGE_GAP_DETECTED / RESEARCH_ONLY`. **Do not change `main`, any published Git/Zenodo ZIP/TXT, private PDFs or historical release records.**

## Reproduction target and exact identities

- The historical published source commit is `a39ac06e69c1b5115bca2016698556730bf920cd`, the source pin used by the merged research release [PR #202](https://github.com/SepehrGhanbari/Ario/pull/202).
- That commit's **actual Git tree object** according to GitHub's immutable Git commit object is `16f0c24c0a1e027a6b9086320464f9653a841e22`.
- [Original SOURCE_MANIFEST.json](https://github.com/SepehrGhanbari/Ario/blob/main/releases/complete-research-2026-11-14-a39ac06e/SOURCE_MANIFEST.json), Git blob `0f508a4c92b8c37fdb3ae680a78a24ec5bac66d2`, has `source_commit=a39ac06e...` **correct** but `source_tree_sha=a39ac06e...` **incorrect** (a commit ID substituted for a different object type).
- [Original RESEARCH_AND_EXPERIMENT_COVERAGE.json](https://github.com/SepehrGhanbari/Ario/blob/main/releases/complete-research-2026-11-14-a39ac06e/RESEARCH_AND_EXPERIMENT_COVERAGE.json), Git blob `da384eedaaa087bbb057382521d1714a2d621a38`, likewise has `source_commit=a39ac06e...` **correct** but `source_git_tree=a39ac06e...` **incorrect**.
- The API-read source commit `GET /repos/SepehrGhanbari/Ario/git/commits/a39ac06e...` gives `tree.sha=16f0c24c...`, and `GET /repos/SepehrGhanbari/Ario/git/trees/16f0c24c...?recursive=1` gives the same `sha`, `truncated=false`.
- A Git **commit** SHA and a Git **tree** SHA are different object identities; using the commit SHA in a field whose name promises a tree creates a false identity binding, even when the commit itself is correctly pinned.

**This is a metadata integrity bug, not evidence that original package file data changed or a Git SHA collision occurred.** There is no indication that somebody modified or forged published bytes. The exact source commit identity remains correct.

## Independently checked source inventory

From the Git tree at the pinned commit, enumerated **264 blob entries**. Compared the explicit `included`, `aliases` and `excluded` arrays from the original release manifest to that tree:

| Source-inventory property | Observation |
| --- | ---: |
| Actual source Git blobs | 264 |
| Manifest `included` entries | 239 |
| Manifest exact-content alias entries | 1 |
| Manifest deliberate exclusions/index-only entries | 24 |
| Unaccounted Git blobs / spurious paths / repeated paths | **0 / 0 / 0** |
| Git blob SHA-1 field mismatches | **0** |
| Git blob byte-length mismatches | **0** |
| Declared alias-to-original SHA-1 mismatches | **0** |
| Included text files / binary assets | 230 / 9 |
| Mistyped tree-identity metadata fields | **2** |

**Scope:** This test verifies the exact Git object paths and blob identities and tree-provided original byte sizes; it **did not** re-download/rehash every raw blob for SHA-256, re-extract the 16.87-MB ZIP, or independently open the 3.86-MB TXT and prove contents match the manifest. Those larger checks were previously *author-reported* in [PR #202](https://github.com/SepehrGhanbari/Ario/pull/202), but are **NOT repeated as W6 execution**. The 2026-11-14 source-audit document explicitly excludes unmerged PR-only and private material; 264/264 is scoped to the source commit, **not all Ario research in the world**.

## RED/GREEN empirical control — executed, not merely proposed

[Public read-only checker](w6_verify_research_release_git_ids.py) accepts four local JSON inputs: the two historical release files and the *GitHub API objects* for their pinned Git commit and actual recursive tree. It has **no network and writes no files**, and uses only the Python standard library.

Ran against the original GitHub-fetched JSON bytes in a separate Windows scratch folder on Python 3.13:

```text
{
  "status": "TREE_METADATA_ONLY_FAIL",
  "source_commit_sha": "a39ac06e69c1b5115bca2016698556730bf920cd",
  "actual_git_tree_sha": "16f0c24c0a1e027a6b9086320464f9653a841e22",
  "blob_entries_checked": 264,
  "paths_covered": 264,
  "error_codes": [
    "TREE_IDENTITY_MISMATCH:coverage.source_git_tree",
    "TREE_IDENTITY_MISMATCH:manifest.source_tree_sha"
  ]
}
W6_SOURCE_EXIT=2
```

A separate [six-case metamorphic test](test_w6_manifest_ids.py) then operated on **in-memory copies only**, with no replacement of any original file or history:

1. Original metadata = `EXPECTED_RED` (exactly two tree-field failures).
2. Replace only those two temporary tree fields with `16f0c24c...` = **GREEN**.
3. Change one copied blob SHA to all zeroes = expected **RED**.
4. Drop one manifest source path = expected **RED**.
5. Pretend GitHub recursive tree is truncated = expected **RED**.
6. Change one recorded source byte count = expected **RED**.

Result `W6_METAMORPHIC_PASS`, all six expectations matched, `W6_CONTROLS_EXIT=0`. Exact tested/public Git blob IDs: checker `e96e50f658f02ed2b0b3e83ad7fc2a16815ecaf7`; test `abe57dbc016f4d9fba60f1e9a9e04433144533ad`. Neither script verifies source SHA-256 without original blob bytes.

**Reproduction:**
```bash
# Download pinned source files; do NOT modify the historical release.
curl -fsS -o commit.json 'https://api.github.com/repos/SepehrGhanbari/Ario/git/commits/a39ac06e69c1b5115bca2016698556730bf920cd'
curl -fsS -o tree.json 'https://api.github.com/repos/SepehrGhanbari/Ario/git/trees/16f0c24c0a1e027a6b9086320464f9653a841e22?recursive=1'
# Copy SOURCE_MANIFEST.json -> manifest.json and RESEARCH_AND_EXPERIMENT_COVERAGE.json -> coverage.json
python w6_verify_research_release_git_ids.py --manifest manifest.json --coverage coverage.json --commit commit.json --tree tree.json
# Expected exit code: 2, exactly two tree-identity-field failures.
python test_w6_manifest_ids.py  # Expected: 6/6 control assertions; exit 0
```

## Correction policy and epistemic decision

**Do not rewrite** the original 2026-11-14 release archives, published DOI objects, historical manifest, or prior PR. Their bytes and their mistakes are part of the audit trail. Publish the [machine-readable append-only corrigendum](W6_SOURCE_TREE_IDENTITY_CORRIGENDUM_2026-11-16.json) and cross-link from the historical release/PR if maintainers want discoverability. **Future** versioned release generator must separately store and validate:
- `source_commit_sha` = exact pinned Git commit SHA
- `source_tree_sha` = `git cat-file -p <commit> | ... tree` or `git rev-parse <commit>^{tree}`
- per-record `git_blob_sha1` = original Git blob object
- `sha256` = separately recalculated raw source bytes when a SHA-256 claim is made

A future test must explicitly fail on `commit==tree` under this pinned sample and compare `commit.tree.sha` to supplied `tree.sha`. Keep independently verified file-payload SHA256 and snapshot packaging as separate quality gates. A green GitHub CI/manifest parser alone cannot substitute for these identity checks.

**Other outstanding, already disclosed limitation, not a new W6 failure:** the 2026-11-14 paper audit and [book README](https://github.com/SepehrGhanbari/Ario/blob/main/papers/being-with-the-other/v6/README.md) document that Zenodo record `23771218` is labeled Version 6 while the publisher-deposited PDF files/cover indicate Fifth Integrated Edition. This mismatch remains explicitly `UNRESOLVED`; do not relabel the original PDF or claim a different sixth-edition full text.

## W6 decision register

- `FIX IN NEXT VERSION / P1`: release generator's distinction of Git commit vs tree object and typed validation.
- `PRESERVE`: original 264-path manifest inventory and all historical ZIP/TXT/source texts unchanged.
- `NOT_ESTABLISHED`: W6 independent SHA-256 verification of the packaged release files, real-world source authenticity, external reviewer independence, no missing untracked work, book version-label resolution.
- `RESEARCH_ONLY / NO_MERGE / MAIN_UNCHANGED / TRUST_ACTIVATION=NO_GO`.

This review is scoped to release provenance accuracy, not to Ario's operational evidence admission, signer or conversational runtime.
