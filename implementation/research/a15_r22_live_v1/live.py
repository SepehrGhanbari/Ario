"""A15/R22 live synthetic experiment; no operational authority or private input.
Nostr transport and Sigsum bootstrap adapted from R22.20 blob fbb47a4f63c889170bdfabdadbe28dafd9812603.
The only publisher input is a new disposable directory. All event data are synthetic.
"""
import base64, hashlib, json, re, secrets, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import a15_custodian_broker_v0_5 as broker
import a15_r22_readonly_adapter_v1 as adapter

TOPIC = "ario-a15-r22-synthetic-v1"
PREFIX = "ARIO A15/R22 synthetic TEST checkpoint (no personal data): "
RELAYS = ("wss://nos.lol", "wss://relay.primal.net")
LOG_ID = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
def check(ok, why):
    if not ok: raise ValueError(why)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def checksum(raw): return sha(hashlib.sha256(raw).digest())
def canonical(obj): return (adapter.canonical(obj)+"\n").encode("ascii")
def parse_json(raw, limit=16384):
    check(type(raw) is bytes and 0 < len(raw) <= limit, "bounded input")
    x=adapter._parse_json(raw)
    check(type(x) is dict and canonical(x)==raw,"canonical object")
    return x

def parse_checkpoint(raw):
    x=parse_json(raw)
    check(set(x)==adapter.ENVELOPE_KEYS,"checkpoint envelope")
    p=x["payload"]
    check(type(p) is dict and set(p)==adapter.PAYLOAD_KEYS,"checkpoint payload")
    check(x["payload_sha256"]==sha(adapter.canonical(p).encode("ascii")),"payload digest")
    check(p["format"]==adapter.FORMAT and p["domain"]==adapter.DOMAIN and p["broker_source"]==adapter.SOURCE,"source/domain")
    check(type(p["journal_scope"]) is str and re.fullmatch("A15_SYNTH_[0-9A-F]{32}",p["journal_scope"]),"synthetic scope")
    h=p["broker_head"]
    check(type(h) is dict and set(h)=={"seq","hash"} and type(h["seq"]) is int and h["seq"] in (1,2) and type(h["hash"]) is str and HEX64.fullmatch(h["hash"]),"synthetic head")
    link=p["previous_external_checkpoint_sha256"]
    check((h["seq"]==1 and p["enrollment"]=="INITIAL_BASELINE" and link=="GENESIS") or (h["seq"]==2 and p["enrollment"]=="CONTINUATION" and type(link) is str and HEX64.fullmatch(link)),"enrollment/link")
    return x

def make_event(raw,key):
    parse_checkpoint(raw)
    event={"pubkey":key.public_key_xonly.format().hex(),"created_at":int(time.time()),"kind":1,
           "tags":[["t",TOPIC],["x",checksum(raw)]],"content":PREFIX+base64.b64encode(raw).decode("ascii")}
    event["id"]=nostr_event_id(event)
    event["sig"]=key.sign_schnorr(bytes.fromhex(event["id"])).hex()
    return event

def verify_event(event,pubkey):
    from coincurve import PublicKeyXOnly
    check(type(event) is dict and set(event)=={"id","pubkey","created_at","kind","tags","content","sig"},"event schema")
    check(type(pubkey) is str and HEX64.fullmatch(pubkey) and event["pubkey"]==pubkey,"signer")
    check(type(event["id"]) is str and HEX64.fullmatch(event["id"]) and type(event["sig"]) is str and re.fullmatch("[0-9a-f]{128}",event["sig"]),"signature fields")
    check(type(event["kind"]) is int and event["kind"]==1 and type(event["created_at"]) is int and event["created_at"]>=0,"event type")
    check(nostr_event_id(event)==event["id"] and PublicKeyXOnly(bytes.fromhex(pubkey)).verify(bytes.fromhex(event["sig"]),bytes.fromhex(event["id"])),"event authenticity")
    c=event["content"]
    check(type(c) is str and c.startswith(PREFIX) and len(c)<24000,"content bounds")
    raw=base64.b64decode(c[len(PREFIX):],validate=True)
    check(event["tags"]==[["t",TOPIC],["x",checksum(raw)]],"content binding")
    return raw,parse_checkpoint(raw)

def successor(a,b,target,pub):
    raw,x=verify_event(a,pub)
    raw2,y=verify_event(b,pub)
    p,q=x["payload"],y["payload"]
    check(target_for_event(b)==target and target_for_event(a)!=target,"discovered leaf binding")
    check(p["broker_head"]["seq"]==1 and q["broker_head"]["seq"]==2 and q["journal_scope"]==p["journal_scope"] and q["previous_external_checkpoint_sha256"]==x["payload_sha256"],"successor link")
    return raw2,y

def request(scope,i,preference="ACCEPT"):
    choice={"actor":"ARIO","role":"RESEARCH_DIALOGUE","origin":"CURRENT","explicit_renewal":False,
            "risk":"LOW","authorization":"ALLOWED","usefulness":"USEFUL","evidence":"SUFFICIENT",
            "preference":preference,"duration":"BOUNDED"}
    return {"v":1,"run_id":scope,"attempt_id":"SYNTH_"+str(i),"choice_json":broker.encode(choice),"claimed_status":preference}
def append(state,scope,i,preference="ACCEPT",provision=False):
    j=broker.Journal(state,provision=provision)
    try:
        r=j.consume(request(scope,i,preference))
        check(r["seq"]==i and r["execution_authorized"] is False and r["origin_attested"] is False and r["independent_custody"]=="NOT_ESTABLISHED","broker receipt")
    finally: j.conn.close()
def seed(root):
    root.mkdir(mode=0o700)
    scope="A15_SYNTH_"+secrets.token_hex(16).upper()
    state=root/"state"
    first=root/"first"; second=root/"second"
    first.mkdir();second.mkdir()
    append(state,scope,1,provision=True)
    a=adapter.build_checkpoint(state,scope,enroll_genesis=True)
    (first/"checkpoint.json").write_bytes(canonical(a))
    shutil.copytree(state,second/"rollback-state")
    append(state,scope,2,"DECLINE")
    b=adapter.build_checkpoint(state,scope,previous_checkpoint_path=first/"checkpoint.json")
    (second/"checkpoint.json").write_bytes(canonical(b))
    shutil.copytree(state,second/"matched-state")
    return first,second
def publish(root):
    from coincurve import PrivateKey
    first,second=seed(root)
    key=PrivateKey()
    for folder in (first,second):
        raw=(folder/"checkpoint.json").read_bytes()
        event=make_event(raw,key)
        verify_event(event,event["pubkey"])
        (folder/"event.json").write_bytes(canonical(event))
        (folder/"event-id.txt").write_bytes(event_leaf_message(event))
        accepted,failures=publish_event(event)
        check(len(accepted)==2,"HOLD relay publication: "+str(failures))
        # Require separate verified readback from each relay before proceeding.
        for url in RELAYS:
            found, payload, obs=fetch_from(url,event["pubkey"],target_for_event(event))
            check(found is not None and payload[0]==raw,"HOLD relay readback: "+str(obs))
        print(json.dumps({"stage":"RELAY_PUBLISH_READBACK","seq":parse_checkpoint(raw)["payload"]["broker_head"]["seq"],"relays":accepted}),flush=True)
    (first/"nostr.pub").write_text(key.public_key_xonly.format().hex()+"\n",encoding="ascii")

def read_event(p): return parse_json(p.read_bytes(),32768)
def discover(first,report,out):
    a=read_event(first/"event.json");pub=(first/"nostr.pub").read_text("ascii").strip()
    raw,_=verify_event(a,pub)
    check(raw==(first/"checkpoint.json").read_bytes(),"first checkpoint binding")
    boot=parse_json((first/"bootstrap.json").read_bytes(),4096)
    r=json.loads(report.read_text().splitlines()[-1]);m=r["matching_signed_leaves"]
    check(r["disposition"]=="HOLD_OPAQUE_NEW_SIGNED_COMMITMENT" and r["complete_sampled_suffix"] is True and len(m)==2 and m[0]=={"index":boot["start"],"checksum":boot["first_checksum"]} and target_for_event(a)==boot["first_checksum"] and m[1]["index"]>m[0]["index"] and HEX64.fullmatch(m[1]["checksum"]),"HOLD incomplete/ambiguous scan")
    target=m[1]["checksum"]
    recovered,observations=fetch_many(RELAYS,pub,target)
    check(recovered is not None,"HOLD_OPAQUE_CONTENT_UNAVAILABLE")
    b,_,source=recovered
    raw2,y=successor(a,b,target,pub)
    check(extract_target([a],target,pub)==(None,None),"stale replay accepted")
    missing,_,_=fetch_from("ws://127.0.0.1:1",pub,target)
    fallback,_,_=fetch_from(source,pub,target)
    check(missing is None and fallback is not None and fallback["id"]==b["id"],"single source fallback")
    check(fetch_many(("ws://127.0.0.1:1","ws://127.0.0.1:2"),pub,target)[0] is None,"outage control")
    out.mkdir()
    (out/"checkpoint.json").write_bytes(raw2)
    (out/"event.json").write_bytes(canonical(b))
    print(json.dumps({"stage":"RECOVERED_LINKED_SYNTHETIC_CHECKPOINT","head":y["payload"]["broker_head"],"observations":observations,"stale_replay":"HOLD","one_endpoint_outage":"PASS","both_endpoints_outage":"HOLD_OPAQUE","global_latest":"NOT_ESTABLISHED"}),flush=True)
def audit(first,second,recovered,report):
    a,b=read_event(first/"event.json"),read_event(second/"event.json")
    r=json.loads(report.read_text().splitlines()[-1])
    raw,x=successor(a,b,r["matching_signed_leaves"][1]["checksum"],a["pubkey"])
    check(raw==(recovered/"checkpoint.json").read_bytes()==(second/"checkpoint.json").read_bytes() and b==read_event(recovered/"event.json"),"reveal mismatch")
    expected=x["payload"]["broker_head"]
    scope=x["payload"]["journal_scope"]
    def observe(state):
        return adapter.build_checkpoint(state,scope,enroll_genesis=True)["payload"]["broker_head"]
    def classify(state):
        h=observe(state)
        if h["seq"]<expected["seq"]:return "HOLD_ROLLBACK"
        if h["seq"]==expected["seq"]:return "MATCH_OBSERVED_ONLY" if h==expected else "HOLD_FORK"
        try: adapter.build_checkpoint(state,scope,previous_checkpoint_path=recovered/"checkpoint.json")
        except adapter.AdapterHold:return "HOLD_FORK_OR_INVALID"
        return "HOLD_UNANCHORED_SUFFIX"
    check(classify(second/"matched-state")=="MATCH_OBSERVED_ONLY","match")
    check(classify(second/"rollback-state")=="HOLD_ROLLBACK","joint rollback")
    fork=second/"fork-state";shutil.copytree(second/"rollback-state",fork)
    append(fork,scope,2,"ACCEPT")
    check(classify(fork)=="HOLD_FORK","fork")
    ahead=second/"ahead-state";shutil.copytree(second/"matched-state",ahead)
    append(ahead,scope,3,"UNKNOWN")
    # UNKNOWN claim must be generated with UNKNOWN preference (broker policy).
    check(classify(ahead)=="HOLD_UNANCHORED_SUFFIX","ahead")
    print(json.dumps({"stage":"A15_REVEAL_MATCH","head":expected,"match":"MATCH_OBSERVED_ONLY","joint_rollback":"HOLD","fork":"HOLD","ahead":"HOLD_UNANCHORED_SUFFIX","independent_custody":"NOT_ESTABLISHED","execution_authorized":False,"origin_attested":False,"global_latest":"NOT_ESTABLISHED","trust_activation":"NO_GO","production":"NO_GO"}),flush=True)
def selftest(root):
    from coincurve import PrivateKey
    first,second=seed(root)
    k=PrivateKey()
    a,b=[make_event((p/"checkpoint.json").read_bytes(),k) for p in (first,second)]
    pub=a["pubkey"];target=target_for_event(b)
    raw,x=successor(a,b,target,pub)
    check(x["payload"]["broker_head"]["seq"]==2,"positive")
    for bad in ({**b,"sig":"0"*128},{**b,"content":b["content"]+"x"},a):
        try:successor(a,bad,target,pub)
        except ValueError:pass
        else:raise ValueError("negative accepted")
    check(extract_target([a],target,pub)==(None,None),"stale accepted")
    print("A15_R22_OFFLINE_TRANSPORT_CONTROLS_PASS",flush=True)

def nostr_event_id(event):
    fields = [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]]
    return hashlib.sha256(json.dumps(fields, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

def event_leaf_message(event):
    return (event["id"] + "\n").encode("ascii")

def target_for_event(event):
    return checksum(event_leaf_message(event))

def extract_target(events, target, pubkey):
    if type(target) is not str or not HEX64.fullmatch(target):
        return None, None
    matches = []
    for event in events:
        try:
            payload = verify_event(event, pubkey)
            if target_for_event(event) == target:
                matches.append((event, payload))
        except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
            continue
    unique = {item[0]["id"]: item for item in matches}
    if len(unique) > 1:
        raise ValueError("conflicting event IDs for one logged checksum")
    if not unique:
        return None, None
    return next(iter(unique.values()))


def connect(url):
    from websockets.sync.client import connect as ws_connect
    return ws_connect(url, open_timeout=8, close_timeout=2, max_size=131072, proxy=None)

def publish_event(event, urls=RELAYS):
    accepted, failures = [], []
    for url in urls:
        try:
            with connect(url) as ws:
                ws.send(json.dumps(["EVENT", event], separators=(",", ":"), ensure_ascii=False))
                deadline = time.monotonic() + 12
                for _ in range(24):
                    msg = json.loads(ws.recv(timeout=max(.01, deadline-time.monotonic())))
                    if isinstance(msg, list) and len(msg) >= 4 and msg[0] == "OK" and msg[1] == event["id"]:
                        if msg[2] is True:
                            accepted.append(url)
                        else:
                            failures.append({"relay": url, "reason": str(msg[3])[:160]})
                        break
                    if time.monotonic() >= deadline:
                        failures.append({"relay": url, "reason": "timeout"})
                        break
        except Exception as exc:
            failures.append({"relay": url, "reason": type(exc).__name__})
    return accepted, failures

def fetch_from(url, pubkey, target):
    events, failure = [], None
    try:
        with connect(url) as ws:
            sub = "ario-a15-r22-v1"
            ws.send(json.dumps(["REQ", sub, {"kinds": [1], "authors": [pubkey], "#t": [TOPIC], "limit": 32}]))
            deadline = time.monotonic() + 16
            for _ in range(128):
                msg = json.loads(ws.recv(timeout=max(.01, deadline-time.monotonic())))
                if isinstance(msg, list) and len(msg) >= 3 and msg[0] == "EVENT" and msg[1] == sub:
                    if type(msg[2]) is dict:
                        events.append(msg[2])
                elif isinstance(msg, list) and len(msg) >= 2 and msg[0] in ("EOSE", "CLOSED") and msg[1] == sub:
                    break
                if time.monotonic() >= deadline:
                    failure = "timeout"
                    break
        event, payload = extract_target(events, target, pubkey)
        return event, payload, {"relay": url, "events_seen": len(events), "matched": event is not None, "error": failure}
    except Exception as exc:
        return None, None, {"relay": url, "events_seen": len(events), "matched": False, "error": type(exc).__name__}

def fetch_many(urls, pubkey, target):
    candidates, observations = [], []
    for url in urls:
        event, payload, observation = fetch_from(url, pubkey, target)
        observations.append(observation)
        if event is not None:
            candidates.append((event, payload, url))
    unique = {item[0]["id"]: item for item in candidates}
    if len(unique) > 1:
        raise ValueError("conflicting event IDs for one logged checksum")
    if not unique:
        return None, observations
    return next(iter(unique.values())), observations


def create_bootstrap(first_dir, log_pub):
    first = Path(first_dir)
    proof = (first / "event-id.txt.proof").read_text("ascii")
    fields = {}
    for line in proof.splitlines():
        k, sep, v = line.partition("=")
        if sep and k in ("size", "root_hash", "leaf_index", "log", "leaf"):
            if k in fields:
                raise ValueError("duplicate proof field")
            fields[k] = v
    if set(fields) != {"size", "root_hash", "leaf_index", "log", "leaf"} or fields["log"] != LOG_ID:
        raise ValueError("proof schema")
    public_blob = base64.b64decode(Path(log_pub).read_text("ascii").split()[1], validate=True)
    n = int.from_bytes(public_blob[:4], "big")
    if public_blob[4:4+n] != b"ssh-ed25519" or int.from_bytes(public_blob[4+n:8+n], "big") != 32:
        raise ValueError("sigsum public key")
    public = public_blob[8+n:]
    if len(public) != 32 or hashlib.sha256(public).hexdigest() != fields["leaf"].split()[0]:
        raise ValueError("proof signer binding")
    msg = (first / "event-id.txt").read_bytes()
    first_hash = checksum(msg)
    leaf_fields = fields["leaf"].split()
    if len(leaf_fields) != 2 or leaf_fields[0] != hashlib.sha256(public).hexdigest() or not re.fullmatch(r"[0-9a-f]{128}", leaf_fields[1]):
        raise ValueError("proof leaf schema/signer binding")
    boot = {
        "start": int(fields["leaf_index"]), "size": int(fields["size"]),
        "root": fields["root_hash"], "public": public.hex(), "first_checksum": first_hash,
    }
    (first / "bootstrap.json").write_bytes(canonical(boot))
    (first / "sigsum.pub").write_text(Path(log_pub).read_text("ascii"), encoding="ascii")
    return boot



if __name__=="__main__":
    mode,*args=sys.argv[1:]
    if mode=="publish": publish(Path(args[0]))
    elif mode=="selftest": selftest(Path(args[0]))
    elif mode=="bootstrap": create_bootstrap(*args)
    elif mode=="discover": discover(*map(Path,args))
    elif mode=="audit": audit(*map(Path,args))
    else: raise SystemExit("invalid invocation")
