#!/usr/bin/env python3
import subprocess, json, hashlib, base64, pathlib, re, zipfile, sys, unicodedata
R=pathlib.Path(__file__).resolve().parent
SRC=R/"source"; OUT=R/"artifacts"; OUT.mkdir(exist_ok=True)
def g(*args):return subprocess.check_output(["git","-C",str(SRC),*args])
def hash256(b):return hashlib.sha256(b).hexdigest()
sha=g("rev-parse","HEAD").decode().strip()
assert re.fullmatch("[0-9a-f]{40}",sha)
tree=g("rev-parse","HEAD^{tree}").decode().strip()
date=g("show","-s","--format=%cI","HEAD").decode().strip()
rec=[]
RESERVED={"CON","PRN","AUX","NUL","CONIN$","CONOUT$","COM¹","COM²","COM³","LPT¹","LPT²","LPT³",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}
seen_paths=set(); folded_paths=set(); all_parents=set(); folded_components={}
def portable_key(s):return unicodedata.normalize("NFC",s.casefold())
for item in g("ls-tree","-r","-z","--full-tree","HEAD").split(b"\x00"):
 if not item:continue
 h,path=item.split(b"\t",1)
 mode,typ,oid=h.decode().split()
 if typ!="blob":raise ValueError(("Unsupported object type",typ,path))
 name=path.decode("utf-8","strict")
 p=pathlib.PurePosixPath(name)
 wp=pathlib.PureWindowsPath(name)
 if p.is_absolute() or wp.drive or wp.root or wp.is_absolute() or ".." in p.parts or p.as_posix()!=name or "\\" in name or any(part.endswith((".", " ")) or ":" in part or part.split(".",1)[0].upper() in RESERVED or any(ord(ch)<32 or ch in '<>"|?*' for ch in part) for part in p.parts):raise ValueError("unsafe or non-portable path")
 if name in seen_paths or name in all_parents or portable_key(name) in folded_paths:raise ValueError("duplicate, case-colliding, or file/directory-conflicting path")
 parts=p.parts
 for i in range(1,len(parts)+1):
  prefix="/".join(parts[:i]);key=portable_key(prefix);previous=folded_components.get(key)
  if previous is not None and previous!=prefix:raise ValueError("case-colliding path component")
  folded_components[key]=prefix
  if i<len(parts) and prefix in seen_paths:raise ValueError("file/directory path conflict")
 seen_paths.add(name);folded_paths.add(portable_key(name))
 for i in range(1,len(parts)):all_parents.add("/".join(parts[:i]))
 raw=g("cat-file","blob",oid)
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
No files are omitted or summarized; duplicate tracked paths are intentionally retained.
Neither format includes .git history, untracked local files, or off-repo resources.
Verify every SHA256 in the manifest. This snapshot is pinned, not live HEAD.
To reconstruct the TXT, use RESTORE_FROM_TXT.py enclosed in ZIP.
"""
(OUT/"README-EXPORT.txt").write_text(guide,encoding="utf-8",newline="\n")
restore=(R/"RESTORE_FROM_TXT_HARDENED.py").read_text(encoding="utf-8")
(OUT/"RESTORE_FROM_TXT.py").write_text(restore,encoding="utf-8",newline="\n")
txt=OUT/"ario-full.txt"
with open(txt,"wb") as f:
 f.write((f"ARIO_FULL_TEXT_EXPORT_V1\nrepo=https://github.com/SepehrGhanbari/Ario\ncommit={sha}\ntree={tree}\ntracked_files={len(rec)}\ntracked_bytes={manifest['tracked_bytes']}\nmanifest_sha256={hash256(m)}\nraw-utf8 records preserve exact bytes; other records Base64 encode exact bytes.\nEach record's payload_bytes gives the exact length. One separator newline follows.\n@@ARIO_BEGIN\n").encode())
 for e,raw in rec:
  payload=raw if e["encoding"]=="raw-utf8" else base64.encodebytes(raw)
  f.write(b"@@ARIO_FILE "+json.dumps({**e,"payload_bytes":len(payload)},ensure_ascii=True,sort_keys=True,separators=(",",":")).encode("ascii")+b"\n")
  f.write(payload)
  f.write(b"\n@@ARIO_END\n")
 f.write((f"@@ARIO_COMPLETE files={len(rec)} commit={sha} tree={tree} tracked_bytes={manifest['tracked_bytes']} manifest_sha256={hash256(m)}\n").encode())
def info(path,mode):
 z=zipfile.ZipInfo(path,(2026,11,11,0,0,0))
 z.create_system=3
 z.external_attr=int(mode,8)<<16
 z.compress_type=zipfile.ZIP_DEFLATED
 return z
zp=OUT/"ario-full.zip"
with zipfile.ZipFile(zp,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9,allowZip64=True) as z:
 for e,raw in rec:z.writestr(info("ARIO_SOURCE/"+e["path"],e["mode"]),raw)
 for x in ["ario-manifest.json","README-EXPORT.txt","RESTORE_FROM_TXT.py"]:z.writestr(info("EXPORT_META/"+x,"100644"),(OUT/x).read_bytes())
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
restored_root=OUT/"restored-from-txt"
restore(txt,restored_root)
for e,raw in rec:
 assert (restored_root/e["path"]).read_bytes()==raw,e["path"]
cs={"commit":sha,"git_tree":tree,"tracked_files":len(rec),"tracked_bytes":manifest["tracked_bytes"],"verification":"PASS: ZIP and TXT independently reconstructed all Git blobs and matched source SHA1/SHA256."}
for x in ["ario-full.zip","ario-full.txt","ario-manifest.json","README-EXPORT.txt","RESTORE_FROM_TXT.py"]:
 b=(OUT/x).read_bytes();cs[x]={"bytes":len(b),"sha256":hash256(b)}
(OUT/"checksums.json").write_text(json.dumps(cs,indent=2)+"\n",encoding="utf-8",newline="\n")
print(json.dumps(cs,indent=2))
