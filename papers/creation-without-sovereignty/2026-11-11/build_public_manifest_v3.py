#!/usr/bin/env python3
"""Build PUBLIC_PACKAGE_FILE_MANIFEST_V3 from immutable Git blobs, never checkout bytes."""
import argparse,hashlib,json,pathlib,re,subprocess,sys
ROOT=pathlib.Path(__file__).resolve().parents[3]
PACKAGE="papers/creation-without-sovereignty/2026-11-11"
V2=pathlib.Path(PACKAGE)/"PUBLIC_PACKAGE_FILE_MANIFEST.json"
def git(*args): return subprocess.check_output(["git","-C",str(ROOT),*args])
def blob(commit,path):
    spec=f"{commit}:{path}"
    oid=git("rev-parse",spec).decode().strip()
    raw=git("cat-file","blob",oid)
    actual=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if actual!=oid: raise SystemExit(f"Git object hash mismatch: {path}")
    return oid,raw
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--commit",required=True)
    ap.add_argument("--output",default=str(pathlib.Path(PACKAGE)/"PUBLIC_PACKAGE_FILE_MANIFEST_V3.json"))
    a=ap.parse_args()
    if not re.fullmatch(r"[0-9a-f]{40}",a.commit): raise SystemExit("invalid commit")
    commit=a.commit
    git("cat-file","-e",commit+"^{commit}")
    tree=git("rev-parse",commit+"^{tree}").decode().strip()
    old_raw=git("show",f"{commit}:{V2.as_posix()}")
    old=json.loads(old_raw)
    files={}
    for rel in sorted(old["files"]):
        if rel.startswith("/") or ".." in pathlib.PurePosixPath(rel).parts or "\\" in rel:
            raise SystemExit(f"unsafe manifest path: {rel}")
        oid,raw=blob(commit,f"{PACKAGE}/{rel}")
        files[rel]={"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"git_blob_sha1":oid}
    if len(files)!=old.get("file_count_excluding_self"):
        raise SystemExit("V2 file count does not match entries")
    out={
      "format":"PUBLIC_PACKAGE_FILE_MANIFEST_V3",
      "date":"2026-11-16",
      "status":"REVIEW_CANDIDATE_GIT_OBJECT_DERIVED_NOT_YET_PUBLISHED",
      "source_commit":commit,
      "source_tree":tree,
      "source_package_path":PACKAGE,
      "source_manifest_format":old.get("format"),
      "source_manifest_sha256":hashlib.sha256(old_raw).hexdigest(),
      "hash_basis":"Exact immutable Git blob bytes retrieved with git cat-file blob at source_commit; independent of checkout newline conversion and working-tree filters.",
      "file_count_excluding_self":len(files),
      "self_hash_excluded":True,
      "historical_v2_preserved":True,
      "excluded_external_asset":old.get("excluded_external_asset"),
      "source_privacy":old.get("source_privacy"),
      "files":files
    }
    target=ROOT/a.output
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")
    # Read-after-write and independently revalidate every generated entry against Git.
    check=json.loads(target.read_text(encoding="utf-8"))
    for rel,entry in check["files"].items():
        oid,raw=blob(commit,f"{PACKAGE}/{rel}")
        assert entry=={"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"git_blob_sha1":oid},rel
    print(json.dumps({"output":str(target.relative_to(ROOT)),"source_commit":commit,"source_tree":tree,"files":len(files),"verification":"PASS_GIT_BLOB_RECOMPUTED"},indent=2))
if __name__=="__main__": main()
