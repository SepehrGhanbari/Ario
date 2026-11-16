#!/usr/bin/env python3
"""Fail-closed, staged restore for ARIO_FULL_TEXT_EXPORT_V1."""
import argparse,base64,binascii,hashlib,json,os,pathlib,re,shutil,stat,tempfile
FMT=b"ARIO_FULL_TEXT_EXPORT_V1"
FOOT=re.compile(rb"@@ARIO_COMPLETE files=(\d+) commit=([0-9a-f]{40}) tree=([0-9a-f]{40}) tracked_bytes=(\d+) manifest_sha256=([0-9a-f]{64})\n")
RES={"CON","PRN","AUX","NUL","CONIN$","CONOUT$","COM¹","COM²","COM³","LPT¹","LPT²","LPT³",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}
class SnapshotError(ValueError): pass
def blobsha(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def safe(s):
 if not isinstance(s,str) or not s or "\\" in s or "\0" in s or any(0xD800 <= ord(ch) <= 0xDFFF for ch in s): raise SnapshotError("invalid path")
 p=pathlib.PurePosixPath(s); w=pathlib.PureWindowsPath(s)
 if p.as_posix()!=s: raise SnapshotError("non-canonical path")
 if p.is_absolute() or w.drive or w.root or w.is_absolute() or ".." in p.parts: raise SnapshotError("absolute or escaping path")
 for x in p.parts:
  if x in ("",".","..") or x.endswith(("."," ")) or ":" in x or x.split(".",1)[0].upper() in RES: raise SnapshotError("non-portable path")
 return p
def restore(src,dst):
 dst=pathlib.Path(dst).absolute()
 if os.path.lexists(dst): raise SnapshotError("destination must not exist")
 dst.parent.mkdir(parents=True,exist_ok=True); stage=pathlib.Path(tempfile.mkdtemp(prefix="."+dst.name+".stage-",dir=dst.parent)); done=False
 try:
  with open(src,"rb") as f:
   if f.readline().rstrip(b"\r\n")!=FMT: raise SnapshotError("unsupported format")
   h={}
   while True:
    line=f.readline()
    if not line: raise SnapshotError("missing begin marker")
    if line==b"@@ARIO_BEGIN\n": break
    try: t=line.decode("ascii").rstrip("\r\n")
    except UnicodeDecodeError as e: raise SnapshotError("non-ascii header") from e
    if "=" in t:
     k,v=t.split("=",1)
     if k in h: raise SnapshotError("duplicate header")
     h[k]=v
   need={"repo","commit","tree","tracked_files","tracked_bytes","manifest_sha256"}
   if not need<=h.keys() or not re.fullmatch("[0-9a-f]{40}",h["commit"]) or not re.fullmatch("[0-9a-f]{40}",h["tree"]) or not re.fullmatch("[0-9a-f]{64}",h["manifest_sha256"]): raise SnapshotError("invalid header")
   if not h["tracked_files"].isdigit() or not h["tracked_bytes"].isdigit(): raise SnapshotError("invalid counts")
   expected_n,expected_b=int(h["tracked_files"]),int(h["tracked_bytes"])
   if expected_n>1000000 or expected_b>2**50: raise SnapshotError("snapshot exceeds limits")
   seen=set(); folded=set(); all_parents=set(); folded_components={}; n=total=0
   while True:
    line=f.readline()
    if not line: raise SnapshotError("missing footer")
    if line.startswith(b"@@ARIO_COMPLETE"):
     m=FOOT.fullmatch(line)
     if not m: raise SnapshotError("malformed footer")
     fn,fc,ft,fb,fm=m.groups()
     if int(fn)!=n or n!=expected_n or fc.decode()!=h["commit"] or ft.decode()!=h["tree"] or int(fb)!=total or total!=expected_b or fm.decode()!=h["manifest_sha256"]: raise SnapshotError("header/footer/record mismatch")
     if f.read(): raise SnapshotError("trailing bytes")
     break
    if not line.startswith(b"@@ARIO_FILE "): raise SnapshotError("bad record boundary")
    try: e=json.loads(line[len(b"@@ARIO_FILE "):].decode("utf-8"))
    except Exception as ex: raise SnapshotError("invalid record JSON") from ex
    keys={"path","mode","git_blob_sha1","sha256","bytes","encoding","payload_bytes"}
    if not isinstance(e,dict) or not keys<=e.keys(): raise SnapshotError("incomplete record")
    p=safe(e["path"]); name=p.as_posix()
    if name in seen or name in all_parents or name.casefold() in folded: raise SnapshotError("duplicate, case collision, or file/directory conflict")
    parts=p.parts
    for i in range(1,len(parts)+1):
     prefix="/".join(parts[:i]); key=prefix.casefold()
     previous=folded_components.get(key)
     if previous is not None and previous!=prefix: raise SnapshotError("case-colliding path component")
     folded_components[key]=prefix
     if i<len(parts) and prefix in seen: raise SnapshotError("file/directory path conflict")
    seen.add(name); folded.add(name.casefold())
    for i in range(1,len(parts)): all_parents.add("/".join(parts[:i]))
    if e["mode"] not in ("100644","100755","120000"): raise SnapshotError("unsupported Git mode")
    for k in ("bytes","payload_bytes"):
     if not isinstance(e[k],int) or isinstance(e[k],bool) or e[k]<0: raise SnapshotError("invalid byte count")
    if e["payload_bytes"]>2**40: raise SnapshotError("record too large")
    if not re.fullmatch("[0-9a-f]{40}",str(e["git_blob_sha1"])) or not re.fullmatch("[0-9a-f]{64}",str(e["sha256"])): raise SnapshotError("invalid digest")
    payload=f.read(e["payload_bytes"])
    if len(payload)!=e["payload_bytes"] or f.readline()!=b"\n" or f.readline()!=b"@@ARIO_END\n": raise SnapshotError("truncated payload/bad terminator")
    if e["encoding"]=="raw-utf8":
     try: payload.decode("utf-8")
     except UnicodeDecodeError as ex: raise SnapshotError("invalid UTF-8") from ex
     raw=payload
    elif e["encoding"]=="base64":
     try: raw=base64.b64decode(b"".join(payload.split()),validate=True)
     except (ValueError,binascii.Error) as ex: raise SnapshotError("invalid Base64") from ex
    else: raise SnapshotError("unsupported encoding")
    if len(raw)!=e["bytes"] or hashlib.sha256(raw).hexdigest()!=e["sha256"] or blobsha(raw)!=e["git_blob_sha1"]: raise SnapshotError("payload integrity mismatch: "+name)
    target=stage.joinpath(*p.parts); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    if e["mode"]=="100755": target.chmod(target.stat().st_mode|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)
    # Symlink blobs remain regular files; never create links from untrusted data.
    total+=len(raw); n+=1
  os.replace(stage,dst); done=True; print(f"RESTORE_VERIFIED: {n} records at {dst}"); return n
 finally:
  if not done and stage.exists(): shutil.rmtree(stage,ignore_errors=True)
def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("input_path"); p.add_argument("output_path"); a=p.parse_args()
 try: restore(a.input_path,a.output_path)
 except (OSError,SnapshotError) as e: p.exit(2,"RESTORE_REJECTED: "+str(e)+"\n")
if __name__=="__main__": main()
