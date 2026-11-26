#!/usr/bin/env python3
"""Offline A15/R22 proof-envelope compatibility audit of retained A15 artifacts."""
from __future__ import annotations
import argparse, base64, hashlib, importlib.util, json, re, subprocess, sys, tempfile, zipfile
from pathlib import Path

HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX128 = re.compile(r"[0-9a-f]{128}\Z")
EVENT_KEYS = {"id", "pubkey", "created_at", "kind", "tags", "content", "sig"}
COUNT = 0

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None: raise RuntimeError("HOLD_MODULE_LOAD")
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module

def check(label, condition):
    global COUNT
    if not condition: raise RuntimeError("HOLD_" + label)
    COUNT += 1; print(label + " PASS", flush=True)

def rejects(label, fn):
    global COUNT
    try: fn()
    except (ValueError, TypeError, KeyError, UnicodeError, IndexError, RecursionError):
        COUNT += 1; print(label + " PASS_REJECTED", flush=True); return
    raise RuntimeError("HOLD_" + label + "_ACCEPTED")

def read(path, limit):
    raw = path.read_bytes()
    if not 0 < len(raw) <= limit: raise ValueError("HOLD_FILE_BOUNDS")
    return raw

def parse_proof(raw, log_id):
    fields = {}; repeated = {"cosignature": [], "node_hash": []}
    allowed = {"version", "log", "leaf", "size", "root_hash", "signature", "leaf_index", "cosignature", "node_hash"}
    for line in raw.decode("ascii", "strict").splitlines():
        if not line: continue
        key, sep, value = line.partition("=")
        if not sep or key not in allowed: raise ValueError("HOLD_PROOF_FIELD")
        if key in repeated: repeated[key].append(value)
        else:
            if key in fields: raise ValueError("HOLD_DUPLICATE_PROOF_FIELD")
            fields[key] = value
    required = {"version", "log", "leaf", "size", "root_hash", "signature", "leaf_index"}
    if set(fields) != required or fields["version"] != "2" or fields["log"] != log_id:
        raise ValueError("HOLD_PROOF_SCHEMA_OR_PROFILE")
    leaf = fields["leaf"].split()
    if len(leaf) != 2 or not HEX64.fullmatch(leaf[0]) or not HEX128.fullmatch(leaf[1]): raise ValueError("HOLD_PROOF_LEAF")
    if not HEX64.fullmatch(fields["root_hash"]) or not HEX128.fullmatch(fields["signature"]): raise ValueError("HOLD_PROOF_DIGEST_OR_SIGNATURE")
    if len(repeated["cosignature"]) < 2 or len(repeated["node_hash"]) > 64: raise ValueError("HOLD_PROOF_REPEATED_FIELDS")
    for item in repeated["node_hash"]:
        if not HEX64.fullmatch(item): raise ValueError("HOLD_PROOF_NODE")
    for item in repeated["cosignature"]:
        parts = item.split()
        if len(parts) != 3 or not HEX64.fullmatch(parts[0]) or not parts[1].isdigit() or not HEX128.fullmatch(parts[2]):
            raise ValueError("HOLD_PROOF_COSIGNATURE")
    size, index = int(fields["size"]), int(fields["leaf_index"])
    if not 0 <= index < size < 2**63: raise ValueError("HOLD_PROOF_COORDINATES")
    return {"size": size, "index": index, "root": fields["root_hash"], "log": fields["log"]}

def verify_sigsum(binary, key, proof, message):
    result = subprocess.run([str(binary), "-k", str(key), "-P", "sigsum-test1-2025", str(proof)],
                            input=message, capture_output=True, timeout=30, check=False)
    return result.returncode == 0

def parse_a15_event(event, expected_pubkey, live, pure):
    if type(event) is not dict or set(event) != EVENT_KEYS: raise ValueError("A15 event schema")
    pure.check(event)
    if event["pubkey"] != expected_pubkey or type(event["kind"]) is not int or event["kind"] != 1:
        raise ValueError("A15 event signer/kind")
    content = event["content"]
    if type(content) is not str or not content.startswith(live.PREFIX) or len(content) >= 24000:
        raise ValueError("A15 event prefix/bounds")
    raw = base64.b64decode(content[len(live.PREFIX):], validate=True)
    envelope = live.parse_checkpoint(raw)
    if event["tags"] != [["t", live.TOPIC], ["x", live.checksum(raw)]]: raise ValueError("A15 event tags")
    return raw, envelope

def parse_r22_event(event, expected_pubkey, codec, pure):
    if type(event) is not dict or set(event) != EVENT_KEYS: raise ValueError("R22 event schema")
    pure.check(event)
    if event["pubkey"] != expected_pubkey or type(event["kind"]) is not int or event["kind"] != 1:
        raise ValueError("R22 event signer/kind")
    content = event["content"]
    if type(content) is not str or not content.startswith(codec.PREFIX) or len(content) > 100000:
        raise ValueError("R22 event prefix/bounds")
    parts = content[len(codec.PREFIX):].split(".")
    if len(parts) != 2: raise ValueError("R22 event payload shape")
    envelope_raw = base64.b64decode(parts[0], validate=True); ledger_raw = base64.b64decode(parts[1], validate=True)
    envelope = codec.parse_envelope(envelope_raw); rows = codec.parse_ledger(ledger_raw, envelope["seq"])
    if (event["tags"] != [["t", codec.TOPIC], ["x", codec.checksum(envelope_raw)]]
        or codec.sha(ledger_raw) != envelope["ledger_sha256"] or rows[-1]["sha256"] != envelope["head_sha256"]):
        raise ValueError("R22 event binding")
    return envelope_raw, envelope, ledger_raw

def make_r22_fixture(codec, PrivateKey):
    row = {"record_id":"ROW-0","observed_at":"LAB-SYNTHETIC-A15-R22-PROFILE-BOUNDARY",
           "payload":{"fixture":"A15-vs-R22.20-profile-rejection"},"previous_sha256":None}
    row["sha256"] = codec.sha(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii"))
    ledger = codec.canonical(row)
    envelope = codec.make_envelope("a"*48, 1, ledger, "1"*64, "2"*64, "GENESIS", "GENESIS", "GENESIS")
    key = PrivateKey(bytes.fromhex("00"*31+"03"))
    event = codec.make_event(envelope, ledger, key); codec.verify_event(event, event["pubkey"])
    return envelope, event

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=Path, required=True); parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--r22-codec", type=Path, required=True); parser.add_argument("--r22-pure-verifier", type=Path, required=True)
    parser.add_argument("--sigsum-verify", type=Path, required=True); args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]; research = repo/"implementation"/"research"; sys.path.insert(0, str(research))
    live = load_module("a15_live_v1", research/"a15_r22_live_v1"/"live.py")
    codec = load_module("r22_22g_event_codec", args.r22_codec); pure = load_module("r22_22g_pure_bip340", args.r22_pure_verifier)
    def git_blob(data):
        normalized=data.replace(b"\r\n",b"\n")
        return hashlib.sha1(b"blob "+str(len(normalized)).encode()+b"\0"+normalized).hexdigest()
    check("PIN_A15_LIVE_SOURCE", git_blob((research/"a15_r22_live_v1"/"live.py").read_bytes())=="b040a4921aff134b50b5c809d3b8e004a885fe8b")
    check("PIN_R22_EVENT_CODEC", git_blob(args.r22_codec.read_bytes())=="95a79184d33a81ffd75b2188f5041d7cef345868")
    check("PIN_R22_PURE_VERIFIER", git_blob(args.r22_pure_verifier.read_bytes())=="a29990a1e695b64d7611483e1d0f5f486c02c932")
    first_event=live.parse_json(read(args.first/"event.json",32768),32768); second_event=live.parse_json(read(args.second/"event.json",32768),32768)
    pub=read(args.first/"nostr.pub",256).decode("ascii").strip(); log_key=args.first/"log-key.pub"
    first_checkpoint=read(args.first/"checkpoint.json",16384); second_checkpoint=read(args.second/"checkpoint.json",16384)
    first_raw,first_env=parse_a15_event(first_event,pub,live,pure); second_raw,second_env=parse_a15_event(second_event,pub,live,pure)
    check("A15_PROFILE_ACCEPTS_BOTH_ARCHIVED_EVENTS", first_raw==first_checkpoint and second_raw==second_checkpoint)
    check("A15_CHECKPOINT_SEQUENCE_AND_SCOPE", first_env["payload"]["broker_head"]["seq"]==1 and second_env["payload"]["broker_head"]["seq"]==2 and first_env["payload"]["journal_scope"]==second_env["payload"]["journal_scope"])
    check("A15_SUCCESSOR_PREVIOUS_DIGEST", second_env["payload"]["previous_external_checkpoint_sha256"]==first_env["payload_sha256"])
    check("A15_SOURCE_PIN_UNCHANGED", first_env["payload"]["broker_source"]==second_env["payload"]["broker_source"])
    proof_paths=[args.first/"event-id.txt.proof",args.second/"event-id.txt.proof"]; proof_data=[]
    for i,(event,directory,proof_path) in enumerate(zip((first_event,second_event),(args.first,args.second),proof_paths)):
        message=live.event_leaf_message(event)
        check("A15_EVENT_ID_FILE_"+str(i+1),read(directory/"event-id.txt",256)==message)
        proof=parse_proof(read(proof_path,16384),live.LOG_ID)
        check("SIGSUM_PROOF_COORDINATES_"+str(i+1),proof["size"]>proof["index"] and proof["log"]==live.LOG_ID)
        check("SIGSUM_OFFICIAL_VERIFY_"+str(i+1),verify_sigsum(args.sigsum_verify,log_key,proof_path,message))
        proof_data.append(proof)
    bootstrap=json.loads(read(args.first/"bootstrap.json",4096).decode("utf-8"))
    check("BOOTSTRAP_BINDS_FIRST_LEAF",bootstrap["start"]==proof_data[0]["index"] and bootstrap["size"]==proof_data[0]["size"] and bootstrap["root"]==proof_data[0]["root"] and bootstrap["first_checksum"]==live.target_for_event(first_event))
    check("EXTERNAL_LEAF_ORDER_ADVANCES",proof_data[1]["index"]>proof_data[0]["index"] and proof_data[1]["size"]>=proof_data[0]["size"])
    from coincurve import PrivateKey
    r22_envelope,r22_event=make_r22_fixture(codec,PrivateKey)
    r22_env_raw,r22_env,r22_ledger=parse_r22_event(r22_event,r22_event["pubkey"],codec,pure)
    check("R22_20_PROFILE_ACCEPTS_OWN_FIXTURE",r22_env_raw==r22_envelope and r22_env["profile"]==codec.PROFILE and bool(r22_ledger))
    rejects("A15_PARSER_REJECTS_R22_20_ENVELOPE",lambda:live.parse_checkpoint(r22_env_raw))
    rejects("R22_20_PARSER_REJECTS_A15_ENVELOPE",lambda:codec.parse_envelope(first_checkpoint))
    rejects("A15_EVENT_PARSER_REJECTS_VALID_R22_20_EVENT",lambda:parse_a15_event(r22_event,r22_event["pubkey"],live,pure))
    rejects("R22_20_EVENT_PARSER_REJECTS_VALID_A15_EVENT",lambda:parse_r22_event(first_event,pub,codec,pure))
    with tempfile.TemporaryDirectory(prefix="a15-r22-proof-compat-") as name:
        tmp=Path(name); swapped=tmp/"swapped.proof"; swapped.write_bytes(read(proof_paths[1],16384))
        check("SIGSUM_REJECTS_SWAPPED_PROOF",not verify_sigsum(args.sigsum_verify,log_key,swapped,live.event_leaf_message(first_event)))
        tampered=bytearray(read(proof_paths[0],16384)); pos=tampered.find(b"root_hash=")
        if pos<0: raise RuntimeError("HOLD_PROOF_ROOT_MISSING")
        value_pos=pos+len(b"root_hash="); tampered[value_pos]=ord("0") if tampered[value_pos]!=ord("0") else ord("1")
        altered=tmp/"tampered.proof"; altered.write_bytes(bytes(tampered))
        check("SIGSUM_REJECTS_TAMPERED_PROOF",not verify_sigsum(args.sigsum_verify,log_key,altered,live.event_leaf_message(first_event)))
    print(json.dumps({"schema":"ARIO_A15_R22_PROOF_ENVELOPE_COMPATIBILITY_V1","status":"PASS_OFFLINE_ARCHIVED_PROFILE_AND_PROOF_BINDING","checks":COUNT,
      "a15_archived_checkpoints":[first_env["payload"]["broker_head"],second_env["payload"]["broker_head"]],
      "sigsum_leaf_indices":[proof_data[0]["index"],proof_data[1]["index"]],"r22_20_profile":codec.PROFILE,
      "cross_profile_acceptance":False,"new_publication":"NONE","global_latest":"UNKNOWN",
      "independent_custody":"NOT_ESTABLISHED","evidence_admission":"NO_ADMISSION","trust_activation":"NO_GO","production":"NO_GO"},sort_keys=True),flush=True)

if __name__=="__main__":
    try: main()
    except (OSError,ValueError,TypeError,KeyError,UnicodeError,RecursionError,subprocess.SubprocessError,zipfile.BadZipFile) as exc:
        print(json.dumps({"schema":"ARIO_A15_R22_PROOF_ENVELOPE_COMPATIBILITY_V1","status":"HOLD_COMPATIBILITY_AUDIT","reason":type(exc).__name__}),flush=True)
        raise SystemExit(2)
