"""R63 actual lab snapshot commitment bridge; review only, never authority."""
import base64
import hashlib
import json
import re
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "r22_11_external_content"))
import recovery as transport

PROFILE = "ARIO-R63-LAB-FLOOR-v2"
PINS = {
    10: ("ed299d6fec64e7dc411c554b534caf67c4aa636047c6462fde0c6ced12034689", "723b27390263695d7bf48f1955e4b08250a0ed34b42faf38580c2e0da9d4d509"),
    11: ("17a26bac82da5e4b84774ad3b4d8ae56ee4f9375af06be7ea1bdeba6f6bd15ab", "1d9ad2b3a9d40e9bf73f55b721afa6f46e3568c2578a115e44e4d51a86ff45aa"),
}
HEX = re.compile(r"[0-9a-f]{64}\Z")
LOG = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
checksum = transport.checksum
canonical = transport.canonical

def require(ok, why):
    if not ok:
        raise ValueError(why)

def envelope(scope, count, previous, nonce):
    salt, commitment = PINS[count]
    return canonical(dict(profile=PROFILE, scope=scope, record_count=count,
        previous_checksum=previous, publication_nonce=nonce, floor_salt=salt,
        floor_commitment_sha256=commitment, authoritative=False,
        provenance="OPERATOR_REPORTED_LAB", history_truth="UNKNOWN",
        trust_activation="NO_GO", production="NO_GO", genesis="NO_GO"))

def parse(raw):
    require(type(raw) is bytes and 0 < len(raw) <= 4096, "size")
    obj = json.loads(raw.decode("ascii"), object_pairs_hook=transport.unique)
    require(type(obj) is dict, "schema")
    count = obj.get("record_count")
    require(type(count) is int and count in PINS, "count")
    scope, nonce, prev = (obj.get(k) for k in ("scope", "publication_nonce", "previous_checksum"))
    require(type(scope) is str and re.fullmatch("[0-9a-f]{48}", scope), "scope")
    require(type(nonce) is str and HEX.fullmatch(nonce), "nonce")
    require(type(prev) is str and (prev == "GENESIS" if count == 10 else bool(HEX.fullmatch(prev))), "prev")
    require(raw == envelope(scope, count, prev, nonce), "canonical or binding mismatch")
    return obj

def pair(first, second, target):
    require(type(target) is str and HEX.fullmatch(target), "target")
    require(second is not None and checksum(second) == target, "missing or hash mismatch")
    a,b = parse(first), parse(second)
    require(a["record_count"] == 10 and b["record_count"] == 11, "sequence")
    require(a["scope"] == b["scope"] and a["publication_nonce"] != b["publication_nonce"], "scope/nonce")
    require(b["previous_checksum"] == checksum(first), "predecessor")
    return b

def make(a,b):
    scope = secrets.token_hex(24)
    x = envelope(scope,10,"GENESIS",secrets.token_hex(32))
    y = envelope(scope,11,checksum(x),secrets.token_hex(32))
    pair(x,y,checksum(y))
    (a/"envelope.json").write_bytes(x)
    (b/"envelope.json").write_bytes(y)

def fields(path):
    keys = {"size","root_hash","leaf_index","log","leaf"}
    out = {}
    for line in path.read_text().splitlines():
        if "=" not in line: continue
        k,v = line.split("=",1)
        if k in keys:
            require(k not in out,"duplicate proof field")
            out[k]=v
    require(set(out)==keys and out["log"]==LOG,"proof fields/log")
    require(bool(HEX.fullmatch(out["root_hash"])),"root")
    return out

def boot(a):
    f = fields(a/"envelope.json.proof")
    raw = (a/"envelope.json").read_bytes()
    require(parse(raw)["record_count"]==10,"bootstrap count")
    blob = base64.b64decode((a/"synthetic-key.pub").read_text().split()[1],validate=True)
    prefix = b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
    require(blob.startswith(prefix) and len(blob)==len(prefix)+32,"public key")
    public=blob[len(prefix):]
    require(hashlib.sha256(public).hexdigest()==f["leaf"].split()[0],"key hash")
    start,size=int(f["leaf_index"]),int(f["size"])
    require(0 < start < size and size-start <=64,"bootstrap position")
    return dict(start=start,size=size,root=f["root_hash"],public=public.hex(),first_checksum=checksum(raw))

def load_report(path):
    return json.loads(path.read_text().splitlines()[-1],object_pairs_hook=transport.unique)

def target_from(a, report):
    b=boot(a)
    require(json.loads((a/"bootstrap.json").read_text(),object_pairs_hook=transport.unique)==b,"bootstrap mismatch")
    return transport.discover_target(report,b)

def selftest():
    scope="a"*48
    a=envelope(scope,10,"GENESIS","1"*64)
    b=envelope(scope,11,checksum(a),"2"*64)
    pair(a,b,checksum(b))
    invalid=[(None,checksum(b)),(b+b"x",checksum(b)),(a,checksum(a)),
             (envelope("b"*48,11,checksum(a),"2"*64),None),
             (envelope(scope,11,"0"*64,"2"*64),None),
             (envelope(scope,11,checksum(a),"1"*64),None),
             (b.replace(b'"authoritative":false',b'"authoritative":true'),None),
             (b.replace(PINS[11][1].encode(),b"0"*64),None),
             (b.replace(b'"record_count":11',b'"record_count":true'),None)]
    for candidate,target in invalid:
        try: pair(a,candidate,target or checksum(candidate))
        except (ValueError,TypeError): continue
        raise AssertionError("unsafe acceptance")
    print("10/10 R63 binding controls PASS")

def main():
    command=sys.argv[1]
    paths=[Path(x) for x in sys.argv[2:]]
    if command=="test": selftest()
    elif command=="make": make(*paths)
    elif command=="bootstrap":
        a,=paths
        (a/"bootstrap.json").write_bytes(canonical(boot(a)))
    elif command=="publish":
        p,=paths
        transport.parse=parse
        transport.publish(p.read_bytes())
    elif command=="recover":
        a,report,out=paths
        target=target_from(a,load_report(report))
        raw,sources=transport.fetch(target)
        pair((a/"envelope.json").read_bytes(),raw,target)
        require(len(set(sources))==2,"both relay readbacks required for this experiment")
        with out.open("xb") as stream: stream.write(raw)
        print(json.dumps(dict(disposition="MATCH_R63_LAB_COMMITMENT_ONLY",checksum=target,sources=sources,independence="NOT_ESTABLISHED",freshness="NOT_ESTABLISHED",genesis="NO_GO"),sort_keys=True))
    elif command=="reveal":
        a,b,report,out=paths
        r=load_report(report)
        target=target_from(a,r)
        x,y=(a/"envelope.json").read_bytes(),(b/"envelope.json").read_bytes()
        require(out.read_bytes()==y,"reveal mismatch")
        pair(x,y,target)
        p,q=fields(a/"envelope.json.proof"),fields(b/"envelope.json.proof")
        require(p["leaf"].split()[0]==q["leaf"].split()[0],"different signer")
        require(int(p["leaf_index"])<int(q["leaf_index"])==r["matching_signed_leaves"][1]["index"],"index mismatch")
        print("R63_EXTERNAL_BYTES_MATCH_WITHHELD_COMMITMENT; REVIEW_ONLY; NO_GO")
    else: raise SystemExit("invalid command")

if __name__=="__main__": main()
