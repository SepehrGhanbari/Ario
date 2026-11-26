"""R22.20 external monotonic floor: Sigsum witnessed index + Nostr content relays.

All records are synthetic. Nostr relays are untrusted retrieval sources; Sigsum
TEST witnesses authenticate append-only order of event identifiers, not content
availability, truth, freshness beyond the sampled tree head, or production trust.
"""
import base64
import hashlib
import json
import os
import re
import secrets
import sys
import time
from pathlib import Path

PROFILE = "ARIO-R22.20-EXTERNAL-MONOTONIC-FLOOR-v1"
PREFIX = "ARIO R22.20 public synthetic floor (no personal data): "
RELAYS = ("wss://nos.lol", "wss://relay.primal.net")
TOPIC = "ario-r22-20"
LOG_ID = "4e89cc51651f0d95f3c6127c15e1a42e3ddf7046c5b17b752689c402e773bb4d"
PRIOR_ARTIFACT_ID = 14954102679
PRIOR_ARTIFACT_SHA256 = "d3b860cc3c0167e8d709a5336a26be231e8143e188b2094250e3fbb1f71ea3db"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
HEX48 = re.compile(r"[0-9a-f]{48}\Z")
MAX_ENVELOPE = 16384
MAX_LEDGER = 65536

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def checksum(raw):
    # Matches the R22.11 Sigsum leaf checksum convention.
    return hashlib.sha256(hashlib.sha256(raw).digest()).hexdigest()

def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                       allow_nan=False) + "\n").encode("ascii")

def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError("duplicate JSON field")
        out[key] = value
    return out

def parse_json(raw, limit):
    if type(raw) is not bytes or not 0 < len(raw) <= limit:
        raise ValueError("bounded size")
    obj = json.loads(raw.decode("ascii"), object_pairs_hook=unique_pairs)
    if type(obj) is not dict or canonical(obj) != raw:
        raise ValueError("canonical object")
    return obj

def parse_ledger(raw, expected_count=None):
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_LEDGER or not raw.endswith(b"\n"):
        raise ValueError("ledger bounds")
    rows = []
    previous = None
    for line in raw.splitlines(keepends=True):
        if not line.endswith(b"\n"):
            raise ValueError("ledger line ending")
        row = parse_json(line, 8192)
        if set(row) != {"record_id", "observed_at", "payload", "previous_sha256", "sha256"}:
            raise ValueError("ledger schema")
        if (row["record_id"] != f"ROW-{len(rows)}" or type(row["observed_at"]) is not str
                or type(row["payload"]) is not dict or row["previous_sha256"] != previous
                or type(row["sha256"]) is not str or not HEX64.fullmatch(row["sha256"])):
            raise ValueError("ledger chain")
        body = dict(row)
        claimed = body.pop("sha256")
        if sha(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")) != claimed:
            raise ValueError("ledger row digest")
        previous = claimed
        rows.append(row)
        if len(rows) > 16:
            raise ValueError("ledger count")
    if expected_count is not None and len(rows) != expected_count:
        raise ValueError("ledger count mismatch")
    return rows

def parse_envelope(raw):
    x = parse_json(raw, MAX_ENVELOPE)
    fields = {"profile", "scope", "seq", "previous_checksum", "previous_event_id",
              "previous_ledger_sha256", "prior_checkpoint_sha256", "prior_ledger_sha256",
              "ledger_sha256", "head_sha256", "synthetic", "authoritative",
              "historical_event_truth", "trust_activation", "production"}
    if set(x) != fields or x["profile"] != PROFILE:
        raise ValueError("envelope schema")
    if (type(x["scope"]) is not str or not HEX48.fullmatch(x["scope"])
            or type(x["seq"]) is not int or not 1 <= x["seq"] <= 16
            or x["synthetic"] is not True or x["authoritative"] is not False
            or x["historical_event_truth"] != "UNKNOWN" or x["trust_activation"] != "NO_GO"
            or x["production"] != "NO_GO"):
        raise ValueError("envelope policy")
    for name in ("prior_checkpoint_sha256", "prior_ledger_sha256", "ledger_sha256", "head_sha256"):
        if type(x[name]) is not str or not HEX64.fullmatch(x[name]):
            raise ValueError(name)
    for name in ("previous_checksum", "previous_event_id", "previous_ledger_sha256"):
        value = x[name]
        if type(value) is not str or not (value == "GENESIS" or HEX64.fullmatch(value)):
            raise ValueError(name)
    return x

def ledger_extend(old):
    rows = parse_ledger(old, 6)
    previous = rows[-1]["sha256"]
    result = old
    for i in (6, 7):
        row = {
            "record_id": f"ROW-{i}",
            "observed_at": f"LAB-SYNTHETIC-STEP-{i}",
            "payload": {
                "claim_id": "R22.20-SYNTHETIC",
                "node_id": f"EXTERNAL-FLOOR-{i}",
                "value": secrets.token_hex(24),
                "lineage_from": f"EXTERNAL-FLOOR-{i-1}",
                "lineage_to": f"EXTERNAL-FLOOR-{i}",
            },
            "previous_sha256": previous,
        }
        row["sha256"] = sha(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii"))
        previous = row["sha256"]
        result += canonical(row)
    parse_ledger(result, 8)
    return result

def make_envelope(scope, seq, ledger_raw, prior_checkpoint, prior_ledger,
                  previous_checksum, previous_event_id, previous_ledger):
    rows = parse_ledger(ledger_raw, seq)
    obj = {
        "profile": PROFILE,
        "scope": scope,
        "seq": seq,
        "previous_checksum": previous_checksum,
        "previous_event_id": previous_event_id,
        "previous_ledger_sha256": previous_ledger,
        "prior_checkpoint_sha256": prior_checkpoint,
        "prior_ledger_sha256": prior_ledger,
        "ledger_sha256": sha(ledger_raw),
        "head_sha256": rows[-1]["sha256"],
        "synthetic": True,
        "authoritative": False,
        "historical_event_truth": "UNKNOWN",
        "trust_activation": "NO_GO",
        "production": "NO_GO",
    }
    return canonical(obj)

def nostr_event_id(event):
    fields = [0, event["pubkey"], event["created_at"], event["kind"], event["tags"], event["content"]]
    return hashlib.sha256(json.dumps(fields, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

def make_event(envelope_raw, ledger_raw, key):
    from coincurve import PrivateKey
    if not isinstance(key, PrivateKey):
        raise TypeError("private key")
    x = parse_envelope(envelope_raw)
    if sha(ledger_raw) != x["ledger_sha256"]:
        raise ValueError("ledger digest")
    content = PREFIX + base64.b64encode(envelope_raw).decode("ascii") + "." + base64.b64encode(ledger_raw).decode("ascii")
    event = {
        "pubkey": key.public_key_xonly.format().hex(),
        "created_at": int(time.time()),
        "kind": 1,
        "tags": [["t", TOPIC], ["x", checksum(envelope_raw)]],
        "content": content,
    }
    event["id"] = nostr_event_id(event)
    event["sig"] = key.sign_schnorr(bytes.fromhex(event["id"])).hex()
    return event

def verify_event(event, expected_pubkey):
    from coincurve import PublicKeyXOnly
    if type(event) is not dict or set(event) != {"id", "pubkey", "created_at", "kind", "tags", "content", "sig"}:
        raise ValueError("event schema")
    if (type(event["id"]) is not str or not HEX64.fullmatch(event["id"])
            or type(event["pubkey"]) is not str or not HEX64.fullmatch(event["pubkey"])
            or event["pubkey"] != expected_pubkey
            or type(event["created_at"]) is not int or event["created_at"] < 0
            or type(event["kind"]) is not int or event["kind"] != 1
            or type(event["sig"]) is not str or not re.fullmatch(r"[0-9a-f]{128}", event["sig"])
            or type(event["tags"]) is not list or ["t", TOPIC] not in event["tags"]):
        raise ValueError("event fields")
    if nostr_event_id(event) != event["id"]:
        raise ValueError("event id")
    if not PublicKeyXOnly(bytes.fromhex(expected_pubkey)).verify(bytes.fromhex(event["sig"]), bytes.fromhex(event["id"])):
        raise ValueError("event signature")
    content = event["content"]
    if type(content) is not str or not content.startswith(PREFIX) or len(content) > 100000:
        raise ValueError("event content")
    parts = content[len(PREFIX):].split(".")
    if len(parts) != 2:
        raise ValueError("event payload shape")
    envelope_raw = base64.b64decode(parts[0], validate=True)
    ledger_raw = base64.b64decode(parts[1], validate=True)
    if len(envelope_raw) > MAX_ENVELOPE or len(ledger_raw) > MAX_LEDGER:
        raise ValueError("event payload size")
    envelope = parse_envelope(envelope_raw)
    rows = parse_ledger(ledger_raw, envelope["seq"])
    if (["x", checksum(envelope_raw)] not in event["tags"]
            or sha(ledger_raw) != envelope["ledger_sha256"]
            or rows[-1]["sha256"] != envelope["head_sha256"]):
        raise ValueError("event payload binding")
    return envelope_raw, envelope, ledger_raw, rows

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

def validate_successor(first_event, second_event, target, pubkey, prior_checkpoint):
    try:
        first_raw, first, first_ledger, first_rows = verify_event(first_event, pubkey)
        if target_for_event(first_event) != checksum(event_leaf_message(first_event)):
            return "HOLD_FIRST_EVENT_BINDING", None
        second_raw, second, second_ledger, second_rows = verify_event(second_event, pubkey)
        if target_for_event(second_event) != target:
            return "HOLD_EVENT_ID_NOT_LOGGED", None
        if (first["seq"] != 6 or first["prior_checkpoint_sha256"] != prior_checkpoint
                or first["prior_ledger_sha256"] != sha(first_ledger)
                or first["previous_checksum"] != "GENESIS"
                or first["previous_event_id"] != "GENESIS"
                or first["previous_ledger_sha256"] != "GENESIS"):
            return "HOLD_FIRST_ANCHOR", None
        if (second["seq"] != 8 or second["scope"] != first["scope"]
                or second["prior_checkpoint_sha256"] != first["prior_checkpoint_sha256"]
                or second["prior_ledger_sha256"] != first["prior_ledger_sha256"]
                or second["previous_checksum"] != checksum(first_raw)
                or second["previous_event_id"] != first_event["id"]
                or second["previous_ledger_sha256"] != sha(first_ledger)):
            return "HOLD_PREDECESSOR_OR_SCOPE", None
        if len(second_ledger) <= len(first_ledger) or not second_ledger.startswith(first_ledger):
            return "HOLD_LEDGER_PREFIX", None
        if len(first_rows) != 6 or len(second_rows) != 8:
            return "HOLD_SEQUENCE", None
        return "RECOVERED_LINKED_SYNTHETIC_EXTERNAL_FLOOR_ONLY", {
            "envelope": second_raw, "ledger": second_ledger, "event": second_event,
            "seq": second["seq"], "ledger_sha256": sha(second_ledger),
            "event_id": second_event["id"],
        }
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        return "HOLD_INVALID_EXTERNAL_CONTENT", None

