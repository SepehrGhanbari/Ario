#!/usr/bin/env python3
"""Read-only verifier for Ario's existing public Markovian R2.11 commitment.
No submission, keys, credentials, mutation, or trust activation.
"""
import base64, datetime, hashlib, json, struct, urllib.request
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

BASE = "https://log.markovianprotocol.com"
WEB = "https://markovianprotocol.com"
EXPECTED_LEAF = 14905
EXPECTED_DIGEST = "79e7b801f802634c4f9546238816a7af0e2c542ce22b39426b991eaf7dba99a"
EXPECTED_TRUST_LEAF = 6112

def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Ario-R2.11-readonly-verifier/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()

def canon(obj):
    # All manifest values are ASCII strings, integers, arrays, objects and null;
    # Python's sorted compact JSON is RFC 8785-equivalent for this value domain.
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()

def parse_vkey(v):
    name, kid_hex, b64 = v.split("+", 2)
    blob = base64.b64decode(b64, validate=True)
    if len(blob) != 33:
        raise ValueError(f"{name}: unexpected key length {len(blob)}")
    kid = hashlib.sha256(name.encode() + b"\n" + blob).digest()[:4]
    if kid.hex() != kid_hex:
        raise ValueError(f"{name}: key id mismatch")
    return name, kid, blob[0], blob[1:]

def verify_manifest(m, predecessor=None):
    if m["version"] == 1:
        unsigned = dict(m); sigobj = unsigned.pop("signature")
        name, kid, alg, pub = parse_vkey(m["log_vkeys"]["ed25519"])
        if sigobj["key_id"] != kid.hex() or sigobj["alg"] != "ed25519" or alg != 1:
            raise ValueError("v1 signature key binding mismatch")
        Ed25519PublicKey.from_public_bytes(pub).verify(base64.b64decode(sigobj["sig"]), canon(unsigned))
    elif m["version"] == 2:
        unsigned = dict(m); sigs = unsigned.pop("signatures")
        keyset = [m["log_vkeys"]["ed25519"]] + m["manifest_vkeys"]["keys"]
        pins = {parse_vkey(v)[0]: parse_vkey(v) for v in keyset}
        valid = set()
        for s in sigs:
            if s["key_name"] not in pins:
                raise ValueError("v2 signature uses unpinned key")
            name, kid, alg, pub = pins[s["key_name"]]
            if s["key_id"] != kid.hex() or alg != 1:
                raise ValueError("v2 signature key binding mismatch")
            Ed25519PublicKey.from_public_bytes(pub).verify(base64.b64decode(s["sig"]), canon(unsigned))
            valid.add(name)
        if m["log_vkeys"]["ed25519"].split("+", 1)[0] not in valid:
            raise ValueError("v2 missing predecessor/log-key signature")
        if m["manifest_vkeys"]["keys"][0].split("+", 1)[0] not in valid:
            raise ValueError("v2 missing offline manifest-key signature")
        if predecessor is not None:
            if m["previous_manifest_sha256"] != hashlib.sha256(canon(predecessor)).hexdigest():
                raise ValueError("v2 previous-manifest digest mismatch")
    else:
        raise ValueError("unsupported trust-root version")
    now = datetime.datetime.now(datetime.timezone.utc)
    start = datetime.datetime.fromisoformat(m["valid_from"].replace("Z", "+00:00"))
    end = datetime.datetime.fromisoformat(m["valid_until"].replace("Z", "+00:00"))
    if not start <= now < end:
        raise ValueError("trust-root manifest outside validity window")
    return hashlib.sha256(canon({k:v for k,v in m.items() if k not in ("signature","signatures")})).hexdigest()

def verify_note(note, manifest):
    body, sep, sigblock = note.partition("\n\n")
    if not sep:
        raise ValueError("checkpoint has no signature block")
    body += "\n"
    origin, size_s, root_b64 = body.splitlines()[:3]
    if origin != manifest["origin"]:
        raise ValueError("checkpoint origin mismatch")
    size, root = int(size_s), base64.b64decode(root_b64)
    logname, logkid, logalg, logpub = parse_vkey(manifest["log_vkeys"]["ed25519"])
    witness_pins = {parse_vkey(v)[0]: parse_vkey(v) for v in manifest["witness_vkeys"]}
    log_ok = False
    valid = set()
    for line in sigblock.splitlines():
        if not line.startswith("— "):
            continue
        _, name, b64 = line.split(" ", 2)
        raw = base64.b64decode(b64)
        if name == logname and len(raw) == 68 and raw[:4] == logkid and logalg == 1:
            Ed25519PublicKey.from_public_bytes(logpub).verify(raw[4:], body.encode())
            log_ok = True
        pin = witness_pins.get(name)
        if pin and len(raw) == 76:
            _, kid, alg, pub = pin
            if raw[:4] != kid or alg != 4:
                raise ValueError(f"{name}: witness key binding mismatch")
            ts = int.from_bytes(raw[4:12], "big")
            msg = b"cosignature/v1\ntime " + str(ts).encode() + b"\n" + body.encode()
            Ed25519PublicKey.from_public_bytes(pub).verify(raw[12:], msg)
            valid.add(name)
    if not log_ok:
        raise ValueError("log signature missing or invalid")
    q = manifest["witness_quorum"]
    if len(valid) < q:
        raise ValueError(f"witness quorum not met: {len(valid)}/{q}")
    return size, root, len(valid)

def parse_proof(data):
    lines = data.decode().splitlines()
    if lines[0] != "c2sp.org/tlog-proof@v1":
        raise ValueError("unexpected proof format")
    idx = int(lines[1].split()[1])
    i = 2; path = []
    while i < len(lines) and lines[i]:
        path.append(base64.b64decode(lines[i])); i += 1
    if i == len(lines):
        raise ValueError("proof missing checkpoint")
    note = "\n".join(lines[i+1:])
    return idx, path, note

def inclusion_root(leaf, index, size, path):
    fn, sn = index, size - 1
    r = hashlib.sha256(b"\x00" + leaf).digest()
    H = lambda a,b: hashlib.sha256(b"\x01" + a + b).digest()
    for node in path:
        if sn == 0:
            raise ValueError("proof path too long")
        if fn & 1 or fn == sn:
            r = H(node, r)
            if not (fn & 1):
                while True:
                    fn >>= 1; sn >>= 1
                    if fn & 1 or fn == 0: break
        else:
            r = H(r, node)
        fn >>= 1; sn >>= 1
    if sn != 0:
        raise ValueError("proof path too short")
    return r

def check_leaf(index, manifest):
    leaf = get(f"{BASE}/leaf/{index}")
    idx, path, note = parse_proof(get(f"{BASE}/proof/{index}"))
    if idx != index:
        raise ValueError("proof index mismatch")
    size, root, quorum = verify_note(note, manifest)
    if index >= size:
        raise ValueError("leaf outside checkpoint")
    computed = inclusion_root(leaf, index, size, path)
    if computed != root:
        raise ValueError("Merkle inclusion mismatch")
    return leaf.decode(), size, quorum

def main():
    v1 = json.loads(get(f"{WEB}/.well-known/trust-root/1.json"))
    v2 = json.loads(get(f"{WEB}/.well-known/trust-root/2.json"))
    h1 = verify_manifest(v1)
    h2 = verify_manifest(v2, v1)
    print(f"TRUST_ROOT_V1_SIGNATURE=PASS sha256={h1}")
    print(f"TRUST_ROOT_V2_DUAL_SIGNATURE=PASS sha256={h2}")
    leaf_v2 = json.loads(get(f"{BASE}/leaf/{EXPECTED_TRUST_LEAF}"))
    if leaf_v2.get("manifest_sha256") != h2:
        raise ValueError("trust-root v2 digest does not match its logged leaf")
    _, trust_size, trust_q = check_leaf(EXPECTED_TRUST_LEAF, v2)
    print(f"TRUST_ROOT_V2_LOGGED_LEAF=PASS index={EXPECTED_TRUST_LEAF} checkpoint_size={trust_size} quorum={trust_q}/{len(v2['witness_vkeys'])}")
    leaf, size, quorum = check_leaf(EXPECTED_LEAF, v2)
    if f"sha256:{EXPECTED_DIGEST}" not in leaf:
        raise ValueError("R2.11 public leaf does not contain expected commitment")
    print(f"ARIO_LEAF_READBACK=PASS index={EXPECTED_LEAF} checkpoint_size={size}")
    print(f"CHECKPOINT_LOG_SIGNATURE=PASS")
    print(f"CHECKPOINT_WITNESS_QUORUM=PASS {quorum}/{len(v2['witness_vkeys'])} (required {v2['witness_quorum']})")
    print("RFC6962_MERKLE_INCLUSION=PASS")
    anchor = json.loads(get(f"{BASE}/anchor"))
    print(f"ANCHOR_CONFIRMED_SIZE={anchor.get('confirmed_size')} BLOCK={anchor.get('confirmed_block')}")
    if int(anchor.get("confirmed_size", 0)) >= EXPECTED_LEAF + 1:
        print("BITCOIN_COVERAGE=SERVICE_STATUS_COVERS_LEAF; independent OTS/header verification still required")
    else:
        print("BITCOIN_COVERAGE=PENDING; confirmed checkpoint does not yet cover leaf 14905")
    print("NO_SUBMISSION / READ_ONLY / RESEARCH_ONLY / NO_TRUST_ACTIVATION / NO_PRODUCTION")

if __name__ == "__main__":
    main()
