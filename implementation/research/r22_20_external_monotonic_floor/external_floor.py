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
            or type(x["seq"]) is not int or x["seq"] not in (6, 8)
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
    if len(unique) != 1:
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
            sub = "ario-r22-20"
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

def prepare(prior_dir, out_dir):
    from coincurve import PrivateKey
    prior, out = Path(prior_dir), Path(out_dir)
    old_env_raw = (prior / "six" / "envelope.json").read_bytes()
    old_env = json.loads(old_env_raw.decode("ascii"), object_pairs_hook=unique_pairs)
    old_ledger = (prior / "six" / "ledger.jsonl").read_bytes()
    parse_ledger(old_ledger, 6)
    if (type(old_env) is not dict or old_env.get("record", {}).get("seq") != 6
            or old_env.get("record", {}).get("ledger_sha256") != sha(old_ledger)
            or old_env.get("scope") is None):
        raise ValueError("R22.15B anchor mismatch")
    prior_checkpoint = sha(old_env_raw)
    prior_ledger = sha(old_ledger)
    scope = old_env["scope"]
    new_ledger = ledger_extend(old_ledger)
    raw6 = make_envelope(scope, 6, old_ledger, prior_checkpoint, prior_ledger,
                         "GENESIS", "GENESIS", "GENESIS")
    key = PrivateKey()
    event6 = make_event(raw6, old_ledger, key)
    raw8 = make_envelope(scope, 8, new_ledger, prior_checkpoint, prior_ledger,
                         checksum(raw6), event6["id"], sha(old_ledger))
    event8 = make_event(raw8, new_ledger, key)
    first, second = out / "first", out / "second"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    prior_anchor = first / "prior-anchor"
    prior_anchor.mkdir()
    for source, name in ((prior / "six" / "envelope.json", "envelope.json"),
                         (prior / "six" / "envelope.json.proof", "envelope.json.proof"),
                         (prior / "six" / "ledger.jsonl", "ledger.jsonl"),
                         (prior / "key.pub", "key.pub")):
        (prior_anchor / name).write_bytes(source.read_bytes())
    for folder, raw, ledger_raw, event in ((first, raw6, old_ledger, event6), (second, raw8, new_ledger, event8)):
        (folder / "envelope.json").write_bytes(raw)
        (folder / "ledger.jsonl").write_bytes(ledger_raw)
        (folder / "event.json").write_bytes(canonical(event))
        (folder / "event-id.txt").write_bytes(event_leaf_message(event))
    (first / "nostr.pub").write_text(event6["pubkey"] + "\n", encoding="ascii")
    accept6, fail6 = publish_event(event6)
    accept8, fail8 = publish_event(event8)
    if not accept6 or not accept8:
        raise RuntimeError("HOLD_EXTERNAL_RELAY_PUBLISH_UNAVAILABLE")
    time.sleep(2)
    got6, obs6 = fetch_many(accept6, event6["pubkey"], target_for_event(event6))
    got8, obs8 = fetch_many(accept8, event8["pubkey"], target_for_event(event8))
    if got6 is None or got8 is None:
        raise RuntimeError("HOLD_EXTERNAL_RELAY_READBACK_UNAVAILABLE")
    plan = {
        "topic": TOPIC,
        "nostr_pubkey": event6["pubkey"],
        "first_accepted_relays": accept6,
        "second_accepted_relays": accept8,
        "first_publish_failures": fail6,
        "second_publish_failures": fail8,
        "first_readback": obs6,
        "second_readback": obs8,
        "private_key_exported": False,
        "second_event_or_checksum_in_first_package": False,
    }
    (first / "relay-plan.json").write_bytes(canonical(plan))
    print(json.dumps({
        "prepared": True, "seq_first": 6, "seq_second": 8,
        "first_relay_acceptances": len(accept6), "second_relay_acceptances": len(accept8),
        "first_readback_relays": [x["relay"] for x in obs6 if x["matched"]],
        "second_readback_relays": [x["relay"] for x in obs8 if x["matched"]],
        "prior_checkpoint_sha256": prior_checkpoint,
        "private_key_exported": False,
    }, sort_keys=True), flush=True)

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
    if len(leaf_fields) < 2 or leaf_fields[1] != first_hash:
        raise ValueError("proof message binding")
    boot = {
        "start": int(fields["leaf_index"]), "size": int(fields["size"]),
        "root": fields["root_hash"], "public": public.hex(), "first_checksum": first_hash,
    }
    (first / "bootstrap.json").write_bytes(canonical(boot))
    (first / "sigsum.pub").write_text(Path(log_pub).read_text("ascii"), encoding="ascii")
    return boot

def recover(first_dir, discovery_path, output_dir):
    first_dir, output = Path(first_dir), Path(output_dir)
    first_event = json.loads((first_dir / "event.json").read_text("ascii"))
    first_env_raw = (first_dir / "envelope.json").read_bytes()
    first_ledger = (first_dir / "ledger.jsonl").read_bytes()
    plan = parse_json((first_dir / "relay-plan.json").read_bytes(), 8192)
    boot = parse_json((first_dir / "bootstrap.json").read_bytes(), 4096)
    pubkey = (first_dir / "nostr.pub").read_text("ascii").strip()
    if first_event["pubkey"] != pubkey:
        raise ValueError("first public key mismatch")
    if (type(boot.get("start")) is not int or type(boot.get("size")) is not int
            or boot["size"] <= boot["start"] or not HEX64.fullmatch(boot.get("first_checksum", ""))
            or target_for_event(first_event) != boot["first_checksum"]):
        raise ValueError("first event/bootstrap binding")
    first_payload = verify_event(first_event, pubkey)
    if first_payload[0] != first_env_raw or first_payload[2] != first_ledger:
        raise ValueError("first event package mismatch")
    prior_dir = first_dir / "prior-anchor"
    prior_raw = (prior_dir / "envelope.json").read_bytes()
    prior_ledger = (prior_dir / "ledger.jsonl").read_bytes()
    prior_env = json.loads(prior_raw.decode("ascii"), object_pairs_hook=unique_pairs)
    first_env = parse_envelope(first_env_raw)
    if (sha(prior_raw) != first_env["prior_checkpoint_sha256"]
            or sha(prior_ledger) != first_env["prior_ledger_sha256"]
            or prior_env.get("record", {}).get("ledger_sha256") != sha(prior_ledger)
            or prior_env.get("scope") != first_env["scope"]):
        raise ValueError("prior R22.15B signed anchor mismatch")
    parse_ledger(prior_ledger, 6)
    report = json.loads(Path(discovery_path).read_text("ascii").splitlines()[-1])
    matches = report.get("matching_signed_leaves")
    if (report.get("disposition") != "HOLD_OPAQUE_NEW_SIGNED_COMMITMENT"
            or report.get("complete_sampled_suffix") is not True
            or type(matches) is not list or len(matches) != 2
            or matches[0] != {"index": boot["start"], "checksum": boot["first_checksum"]}
            or type(matches[1].get("index")) is not int
            or matches[1]["index"] <= matches[0]["index"]
            or not HEX64.fullmatch(matches[1].get("checksum", ""))):
        raise ValueError("blind discovery binding")
    target = matches[1]["checksum"]
    urls = plan.get("second_accepted_relays")
    if type(urls) is not list or not urls:
        raise ValueError("no external relay plan")
    candidates, observations = [], []
    for url in urls:
        event, payload, observation = fetch_from(url, pubkey, target)
        observations.append(observation)
        if event is not None:
            candidates.append((event, url))
    if len({x[0]["id"] for x in candidates}) > 1:
        raise ValueError("conflicting relayed events for one logged commitment")
    if not candidates:
        raise RuntimeError("HOLD_OPAQUE_NEW_SIGNED_COMMITMENT_CONTENT_UNAVAILABLE")
    second_event, source = candidates[0]
    status, recovered = validate_successor(first_event, second_event, target, pubkey,
                                           parse_envelope(first_env_raw)["prior_checkpoint_sha256"])
    if status != "RECOVERED_LINKED_SYNTHETIC_EXTERNAL_FLOOR_ONLY":
        raise RuntimeError(status)
    # Forced one-endpoint outage: the loopback endpoint is deliberately unavailable;
    # the other endpoint is a real relay that accepted the event.
    fallback_event, _, fallback_obs = fetch_from("ws://127.0.0.1:1", pubkey, target)
    if fallback_event is not None:
        raise AssertionError("unavailable endpoint unexpectedly responded")
    fallback_event, _, working_obs = fetch_from(source, pubkey, target)
    if fallback_event is None or fallback_event["id"] != second_event["id"]:
        raise AssertionError("single-source fallback failed")
    # Replay the authentic first event against the later Sigsum-discovered leaf.
    if target_for_event(first_event) == target:
        raise AssertionError("event identifier collision")
    stale_replay = "HOLD_STALE_EVENT_REPLAY" if extract_target([first_event], target, pubkey)[0] is None else "UNEXPECTED_ACCEPT"
    if stale_replay != "HOLD_STALE_EVENT_REPLAY":
        raise AssertionError(stale_replay)
    # Simulate loss of both content relays after the log has exposed the new commitment.
    absent_a, _, outage_a = fetch_from("ws://127.0.0.1:1", pubkey, target)
    absent_b, _, outage_b = fetch_from("ws://127.0.0.1:2", pubkey, target)
    if absent_a is not None or absent_b is not None:
        raise AssertionError("outage injection")
    all_sources_down = "HOLD_CONTENT_UNAVAILABLE"
    output.mkdir(parents=True, exist_ok=True)
    (output / "envelope.json").write_bytes(recovered["envelope"])
    (output / "ledger.jsonl").write_bytes(recovered["ledger"])
    (output / "event.json").write_bytes(canonical(recovered["event"]))
    result = {
        "disposition": status,
        "seq": recovered["seq"],
        "event_id": recovered["event_id"],
        "event_id_leaf_checksum": target,
        "external_read_source": source,
        "actual_relay_observations": observations,
        "forced_single_source_outage": "PASS_FALLBACK_FROM_OTHER_RELAY",
        "stale_signed_event_replay": stale_replay,
        "both_content_sources_unavailable": all_sources_down,
        "both_unavailable_policy": "HOLD_OPAQUE_NEW_SIGNED_COMMITMENT",
        "recovered_content": True,
        "sigsum_witnessed_tree_order": "VERIFIED_BY_PINNED_SCANNER",
        "global_latest": "NOT_ESTABLISHED",
        "relay_durability": "NOT_ESTABLISHED",
        "independent_relay_administration": "NOT_ESTABLISHED",
        "independent_witness_quorum": "POLICY_VERIFIED_TEST_ONLY",
        "history_truth": "UNKNOWN",
        "trust_activation": "NO_GO",
        "production": "NO_GO",
        "merge_authorized": False,
    }
    (output / "report.json").write_bytes(canonical(result))
    print(json.dumps(result, sort_keys=True), flush=True)

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "prepare":
        prepare(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3 and sys.argv[1] == "bootstrap":
        create_bootstrap(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 4 and sys.argv[1] == "recover":
        recover(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit("invalid invocation")
