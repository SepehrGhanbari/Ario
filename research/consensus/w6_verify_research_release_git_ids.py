#!/usr/bin/env python3
"""W6 read-only check of published Ario research release metadata against Git objects.

Inputs are exact raw JSON responses for:
- GitHub git/commits/<source commit>
- GitHub git/trees/<actual commit.tree.sha>?recursive=1
- Release SOURCE_MANIFEST.json and RESEARCH_AND_EXPERIMENT_COVERAGE.json

Does NOT validate included ZIP/TXT payload bytes, SHA256 of source blobs, or publication authenticity.
Exit 2: manifest/coverage identity mismatch or record mismatch. No file writes.
"""
import argparse
import json
from pathlib import Path
import sys


def check(manifest, coverage, commit, tree):
    failed = []
    info = {}
    commit_sha = commit.get("sha")
    tree_sha = commit.get("tree", {}).get("sha")
    if not (isinstance(commit_sha, str) and isinstance(tree_sha, str)):
        return {"status": "FAIL", "errors": ["MISSING_GIT_COMMIT_IDENTITY"]}

    if commit_sha != manifest.get("source_commit") or commit_sha != coverage.get("source_commit"):
        failed.append("SOURCE_COMMIT_MISMATCH")
    if tree_sha != tree.get("sha") or tree.get("truncated") is not False:
        failed.append("TREE_OBJECT_MISMATCH_OR_TRUNCATED")
    for field, value in (
        ("manifest.source_tree_sha", manifest.get("source_tree_sha")),
        ("coverage.source_git_tree", coverage.get("source_git_tree")),
    ):
        if tree_sha != value:
            failed.append("TREE_IDENTITY_MISMATCH:" + field)

    blobs = {x["path"]: x for x in tree.get("tree", []) if x.get("type") == "blob"}
    grouped = {k: manifest.get(k, []) for k in ("included", "aliases", "excluded")}
    records = [v for values in grouped.values() for v in values]
    paths = [v.get("path") for v in records]
    if len(paths) != len(set(paths)):
        failed.append("DUPLICATE_PATH_RECORD")
    if set(paths) != set(blobs):
        failed.append("PATH_SET_MISMATCH")
    for r in records:
        b = blobs.get(r.get("path"))
        if b is None:
            continue
        if b.get("sha") != r.get("git_blob_sha1"):
            failed.append("BLOB_MISMATCH:" + str(r.get("path")))
        if b.get("size") != r.get("original_bytes"):
            failed.append("SIZE_MISMATCH:" + str(r.get("path")))
    for r in grouped["aliases"]:
        target = blobs.get(r.get("identical_to"))
        if target is None or target.get("sha") != r.get("git_blob_sha1"):
            failed.append("ALIAS_TARGET_BLOB_MISMATCH:" + str(r.get("path")))

    sizes = {
        "source_tracked_paths": coverage.get("source_tracked_paths"),
        "all_tracked_files_verified": manifest.get("all_tracked_files_verified"),
        "included_total_original_paths": manifest.get("included_total_original_paths"),
        "included_full_text_files": manifest.get("included_full_text_files"),
        "included_original_binary_assets": manifest.get("included_original_binary_assets"),
        "excluded_nested_exports_or_old_book_manuscripts": manifest.get("excluded_nested_exports_or_old_book_manuscripts"),
        "exact_duplicate_aliases": manifest.get("exact_duplicate_aliases"),
    }
    want = {"source_tracked_paths": len(blobs), "all_tracked_files_verified": len(blobs),
            "included_total_original_paths": len(grouped["included"]),
            "included_full_text_files": len([x for x in grouped["included"] if x.get("format") == "text"]),
            "included_original_binary_assets": len([x for x in grouped["included"] if x.get("format") != "text"]),
            "excluded_nested_exports_or_old_book_manuscripts": len(grouped["excluded"]),
            "exact_duplicate_aliases": len(grouped["aliases"])}
    for key, value in sizes.items():
        if value != want[key]:
            failed.append("COUNT_MISMATCH:" + key)
    info.update({"source_commit_sha": commit_sha, "actual_git_tree_sha": tree_sha,
                 "manifest_claimed_tree_sha": manifest.get("source_tree_sha"),
                 "coverage_claimed_tree_sha": coverage.get("source_git_tree"),
                 "blob_entries_checked": len(blobs), "paths_covered": len(set(paths)),
                 "included": len(grouped["included"]), "aliases": len(grouped["aliases"]),
                 "excluded": len(grouped["excluded"]),
                 "error_codes": sorted(set(failed)),
                 "scope": "Git object identity, path/blob identity and length only; not full source SHA256 or ZIP/TXT re-extraction"})
    info["status"] = "PASS" if not failed else ("TREE_METADATA_ONLY_FAIL" if all(x.startswith("TREE_IDENTITY_MISMATCH:") for x in failed) else "FAIL")
    return info


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for field in ("manifest", "coverage", "commit", "tree"):
        ap.add_argument("--" + field, type=Path, required=True)
    args = ap.parse_args()
    try:
        docs = [json.loads(getattr(args, n).read_text(encoding="utf-8")) for n in ("manifest", "coverage", "commit", "tree")]
        result = check(*docs)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["status"] == "PASS" else 2
    except (ValueError, OSError, TypeError, KeyError) as e:
        print("HOLD: " + str(e), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
