#!/usr/bin/env python3
import hashlib, json, shutil, subprocess, sys, tempfile
from pathlib import Path

bundle=Path(sys.argv[1])
go_dir=Path(sys.argv[2])
cases=[
 ("checkpoint.raw", b"signature=", "log-signature"),
 ("consistency-281670.raw", b"node_hash=", "consistency-proof"),
 ("inclusion-281650.raw", b"leaf_index=", "inclusion-proof"),
 ("leaf-281650.ascii", b"leaf=", "leaf-signature"),
]
def flip(data,prefix):
 lines=data.splitlines(keepends=True)
 for i,line in enumerate(lines):
  if line.startswith(prefix):
   pos=line.find(b"=")+1
   if pos>=len(line): continue
   c=line[pos:pos+1]
   replacement=b"0" if c!=b"0" else b"1"
   lines[i]=line[:pos]+replacement+line[pos+1:]
   return b"".join(lines)
 raise RuntimeError("MISSING_MUTATION_FIELD:"+prefix.decode())
for filename,prefix,label in cases:
 with tempfile.TemporaryDirectory(prefix="a15-negative-") as td:
  dst=Path(td)/"bundle";shutil.copytree(bundle,dst)
  target=dst/filename;mutated=flip(target.read_bytes(),prefix);target.write_bytes(mutated)
  mpath=dst/"manifest.json";m=json.loads(mpath.read_text())
  m["files"][filename]=hashlib.sha256(mutated).hexdigest()
  mpath.write_text(json.dumps(m,indent=2)+"\n")
  r=subprocess.run(["go","run",".","verify",str(dst)],cwd=go_dir,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
  if r.returncode==0: raise SystemExit("FAIL: tampered "+label+" accepted")
  print("PASS: tampered "+label+" rejected")
print("A15_V10_FOUR_CRYPTOGRAPHIC_TAMPERS_REJECTED")
