"""R63 G4 synthetic journal adapter: canonical V9-format data, NO signer/key."""
from __future__ import annotations
import hashlib,json,os,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'r63_g3_witness_ci'))
import spend_chain_v2 as v2
PIN="c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"
BASE=(("a"*64,"1"*64),("b"*64,"2"*64))
def exact():
    if hashlib.sha256(Path(v2.__file__).read_bytes()).hexdigest()!=PIN:
        raise RuntimeError("FROZEN_V9_V2_SOURCE_MISMATCH")
def v1(rows):return b"".join(v2.canonical(list(r))+b"\n" for r in rows)
def fsync_create(p,data):
    with p.open("xb") as f:
        f.write(data);f.flush();os.fsync(f.fileno())
def fsync_append(p,data):
    with p.open("ab") as f:
        f.write(data);f.flush();os.fsync(f.fileno())
def inspect(root):
    a=(root/"v1.jsonl").read_bytes();b=(root/"v2.jsonl").read_bytes()
    s=v2.review(b)
    return {"v1_rows":len(a.splitlines()),"v2_events":s.seq,
            "v1_sha256":v2.sha(a),"v2_sha256":v2.sha(b),"head":s.head,
            "coherent":a==v1(s.pairs),"flag":(root/"uncertain.flag").exists()}
def prepare(root):
    exact();root.mkdir(parents=True,exist_ok=False)
    b=b""
    for n,k in BASE:
        b,status=v2.append(b,n,k)
        if status!="NEW_NEEDS_DURABLE_APPEND":raise RuntimeError("BASE_RECORD_INVALID")
    fsync_create(root/"v1.jsonl",v1(BASE))
    fsync_create(root/"v2.jsonl",b)
    return inspect(root)
def commit(root,n,k):
    exact()
    if not v2.ishash(n) or not v2.ishash(k):return "HOLD_BAD_IDENTIFIER"
    if (root/"uncertain.flag").exists():return "HOLD_UNCERTAIN"
    a=(root/"v1.jsonl").read_bytes();b=(root/"v2.jsonl").read_bytes()
    s=v2.review(b)
    if a!=v1(s.pairs):return "HOLD_UNCERTAIN"
    updated,status=v2.append(b,n,k)
    if status=="ALREADY_RESERVED_NO_APPEND":return status
    if status!="NEW_NEEDS_DURABLE_APPEND":return "HOLD_UNCERTAIN"
    fsync_append(root/"v2.jsonl",updated[len(b):])
    fsync_append(root/"v1.jsonl",v2.canonical([n,k])+b"\n")
    return "RESERVED_ONLY_NO_SIGN"
def cli(args):
    if len(args)==2 and args[0]=="--prepare":print(json.dumps(prepare(Path(args[1]))))
    elif len(args)==2 and args[0]=="--inspect":print(json.dumps(inspect(Path(args[1]))))
    elif len(args)==4 and args[0]=="--commit":
        try:print(commit(Path(args[1]),args[2],args[3]))
        except (v2.Hold,OSError,ValueError):print("HOLD_UNCERTAIN")
    elif len(args)==1 and args[0]=="--self-test":
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"journal"
            assert prepare(root)["coherent"]
            n,k="c"*64,"3"*64
            assert commit(root,n,k)=="RESERVED_ONLY_NO_SIGN"
            assert commit(root,n,k)=="ALREADY_RESERVED_NO_APPEND"
            assert inspect(root)["v2_events"]==3
            raw=(root/"v2.jsonl").read_bytes()
            updated,status=v2.append(raw,"d"*64,"4"*64)
            assert status=="NEW_NEEDS_DURABLE_APPEND"
            fsync_append(root/"v2.jsonl",updated[len(raw):])
            assert commit(root,"e"*64,"5"*64)=="HOLD_UNCERTAIN"
        print("G4_JOURNAL_CANONICAL_AND_SPLIT_HOLD=PASS")
    else:raise SystemExit("INVALID_ARGUMENTS")
if __name__=="__main__":cli(sys.argv[1:])
