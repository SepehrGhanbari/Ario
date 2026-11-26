"""R4: use the EXISTING public R22.22B kit as retained reference.

Exact historical fixture projection, not a new archive commitment, witness,
generic proof verifier, trusted root or admission protocol. All local files
are disposable synthetic data; external input is the already-published kit.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

SCHEMA = "ARIO_RIO01_R22_RETAINED_PROJECTION_R4"
PASTE_SHA = "c122dc2fcdbfc304ffe6db809dec2e7e14d3feced480918b7cbc2d6a3edd0f69"
KIT_SHA = "304765d8d7f0da2d5e62443b7d1f48c00c8ff9bd324b8f8ed9c88c0ab7fffe24"
FIRST_ZIP = "2bedc6d0cc85857cfaed3ceafeb5d7700d78923057e661d9c5675d6925e6262b"
SECOND_ZIP = "717fbcf540cba37e7d5c6c83f3740fe301ece42fdc983fe4e9af484a37d56d27"
OLD_LEDGER = "d68d83b0418e77937794a7f57fa178177da8dcb5cb473b2379cebcd448e8e51e"
PREFIX = "ARIO R22.20 public synthetic floor (no personal data): "
QUESTION = "Which fictional public ledger record is at position 1?"
WORKER = Path(__file__).resolve().parents[2] / "implementation/core/historical_metadata_ipc_worker_r2.py"
MAX_INPUT = 4 * 1024 * 1024

class Hold(ValueError):
    pass

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def need(value, code):
    if not value:
        raise Hold(code)

def bounded(path):
    with path.open("rb") as f:
        raw = f.read(MAX_INPUT + 1)
    need(0 < len(raw) <= MAX_INPUT, "HOLD_INPUT_SIZE")
    return raw

def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, "HOLD_DUPLICATE_KEY")
        result[key] = value
    return result

def parse(raw):
    return json.loads(raw, object_pairs_hook=unique)

def member(raw, name, maximum):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        matches = [i for i in z.infolist() if i.filename == name]
        need(len(matches) == 1 and 0 < matches[0].file_size <= maximum,
             "HOLD_ZIP_MEMBER")
        with z.open(matches[0]) as f:
            data = f.read(maximum + 1)
        need(0 < len(data) <= maximum, "HOLD_ZIP_MEMBER")
        return data

def retained_pin(paste):
    need(type(paste) is bytes and sha(paste) == PASTE_SHA,
         "HOLD_EXTERNAL_REFERENCE_MISSING_OR_CHANGED")
    need(paste.endswith(b"\\n"), "HOLD_EXTERNAL_FORMAT")
    obj = parse(paste[:-2])
    need(obj["profile"] == "ARIO-R22.22B-EXTERNAL-KIT-COPY",
         "HOLD_EXTERNAL_PROFILE")
    kit = base64.b64decode(obj["kit_base64"], validate=True)
    need(len(kit) == obj["kit_bytes"] and sha(kit) == KIT_SHA == obj["kit_sha256"],
         "HOLD_EXTERNAL_KIT_PIN")
    pin = parse(member(kit, "RECOVERY_PIN.json", 16384))
    need(pin["profile"] == "ARIO-R22.22-RESEARCH_ONLY"
         and pin["archive_sha256"] == FIRST_ZIP
         and pin["trust_activation"] == pin["production"] == "NO_GO",
         "HOLD_EXTERNAL_PIN_PROFILE")
    return pin["retained_observation"]["ledger_sha256"]

def ledger(archive, expected_zip):
    need(sha(archive) == expected_zip, "HOLD_ARCHIVED_EVIDENCE_CHANGED")
    event = parse(member(archive, "event.json", 262144))
    need(event["content"].startswith(PREFIX), "HOLD_EVENT_PROFILE")
    env, data = [base64.b64decode(x, validate=True)
                 for x in event["content"][len(PREFIX):].split(".")]
    v = parse(env)
    need(v["synthetic"] is True and v["authoritative"] is False
         and v["trust_activation"] == v["production"] == "NO_GO"
         and 0 < len(data) <= 65536, "HOLD_EVENT_BOUNDARY")
    return v, env, data

def project(data):
    # A new deterministic *derived* synthetic fixture. No actual historical
    # Ario output or real ledger contents are embedded in user/answer text.
    result = []
    for i, line in enumerate(data.splitlines(keepends=True), 1):
        q = "Which fictional public ledger record is at position %d?" % i
        a = "Synthetic projection of ledger line SHA256 " + sha(line)
        obj = {"record_id": "projection-%d" % i, "session_id": "rio01-r4",
               "record_version": "15.3", "user": q, "ario": a,
               "user_sha256": sha(q.encode()), "ario_sha256": sha(a.encode()),
               "event_sha256": sha(line), "relations": []}
        result.append(json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n")
    return "".join(result).encode()

def worker(source, pin):
    request = {"op": "METADATA_LOOKUP_ONLY", "archive_path": str(source),
               "expected_sha256": pin, "question": QUESTION, "mode": "HISTORICAL"}
    p = subprocess.run([sys.executable, "-I", "-B", str(WORKER),
                        "--research-synthetic-only"],
                       input=json.dumps(request).encode(), capture_output=True,
                       timeout=20, check=False)
    need(not p.stderr and len(p.stdout) <= 16384
         and len(p.stdout.splitlines()) == 1, "HOLD_WORKER_OUTPUT")
    need(b"Synthetic projection of ledger line" not in p.stdout
         and QUESTION.encode() not in p.stdout, "HOLD_WORKER_TEXT_EGRESS")
    obj = parse(p.stdout)
    if p.returncode == 0:
        need(obj["status"] == "METADATA_ONLY_NOT_AUTHENTICATED"
             and obj["evidence_admission"] == "NO_ADMISSION"
             and obj["model_dispatch_permitted"] is False
             and obj["memory_write_permitted"] is False
             and not any(k in obj for k in ("historical_quote", "rendered_html", "text", "answer")),
             "HOLD_WORKER_CONTRACT")
    return p.returncode, obj["status"]

def atomic_replace(path, raw):
    temp = path.with_suffix(".pending")
    temp.write_bytes(raw)
    os.replace(temp, path)

def run(paste, first_zip, second_zip):
    ext = retained_pin(paste)
    a, araw, old = ledger(first_zip, FIRST_ZIP)
    b, _, new = ledger(second_zip, SECOND_ZIP)
    need(a["seq"] == 6 and b["seq"] == 8 and a["scope"] == b["scope"]
         and sha(old) == OLD_LEDGER and sha(new) == ext
         and b["previous_ledger_sha256"] == OLD_LEDGER
         and b["previous_checksum"] == sha(hashlib.sha256(araw).digest())
         and len(old.splitlines()) == 6 and len(new.splitlines()) == 8
         and new.startswith(old), "HOLD_EXTERNAL_TRANSITION")
    old_archive, new_archive = project(old), project(new)
    need(new_archive.startswith(old_archive) and sha(old_archive) != sha(new_archive),
         "HOLD_PROJECTION")
    observations = {}
    def check(name, actual, expected):
        need(actual == expected, "HOLD_CONTROL_" + name)
        observations[name] = actual
    with tempfile.TemporaryDirectory(prefix="rio01-r4-") as name:
        local = Path(name)
        archive = local / "RIO01_SYNTHETIC_PROJECTION.jsonl"
        pin = local / "local.sha256"
        archive.write_bytes(new_archive)
        pin.write_text(sha(new_archive), encoding="ascii")
        external_archive_pin = sha(new_archive)
        # Keep the readback and derived pin outside this local rollback set.
        def external_lookup(reference):
            try:
                need(retained_pin(reference) == ext, "HOLD_EXTERNAL_REFERENCE")
            except (Hold, ValueError, KeyError, TypeError, OSError):
                return 2, "HOLD_EXTERNAL_REFERENCE_MISSING_OR_CHANGED"
            return worker(archive, external_archive_pin)
        def local_lookup():
            return worker(archive, pin.read_text(encoding="ascii"))
        ok = (0, "METADATA_ONLY_NOT_AUTHENTICATED")
        stale = (2, "HOLD_SOURCE_SHA256_MISMATCH")
        missing = (2, "HOLD_EXTERNAL_REFERENCE_MISSING_OR_CHANGED")
        check("01_current_local", local_lookup(), ok)
        check("02_current_external", external_lookup(paste), ok)
        # Actual rollback of BOTH publisher-controlled files.
        atomic_replace(archive, old_archive)
        atomic_replace(pin, sha(old_archive).encode("ascii"))
        check("03_joint_rollback_local_only_RED", local_lookup(), ok)
        check("04_joint_rollback_external_rejects", external_lookup(paste), stale)
        check("05_external_missing_no_fallback", external_lookup(None), missing)
        check("06_external_corrupt_no_fallback", external_lookup(paste+b"!"), missing)
        check("07_external_old_reference_no_fallback", external_lookup(first_zip), missing)
        atomic_replace(archive, new_archive + b"{}\n")
        atomic_replace(pin, sha(archive.read_bytes()).encode("ascii"))
        check("08_unverified_extension_rejected", external_lookup(paste), stale)
        atomic_replace(archive, new_archive)
        # Local pin remains wrong: the external guard does not depend on it.
        check("09_current_with_wrong_local_pin", external_lookup(paste), ok)
        check("10_local_pin_alone_wrong", local_lookup(), stale)
    return {"schema": SCHEMA, "status": "EXACT_DERIVED_SYNTHETIC_OBSERVATION_ONLY",
            "controls": observations, "control_count": len(observations),
            "external_payload_sha256": PASTE_SHA, "external_kit_sha256": KIT_SHA,
            "retained_public_ledger_sha256": ext,
            "old_projection_sha256": sha(old_archive),
            "new_projection_sha256": sha(new_archive),
            "common_admin_local_only_rollback": "RED",
            "independent_admin_custody_established": False,
            "external_verifier_integrity_established": False,
            "global_freshness": "UNKNOWN",
            "new_archive_commitment_published": False,
            "evidence_admission": "NO_ADMISSION",
            "trust_activation": False, "production_authorized": False}

def main():
    if len(sys.argv) != 5 or sys.argv[1] != "--read-existing-synthetic-evidence":
        print(json.dumps({"schema": SCHEMA, "status": "HOLD_EXPLICIT_OPT_IN_REQUIRED"}))
        return 2
    try:
        result = run(*(bounded(Path(x)) for x in sys.argv[2:]))
    except (Hold, OSError, ValueError, TypeError, KeyError, RuntimeError,
            RecursionError, subprocess.SubprocessError, zipfile.BadZipFile):
        print(json.dumps({"schema": SCHEMA, "status": "HOLD_R4_EVIDENCE_OR_CONTROL"}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
