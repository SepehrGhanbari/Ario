"""RIO-01 R3 Linux DAC lab: separate numeric UIDs, disposable synthetic data.

Run only on a disposable Linux test runner as root with explicit opt-in.
Root is a trusted test orchestrator, not an independent custodian. No live
agent, real archive, signer, external network, account creation or service.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

CUSTODIAN = 61001
CONSUMER = 61002
SCHEMA = "ARIO_RIO01_LINUX_TWO_UID_LAB_R3"
QUESTION = "Synthetic historical question?"
SECRET = "RIO01_FICTIONAL_REPLY_NOT_ON_WIRE"
ROOT = Path(__file__).resolve().parents[2]
CORE = ("legacy_v153_historical_view.py", "historical_qa_research_boundary.py",
        "historical_metadata_ipc_worker_r2.py")

# Fixed executable snippets; no commands constructed from archive text.
CONSUMER_CODE = r"""
import json, os, pathlib, sys
source, pin, worker, control = map(pathlib.Path, sys.argv[1:5])
result = {"uid": os.getuid(), "gid": os.getgid(), "groups": os.getgroups()}
result["cap_eff"] = next(x.split()[1] for x in open("/proc/self/status") if x.startswith("CapEff:"))
def probe(fn):
    try:
        fn()
    except PermissionError:
        return "DENIED"
    except OSError:
        return "OTHER_OS_ERROR"
    return "ALLOWED"
def write_open(path):
    with path.open("r+b"):
        pass
result["read_archive"] = probe(lambda: source.read_bytes())
result["write_archive"] = probe(lambda: write_open(source))
result["rename_archive"] = probe(lambda: source.rename(source.with_name("replaced.jsonl")))
result["unlink_archive"] = probe(source.unlink)
result["write_pin"] = probe(lambda: write_open(pin))
result["write_worker"] = probe(lambda: write_open(worker))
result["positive_public_read"] = probe(lambda: control.read_bytes())
result["requests"] = [
    {"op": "METADATA_LOOKUP_ONLY", "question": "Synthetic historical question?", "mode": "HISTORICAL"},
    {"op": "RAW_QUOTE", "question": "Synthetic historical question?", "mode": "HISTORICAL"},
    {"op": "METADATA_LOOKUP_ONLY", "question": "Synthetic historical question?", "mode": "HISTORICAL", "expected_sha256": "0" * 64},
]
print(json.dumps(result, sort_keys=True))
"""
OWNER_CODE = r"""
import json, os, pathlib, sys
p = pathlib.Path(sys.argv[1])
raw = p.read_bytes()
print(json.dumps({"uid": os.getuid(), "gid": os.getgid(), "groups": os.getgroups(),
                  "read_nonempty": bool(raw),
                  "cap_eff": next(x.split()[1] for x in open("/proc/self/status") if x.startswith("CapEff:"))}))
"""
OWNER_MUTATE_CODE = r"""
import json, os, pathlib, sys
p = pathlib.Path(sys.argv[1])
p.write_bytes(sys.stdin.buffer.read())
print(json.dumps({"uid": os.getuid(), "mutated": True}))
"""


def require(condition, code):
    if not condition:
        raise RuntimeError(code)


def child(uid, argv, data=b"", cwd="/tmp"):
    run = subprocess.run(
        [sys.executable, "-I", "-B", *argv], input=data,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20, check=False,
        cwd=cwd, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
        user=uid, group=uid, extra_groups=[], umask=0o077,
    )
    require(not run.stderr and len(run.stdout) <= 32768 and
            len(run.stdout.splitlines()) == 1, "HOLD_CHILD_OUTPUT")
    require(SECRET.encode() not in run.stdout, "HOLD_RAW_REPLY_EGRESS")
    return run.returncode, json.loads(run.stdout)


def fixture(answer):
    return (json.dumps({
        "record_id": "fictional1", "session_id": "fictional",
        "record_version": "15.3", "user": QUESTION, "ario": answer,
        "user_sha256": hashlib.sha256(QUESTION.encode()).hexdigest(),
        "ario_sha256": hashlib.sha256(answer.encode()).hexdigest(),
        "event_sha256": "a" * 64, "relations": [],
    }) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def run_lab():
    require(sys.platform.startswith("linux") and os.geteuid() == 0,
            "HOLD_REQUIRES_DISPOSABLE_LINUX_ROOT_RUNNER")
    with tempfile.TemporaryDirectory(prefix="rio01-two-uid-", dir="/tmp") as name:
        base = Path(name)
        base.chmod(0o755)
        staged = base / "staged"
        core = staged / "core"
        core.mkdir(parents=True)
        for filename in CORE:
            dst = core / filename
            shutil.copyfile(ROOT / "implementation" / "core" / filename, dst)
            dst.chmod(0o444)
        core.chmod(0o555)
        staged.chmod(0o555)
        worker = core / CORE[-1]

        vault = base / "vault"
        vault.mkdir(mode=0o700)
        source = vault / "RIO01_SYNTHETIC_ARCHIVE.jsonl"
        raw = fixture(SECRET)
        source.write_bytes(raw)
        source.chmod(0o600)
        os.chown(source, CUSTODIAN, CUSTODIAN)
        os.chown(vault, CUSTODIAN, CUSTODIAN)

        pin = digest(raw)
        pin_path = base / "retained_pin"
        pin_path.write_text(pin, encoding="ascii")
        pin_path.chmod(0o400)
        public = base / "public_control"
        public.write_text("fictional public control", encoding="ascii")
        public.chmod(0o444)

        code, owner = child(CUSTODIAN, ["-c", OWNER_CODE, str(source)])
        require(code == 0 and owner["uid"] == CUSTODIAN and
                owner["gid"] == CUSTODIAN and owner["groups"] == [] and
                int(owner["cap_eff"], 16) == 0 and owner["read_nonempty"] is True,
                "HOLD_CUSTODIAN_POSITIVE_CONTROL")

        code, consumer = child(CONSUMER, ["-c", CONSUMER_CODE, str(source),
                               str(pin_path), str(worker), str(public)])
        require(code == 0 and consumer["uid"] == CONSUMER and
                consumer["gid"] == CONSUMER and consumer["groups"] == [] and
                int(consumer["cap_eff"], 16) == 0, "HOLD_CONSUMER_IDENTITY")
        operations = ("read_archive", "write_archive", "rename_archive",
                      "unlink_archive", "write_pin", "write_worker")
        require(all(consumer[op] == "DENIED" for op in operations),
                "HOLD_CONSUMER_ACCESS_NOT_DENIED")
        require(consumer["positive_public_read"] == "ALLOWED" and
                source.read_bytes() == raw, "HOLD_DAC_POSITIVE_CONTROL")

        # Trusted root coordinator selects the source and retained pin; the
        # consumer cannot choose either. This is a simulated one-shot relay,
        # not a persistent authenticated IPC service or independent root.
        def relay(request):
            if (type(request) is not dict or
                set(request) != {"op", "question", "mode"} or
                request.get("op") != "METADATA_LOOKUP_ONLY" or
                request.get("mode") not in ("HISTORICAL", "CURRENT") or
                type(request.get("question")) is not str):
                return 2, {"status": "HOLD_RELAY_REQUEST"}
            payload = dict(request, archive_path=str(source),
                           expected_sha256=pin_path.read_text(encoding="ascii"))
            return child(CUSTODIAN, [str(worker), "--research-synthetic-only"],
                         json.dumps(payload).encode())

        valid, raw_request, replacement_pin = consumer["requests"]
        code, receipt = relay(valid)
        require(code == 0 and receipt.get("status") == "METADATA_ONLY_NOT_AUTHENTICATED"
                and receipt.get("disposition") == "RECALLED_HISTORICAL_ONLY"
                and receipt.get("archive_sha256") == pin
                and receipt.get("source_line") == 1
                and receipt.get("evidence_admission") == "NO_ADMISSION"
                and receipt.get("context_injection_allowed") is False
                and receipt.get("model_dispatch_permitted") is False
                and receipt.get("memory_write_permitted") is False
                and not any(k in receipt for k in
                            ("historical_quote", "rendered_html", "answer", "text", "model_prompt")),
                "HOLD_METADATA_CONTRACT")
        for request in (raw_request, replacement_pin):
            require(relay(request) == (2, {"status": "HOLD_RELAY_REQUEST"}),
                    "HOLD_RELAY_FORBIDDEN_REQUEST")

        # Even the file owner can rewrite its own source. The retained pin
        # outside that child's control must reject the changed valid fixture.
        changed = fixture("Fictional changed answer")
        code, mutation = child(CUSTODIAN, ["-c", OWNER_MUTATE_CODE, str(source)], changed)
        require(code == 0 and mutation["uid"] == CUSTODIAN and
                mutation["mutated"] is True and source.read_bytes() == changed,
                "HOLD_MUTATION_CONTROL")
        code, stale = relay(valid)
        require(code == 2 and stale.get("status") == "HOLD_SOURCE_SHA256_MISMATCH",
                "HOLD_STALE_PIN_NOT_REJECTED")
        # Deliberately unsafe control: if a trusted caller chooses the new
        # pin, the same reader accepts it. Pinning is not independent custody.
        pin_path.chmod(0o600)
        pin_path.write_text(digest(changed), encoding="ascii")
        pin_path.chmod(0o400)
        code, unsafe = relay(valid)
        require(code == 0 and unsafe.get("archive_sha256") == digest(changed),
                "HOLD_UNSAFE_REPIN_CONTROL")
        return {
            "schema": SCHEMA, "status": "LINUX_DAC_SYNTHETIC_OBSERVATION_ONLY",
            "custodian_uid": CUSTODIAN, "consumer_uid": CONSUMER,
            "effective_capabilities_zero": True,
            "consumer_denied": {k: consumer[k] for k in operations},
            "custodian_read_positive_control": True,
            "consumer_public_read_positive_control": True,
            "metadata_only_lookup": True,
            "raw_quote_and_replacement_pin_refused": True,
            "custodian_mutation_rejected_by_retained_pin": True,
            "unsafe_root_repin_accepted": True,
            "root_coordinator_trusted": True,
            "independent_custody_established": False,
            "authenticated_ipc_established": False,
            "windows_acl_test": "NOT_RUN",
            "live_ario_recall_established": False,
            "evidence_admission": "NO_ADMISSION",
            "trust_activation": False, "production_authorized": False,
        }


def main():
    if sys.argv[1:] != ["--run-synthetic-root-lab"]:
        print(json.dumps({"schema": SCHEMA, "status": "HOLD_EXPLICIT_OPT_IN_REQUIRED"}))
        return 2
    try:
        print(json.dumps(run_lab(), sort_keys=True))
        return 0
    except (RuntimeError, OSError, ValueError, subprocess.SubprocessError, KeyError):
        # No archive bytes, path or traceback on unexpected failure.
        print(json.dumps({"schema": SCHEMA, "status": "HOLD_LAB_FAILURE"}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
