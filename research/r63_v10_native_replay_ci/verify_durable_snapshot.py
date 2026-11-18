"""Read-only precondition: signed synthetic payload must match CURRENT V1/V2 bytes.

This checks payload data, not its ECDSA signature: a SEPARATE public-only
signature verifier is mandatory. No atomic filesystem snapshot, witness
independence, cross-process lock, or antirollback is established.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"r63_v10_source_gate"))
import spend_chain_v2 as v2

V2_PIN="c61ea488b082a5f01e74bc84b85a60b2a522b5a7274ed41b6d7addee10b060cd"
DOMAIN=b"ARIO-R63-CI-PUBLIC-ONLY-SYNTHETIC-RECEIPT-2026\0"
MAX=2*1024*1024

class Hold(ValueError):pass

def sha(b):return hashlib.sha256(b).hexdigest()

def bounded(path):
    try:
        with path.open("rb") as f:raw=f.read(MAX+1)
    except OSError as exc:
        raise Hold("missing or unreadable input") from exc
    if len(raw)>MAX:raise Hold("oversize input")
    return raw

def verify(root:Path):
    root=Path(root)
    if sha(Path(v2.__file__).read_bytes())!=V2_PIN:
        raise Hold("frozen source mismatch")
    raw1=bounded(root/"v1.jsonl")
    raw2=bounded(root/"v2.jsonl")
    payload=bounded(root/"payload.bin")
    metadata=bounded(root/"metadata.json")
    try:
        obj=json.loads(metadata.decode("utf-8"))
        if metadata!=(json.dumps(obj,sort_keys=True,indent=2)+"\n").encode("utf-8"):
            raise Hold("metadata not exact canonical persisted bytes")
        if type(obj) is not dict or set(obj)!={
            "version","nonce","identifier","v1_sha256","v2_sha256",
            "v2_head","v2_event_count","disposition"}:
            raise Hold("metadata fields mismatch")
        if obj["version"]!="R63_CI_P256_PUBLIC_RECEIPT_1" or obj["disposition"]!="SYNTHETIC_COMMITTED_FIXTURE":
            raise Hold("wrong version or purpose")
        state=v2.review(raw2)
        if type(obj["v2_event_count"]) is not int or state.seq!=obj["v2_event_count"]:
            raise Hold("event count mismatch")
        if (obj["v2_head"]!=state.head or
            obj["v1_sha256"]!=sha(raw1) or obj["v2_sha256"]!=sha(raw2)):
            raise Hold("durable snapshot commitment mismatch")
        if not any(pair==(obj["nonce"],obj["identifier"]) for pair in state.pairs):
            raise Hold("target reservation not in V2")
        expected_v1=b"".join(v2.canonical(list(pair))+b"\n" for pair in state.pairs)
        if raw1!=expected_v1:
            raise Hold("append order V1/V2 disagreement")
        if payload!=DOMAIN+v2.canonical(obj):
            raise Hold("payload not bound to metadata")
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,RecursionError) as exc:
        raise Hold("untrusted durable snapshot or metadata") from exc
    if bounded(root/"v1.jsonl")!=raw1 or bounded(root/"v2.jsonl")!=raw2:
        raise Hold("journal changed during review")
    return {"v2_event_count":state.seq,"v2_head":state.head,
            "v1_sha256":sha(raw1),"v2_sha256":sha(raw2),
            "payload_sha256":sha(payload)}

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit("usage: verify_durable_snapshot.py RUNNER_ROOT")
    try:
        verdict=verify(Path(sys.argv[1]))
        print("CURRENT_JOURNAL_AND_PAYLOAD_BINDING=PASS")
        print("V2_EVENTS="+str(verdict["v2_event_count"]))
        print("PAYLOAD_SHA256="+verdict["payload_sha256"])
        print("SIGNED_RECEIPT_CRYPTO_VERIFICATION=SEPARATE_STEP_REQUIRED")
        print("INDEPENDENT_CUSTODY=NOT_ESTABLISHED")
    except Hold as exc:
        print("HOLD_UNCERTAIN: "+str(exc),file=sys.stderr)
        raise SystemExit(1)
