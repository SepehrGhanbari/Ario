#!/usr/bin/env python3
"""Fail-closed, staged restore for ARIO_FULL_TEXT_EXPORT_V1."""
import argparse,base64,binascii,hashlib,json,os,pathlib,re,shutil,stat,tempfile,unicodedata
FMT=b"ARIO_FULL_TEXT_EXPORT_V1"
FOOT=re.compile(rb"@@ARIO_COMPLETE files=(\d+) commit=([0-9a-f]{40}) tree=([0-9a-f]{40}) tracked_bytes=(\d+) manifest_sha256=([0-9a-f]{64})\n")
RES={"CON","PRN","AUX","NUL","CONIN$","CONOUT$","COM¹","COM²","COM³","LPT¹","LPT²","LPT³",*(f"COM{i}" for i in range(1,10)),*(f"LPT{i}" for i in range(1,10))}
# Default resource limits for a research-only V1 restore consumer.
MAX_INPUT_BYTES = 384 * 1024 * 1024
MAX_HEADER_LINE_BYTES = 4096
MAX_HEADER_BYTES = 16384
MAX_RECORD_LINE_BYTES = 65536
MAX_FOOTER_LINE_BYTES = 512
MAX_FILES = 10000
MAX_TRACKED_BYTES = 256 * 1024 * 1024
MAX_RECORD_RAW_BYTES = 64 * 1024 * 1024
# Base64's line-wrapped representation is larger than the raw blob.
MAX_RECORD_PAYLOAD_BYTES = 90 * 1024 * 1024
MAX_PATH_BYTES = 4096
MAX_PATH_COMPONENT_BYTES = 255
MAX_PATH_DEPTH = 128
MAX_PATH_INDEX_ENTRIES = 100000
MAX_PATH_INDEX_BYTES = 8 * 1024 * 1024
class SnapshotError(ValueError): pass
def blobsha(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def portable_key(s): return unicodedata.normalize("NFC",s.casefold())
def compact_base64(payload):
 # bytes.split() builds one Python object per whitespace-delimited token and
 # can amplify a bounded ~1 MiB payload into tens of MiB of transient memory.
 return payload.translate(None,b" \t\r\n\v\f")
def _unique_object(pairs):
 result={}
 for key,value in pairs:
  if key in result: raise SnapshotError("duplicate record JSON key")
  result[key]=value
 return result
def _reject_nonfinite(_token):
 raise SnapshotError("non-finite JSON constant")
def safe(s):
 if not isinstance(s,str) or not s or "\\" in s or "\0" in s or any(0xD800 <= ord(ch) <= 0xDFFF for ch in s): raise SnapshotError("invalid path")
 if len(s.encode("utf-8"))>MAX_PATH_BYTES: raise SnapshotError("path length limit")
 p=pathlib.PurePosixPath(s); w=pathlib.PureWindowsPath(s)
 if not p.parts or p.as_posix()!=s: raise SnapshotError("non-canonical or empty path")
 if len(p.parts)>MAX_PATH_DEPTH: raise SnapshotError("path depth limit")
 if p.is_absolute() or w.drive or w.root or w.is_absolute() or ".." in p.parts: raise SnapshotError("absolute or escaping path")
 for x in p.parts:
  if len(x.encode("utf-8"))>MAX_PATH_COMPONENT_BYTES: raise SnapshotError("path component byte limit")
  device_base=x.split(".",1)[0].rstrip(" ").upper()
  if (x in ("",".","..") or x.endswith(("."," ")) or ":" in x
      or any(ord(c)<32 or c in '<>"|?*' for c in x)
      or device_base in RES): raise SnapshotError("non-portable path")
 return p
def restore(src,dst):
 dst=pathlib.Path(dst).absolute()
 if os.path.lexists(dst): raise SnapshotError("destination must not exist")
 dst.parent.mkdir(parents=True,exist_ok=True); stage=pathlib.Path(tempfile.mkdtemp(prefix="."+dst.name+".stage-",dir=dst.parent)); done=False
 try:
  with open(src,"rb") as f:
   info=os.fstat(f.fileno())
   if not stat.S_ISREG(info.st_mode) or info.st_size>MAX_INPUT_BYTES: raise SnapshotError("input source type or size limit")
   fmt=f.readline(MAX_HEADER_LINE_BYTES+1)
   if len(fmt)>MAX_HEADER_LINE_BYTES or fmt.rstrip(b"\r\n")!=FMT: raise SnapshotError("unsupported format or oversized format line")
   h={}; header_bytes=len(fmt)
   while True:
    line=f.readline(MAX_HEADER_LINE_BYTES+1)
    header_bytes+=len(line)
    if len(line)>MAX_HEADER_LINE_BYTES or header_bytes>MAX_HEADER_BYTES: raise SnapshotError("header resource limit")
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
   if len(h["tracked_files"])>len(str(MAX_FILES)) or len(h["tracked_bytes"])>len(str(MAX_TRACKED_BYTES)): raise SnapshotError("oversized count encoding")
   expected_n,expected_b=int(h["tracked_files"]),int(h["tracked_bytes"])
   if expected_n>MAX_FILES or expected_b>MAX_TRACKED_BYTES: raise SnapshotError("snapshot resource limit")
   seen=set(); folded=set(); all_parents=set(); folded_components={}; path_index_entries=path_index_bytes=0; n=total=0
   while True:
    line=f.readline(MAX_RECORD_LINE_BYTES+1)
    if len(line)>MAX_RECORD_LINE_BYTES or f.tell()>MAX_INPUT_BYTES: raise SnapshotError("record header resource limit")
    if not line: raise SnapshotError("missing footer")
    if line.startswith(b"@@ARIO_COMPLETE"):
     if len(line)>MAX_FOOTER_LINE_BYTES: raise SnapshotError("footer resource limit")
     m=FOOT.fullmatch(line)
     if not m: raise SnapshotError("malformed footer")
     fn,fc,ft,fb,fm=m.groups()
     if int(fn)!=n or n!=expected_n or fc.decode()!=h["commit"] or ft.decode()!=h["tree"] or int(fb)!=total or total!=expected_b or fm.decode()!=h["manifest_sha256"]: raise SnapshotError("header/footer/record mismatch")
     if f.read(1): raise SnapshotError("trailing bytes")
     break
    if not line.startswith(b"@@ARIO_FILE "): raise SnapshotError("bad record boundary")
    try: e=json.loads(line[len(b"@@ARIO_FILE "):].decode("utf-8"),object_pairs_hook=_unique_object,parse_constant=_reject_nonfinite)
    except Exception as ex: raise SnapshotError("invalid record JSON") from ex
    keys={"path","mode","git_blob_sha1","sha256","bytes","encoding","payload_bytes"}
    if not isinstance(e,dict) or not keys<=e.keys(): raise SnapshotError("incomplete record")
    if n>=expected_n or n>=MAX_FILES: raise SnapshotError("record count budget exceeded")
    p=safe(e["path"]); name=p.as_posix()
    if name in seen or name in all_parents or portable_key(name) in folded: raise SnapshotError("duplicate, case collision, or file/directory conflict")
    parts=p.parts
    for i in range(1,len(parts)+1):
     prefix="/".join(parts[:i]); key=portable_key(prefix)
     previous=folded_components.get(key)
     if previous is None:
      added=len(key.encode("utf-8"))+len(prefix.encode("utf-8"))
      if path_index_entries>=MAX_PATH_INDEX_ENTRIES or path_index_bytes+added>MAX_PATH_INDEX_BYTES: raise SnapshotError("path index resource limit")
      folded_components[key]=prefix; path_index_entries+=1; path_index_bytes+=added
     elif previous!=prefix: raise SnapshotError("case-colliding path component")
     if i<len(parts):
      if prefix in seen: raise SnapshotError("file/directory path conflict")
      all_parents.add(prefix)
    seen.add(prefix); folded.add(key)
    if e["mode"] not in ("100644","100755","120000"): raise SnapshotError("unsupported Git mode")
    for k in ("bytes","payload_bytes"):
     if not isinstance(e[k],int) or isinstance(e[k],bool) or e[k]<0: raise SnapshotError("invalid byte count")
    if (e["payload_bytes"]>MAX_RECORD_PAYLOAD_BYTES
        or e["bytes"]>MAX_RECORD_RAW_BYTES
        or total+e["bytes"]>expected_b
        or total+e["bytes"]>MAX_TRACKED_BYTES
        or f.tell()+e["payload_bytes"]>MAX_INPUT_BYTES): raise SnapshotError("record resource limit")
    if not re.fullmatch("[0-9a-f]{40}",str(e["git_blob_sha1"])) or not re.fullmatch("[0-9a-f]{64}",str(e["sha256"])): raise SnapshotError("invalid digest")
    payload=f.read(e["payload_bytes"])
    if len(payload)!=e["payload_bytes"] or f.readline()!=b"\n" or f.readline()!=b"@@ARIO_END\n": raise SnapshotError("truncated payload/bad terminator")
    if e["encoding"]=="raw-utf8":
     try: payload.decode("utf-8")
     except UnicodeDecodeError as ex: raise SnapshotError("invalid UTF-8") from ex
     raw=payload
    elif e["encoding"]=="base64":
     try: raw=base64.b64decode(compact_base64(payload),validate=True)
     except (ValueError,binascii.Error) as ex: raise SnapshotError("invalid Base64") from ex
    else: raise SnapshotError("unsupported encoding")
    if len(raw)!=e["bytes"] or hashlib.sha256(raw).hexdigest()!=e["sha256"] or blobsha(raw)!=e["git_blob_sha1"]: raise SnapshotError("payload integrity mismatch: "+name)
    target=stage.joinpath(*p.parts); target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(raw)
    if e["mode"]=="100755": target.chmod(target.stat().st_mode|stat.S_IXUSR|stat.S_IXGRP|stat.S_IXOTH)
    # Symlink blobs remain regular files; never create links from untrusted data.
    total+=len(raw); n+=1
  os.replace(stage,dst); done=True; print(f"RESTORE_STRUCTURAL_PASS_AUTHENTICITY_UNKNOWN: {n} records at {dst}"); return n
 finally:
  if not done and stage.exists(): shutil.rmtree(stage,ignore_errors=True)
def main():
 p=argparse.ArgumentParser(description=__doc__); p.add_argument("input_path"); p.add_argument("output_path"); a=p.parse_args()
 try: restore(a.input_path,a.output_path)
 except (OSError,SnapshotError) as e: p.exit(2,"RESTORE_REJECTED: "+str(e)+"\n")
if __name__=="__main__": main()
