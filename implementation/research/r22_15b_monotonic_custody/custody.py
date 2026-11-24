"""Bounded synthetic 4->6 custody; no runtime authority or signer continuity."""
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

LOG="4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
PROFILE="ARIO-R22.15B-SYNTHETIC-CUSTODY-v1"
HEX=re.compile("[0-9a-f]{64}")
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")
def sha(x): return hashlib.sha256(x).hexdigest()
def checksum(x): return sha(hashlib.sha256(x).digest())
def unique(pairs):
    x={}
    for k,v in pairs:
        if k in x: raise ValueError("duplicate")
        x[k]=v
    return x
def parse(raw):
    x=json.loads(raw.decode("ascii"),object_pairs_hook=unique)
    if canon(x)+b"\n"!=raw: raise ValueError("noncanonical")
    return x
def read(p,n=65536):
    with Path(p).open("rb") as f: x=f.read(n+1)
    if not 0<len(x)<=n: raise ValueError("size")
    return x
def ledger(raw):
    rows=[]; prev=None
    if not raw.endswith(b"\n"): raise ValueError("ledger end")
    for line in raw.splitlines(keepends=True):
        x=parse(line)
        if type(x) is not dict or set(x)!={"record_id","observed_at","payload","previous_sha256","sha256"}: raise ValueError("row")
        claimed=x["sha256"]; y=dict(x); del y["sha256"]
        if x["previous_sha256"]!=prev or sha(canon(y))!=claimed or x["record_id"]!=f"ROW-{len(rows)}": raise ValueError("chain")
        if type(x["payload"]) is not dict: raise ValueError("payload")
        prev=claimed; rows.append(x)
    if len(rows) not in (4,6): raise ValueError("count")
    return rows
def record(raw, prior_pin):
    rows=ledger(raw)
    return dict(profile=PROFILE,seq=len(rows),head=rows[-1]["sha256"],ledger_sha256=sha(raw),historical_pin_sha256=prior_pin)
def envelope(raw,scope,previous,prior_pin):
    return dict(profile=PROFILE,scope=scope,previous_checksum=previous,record=record(raw,prior_pin),
                nonce=secrets.token_hex(32),synthetic=True,authoritative=False,trust_activation="NO_GO")
def generate(old_dir,pin_path,new_root):
    a,p,r=map(Path,(old_dir,pin_path,new_root))
    old=read(a/"ledger.jsonl"); rows=ledger(old); assert len(rows)==4
    pin=read(p); pin_obj=parse(pin)
    assert pin_obj["seq"]==4 and pin_obj["ledger_sha256"]==sha(old)
    # The historical pin binds exact bytes, not transfer of the destroyed signer.
    scope=secrets.token_hex(24)
    previous=rows[-1]["sha256"]
    newer=old
    for i in (4,5):
        row=dict(record_id=f"ROW-{i}",observed_at=f"LAB-STEP-{i}",
                 payload=dict(claim_id="R22.15B-SYNTHETIC",node_id=f"OBS-{i}",value=secrets.token_hex(32),lineage_from=f"OBS-{i-1}",lineage_to=f"OBS-{i}"),previous_sha256=previous)
        row["sha256"]=sha(canon(row)); previous=row["sha256"]
        newer+=canon(row)+b"\n"
    prev="GENESIS"
    for name,raw in (("four",old),("six",newer)):
        d=r/name; d.mkdir(parents=True)
        e=canon(envelope(raw,scope,prev,sha(pin)))+b"\n"
        (d/"envelope.json").write_bytes(e); (d/"ledger.jsonl").write_bytes(raw)
        prev=checksum(e)

def verify(d,key,verifier,prior_pin):
    d=Path(d); raw=read(d/"envelope.json",4096); history=read(d/"ledger.jsonl"); proof=read(d/"envelope.json.proof")
    e=parse(raw)
    if (set(e)!={"profile","scope","previous_checksum","record","nonce","synthetic","authoritative","trust_activation"}
        or e["profile"]!=PROFILE or e["synthetic"] is not True or e["authoritative"] is not False or e["trust_activation"]!="NO_GO"
        or not re.fullmatch("[0-9a-f]{48}",e["scope"]) or not HEX.fullmatch(e["nonce"])
        or not (e["previous_checksum"]=="GENESIS" or HEX.fullmatch(e["previous_checksum"]))
        or e["record"]!=record(history,prior_pin)): raise ValueError("envelope binding")
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)/"proof";p.write_bytes(proof)
        subprocess.run([verifier,"-k",key,"-P","sigsum-test1-2025",str(p)],input=raw,check=True,timeout=30,capture_output=True)
    fields={}
    for line in proof.decode("ascii").splitlines():
        k,sep,v=line.partition("=")
        if sep and k in ("log","size","root_hash","leaf_index","leaf"):
            if k in fields: raise ValueError("duplicate proof field")
            fields[k]=v
    if set(fields)!={"log","size","root_hash","leaf_index","leaf"} or fields["log"]!=LOG: raise ValueError("log")
    p=dict(size=int(fields["size"]),root=fields["root_hash"],index=int(fields["leaf_index"]),signer=fields["leaf"].split()[0],checksum=checksum(raw))
    if not 0<=p["index"]<p["size"] or not HEX.fullmatch(p["root"]) or not HEX.fullmatch(p["signer"]): raise ValueError("proof fields")
    return dict(envelope=e,proof=p,ledger=history.decode("ascii"))

def scan(scanner,key,old,new):
    import base64
    blob=base64.b64decode(read(key,2048).decode().split()[1],validate=True)
    n=int.from_bytes(blob[:4],"big")
    if blob[4:4+n]!=b"ssh-ed25519" or int.from_bytes(blob[4+n:8+n],"big")!=32 or len(blob)!=8+n+32: raise ValueError("key")
    pub=blob[8+n:]
    p,q=old["proof"],new["proof"]
    if sha(pub)!=p["signer"] or q["signer"]!=p["signer"]: raise ValueError("signer")
    reports=[]
    for anchor in (p,q):
        boot=dict(start=p["index"],size=anchor["size"],root=anchor["root"],public=pub.hex(),first_checksum=p["checksum"])
        with tempfile.TemporaryDirectory() as td:
            (Path(td)/"bootstrap.json").write_bytes(canon(boot)+b"\n")
            proc=subprocess.run([scanner],cwd=td,check=True,timeout=160,capture_output=True,text=True)
        result=json.loads(proc.stdout.splitlines()[-1])
        if result["complete_sampled_suffix"] is not True or result["matching_signed_leaves"]!=[dict(index=x["index"],checksum=x["checksum"]) for x in (p,q)]: raise ValueError("scan membership")
        reports.append(result)
    a,b=reports
    if (a["sampled_tree_size"],a["sampled_tree_root"])!=(b["sampled_tree_size"],b["sampled_tree_root"]): raise ValueError("sample drift")
    return dict(size=b["sampled_tree_size"],root=b["sampled_tree_root"])

def persist(path,x):
    path=Path(path)
    fd,tmp=tempfile.mkstemp(prefix=".floor-",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as stream:
            stream.write(canon(x)+b"\n");stream.flush();os.fsync(stream.fileno())
        os.replace(tmp,path)
        d=os.open(path.parent,os.O_DIRECTORY)
        try: os.fsync(d)
        finally: os.close(d)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def request(action,state,candidate,key,verifier,scanner,pin,crash=False):
    import fcntl
    state=Path(state); pin_raw=read(pin); prior=sha(pin_raw); historical=parse(pin_raw)
    # lock is in custody-only directory; no publisher-owned path controls it.
    with (state.parent/"lock").open("a+b") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if action=="bootstrap":
            if state.exists(): return "HOLD_ALREADY_PROVISIONED"
            x=verify(candidate,key,verifier,prior)
            if x["envelope"]["record"]["seq"]!=4 or x["envelope"]["previous_checksum"]!="GENESIS" or x["envelope"]["record"]["ledger_sha256"]!=historical["ledger_sha256"]:
                return "HOLD_BOOTSTRAP"
            persist(state,dict(current=x,live_tree=None))
            return "PROVISIONED_4_LAB_ONLY"
        if not state.exists(): return "HOLD_MISSING_RETAINED_STATE"
        retained=parse(read(state,131072)); old=retained["current"]
        if action=="assess":
            raw=read(Path(candidate)/"ledger.jsonl")
            ledger(raw)
            return "MATCH_RETAINED_NOT_FRESHNESS" if raw==old["ledger"].encode("ascii") else "HOLD_HISTORY_MISMATCH"
        new=verify(candidate,key,verifier,prior)
        a,b=old["envelope"],new["envelope"];p,q=old["proof"],new["proof"]
        if new==old: return "MATCH_RETAINED_NOT_FRESHNESS"
        if a["scope"]!=b["scope"] or p["signer"]!=q["signer"]: return "HOLD_SCOPE_OR_SIGNER"
        if b["record"]["seq"]<=a["record"]["seq"]: return "HOLD_NON_ADVANCING"
        if a["record"]["seq"]!=4 or b["record"]["seq"]!=6 or b["previous_checksum"]!=p["checksum"] or q["size"]<=p["size"] or q["index"]<=p["index"]:
            return "HOLD_PREDECESSOR"
        if not new["ledger"].startswith(old["ledger"]): return "HOLD_PREFIX"
        live=scan(scanner,key,old,new)
        persist(state,dict(current=new,live_tree=live))
        if crash: os._exit(75)
        return "ADVANCED_4_TO_6_LAB_ONLY"

if __name__=="__main__":
    if sys.argv[1]=="generate": generate(*sys.argv[2:]);sys.exit(0)
    if sys.argv[1]!="request": raise SystemExit(2)
    args=sys.argv[2:]; crash=args.pop()=="crash"
    try:
        result=request(*args,crash=crash)
    except (ValueError,TypeError,KeyError,IndexError,UnicodeError,OSError,subprocess.SubprocessError,RecursionError):
        result="HOLD_INVALID_OR_UNAVAILABLE_EVIDENCE"
    print(result,flush=True)
