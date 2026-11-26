"""Read-only R63 witness reconciliation against R22.22D's retained head.

No publish, key, write-quorum, enrollment, trust activation, or production action.
The 282778 head is a pinned historical observation, not a global-latest oracle.
"""
import base64, hashlib, json, sys, time, urllib.request, zipfile
from pathlib import Path

ARCHIVE_SHA256 = "b36acf47e4e2c82d6009c72957d8535536c6c1773cdd1967170107a31a05feac"
FLOOR_SIZE = 282778
FLOOR_ROOT = bytes.fromhex("90e8bde586ae1d41a95a87b8b57e9b7c7ef3636fb07963b835ea26acdeae2864")
FLOOR_SOURCE = "R22.22D run 45824098389, source commit 83e9a0a9cb4ec5be0f235ee2643823d46d2d0f32"
SUFFIX = "eea2eb8af49836d7eeedbc0390f53632f45e051c71f7fc453b724d23d7d29640/checkpoint"
URLS = {
    "geomys": "https://witness.navigli.skylight.geomys.org/" + SUFFIX,
    "markovian": "https://witness.markovianprotocol.com/" + SUFFIX,
}

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("redirect refused")

def get(url, limit=16384):
    request = urllib.request.Request(url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache"})
    with urllib.request.build_opener(NoRedirect).open(request, timeout=15) as response:
        raw = response.read(limit + 1)
    if not 0 < len(raw) <= limit:
        raise ValueError("response bounds")
    return raw

def proof_nodes(m, n, out, tag):
    if not 0 < m < n or n >= 2**64:
        raise ValueError("consistency sizes")
    raw = get("https://test.sigsum.org/barreleye/get-consistency-proof/" + str(m) + "/" + str(n), 8192)
    (out / (tag + "-" + str(m) + "-" + str(n) + ".proof")).write_bytes(raw)
    lines = raw.decode("ascii").splitlines()
    if not 1 <= len(lines) <= 64:
        raise ValueError("consistency proof bounds")
    nodes = []
    for line in lines:
        if not line.startswith("node_hash="):
            raise ValueError("consistency proof syntax")
        value = bytes.fromhex(line[len("node_hash="):])
        if len(value) != 32:
            raise ValueError("consistency node length")
        nodes.append(value)
    return nodes

def compare_heads(a, b, source, consistency, out, tag):
    sa, ra = a
    sb, rb = b
    if sa == sb:
        consistency(sa, sb, ra, rb, [])
        return {"result": "SAME_HEAD", "size": sa, "root": ra.hex()}
    if sa < sb:
        nodes = proof_nodes(sa, sb, out, tag)
        consistency(sa, sb, ra, rb, nodes)
        return {"result": "CONSISTENT_OLDER_TO_NEWER", "older_size": sa, "newer_size": sb}
    nodes = proof_nodes(sb, sa, out, tag)
    consistency(sb, sa, rb, ra, nodes)
    return {"result": "CONSISTENT_OLDER_TO_NEWER", "older_size": sb, "newer_size": sa}

def compare_to_floor(head, consistency, out, tag):
    size, root = head
    if size == FLOOR_SIZE:
        consistency(size, FLOOR_SIZE, root, FLOOR_ROOT, [])
        return {"result": "EXACT_PINNED_FLOOR", "size": size}
    if size < FLOOR_SIZE:
        nodes = proof_nodes(size, FLOOR_SIZE, out, tag)
        consistency(size, FLOOR_SIZE, root, FLOOR_ROOT, nodes)
        return {"result": "PREFIX_OF_PINNED_FLOOR", "size": size, "floor_size": FLOOR_SIZE}
    nodes = proof_nodes(FLOOR_SIZE, size, out, tag)
    consistency(FLOOR_SIZE, size, FLOOR_ROOT, root, nodes)
    return {"result": "EXTENDS_PINNED_FLOOR", "floor_size": FLOOR_SIZE, "size": size}

def load_modules(source):
    sys.path.insert(0, str(source))
    from verify_witness import KEYS, ORIGIN, note
    from verify_direct import consistency
    from read_quorum import decide
    from audit import H
    from note_normalizer import normalize_ed25519_note
    return KEYS, ORIGIN, note, consistency, H, normalize_ed25519_note, decide

def parse_one(raw, name, KEYS, ORIGIN, note, normalizer, include_wire=False):
    normalized, extras = normalizer(raw, name, KEYS, ORIGIN)
    size, root, ts = note(normalized, KEYS[name])
    item = {"size": size, "root": root, "signed_timestamp": ts,
            "ed25519": "VERIFIED", "unverified_extra_signature_bytes": extras,
            "raw_sha256": hashlib.sha256(raw).hexdigest()}
    return (item, normalized) if include_wire else item

def selftest(archive, source):
    KEYS, ORIGIN, note, consistency, H, normalizer, decide = load_modules(source)
    rawzip = archive.read_bytes()
    if hashlib.sha256(rawzip).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("retained archive digest mismatch")
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise ValueError("retained archive CRC")
        expected = {
            "geomys": (282774, "4a75206b4b69142d1d90a284420d64cabf11ebe09931ba8e97262e2ad7baa1d5", [2432]),
            "markovian": (282772, "81b7ff78f817bf8460b2487d3ab3a9cfd7ba217ca17b1745e57492a0ed3d35e9", []),
        }
        out = {}
        for name, (size, root, extras) in expected.items():
            raw = z.read("monitors/" + name + ".raw")
            item = parse_one(raw, name, KEYS, ORIGIN, note, normalizer)
            if (item["size"], item["root"].hex(), item["unverified_extra_signature_bytes"]) != (size, root, extras):
                raise ValueError("archived note fixture mismatch: " + name)
            out[name] = {"size": size, "root": root, "extras": extras}
    print(json.dumps({"stage": "R63_NOTE_NORMALIZER_SELFTEST", "archive_sha256": ARCHIVE_SHA256,
                      "geomys": {"size": out["geomys"]["size"], "root": out["geomys"]["root"], "unverified_extra_signature_bytes": out["geomys"]["extras"]},
                      "markovian": {"size": out["markovian"]["size"], "root": out["markovian"]["root"]},
                      "result": "PASS"}, sort_keys=True), flush=True)

def run(archive, source, out):
    KEYS, ORIGIN, note, consistency, H, normalizer = load_modules(source)
    out.mkdir(parents=True, exist_ok=True)
    rawzip = archive.read_bytes()
    if hashlib.sha256(rawzip).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("retained archive digest mismatch")
    report = {
        "stage": "R63_R22_22D_READ_ONLY_RECONCILIATION",
        "reference": {"tree_size": FLOOR_SIZE, "tree_root": FLOOR_ROOT.hex(), "source": FLOOR_SOURCE},
        "freshness": "NOT_ESTABLISHED",
        "trusted_clock": "NOT_ESTABLISHED",
        "nonce_bound_read": "NOT_ESTABLISHED",
        "independent_custody": "NOT_ESTABLISHED",
        "global_latest": "NOT_ESTABLISHED",
        "write_quorum": "NOT_ESTABLISHED",
        "trust_activation": "NO_GO",
        "production": "NO_GO",
    }
    with zipfile.ZipFile(archive) as z:
        archived = {}
        for name in ("geomys", "markovian"):
            try:
                raw = z.read("monitors/" + name + ".raw")
                (out / ("archived-" + name + ".raw")).write_bytes(raw)
                item = parse_one(raw, name, KEYS, ORIGIN, note, normalizer)
                archived[name] = item
            except Exception as exc:
                archived[name] = {"status": "HOLD", "error": type(exc).__name__, "detail": str(exc)[:180]}
    report["archived_notes"] = {
        name: ({k: (v.hex() if isinstance(v, bytes) else v) for k, v in item.items()} if "status" not in item else item)
        for name, item in archived.items()
    }
    try:
        if all("status" not in archived[n] for n in archived):
            report["archived_pair"] = compare_heads(
                (archived["geomys"]["size"], archived["geomys"]["root"]),
                (archived["markovian"]["size"], archived["markovian"]["root"]),
                "archived", consistency, out, "archived-pair")
            report["archived_to_r22_22d"] = {
                name: compare_to_floor((item["size"], item["root"]), consistency, out, "archived-" + name)
                for name, item in archived.items()
            }
            report["archived_result"] = "PASS_HISTORICAL_NOTES_PREFIX_CONSISTENT"
        else:
            report["archived_result"] = "HOLD_ARCHIVED_NOTE"
    except Exception as exc:
        report["archived_result"] = "HOLD_" + type(exc).__name__
        report["archived_error"] = str(exc)[:180]

    current = {}
    current_wire = {}
    report["retrieved_at_runner_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for name, url in URLS.items():
        try:
            raw = get(url)
            (out / (name + ".raw")).write_bytes(raw)
            item, wire = parse_one(raw, name, KEYS, ORIGIN, note, normalizer, include_wire=True)
            item["runner_clock_age_seconds_diagnostic_only"] = int(time.time()) - item["signed_timestamp"]
            current[name] = item
            current_wire[name] = wire
        except Exception as exc:
            current[name] = {"status": "HOLD", "error": type(exc).__name__, "detail": str(exc)[:180]}
    report["endpoint_notes"] = {
        name: ({k: (v.hex() if isinstance(v, bytes) else v) for k, v in item.items()} if "status" not in item else item)
        for name, item in current.items()
    }
    try:
        if not all("status" not in current[n] for n in current):
            raise ValueError("one or more direct monitor notes unavailable or invalid")
        report["endpoint_pair"] = compare_heads(
            (current["geomys"]["size"], current["geomys"]["root"]),
            (current["markovian"]["size"], current["markovian"]["root"]),
            "endpoint", consistency, out, "endpoint-pair")
        report["endpoint_to_r22_22d"] = {
            name: compare_to_floor((item["size"], item["root"]), consistency, out, "endpoint-" + name)
            for name, item in current.items()
        }
        report["endpoint_result"] = "PASS_TWO_SIGNED_NOTES_PREFIX_CONSISTENT_REVIEW_ONLY"
        high_name = max(current, key=lambda name: current[name]["size"])
        high = current[high_name]
        low_name = min(current, key=lambda name: current[name]["size"])
        low = current[low_name]
        read_proofs = {}
        if low["size"] < high["size"]:
            read_proofs[(low["size"], high["size"])] = proof_nodes(low["size"], high["size"], out, "endpoint-read-quorum")
        report["r63_fixed_two_witness_policy_diagnostic"] = decide(
            (high["size"], high["root"]),
            [("geomys", current_wire["geomys"]), ("markovian", current_wire["markovian"])],
            read_proofs,
            int(time.time()))
        report["r63_policy_clock_source"] = "RUNNER_CLOCK_DIAGNOSTIC_ONLY_NOT_TRUSTED"
    except Exception as exc:
        report["endpoint_result"] = "HOLD_" + type(exc).__name__
        report["endpoint_error"] = str(exc)[:180]

    if report.get("archived_result") == "PASS_HISTORICAL_NOTES_PREFIX_CONSISTENT" and report.get("endpoint_result") == "PASS_TWO_SIGNED_NOTES_PREFIX_CONSISTENT_REVIEW_ONLY":
        report["result"] = "PASS_R63_R22_22D_PREFIX_RECONCILIATION_REVIEW_ONLY"
    else:
        report["result"] = "HOLD_R63_R22_22D_RECONCILIATION"
    (out / "report.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True), flush=True)

if __name__ == "__main__":
    mode = sys.argv[1]
    archive, source = Path(sys.argv[2]), Path(sys.argv[3])
    if mode == "selftest":
        selftest(archive, source)
    elif mode == "run":
        run(archive, source, Path(sys.argv[4]))
    else:
        raise SystemExit("invalid mode")
