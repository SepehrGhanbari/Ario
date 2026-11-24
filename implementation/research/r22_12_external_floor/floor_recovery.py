"""R22.12: exact synthetic floor and ledger recovery. No admission or writes to local history."""
import base64
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "r22_11_external_content"))
import recovery as env
from test_r22_7_retained_witness_floor import read_floor, assess, floor_record, r10, ledger
from test_r22_8_witness_receipt_recovery import commitment

MAX_FLOOR = 32768
MAX_LEDGER = 16384
MAX_BUNDLE = 48000
PREFIX = "ARIO R22.12 PUBLIC SYNTHETIC floor and ledger: "
SUB = "ario-r22-12-floor"

def bundle(floor, history):
    return env.canonical({"profile":"ARIO-R22.12-PUBLIC-SYNTHETIC-FLOOR-PREIMAGE-v1",
                          "floor_b64":base64.b64encode(floor).decode("ascii"),
                          "ledger_b64":base64.b64encode(history).decode("ascii")})

def unpack(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BUNDLE:
        raise ValueError("bundle size")
    obj = json.loads(raw.decode("ascii"), object_pairs_hook=env.unique)
    if (type(obj) is not dict or set(obj) != {"profile","floor_b64","ledger_b64"}
        or obj["profile"] != "ARIO-R22.12-PUBLIC-SYNTHETIC-FLOOR-PREIMAGE-v1"
        or env.canonical(obj) != raw):
        raise ValueError("bundle schema")
    floor = base64.b64decode(obj["floor_b64"], validate=True)
    history = base64.b64decode(obj["ledger_b64"], validate=True)
    if not 0 < len(floor) <= MAX_FLOOR or not 0 < len(history) <= MAX_LEDGER:
        raise ValueError("object size")
    if bundle(floor, history) != raw:
        raise ValueError("noncanonical bundle encoding")
    return floor, history

def inspect_floor(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_FLOOR:
        raise ValueError("floor size")
    obj = json.loads(raw.decode("ascii"), object_pairs_hook=env.unique)
    if r10.canonical(obj) + b"\n" != raw:
        raise ValueError("canonical floor")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)/"floor.json"
        path.write_bytes(raw)
        record, _ = read_floor(path)
    return record

def floor_digest(raw):
    return commitment(inspect_floor(raw))

def inspect_ledger(raw, floor_raw, record):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_LEDGER:
        raise ValueError("ledger size")
    if hashlib.sha256(raw).hexdigest() != record["prefix_sha256"]:
        raise ValueError("ledger digest")
    if len(raw.splitlines()) != record["seq"] or not raw.endswith(b"\n"):
        raise ValueError("ledger count")
    with tempfile.TemporaryDirectory() as d:
        path = Path(d)/"floor.json"
        path.write_bytes(floor_raw)
        if assess(raw, path) != "MATCH_RETAINED_LAB_CHECKPOINT_ONLY":
            raise ValueError("ledger correspondence")
    return True

def verify(first_envelope, later_envelope, first_floor, first_ledger, candidate, discovered, first_pin):
    if env.validate(first_envelope, later_envelope, discovered, first_pin) != "RECOVERED_LINKED_SYNTHETIC_ENVELOPE_ONLY":
        return "HOLD_ENVELOPE_LINK"
    if candidate is None:
        return "HOLD_FLOOR_PREIMAGE_UNAVAILABLE"
    try:
        old, new = env.parse(first_envelope), env.parse(later_envelope)
        previous = inspect_floor(first_floor)
        if commitment(previous) != old["floor_commitment_sha256"] or previous["seq"] != old["record_count"]:
            return "HOLD_FIRST_FLOOR_PIN"
        inspect_ledger(first_ledger, first_floor, previous)
        floor_raw, history = unpack(candidate)
        current = inspect_floor(floor_raw)
        if commitment(current) != new["floor_commitment_sha256"]:
            return "HOLD_FLOOR_COMMITMENT"
        if current["scope"] != previous["scope"] or current["seq"] != new["record_count"] or current["seq"] <= previous["seq"]:
            return "HOLD_FLOOR_SCOPE_OR_SEQUENCE"
        if any(c["parent"] != p["checkpoint"] for c,p in zip(current["anchors"],previous["anchors"],strict=True)):
            return "HOLD_FLOOR_PREDECESSOR"
        if not history.startswith(first_ledger):
            return "HOLD_LEDGER_PREFIX"
        inspect_ledger(history, floor_raw, current)
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, AssertionError, OSError, OverflowError):
        return "HOLD_INVALID_FLOOR_OR_LEDGER"
    return "RECOVERED_LINKED_SYNTHETIC_FLOOR_AND_LEDGER_ONLY"

def event_for(raw, target):
    from coincurve import PrivateKey
    floor, history = unpack(raw)
    record = inspect_floor(floor)
    inspect_ledger(history, floor, record)
    if commitment(record) != target:
        raise ValueError("target")
    key = PrivateKey()
    event = {"pubkey":key.public_key_xonly.format().hex(),"created_at":int(time.time()),"kind":env.KIND,
             "tags":[["x",target]],"content":PREFIX+base64.b64encode(raw).decode("ascii")}
    event["id"] = env.event_id(event)
    event["sig"] = key.sign_schnorr(bytes.fromhex(event["id"])).hex()
    return event

def extract(event, target):
    from coincurve import PublicKeyXOnly
    try:
        if event["kind"] != env.KIND or ["x",target] not in event["tags"] or env.event_id(event) != event["id"]:
            return None
        if not PublicKeyXOnly(bytes.fromhex(event["pubkey"])).verify(bytes.fromhex(event["sig"]),bytes.fromhex(event["id"])):
            return None
        content = event["content"]
        if not isinstance(content,str) or not content.startswith(PREFIX) or len(content)>64080:
            return None
        raw = base64.b64decode(content[len(PREFIX):],validate=True)
        floor, history = unpack(raw)
        record = inspect_floor(floor)
        if commitment(record)!=target:
            return None
        inspect_ledger(history,floor,record)
        return raw
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError, AssertionError, OSError, OverflowError, AttributeError):
        return None

def publish(raw, target):
    event = event_for(raw,target)
    accepted = []
    for url in env.RELAYS:
        try:
            with env.connect(url) as ws:
                ws.send(json.dumps(["EVENT",event]))
                deadline = time.monotonic()+12
                for _ in range(16):
                    msg = json.loads(ws.recv(timeout=max(.01,deadline-time.monotonic())))
                    if isinstance(msg,list) and len(msg)>=4 and msg[:2]==["OK",event["id"]]:
                        if msg[2] is True: accepted.append(url)
                        break
                    if time.monotonic()>=deadline: break
        except Exception as exc:
            print(json.dumps({"relay":url,"floor_publish_error":type(exc).__name__}),flush=True)
    print(json.dumps({"floor_relay_accepted":accepted,"floor_commitment":target,"bundle_bytes":len(raw)}),flush=True)
    if not accepted: raise SystemExit("HOLD_FLOOR_STORAGE_UNAVAILABLE")

def fetch(target):
    if not isinstance(target,str) or not env.HEX.fullmatch(target): return None,[]
    found, sources = None,[]
    for url in env.RELAYS:
        try:
            with env.connect(url) as ws:
                ws.send(json.dumps(["REQ",SUB,{"kinds":[env.KIND],"#x":[target],"limit":16}]))
                deadline=time.monotonic()+15
                for _ in range(32):
                    msg=json.loads(ws.recv(timeout=max(.01,deadline-time.monotonic())))
                    if isinstance(msg,list) and len(msg)>=3 and msg[:2]==["EVENT",SUB]:
                        raw=extract(msg[2],target)
                        if raw is not None:
                            if found is not None and found!=raw:
                                return None,[]
                            found=raw
                            sources.append(url)
                            break
                    if isinstance(msg,list) and len(msg)>=2 and msg[0] in ("EOSE","CLOSED") and msg[1]==SUB: break
                    if time.monotonic()>=deadline: break
        except Exception as exc:
            print(json.dumps({"relay":url,"floor_read_error":type(exc).__name__}),flush=True)
    return found,sources

def recover(first_dir, recovered_dir, discovery):
    a,b=Path(first_dir),Path(recovered_dir)
    first=(a/"envelope.json").read_bytes()
    later=(b/"envelope.json").read_bytes()
    boot=json.loads((a/"bootstrap.json").read_text())
    report=json.loads(Path(discovery).read_text().splitlines()[-1])
    target=env.discover_target(report,boot)
    if env.validate(first,later,target,boot["first_checksum"])!="RECOVERED_LINKED_SYNTHETIC_ENVELOPE_ONLY":
        raise SystemExit("HOLD_ENVELOPE_LINK")
    pin=env.parse(later)["floor_commitment_sha256"]
    raw,sources=fetch(pin)
    status=verify(first,later,(a/"floor.json").read_bytes(),(a/"ledger.jsonl").read_bytes(),raw,target,boot["first_checksum"])
    ok=status=="RECOVERED_LINKED_SYNTHETIC_FLOOR_AND_LEDGER_ONLY"
    result={"disposition":status,"floor_commitment":pin,"floor_preimage_recovered":ok,
            "ledger_preimage_recovered":ok,"external_read_sources":sources,"global_latest":"NOT_ESTABLISHED",
            "source_durability":"NOT_ESTABLISHED","independent_latest_floor":"NOT_ESTABLISHED",
            "history_truth":"UNKNOWN","trust_activation":"NO_GO","production":"NO_GO","merge_authorized":False}
    if ok:
        floor,history=unpack(raw)
        (b/"floor.json").write_bytes(floor)
        (b/"ledger.jsonl").write_bytes(history)
        result["verified_record_count"]=inspect_floor(floor)["seq"]
        result["ledger_sha256"]=hashlib.sha256(history).hexdigest()
    print(json.dumps(result,sort_keys=True),flush=True)
    if not ok: raise SystemExit(2)

if __name__=="__main__":
    if len(sys.argv)==4 and sys.argv[1]=="publish":
        directory=Path(sys.argv[2])
        publish(bundle((directory/"floor.json").read_bytes(),(directory/"ledger.jsonl").read_bytes()),sys.argv[3])
    elif len(sys.argv)==5 and sys.argv[1]=="recover":
        recover(*sys.argv[2:])
    else: raise SystemExit("invalid invocation")
