"""Read-only delayed recovery and injected relay fault controls (no external deletion)."""
import json
import hashlib
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"r22_12_external_floor"))
import floor_recovery as floor
env=floor.env
GOOD="RECOVERED_LINKED_SYNTHETIC_FLOOR_AND_LEDGER_ONLY"

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def resign_retag(event,target):
    from coincurve import PrivateKey
    k=PrivateKey()
    e=dict(event,pubkey=k.public_key_xonly.format().hex(),tags=[["x",target]])
    e["id"]=env.event_id(e)
    e["sig"]=k.sign_schnorr(bytes.fromhex(e["id"])).hex()
    return e

class FaultSocket:
    """Deterministic injected responses at websocket boundary; no real relay mutation."""
    def __init__(self, events):
        self.events=events
        self.queue=[]
    def __enter__(self): return self
    def __exit__(self,*args): return False
    def send(self,raw):
        request=json.loads(raw)
        assert request[0]=="REQ"
        sub=request[1]
        self.queue=[json.dumps(["EVENT",sub,e]) for e in self.events]+[json.dumps(["EOSE",sub])]
    def recv(self,timeout): return self.queue.pop(0)

def main(first_dir,discovery,output):
    a,out=Path(first_dir),Path(output)
    out.mkdir(exist_ok=False)
    paths=[a/"envelope.json",a/"floor.json",a/"ledger.jsonl",a/"local-state.json",a/"bootstrap.json"]
    original={p.name:sha(p.read_bytes()) for p in paths}
    ea,fa,la,_,_=map(Path.read_bytes,paths)
    boot=json.loads((a/"bootstrap.json").read_text())
    report=json.loads(Path(discovery).read_text().splitlines()[-1])
    target=env.discover_target(report,boot)
    pin=boot["first_checksum"]
    relays=tuple(env.RELAYS)
    assert len(relays)==2
    results=[]
    # Positive controls: one real network endpoint per case, the other never contacted.
    later=bundle=None
    for relay in relays:
        with patch.object(env,"RELAYS",(relay,)):
            eb,es=env.fetch(target)
            estate=env.validate(ea,eb,target,pin)
            if estate!="RECOVERED_LINKED_SYNTHETIC_ENVELOPE_ONLY":
                results.append(dict(case="LIVE_SINGLE_RELAY",relay=relay,envelope=estate,disposition="HOLD_NEW_ENVELOPE_UNAVAILABLE"))
                continue
            digest=env.parse(eb)["floor_commitment_sha256"]
            raw,fs=floor.fetch(digest)
            state=floor.verify(ea,eb,fa,la,raw,target,pin)
            results.append(dict(case="LIVE_SINGLE_RELAY",relay=relay,envelope_sources=es,floor_sources=fs,disposition=state))
            if state==GOOD:
                assert es==[relay] and fs==[relay]
                if later is not None: assert later==eb and bundle==raw
                later,bundle=eb,raw
    # A live positive is required; the no-fault claim requires both positive controls.
    if later is None:
        print(json.dumps({"cases":results,"disposition":"HOLD_NO_LIVE_RECOVERY","trust_activation":"NO_GO"}))
        raise SystemExit(2)
    digest=env.parse(later)["floor_commitment_sha256"]
    old_digest=env.parse(ea)["floor_commitment_sha256"]
    assert floor.floor_digest(fa)==old_digest
    assert floor.inspect_ledger(la,fa,floor.inspect_floor(fa))
    # Old valid signed content, maliciously re-tagged and re-signed under fresh transport key.
    old_env=resign_retag(env.event_for(ea),target)
    old_bundle=resign_retag(floor.event_for(floor.bundle(fa,la),old_digest),digest)
    # Positive under exact old lookup: same source objects are not intrinsically invalid.
    assert env.extract(old_env,target) is None
    assert floor.extract(old_bundle,digest) is None
    assert env.extract(env.event_for(ea),pin)==ea
    assert floor.extract(floor.event_for(floor.bundle(fa,la),old_digest),old_digest)==floor.bundle(fa,la)
    for name,events,fetcher,lookup,expected in (
        ("REPLAY_OLD_ENVELOPE_RETAGGED",[old_env],env.fetch,target,"HOLD_CONTENT_UNAVAILABLE"),
        ("WITHHOLD_NEW_ENVELOPE",[],env.fetch,target,"HOLD_CONTENT_UNAVAILABLE"),
        ("REPLAY_OLD_FLOOR_RETAGGED",[old_bundle],floor.fetch,digest,"HOLD_FLOOR_PREIMAGE_UNAVAILABLE"),
        ("WITHHOLD_NEW_FLOOR",[],floor.fetch,digest,"HOLD_FLOOR_PREIMAGE_UNAVAILABLE")):
        with patch.object(env,"connect",side_effect=lambda url:FaultSocket(events)) as connect:
            raw,sources=fetcher(lookup)
            assert connect.call_count==len(relays)
        assert raw is None and sources==[]
        state=(env.validate(ea,raw,target,pin) if fetcher is env.fetch else
               floor.verify(ea,later,fa,la,raw,target,pin))
        assert state==expected
        results.append(dict(case=name,disposition=state,old_as_latest=False,transport="INJECTED_RELAY_RESPONSES"))
    # Check direct substitution separately, not just transport filtering.
    assert env.validate(ea,ea,target,pin)=="HOLD_CONTENT_HASH_MISMATCH"
    assert floor.verify(ea,later,fa,la,floor.bundle(fa,la),target,pin)=="HOLD_FLOOR_COMMITMENT"
    results.append(dict(case="DIRECT_OLD_SUBSTITUTION",disposition="HOLD_HASH_AND_FLOOR_COMMITMENT",old_as_latest=False))
    assert original=={p.name:sha(p.read_bytes()) for p in paths}
    f,l=floor.unpack(bundle)
    (out/"envelope.json").write_bytes(later)
    (out/"floor.json").write_bytes(f)
    (out/"ledger.jsonl").write_bytes(l)
    both=all(c["disposition"]==GOOD for c in results[:2])
    result=dict(disposition="DELAYED_RECOVERY_AND_FAULT_CONTROLS_PASS" if both else "HOLD_SINGLE_SOURCE_UNAVAILABLE",
                cases=results,old_state_unchanged=True,old_valid_as_prefix=True,old_as_latest=False,
                discovered_checksum=target,floor_commitment=digest,ledger_sha256=sha(l),
                verified_record_count=floor.inspect_floor(f)["seq"],
                global_latest="NOT_ESTABLISHED",source_durability="NOT_ESTABLISHED",
                administrative_independence="NOT_ESTABLISHED",history_truth="UNKNOWN",
                trust_activation="NO_GO",production="NO_GO",merge_authorized=False)
    (out/"report.json").write_text(json.dumps(result,sort_keys=True)+"\n")
    print(json.dumps(result,sort_keys=True),flush=True)
    if not both: raise SystemExit(2)

if __name__=="__main__":
    if len(sys.argv)!=4: raise SystemExit("invalid invocation")
    main(*sys.argv[1:])
