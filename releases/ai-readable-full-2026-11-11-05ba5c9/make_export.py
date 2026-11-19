#!/usr/bin/env python3
import subprocess, json, hashlib, base64, pathlib, re, zipfile, sys, unicodedata, tempfile, atexit, os, shutil
R=pathlib.Path(__file__).resolve().parent
SRC=R/"source"; FINAL_OUT=R/"artifacts"
if FINAL_OUT.is_symlink():raise ValueError("refusing symlink artifacts destination")
if FINAL_OUT.exists() and not FINAL_OUT.is_dir():raise ValueError("artifacts destination is not a directory")
OUT=pathlib.Path(tempfile.mkdtemp(prefix=".artifacts-stage-",dir=R))
atexit.register(shutil.rmtree,OUT,ignore_errors=True)
def g(*args):return subprocess.check_output(["git","-C",str(SRC),*args])
def hash256(b):return hashlib.sha256(b).hexdigest()
sha=g("rev-parse","HEAD").decode().strip()
assert re.fullmatch("[0-9a-f]{40}",sha)
tree=g("rev-parse","HEAD^{tree}").decode().strip()
date=g("show","-s","--format=%cI","HEAD").decode().strip()
rec=[]
RESERVED={"CON","PRN","AUX","NUL","CONIN$","CONOUT$","COM¹","COM²","COM³","LPT¹","LPT²","LPT³",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}
MAX_FILES=10000
MAX_TRACKED_BYTES=256*1024*1024
MAX_RECORD_RAW_BYTES=64*1024*1024
MAX_RECORD_PAYLOAD_BYTES=90*1024*1024
MAX_PATH_BYTES=4096
MAX_PATH_COMPONENT_BYTES=255
MAX_PATH_DEPTH=128
MAX_PATH_INDEX_ENTRIES=100000
MAX_PATH_INDEX_BYTES=8*1024*1024
MAX_INPUT_BYTES=384*1024*1024
MAX_MANIFEST_BYTES=8*1024*1024
seen_paths=set(); folded_paths=set(); all_parents=set(); folded_components={};sum_raw=0;path_index_entries=path_index_bytes=0
def portable_key(s):return unicodedata.normalize("NFC",s.casefold())
def validate_portable_path(name):
 encoded=name.encode("utf-8","strict")
 if not encoded or len(encoded)>MAX_PATH_BYTES:raise ValueError("path length limit")
 p=pathlib.PurePosixPath(name);wp=pathlib.PureWindowsPath(name)
 if p.is_absolute() or wp.drive or wp.root or wp.is_absolute() or ".." in p.parts or p.as_posix()!=name or chr(92) in name or chr(0) in name:raise ValueError("unsafe or non-canonical path")
 if len(p.parts)>MAX_PATH_DEPTH:raise ValueError("path depth limit")
 for part in p.parts:
  if len(part.encode("utf-8"))>MAX_PATH_COMPONENT_BYTES:raise ValueError("path component byte limit")
  device_base=part.split(".",1)[0].rstrip(" ").upper()
  if (part in ("",".","..") or part.endswith(("."," ")) or ":" in part
      or any(ord(ch)<32 or ch in '<>"|?*' for ch in part)
      or device_base in RESERVED):raise ValueError("unsafe or non-portable path")
 return p
for item in g("ls-tree","-r","-z","--full-tree","HEAD").split(b"\x00"):
 if not item:continue
 h,path=item.split(b"\t",1)
 mode,typ,oid=h.decode().split()
 if typ!="blob":raise ValueError(("Unsupported object type",typ,path))
 name=path.decode("utf-8","strict")
 p=validate_portable_path(name)
 if len(rec)>=MAX_FILES:raise ValueError("tracked file count limit")
 raw_size=int(g("cat-file","-s",oid))
 if raw_size>MAX_RECORD_RAW_BYTES or sum_raw+raw_size>MAX_TRACKED_BYTES:raise ValueError("tracked byte/resource limit")
 if name in seen_paths or portable_key(name) in all_parents or portable_key(name) in folded_paths:raise ValueError("duplicate, case-colliding, or file/directory-conflicting path")
 parts=p.parts
 for i in range(1,len(parts)+1):
  prefix="/".join(parts[:i]);key=portable_key(prefix)
  if i<len(parts) and key in folded_paths:raise ValueError("file/directory path conflict")
  previous=folded_components.get(key)
  if previous is None:
   added=len(key.encode("utf-8"))+len(prefix.encode("utf-8"))
   if path_index_entries>=MAX_PATH_INDEX_ENTRIES or path_index_bytes+added>MAX_PATH_INDEX_BYTES:raise ValueError("path index resource limit")
   folded_components[key]=prefix;path_index_entries+=1;path_index_bytes+=added
  elif previous!=prefix:raise ValueError("case-colliding path component")
  if i<len(parts):all_parents.add(key)
 seen_paths.add(prefix);folded_paths.add(key)
 raw=g("cat-file","blob",oid)
 if len(raw)!=raw_size:raise ValueError("Git blob size mismatch")
 sum_raw+=len(raw)
 if hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=oid:raise ValueError("git sha mismatch")
 try:
  raw.decode("utf-8")
  text=not any((c<32 and c not in (9,10,13)) or c==127 for c in raw)
 except UnicodeDecodeError:text=False
 obj={"path":name,"mode":mode,"git_blob_sha1":oid,"sha256":hash256(raw),"bytes":len(raw),"encoding":"raw-utf8" if text else "base64"}
 rec.append((obj,raw))
rec.sort(key=lambda x:x[0]["path"].encode("utf-8","surrogateescape"))
manifest={"format":"ARIO_FULL_SNAPSHOT_v1","source_repo":"https://github.com/SepehrGhanbari/Ario","ref":"refs/heads/main","commit":sha,"tree":tree,"commit_date":date,"tracked_files":len(rec),"tracked_bytes":sum(len(raw) for _,raw in rec),"text_files":sum(e["encoding"]=="raw-utf8" for e,_ in rec),"binary_files":sum(e["encoding"]=="base64" for e,_ in rec),"scope":"Every tracked Git blob at pinned commit, excluding untracked files, Git history and external submodule data.","files":[e for e,_ in rec]}
m=(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8")
if len(m)>MAX_MANIFEST_BYTES:raise ValueError("manifest byte limit")
(OUT/"ario-manifest.json").write_bytes(m)
guide=f"""ARIO FULL MODEL-READABLE SNAPSHOT
Source: https://github.com/SepehrGhanbari/Ario
Commit: {sha}
Tree: {tree}
File count: {len(rec)}
Total tracked bytes: {manifest["tracked_bytes"]}
ZIP contains each Git-tracked source file byte-for-byte in ARIO_SOURCE/.
TXT includes all files in path order: exact UTF-8 text or Base64 for non-text content.
Every TXT record is length-framed, so an accidental delimiter within source content is harmless.
All accepted tracked Git blobs are included byte-for-byte; unsupported/non-portable paths cause a hard failure, not silent omission.
Duplicate, case-fold/Unicode-normalization aliases and file/directory conflicts are rejected.
Path policy: 4096-byte path, 255-byte component, 128 components, 100,000 indexed prefixes and 8 MiB prefix-index bytes maximum.
Resource policy: 10,000 files, 64 MiB raw per blob, 256 MiB cumulative raw bytes, 90 MiB encoded record and 384 MiB TXT input maximum.
Git symlink blobs are represented as ordinary files containing link-target bytes; link semantics are not recreated.
Neither format includes .git history, untracked local files, or off-repo resources.
Verify every SHA256 in the manifest. This snapshot is pinned, not live HEAD.
To reconstruct the TXT, use RESTORE_FROM_TXT.py in the NEW candidate ZIP.
The historical ZIP is unchanged and may contain an older unsafe restore script.
Independently obtain the expected manifest SHA-256 from a trusted OUT-OF-BAND source.
Then verify the candidate TXT against the candidate manifest and that external pin:
  python VERIFY_PINNED_MANIFEST.py --txt ario-full.txt --manifest ario-manifest.json --expected-manifest-sha256 PIN
A hash appearing only in the downloaded package is not an independent trust anchor.
Even a match does not establish the publisher's identity without trustworthy pin custody.
"""
(OUT/"README-EXPORT.txt").write_text(guide,encoding="utf-8",newline="\n")
restore=(R/"RESTORE_FROM_TXT_HARDENED.py").read_text(encoding="utf-8")
(OUT/"RESTORE_FROM_TXT.py").write_text(restore,encoding="utf-8",newline="\n")
(OUT/"VERIFY_PINNED_MANIFEST.py").write_bytes((R/"verify_pinned_manifest.py").read_bytes())
txt=OUT/"ario-full.txt"
with open(txt,"wb") as f:
 f.write((f"ARIO_FULL_TEXT_EXPORT_V1\nrepo=https://github.com/SepehrGhanbari/Ario\ncommit={sha}\ntree={tree}\ntracked_files={len(rec)}\ntracked_bytes={manifest['tracked_bytes']}\nmanifest_sha256={hash256(m)}\nraw-utf8 records preserve exact bytes; other records Base64 encode exact bytes.\nEach record's payload_bytes gives the exact length. One separator newline follows.\n@@ARIO_BEGIN\n").encode())
 for e,raw in rec:
  payload=raw if e["encoding"]=="raw-utf8" else base64.encodebytes(raw)
  if len(payload)>MAX_RECORD_PAYLOAD_BYTES:raise ValueError("record payload byte limit")
  f.write(b"@@ARIO_FILE "+json.dumps({**e,"payload_bytes":len(payload)},ensure_ascii=True,sort_keys=True,separators=(",",":")).encode("ascii")+b"\n")
  f.write(payload)
  f.write(b"\n@@ARIO_END\n")
 f.write((f"@@ARIO_COMPLETE files={len(rec)} commit={sha} tree={tree} tracked_bytes={manifest['tracked_bytes']} manifest_sha256={hash256(m)}\n").encode())
if txt.stat().st_size>MAX_INPUT_BYTES:raise ValueError("TXT input byte limit; candidate not compatible with restore policy")
def info(path,mode):
 z=zipfile.ZipInfo(path,(2026,11,11,0,0,0))
 z.create_system=3
 z.external_attr=int(mode,8)<<16
 z.compress_type=zipfile.ZIP_DEFLATED
 return z
zp=OUT/"ario-full.zip"
with zipfile.ZipFile(zp,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9,allowZip64=True) as z:
 for e,raw in rec:z.writestr(info("ARIO_SOURCE/"+e["path"],"100644" if e["mode"]=="120000" else e["mode"]),raw)
 for x in ["ario-manifest.json","README-EXPORT.txt","RESTORE_FROM_TXT.py","VERIFY_PINNED_MANIFEST.py"]:z.writestr(info("EXPORT_META/"+x,"100644"),(OUT/x).read_bytes())
# Full archive verification against original Git blobs, not just ZIP CRC.
with zipfile.ZipFile(zp) as z:
 assert z.testzip() is None
 names={x.filename.removeprefix("ARIO_SOURCE/") for x in z.infolist() if x.filename.startswith("ARIO_SOURCE/")}
 assert names=={e["path"] for e,_ in rec}
 for e,raw in rec:assert z.read("ARIO_SOURCE/"+e["path"])==raw,e["path"]
 assert z.read("EXPORT_META/ario-manifest.json")==m
# Verify TXT record by record: exact byte reconstruction of ALL source files.
with open(txt,"rb") as f:
 while f.readline()!=b"@@ARIO_BEGIN\n":pass
 for e,raw in rec:
  h=f.readline()
  assert h.startswith(b"@@ARIO_FILE "),e["path"]
  obj=json.loads(h[12:])
  assert obj["path"]==e["path"]
  payload=f.read(obj["payload_bytes"])
  assert len(payload)==obj["payload_bytes"]
  assert f.readline()==b"\n" and f.readline()==b"@@ARIO_END\n"
  restored=payload if obj["encoding"]=="raw-utf8" else base64.b64decode(payload)
  assert restored==raw and hash256(restored)==obj["sha256"],e["path"]
 assert f.readline()==(f"@@ARIO_COMPLETE files={len(rec)} commit={sha} tree={tree} tracked_bytes={manifest['tracked_bytes']} manifest_sha256={hash256(m)}\n").encode()
 assert f.read()==b""
# Exercise the actual published restore consumer, independently of the TXT parser above.
sys.path.insert(0,str(R))
from RESTORE_FROM_TXT_HARDENED import restore
with tempfile.TemporaryDirectory(prefix="ario-restore-check-") as temp:
 restored_root=pathlib.Path(temp)/"restored"
 restore(txt,restored_root)
 for e,raw in rec:
  restored_file=restored_root/e["path"]
  assert restored_file.read_bytes()==raw,e["path"]
  if e["mode"]=="120000":assert restored_file.is_file() and not restored_file.is_symlink(),e["path"]
cs={"commit":sha,"git_tree":tree,"tracked_files":len(rec),"tracked_bytes":manifest["tracked_bytes"],"verification":"PASS: ZIP and TXT independently reconstructed all Git blobs and matched source SHA1/SHA256."}
for x in ["ario-full.zip","ario-full.txt","ario-manifest.json","README-EXPORT.txt","RESTORE_FROM_TXT.py","VERIFY_PINNED_MANIFEST.py"]:
 b=(OUT/x).read_bytes();cs[x]={"bytes":len(b),"sha256":hash256(b)}
(OUT/"checksums.json").write_text(json.dumps(cs,indent=2)+"\n",encoding="utf-8",newline="\n")
backup=None
if FINAL_OUT.exists():
 backup=pathlib.Path(tempfile.mkdtemp(prefix=".artifacts-backup-",dir=R));backup.rmdir()
 os.replace(FINAL_OUT,backup)
try:
 os.replace(OUT,FINAL_OUT)
except BaseException:
 if backup is not None and not FINAL_OUT.exists():os.replace(backup,FINAL_OUT)
 raise
if backup is not None:shutil.rmtree(backup,ignore_errors=True)
print(json.dumps(cs,indent=2))
