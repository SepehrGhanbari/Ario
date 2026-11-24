"""R22.11: public synthetic envelope recovery, never evidence admission."""
import base64
import hashlib
import json
import re
import sys
import time
from pathlib import Path

RELAYS = ("wss://nos.lol", "wss://relay.primal.net")
KIND = 1
PROFILE = "ARIO-R22.10-PUBLIC-SYNTHETIC-FLOOR-v1"
LIMIT = 4096
HEX = re.compile(r"[0-9a-f]{64}\Z")
SCOPE = re.compile(r"[0-9a-f]{48}\Z")
FIELDS = {"profile", "scope", "record_count", "previous_checksum",
          "floor_commitment_sha256", "synthetic_nonce", "synthetic",
          "authoritative", "historical_event_truth", "trust_activation", "production"}

def checksum(raw):
    return hashlib.sha256(hashlib.sha256(raw).digest()).hexdigest()

def canonical(obj):
    return (json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")

def unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError("duplicate field")
        out[k] = v
    return out

def parse(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= LIMIT:
        raise ValueError("size")
    obj = json.loads(raw.decode("ascii"), object_pairs_hook=unique)
    if not isinstance(obj, dict) or set(obj) != FIELDS or canonical(obj) != raw:
        raise ValueError("schema/canonical")
    if (obj["profile"] != PROFILE or obj["synthetic"] is not True
        or obj["authoritative"] is not False or obj["historical_event_truth"] != "UNKNOWN"
        or obj["trust_activation"] != "NO_GO" or obj["production"] != "NO_GO"):
        raise ValueError("scope/authority profile")
    if type(obj["record_count"]) is not int or not 1 <= obj["record_count"] <= 2**53-1:
        raise ValueError("count")
    for k, regex in (("scope", SCOPE), ("floor_commitment_sha256", HEX), ("synthetic_nonce", HEX)):
        if not isinstance(obj[k], str) or not regex.fullmatch(obj[k]):
            raise ValueError(k)
    prev = obj["previous_checksum"]
    if prev != "GENESIS" and (not isinstance(prev, str) or not HEX.fullmatch(prev)):
        raise ValueError("previous")
    return obj

def validate(first_raw, candidate, target, first_hash):
    if candidate is None:
        return "HOLD_CONTENT_UNAVAILABLE"
    if not isinstance(target, str) or not HEX.fullmatch(target):
        return "HOLD_INVALID_DISCOVERY"
    if checksum(first_raw) != first_hash:
        return "HOLD_BOOTSTRAP_MISMATCH"
    if checksum(candidate) != target:
        return "HOLD_CONTENT_HASH_MISMATCH"
    try:
        first, later = parse(first_raw), parse(candidate)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return "HOLD_CONTENT_SCHEMA"
    if later["scope"] != first["scope"]:
        return "HOLD_WRONG_SCOPE"
    if later["previous_checksum"] != first_hash:
        return "HOLD_PREDECESSOR"
    if later["record_count"] <= first["record_count"]:
        return "HOLD_NON_ADVANCING_COUNT"
    if later["floor_commitment_sha256"] == first["floor_commitment_sha256"]:
        return "HOLD_UNCHANGED_FLOOR_COMMITMENT"
    return "RECOVERED_LINKED_SYNTHETIC_ENVELOPE_ONLY"

def event_id(event):
    data = [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]]
    return hashlib.sha256(json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()

def event_for(raw):
    from coincurve import PrivateKey
    parse(raw)
    key = PrivateKey()
    event = {"pubkey": key.public_key_xonly.format().hex(), "created_at": int(time.time()),
             "kind": KIND, "tags": [["x", checksum(raw)]],
             "content": "ARIO public synthetic research envelope (no real user data): " + base64.b64encode(raw).decode("ascii")}
    event["id"] = event_id(event)
    event["sig"] = key.sign_schnorr(bytes.fromhex(event["id"])).hex()
    return event

def extract(event, target):
    from coincurve import PublicKeyXOnly
    try:
        if event["kind"] != KIND or ["x", target] not in event["tags"]:
            return None
        if event_id(event) != event["id"]:
            return None
        if not PublicKeyXOnly(bytes.fromhex(event["pubkey"])).verify(bytes.fromhex(event["sig"]), bytes.fromhex(event["id"])):
            return None
        prefix = "ARIO public synthetic research envelope (no real user data): "
        value = event["content"]
        if not isinstance(value, str) or not value.startswith(prefix) or len(value) > 6000:
            return None
        raw = base64.b64decode(value[len(prefix):], validate=True)
        if len(raw) > LIMIT or checksum(raw) != target:
            return None
        return raw
    except (ValueError, TypeError, KeyError, AttributeError, RecursionError):
        return None

def connect(url):
    from websockets.sync.client import connect as ws_connect
    return ws_connect(url, open_timeout=8, close_timeout=2, max_size=65536, proxy=None)

def publish(raw):
    event = event_for(raw)
    accepted = []
    for url in RELAYS:
        try:
            with connect(url) as ws:
                ws.send(json.dumps(["EVENT", event]))
                deadline = time.monotonic() + 12
                for _ in range(16):
                    msg = json.loads(ws.recv(timeout=max(.01, deadline-time.monotonic())))
                    if isinstance(msg, list) and len(msg) >= 4 and msg[:2] == ["OK", event["id"]]:
                        if msg[2] is True:
                            accepted.append(url)
                        break
                    if time.monotonic() >= deadline:
                        break
        except Exception as exc:
            print(json.dumps({"relay":url, "publish_error":type(exc).__name__}), flush=True)
    print(json.dumps({"relay_accepted":accepted, "checksum":checksum(raw)}), flush=True)
    if not accepted:
        raise SystemExit("HOLD_EXTERNAL_STORAGE_UNAVAILABLE")

def fetch(target):
    if not isinstance(target, str) or not HEX.fullmatch(target):
        return None, []
    found, sources = None, []
    for url in RELAYS:
        try:
            with connect(url) as ws:
                ws.send(json.dumps(["REQ","ario-r22-11",{"kinds":[KIND],"#x":[target],"limit":16}]))
                deadline = time.monotonic() + 15
                for _ in range(32):
                    msg = json.loads(ws.recv(timeout=max(.01, deadline-time.monotonic())))
                    if isinstance(msg,list) and len(msg)>=3 and msg[:2]==["EVENT","ario-r22-11"]:
                        raw = extract(msg[2],target)
                        if raw is not None:
                            found = raw
                            sources.append(url)
                            break
                    if isinstance(msg,list) and len(msg)>=2 and msg[0] in ("EOSE","CLOSED") and msg[1]=="ario-r22-11":
                        break
                    if time.monotonic() >= deadline:
                        break
        except Exception as exc:
            print(json.dumps({"relay":url,"read_error":type(exc).__name__}), flush=True)
    return found, sources

def discover_target(report, boot):
    matches = report.get("matching_signed_leaves")
    if (report.get("disposition") != "HOLD_OPAQUE_NEW_SIGNED_COMMITMENT"
        or report.get("complete_sampled_suffix") is not True
        or report.get("new_opaque_signed_commitments") != 1
        or not isinstance(matches, list) or len(matches) != 2
        or matches[0] != {"index":boot["start"],"checksum":boot["first_checksum"]}
        or type(matches[1]["index"]) is not int
        or not boot["start"] < matches[1]["index"] < report["sampled_tree_size"]
        or not HEX.fullmatch(matches[1]["checksum"]) or matches[1]["checksum"] == boot["first_checksum"]):
        raise ValueError("not a complete two-match discovery report")
    return matches[1]["checksum"]

def recover(first_path, bootstrap_path, discovery_path, output):
    first_raw = Path(first_path).read_bytes()
    boot = json.loads(Path(bootstrap_path).read_text())
    report = json.loads(Path(discovery_path).read_text().splitlines()[-1])
    target = discover_target(report, boot)
    candidate, sources = fetch(target)
    status = validate(first_raw, candidate, target, boot["first_checksum"])
    result = {"disposition":status,"checksum":target,"external_read_sources":sources,
              "content_recovered": status == "RECOVERED_LINKED_SYNTHETIC_ENVELOPE_ONLY",
              "floor_preimage_recovered":False,"global_latest":"NOT_ESTABLISHED",
              "source_durability":"NOT_ESTABLISHED","independent_latest_floor":"NOT_ESTABLISHED",
              "history_truth":"UNKNOWN","trust_activation":"NO_GO","production":"NO_GO",
              "merge_authorized":False}
    if result["content_recovered"]:
        result["verified_envelope_record_count"] = parse(candidate)["record_count"]
        Path(output).write_bytes(candidate)
    print(json.dumps(result,sort_keys=True), flush=True)
    if not result["content_recovered"]:
        raise SystemExit(2)

if __name__ == "__main__":
    if len(sys.argv)==3 and sys.argv[1]=="publish":
        publish(Path(sys.argv[2]).read_bytes())
    elif len(sys.argv)==6 and sys.argv[1]=="recover":
        recover(*sys.argv[2:])
    else:
        raise SystemExit("invalid invocation")
