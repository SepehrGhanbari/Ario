#!/usr/bin/env python3
"""Build PUBLIC_PACKAGE_FILE_MANIFEST_V3 from immutable Git blob bytes."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, subprocess, sys, os

def git(repo: pathlib.Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(repo), *args])

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\\0" + data).hexdigest()

def build(repo: pathlib.Path, manifest_v2: pathlib.Path, ref: str) -> dict:
    repo = repo.resolve()
    manifest_v2 = manifest_v2.resolve()
    old = json.loads(manifest_v2.read_text(encoding="utf-8"))
    if old.get("format") != "PUBLIC_PACKAGE_FILE_MANIFEST_V2":
        raise ValueError("input manifest is not V2")
    listed = old.get("files")
    if not isinstance(listed, dict) or len(listed) != old.get("file_count_excluding_self"):
        raise ValueError("V2 file list/count is inconsistent")
    commit = git(repo, "rev-parse", "--verify", ref + "^{commit}").decode("ascii").strip()
    tree_rows = {}
    for row in git(repo, "ls-tree", "-r", "-z", "--full-tree", commit).split(b"\\0"):
        if not row:
            continue
        meta, raw_path = row.split(b"\\t", 1)
        mode, obj_type, oid = meta.decode("ascii").split()
        tree_rows[raw_path.decode("utf-8")] = (mode, obj_type, oid)
    package_root = pathlib.Path(os.path.relpath(manifest_v2.parent, repo)).as_posix()
    entries, corrections = {}, []
    for rel_path, previous in sorted(listed.items()):
        if not isinstance(rel_path, str) or rel_path.startswith("/") or ".." in pathlib.PurePosixPath(rel_path).parts:
            raise ValueError("unsafe path in V2 manifest: " + repr(rel_path))
        full_path = package_root + "/" + rel_path
        row = tree_rows.get(full_path)
        if row is None:
            raise ValueError("path absent from selected Git tree: " + full_path)
        mode, obj_type, oid = row
        if obj_type != "blob" or mode not in ("100644", "100755"):
            raise ValueError("manifest path is not a regular Git blob: " + full_path)
        raw = git(repo, "cat-file", "blob", oid)
        if git_blob_sha1(raw) != oid:
            raise ValueError("Git blob object hash mismatch: " + full_path)
        current = {"bytes": len(raw), "sha256": sha256(raw), "git_blob_sha1": oid}
        entries[rel_path] = current
        if previous.get("bytes") != current["bytes"] or previous.get("sha256") != current["sha256"]:
            crlf = raw.replace(b"\\n", b"\\r\\n") if b"\\r\\n" not in raw else raw
            crlf_match = crlf != raw and len(crlf) == previous.get("bytes") and sha256(crlf) == previous.get("sha256")
            corrections.append({
                "path": rel_path,
                "previous_v2": {"bytes": previous.get("bytes"), "sha256": previous.get("sha256")},
                "git_blob_v3": current,
                "diagnosis": "V2_HASH_MATCHED_LF_TO_CRLF_CONVERSION" if crlf_match else "V2_VALUE_DID_NOT_MATCH_GIT_BLOB",
            })
    out = {k: v for k, v in old.items() if k not in ("format", "date", "files", "file_count_excluding_self")}
    out.update({
        "format": "PUBLIC_PACKAGE_FILE_MANIFEST_V3",
        "revision_date": "2026-11-16",
        "supersedes": "PUBLIC_PACKAGE_FILE_MANIFEST.json (V2 retained unchanged)",
        "source_git_commit": commit,
        "hash_basis": "Exact bytes read from Git blob objects using git cat-file; not checkout/worktree bytes.",
        "line_ending_policy": "No normalization. LF, CRLF, and all other bytes are hashed exactly as stored in the selected Git blob.",
        "file_count_excluding_self": len(entries),
        "correction_log": corrections,
        "files": entries,
    })
    return out

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repo", type=pathlib.Path, default=pathlib.Path.cwd())
    ap.add_argument("--manifest-v2", type=pathlib.Path, required=True)
    ap.add_argument("--ref", required=True, help="Explicit Git ref or commit; never inferred.")
    ap.add_argument("--output", type=pathlib.Path, required=True)
    args = ap.parse_args()
    try:
        result = build(args.repo, args.manifest_v2, args.ref)
        data = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\\n").encode("utf-8")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(data)
        print(json.dumps({"status":"BUILT_FROM_GIT_BLOBS","source_git_commit":result["source_git_commit"],"file_count":result["file_count_excluding_self"],"corrections":len(result["correction_log"]),"output":str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
        print("MANIFEST_BUILD_REJECTED: " + str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
