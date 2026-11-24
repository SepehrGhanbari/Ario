"""R22.14 bounded research-only retained tree/floor gate."""
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"r22_12_external_floor"))
import floor_recovery as f
env=f.env
LOG="4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
HEX=re.compile(r"[0-9a-f]{64}\Z")
FIELDS={"profile","log","signer","size","root","index","checksum","scope","seq","floor_commitment","ledger_sha256"}
PROFILE="ARIO-R22.14-RETAINED-SYNTHETIC-FLOOR-v1"

def digest(raw): return hashlib.sha256(raw).hexdigest()
def canonical(obj): return env.canonical(obj)
def bounded(path,cap=32768):
    with Path(path).open("rb") as stream: raw=stream.read(cap+1)
    if not 0<len(raw)<=cap: raise ValueError("size")
    return raw

def valid_floor(x):
    if type(x) is not dict or set(x)!=FIELDS or x["profile"]!=PROFILE or x["log"]!=LOG:
        raise ValueError("floor schema")
    for k in ("signer","root","checksum","floor_commitment","ledger_sha256"):
        if type(x[k]) is not str or not HEX.fullmatch(x[k]): raise ValueError(k)
    if type(x["scope"]) is not str or not env.SCOPE.fullmatch(x["scope"]): raise ValueError("scope")
    if any(type(x[k]) is not int for k in ("size","index","seq")): raise ValueError("integer")
    if not 0<=x["index"]<x["size"]<=2**63-1 or x["seq"] not in (2,4): raise ValueError("range")
    return x

def load_floor(path,expected):
    raw=bounded(path,4096)
    if digest(raw)!=expected: raise ValueError("retained floor digest")
    obj=json.loads(raw.decode("ascii"),object_pairs_hook=env.unique)
    if canonical(obj)!=raw: raise ValueError("noncanonical floor")
    return valid_floor(obj)

def verified(directory,public):
    """Verify exact snapshotted proof and envelope bytes before interpreting fields."""
    directory=Path(directory)
    raw=bounded(directory/"envelope.json",4096)
    proof=bounded(directory/"envelope.json.proof")
    key=bounded(public,2048)
    obj=env.parse(raw)
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)
        (p/"proof").write_bytes(proof)
        (p/"key.pub").write_bytes(key)
        subprocess.run(["sigsum-verify","-k",str(p/"key.pub"),"-P","sigsum-test1-2025",str(p/"proof")],
                       input=raw,check=True,timeout=30,capture_output=True)
    fields={}
    for line in proof.decode("ascii").splitlines():
        k,sep,v=line.partition("=")
        if sep and k in ("log","size","root_hash","leaf_index","leaf"):
            if k in fields: raise ValueError("duplicate proof field")
            fields[k]=v
    if set(fields)!={"log","size","root_hash","leaf_index","leaf"} or fields["log"]!=LOG:
        raise ValueError("proof schema")
    signer=fields["leaf"].split()[0]
    # The official verifier establishes leaf signature and proof membership.
    result=dict(profile=PROFILE,log=LOG,signer=signer,size=int(fields["size"]),root=fields["root_hash"],
                index=int(fields["leaf_index"]),checksum=env.checksum(raw),scope=obj["scope"],seq=obj["record_count"],
                floor_commitment=obj["floor_commitment_sha256"],ledger_sha256="0"*64)
    valid_floor(result)
    return result,raw

def gate(retained,candidate):
    # This function is a post-authentication comparison; not a proof verifier.
    try: valid_floor(retained); valid_floor(candidate)
    except (ValueError,TypeError,KeyError): return "HOLD_INVALID_FLOOR"
    if any(candidate[k]!=retained[k] for k in ("log","signer","scope")):
        return "HOLD_IDENTITY_SCOPE"
    if candidate["size"]<retained["size"]: return "HOLD_STALE_SIGNED_TREE"
    if candidate["size"]==retained["size"] and candidate["root"]!=retained["root"]:
        return "HOLD_SAME_SIZE_ROOT_CONFLICT"
    if candidate["seq"]<retained["seq"] or candidate["index"]<retained["index"]:
        return "HOLD_STALE_SCOPE"
    if candidate["seq"]==retained["seq"] and any(candidate[k]!=retained[k] for k in ("checksum","floor_commitment","index")):
        return "HOLD_SAME_SEQUENCE_CONFLICT"
    if candidate["size"]>retained["size"]:
        return "HOLD_NEEDS_CONSISTENCY"
    if candidate["seq"]!=retained["seq"] or candidate["index"]!=retained["index"]:
        return "HOLD_UNEXPECTED_SCOPE_ADVANCE"
    return "MATCH_RETAINED_NOT_FRESHNESS"

def provision(first,second,recovered,out):
    a,b,c,o=map(Path,(first,second,recovered,out))
    old,ea=verified(a,a/"synthetic-key.pub")
    new,eb=verified(b,a/"synthetic-key.pub")
    assert new["size"]>old["size"] and new["index"]>old["index"]
    assert eb==bounded(c/"envelope.json")
    fa,la=bounded(a/"floor.json"),bounded(a/"ledger.jsonl")
    fb,lb=bounded(c/"floor.json"),bounded(c/"ledger.jsonl")
    assert fb==bounded(b/"floor.json") and lb==bounded(b/"ledger.jsonl")
    assert f.verify(ea,eb,fa,la,f.bundle(fb,lb),new["checksum"],old["checksum"])=="RECOVERED_LINKED_SYNTHETIC_FLOOR_AND_LEDGER_ONLY"
    new["ledger_sha256"]=digest(lb)
    assert gate(old,new)=="HOLD_NEEDS_CONSISTENCY"
    # Use the previous verified scanner result, but require fresh live consistency
    # from first proof to second proof in this workflow before retaining it.
    o.mkdir(exist_ok=False)
    (o/"floor-pin.json").write_bytes(canonical(new))
    (o/"floor-pin.sha256").write_text(digest(canonical(new))+"\n")
    print(json.dumps({"proposed_floor":new,"retained_floor_digest":digest(canonical(new))},sort_keys=True))

def cold(first,second,pin_dir,out):
    a,b,p,o=map(Path,(first,second,pin_dir,out))
    expected=bounded(p/"floor-pin.sha256",128).decode().strip()
    retained=load_floor(p/"floor-pin.json",expected)
    old,ea=verified(a,a/"synthetic-key.pub")
    new,eb=verified(b,a/"synthetic-key.pub")
    assert gate(retained,old)=="HOLD_STALE_SIGNED_TREE"
    assert gate(retained,new)=="MATCH_RETAINED_NOT_FRESHNESS"
    assert gate(old,old)=="MATCH_RETAINED_NOT_FRESHNESS" # reset-both residual
    cases={"actual_old_valid_proof":gate(retained,old),"actual_retained_valid_proof":gate(retained,new),
           "reset_both_residual":gate(old,old)}
    for name,changes,want in (
        ("same_size_conflict",{"root":"0"*64},"HOLD_SAME_SIZE_ROOT_CONFLICT"),
        ("same_seq_conflict",{"checksum":"0"*64},"HOLD_SAME_SEQUENCE_CONFLICT"),
        ("wrong_scope",{"scope":"0"*48},"HOLD_IDENTITY_SCOPE"),
        ("wrong_signer",{"signer":"0"*64},"HOLD_IDENTITY_SCOPE"),
        ("older_scope_newer_tree",{"size":retained["size"]+1,"seq":2},"HOLD_STALE_SCOPE"),
        ("newer_tree_without_consistency",{"size":retained["size"]+1},"HOLD_NEEDS_CONSISTENCY"),
        ("invalid_size",{"size":True},"HOLD_INVALID_FLOOR")):
        got=gate(retained,dict(retained,**changes))
        assert got==want,(name,got)
        cases[name]=got
    with tempfile.TemporaryDirectory() as d:
        q=Path(d)/"floor.json"
        for name,raw in (("missing_floor",None),("corrupt_floor",b"{}"),("rollback_floor",canonical(old))):
            if raw is not None:q.write_bytes(raw)
            try: load_floor(q,expected)
            except (OSError,ValueError,TypeError): cases[name]="HOLD_RETAINED_FLOOR_UNAVAILABLE_OR_INVALID"
            else: raise AssertionError(name)
    # Explicitly reject tampered proof before the comparison gate.
    with tempfile.TemporaryDirectory() as d:
        q=Path(d)
        (q/"envelope.json").write_bytes(ea+b" ")
        (q/"envelope.json.proof").write_bytes(bounded(a/"envelope.json.proof"))
        try: verified(q,a/"synthetic-key.pub")
        except (ValueError,subprocess.CalledProcessError): cases["tampered_envelope"]="HOLD_UNAUTHENTICATED"
        else: raise AssertionError("tampered")
    assert digest(bounded(p/"floor-pin.json"))==expected
    boot=json.loads(bounded(a/"bootstrap.json",4096))
    boot.update(size=retained["size"],root=retained["root"])
    o.mkdir(exist_ok=False)
    (o/"bootstrap.json").write_bytes(canonical(boot))
    result=dict(cases=cases,retained_floor_unchanged=True,old_proof_crypto_verified=True,
                retained_proof_crypto_verified=True,global_latest="NOT_ESTABLISHED",
                administrative_independence="NOT_ESTABLISHED",history_truth="UNKNOWN",
                trust_activation="NO_GO",production="NO_GO",merge_authorized=False)
    (o/"cold-report.json").write_bytes(canonical(result))
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    if len(sys.argv)==6 and sys.argv[1]=="provision": provision(*sys.argv[2:])
    elif len(sys.argv)==6 and sys.argv[1]=="cold": cold(*sys.argv[2:])
    else: raise SystemExit("invalid invocation")
