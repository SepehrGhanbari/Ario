"""Research-only R63 spend V2 sidecar. No private keys, CNG or signer IO."""
from __future__ import annotations
import hashlib, json, re
from dataclasses import dataclass

VERSION="ARIO_R63_SPEND_V2_RESEARCH"
DOMAIN=b"ARIO-R63/spend/v2\0"
ZERO="0"*64

class Hold(ValueError):pass
def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,
                      allow_nan=False).encode("ascii")
def sha(b):return hashlib.sha256(b).hexdigest()
def ishash(v):return type(v) is str and re.fullmatch(r"[0-9a-f]{64}",v) is not None
def snapshot(pairs):
    """R60 uses SELECT nonce,id ORDER BY nonce; preserve append order separately."""
    return sha(canonical(sorted([list(p) for p in pairs],key=lambda p:p[0])))
def eventhash(body):return sha(DOMAIN+canonical(body))
@dataclass(frozen=True)
class State:
    seq:int
    head:str
    pairs:tuple
    verdict:str

def review(journal:bytes,external_anchor=None):
    """Fail closed for malformed lines, chain breaks, forks, gaps, old anchors."""
    if type(journal) is not bytes:raise Hold("journal is not bytes")
    if journal and not journal.endswith(b"\n"):raise Hold("partial last line")
    lines=journal.split(b"\n")[:-1] if journal else []
    if len(lines)>100000:raise Hold("too many records")
    seq,prev,pairs=0,ZERO,[]
    anchor_seen=False
    if external_anchor is not None:
        if not isinstance(external_anchor,tuple) or len(external_anchor)!=2:
            raise Hold("bad external anchor")
        aseq,ahead=external_anchor
        if type(aseq) is not int or aseq<0 or not ishash(ahead):
            raise Hold("bad external anchor fields")
        if aseq==0:
            if ahead!=ZERO:raise Hold("genesis mismatch")
            anchor_seen=True
    for line in lines:
        if not line or len(line)>8192:raise Hold("empty or oversized record")
        try:
            obj=json.loads(line.decode("ascii"))
            if type(obj) is not dict or canonical(obj)!=line:raise Hold("not canonical")
        except (ValueError,UnicodeError,TypeError,RecursionError) as exc:
            raise Hold("noncanonical or undecodable record") from exc
        if set(obj)!={"version","seq","prev","nonce","id","before","after","hash"}:
            raise Hold("unexpected field set")
        n,k=obj["nonce"],obj["id"]
        if obj["version"]!=VERSION or not ishash(n) or not ishash(k):
            raise Hold("invalid version/nonce/id")
        if type(obj["seq"]) is not int or obj["seq"]!=seq+1 or obj["prev"]!=prev:
            raise Hold("sequence or predecessor mismatch")
        if any(n==p[0] or k==p[1] for p in pairs):raise Hold("duplicate reservation")
        updated=pairs+[[n,k]]
        body={key:v for key,v in obj.items() if key!="hash"}
        if obj["before"]!=snapshot(pairs) or obj["after"]!=snapshot(updated):
            raise Hold("R60 sorted content commitment mismatch")
        if obj["hash"]!=eventhash(body):raise Hold("event hash mismatch")
        seq,prev,pairs=obj["seq"],obj["hash"],updated
        if external_anchor is not None and seq==aseq:
            if prev!=ahead:raise Hold("fork against retained anchor")
            anchor_seen=True
    if external_anchor is not None and not anchor_seen:
        raise Hold("missing anchored prefix (rollback or deletion)")
    verdict=("CONSISTENT_WITH_RETAINED_ANCHOR" if external_anchor is not None
             else "LOCAL_SELF_ADMINISTERED_NO_ROLLBACK_PROOF")
    return State(seq,prev,tuple(tuple(p) for p in pairs),verdict)

def append(journal:bytes,nonce:str,identifier:str):
    if not ishash(nonce) or not ishash(identifier):raise Hold("bad nonce/id")
    state=review(journal)
    for n,k in state.pairs:
        if n==nonce and k==identifier:
            return journal,"ALREADY_RESERVED_NO_APPEND"
        if n==nonce or k==identifier:raise Hold("reused nonce or identity")
    body={"version":VERSION,"seq":state.seq+1,"prev":state.head,
          "nonce":nonce,"id":identifier,"before":snapshot(state.pairs),
          "after":snapshot(list(state.pairs)+[[nonce,identifier]])}
    return journal+canonical({**body,"hash":eventhash(body)})+b"\n","NEW_NEEDS_DURABLE_APPEND"

def anchor(journal):
    s=review(journal)
    return s.seq,s.head

def compare_legacy_spends(append_order,broker_hash):
    pairs=[]
    for item in append_order:
        if type(item) not in (list,tuple) or len(item)!=2:raise Hold("bad legacy record")
        n,k=item
        if not ishash(n) or not ishash(k) or any(n==p[0] or k==p[1] for p in pairs):
            raise Hold("duplicate or malformed legacy record")
        pairs.append([n,k])
    if snapshot(pairs)!=broker_hash:raise Hold("legacy content mismatch")
    return "CONTENT_EQUAL__LEGACY_APPEND_ORDER_RETAINED__ANCHOR_NOT_ESTABLISHED"
