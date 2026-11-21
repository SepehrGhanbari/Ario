#!/usr/bin/env python3
"""Compare restored snapshot files with Git blob objects from the pinned source checkout."""
import argparse,hashlib,os,pathlib,subprocess
def git(root,*args): return subprocess.check_output(["git","-C",str(root),*args])
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--source",required=True);ap.add_argument("--restored",required=True);a=ap.parse_args()
 src=pathlib.Path(a.source).resolve();dst=pathlib.Path(a.restored).resolve()
 rows=[]
 for item in git(src,"ls-tree","-r","-z","--full-tree","HEAD").split(b"\0"):
  if not item:continue
  head,path=item.split(b"\t",1);mode,typ,oid=head.decode().split()
  if typ!="blob":raise SystemExit(f"unsupported object type {typ}: {os.fsdecode(path)}")
  rows.append((os.fsdecode(path),mode,oid))
 expected={p for p,_,_ in rows}
 actual={p.relative_to(dst).as_posix() for p in dst.rglob("*") if p.is_file()}
 if actual!=expected:
  raise SystemExit(f"path set mismatch: missing={sorted(expected-actual)[:10]} extra={sorted(actual-expected)[:10]}")
 for path,mode,oid in rows:
  raw=git(src,"cat-file","blob",oid)
  got=(dst/path).read_bytes()
  if got!=raw:raise SystemExit(f"byte mismatch: {path}")
  actual_oid=hashlib.sha1(b"blob "+str(len(got)).encode()+b"\0"+got).hexdigest()
  if actual_oid!=oid:raise SystemExit(f"Git blob SHA-1 mismatch: {path}")
  if os.name!="nt" and mode=="100755" and not ((dst/path).stat().st_mode & 0o111):raise SystemExit(f"executable bit missing: {path}")
 print(f"ROUNDTRIP_VERIFIED: {len(rows)} Git blobs; exact paths and bytes; executable modes checked")
if __name__=="__main__":main()
