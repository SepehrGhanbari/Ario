"""Read-only synthetic checkpoint verification extracted from A15 v1; no publication or Broker dependency."""
import base64, hashlib, json, re

FORMAT = "ario-a15-r22-readonly-checkpoint-v1"
DOMAIN = "ARIO/A15/R22"
BROKER_SOURCE_FILENAME = "a15_custodian_broker_v0_5.py"
BROKER_SOURCE_COMMIT = "bfe66cbba60a25086773d1790284eb97e3a6202a"
BROKER_SOURCE_GIT_BLOB_SHA1 = "612fa44e6eb2cb1078561bca85bb0f69f984bff9"
BROKER_SOURCE_REPO_PATH = "implementation/research/a15_custodian_broker_v0_5.py"
PAYLOAD_KEYS = frozenset((
    "format", "domain", "enrollment", "journal_scope", "broker_source",
    "broker_head", "previous_external_checkpoint_sha256",
))
ENVELOPE_KEYS = frozenset(("payload", "payload_sha256"))
SOURCE = {
    "commit": BROKER_SOURCE_COMMIT,
    "git_blob_sha1": BROKER_SOURCE_GIT_BLOB_SHA1,
    "path": BROKER_SOURCE_REPO_PATH,
}


class AdapterHold(ValueError):
    """Fail-closed result: no checkpoint should be published."""


def canonical(value):
    """Canonical ASCII JSON for the new envelope (not the Broker's row JSON)."""
    return json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":"),
        allow_nan=False,
    )


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AdapterHold("duplicate JSON key")
        result[key] = value
    return result


def _parse_json(raw):
    try:
        return json.loads(
            raw.decode("utf-8", "strict"),
            object_pairs_hook=_no_duplicates,
            parse_constant=lambda _value: (_ for _ in ()).throw(
                AdapterHold("non-finite JSON value")
            ),
        )
    except (UnicodeError, json.JSONDecodeError, TypeError) as exc:
        raise AdapterHold("invalid JSON input") from exc


TOPIC = "ario-a15-r22-synthetic-v1"
PREFIX = "ARIO A15/R22 synthetic TEST checkpoint (no personal data): "

LOG_ID = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
def check(ok, why):
    if not ok: raise ValueError(why)
def sha(raw): return hashlib.sha256(raw).hexdigest()
def checksum(raw): return sha(hashlib.sha256(raw).digest())
def canonical(obj): return (canonical(obj)+"\n").encode("ascii")
def parse_json(raw, limit=16384):
    check(type(raw) is bytes and 0 < len(raw) <= limit, "bounded input")
    x=_parse_json(raw)
    check(type(x) is dict and canonical(x)==raw,"canonical object")
    return x

def parse_checkpoint(raw):
    x=parse_json(raw)
    check(set(x)==ENVELOPE_KEYS,"checkpoint envelope")
    p=x["payload"]
    check(type(p) is dict and set(p)==PAYLOAD_KEYS,"checkpoint payload")
    check(x["payload_sha256"]==sha(canonical(p).encode("ascii")),"payload digest")
    check(p["format"]==FORMAT and p["domain"]==DOMAIN and p["broker_source"]==SOURCE,"source/domain")
    check(type(p["journal_scope"]) is str and re.fullmatch("A15_SYNTH_[0-9A-F]{32}",p["journal_scope"]),"synthetic scope")
    h=p["broker_head"]
    check(type(h) is dict and set(h)=={"seq","hash"} and type(h["seq"]) is int and h["seq"] in (1,2) and type(h["hash"]) is str and HEX64.fullmatch(h["hash"]),"synthetic head")
    link=p["previous_external_checkpoint_sha256"]
    check((h["seq"]==1 and p["enrollment"]=="INITIAL_BASELINE" and link=="GENESIS") or (h["seq"]==2 and p["enrollment"]=="CONTINUATION" and type(link) is str and HEX64.fullmatch(link)),"enrollment/link")
    return x

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

def nostr_event_id(event):
    fields = [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]]
    return hashlib.sha256(json.dumps(fields, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

def event_leaf_message(event):
    return (event["id"] + "\n").encode("ascii")

def target_for_event(event):
    return checksum(event_leaf_message(event))

