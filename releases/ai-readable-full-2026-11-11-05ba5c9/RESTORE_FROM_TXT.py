#!/usr/bin/env python3
import sys,json,base64,hashlib,pathlib
def restore(input_path,output_path):
 dst=pathlib.Path(output_path)
 if dst.exists() and any(dst.iterdir()):raise ValueError("Output directory is not empty")
 dst.mkdir(parents=True,exist_ok=True)
 seen=set();count=0
 with open(input_path,"rb") as f:
  while True:
   line=f.readline()
   if not line:raise ValueError("Missing ARIO_BEGIN")
   if line==b"@@ARIO_BEGIN\n":break
  while True:
   line=f.readline()
   if line.startswith(b"@@ARIO_COMPLETE "):break
   if not line.startswith(b"@@ARIO_FILE "):raise ValueError("Bad record boundary")
   e=json.loads(line[len(b"@@ARIO_FILE "):])
   path=pathlib.PurePosixPath(e["path"])
   if path.is_absolute() or ".." in path.parts or str(path) in seen:raise ValueError("Unsafe or duplicate path")
   seen.add(str(path))
   blob=f.read(e["payload_bytes"])
   if len(blob)!=e["payload_bytes"]:raise ValueError("Truncated payload")
   if f.readline()!=b"\n" or f.readline()!=b"@@ARIO_END\n":raise ValueError("Bad record ending")
   raw=blob if e["encoding"]=="raw-utf8" else base64.b64decode(blob)
   if len(raw)!=e["bytes"] or hashlib.sha256(raw).hexdigest()!=e["sha256"]:raise ValueError("Hash mismatch: "+str(path))
   target=dst.joinpath(*path.parts)
   target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(raw)
   count+=1
  if f.read():raise ValueError("Unexpected trailing TXT bytes")
 print("Restored",count,"tracked Git blobs")
if __name__=="__main__":
 if len(sys.argv)!=3:raise SystemExit("Usage: python RESTORE_FROM_TXT.py ario-full.txt output-directory")
 restore(sys.argv[1],sys.argv[2])
