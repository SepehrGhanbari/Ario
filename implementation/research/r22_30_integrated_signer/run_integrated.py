"""Bounded, first-generation integrated signing experiment.

Actual swtpm, Ed25519 dual approvals, existing Go witness/quorum modules,
separate Linux UIDs, durable authorization and receipt state, process kills.
Root is the fixture administrator, not an independent custodian.
"""
from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

from ario_r2230.common import LabError, atomic_write, canonical_bytes, hash_object, read_json, run, sha256_hex, strict_loads
from ario_r2230.tpm import TpmLab, provision, verify_with_openssl

PROFILE = "ARIO-R22.30-INTEGRATED-FIRST-v1"
ROLES = dict(signer=24001, policy=24002, founder=24003, ario=24004,
             w1=24005, w2=24006, w3=24007, publisher=24008)
TPM_GROUP = 24010

def require(ok, reason):
    if not ok:
        raise LabError(reason)

def validhash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None

def owned_dir(path, role):
    path.mkdir(mode=0o700)
    os.chown(path, ROLES[role], ROLES[role])

def owned_write(path, value, role):
    atomic_write(path, value, mode=0o600, uid=ROLES[role], gid=ROLES[role])

def public_write(path, value):
    atomic_write(path, value, mode=0o644)

def as_role(role, args, *, data=None, tpm=False):
    uid = ROLES[role]
    group_flag = f"--groups={TPM_GROUP}" if tpm else "--clear-groups"
    return run(["setpriv", f"--reuid={uid}", f"--regid={uid}", group_flag,
                "--no-new-privs", *map(str, args)], check=False, input_bytes=data, timeout=90)

def successful(result):
    if result.returncode:
        raise LabError(f"role failed ({result.returncode}): {result.stderr.decode(errors='replace')}")
    return result.stdout

def role_tpm(base, role):
    # Attach to the disposable fixture only; never use automatic TCTI selection.
    tpm = object.__new__(TpmLab)
    tpm.base = base / "tpm"
    tpm.socket = tpm.base / "tpm.sock"
    tpm.ctrl = tpm.base / "tpm.sock.ctrl"
    tpm.state = tpm.base / "tpm-state"
    tpm.log = tpm.base / "swtpm.log"
    tpm.work = base / role
    tpm.nv_index = "0x01500030"
    return tpm

@contextlib.contextmanager
def locked(directory):
    fd = os.open(directory / "lock", os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)

def crash(point, selected):
    if point == selected:
        os.kill(os.getpid(), signal.SIGKILL)

def validate_op(op, pins):
    require(isinstance(op, dict) and set(op) == {
        "profile", "identity", "epoch", "generation", "previous",
        "request_id", "payload_sha256"}, "operation schema")
    require(op["profile"] == PROFILE and op["identity"] == pins["identity"]
            and type(op["epoch"]) is int and op["epoch"] == 1
            and type(op["generation"]) is int and op["generation"] == 1
            and op["previous"] == pins["genesis"], "identity/epoch/generation/floor")
    require(isinstance(op["request_id"], str) and re.fullmatch(r"req-[0-9a-f]{32}", op["request_id"])
            and validhash(op["payload_sha256"]), "request binding")
    return hash_object(op)

def approval_bytes(role, decision, op_hash):
    return canonical_bytes({"profile": PROFILE + "-APPROVAL", "role": role,
                            "decision": decision, "operation": op_hash})

def verify_approvals(base, approvals, op_hash):
    require(isinstance(approvals, list) and len(approvals) == 2, "two approvals required")
    seen = set()
    with tempfile.TemporaryDirectory(dir=base / "policy") as name:
        scratch = Path(name)
        for a in approvals:
            require(isinstance(a, dict) and set(a) == {"role", "decision", "signature"}, "approval schema")
            role = a["role"]
            require(role in ("founder", "ario") and role not in seen, "approval role")
            require(a["decision"] == "APPROVE", "denial or veto")
            require(isinstance(a["signature"], str) and re.fullmatch(r"[0-9a-f]{128}", a["signature"]), "approval encoding")
            seen.add(role)
            (scratch / "message").write_bytes(approval_bytes(role, a["decision"], op_hash))
            (scratch / "signature").write_bytes(bytes.fromhex(a["signature"]))
            run(["openssl", "pkeyutl", "-verify", "-pubin", "-rawin",
                 "-inkey", str(base / "public" / (role + ".pem")),
                 "-in", str(scratch / "message"), "-sigfile", str(scratch / "signature")])
    require(seen == {"founder", "ario"}, "approval roles")

def policy_worker(base, bundle, stop):
    directory = base / "policy"
    pins = read_json(base / "public" / "pins.json")
    with locked(directory):
        require(set(bundle) == {"operation", "approvals", "proofs"}, "bundle schema")
        op = bundle["operation"]
        op_hash = validate_op(op, pins)
        verify_approvals(base, bundle["approvals"], op_hash)
        nonce = sha256_hex(op["request_id"].encode())
        run([str(base / "public" / "bridge"), "verify",
             str(base / "public" / "witnesses.json"), nonce, op_hash],
            input_bytes=canonical_bytes(bundle["proofs"]))
        state = read_json(directory / "state")
        if state.get("phase") == "ISSUED" and state.get("operation") == op_hash:
            return state["token"]
        require(state == {"phase": "EMPTY"}, "authority already reserved or issued")
        tpm = role_tpm(base, "policy")
        require(tpm.key_name().hex() == pins["identity"], "TPM identity")
        require(tpm.read_counter() == 1, "TPM counter")
        # Reserve before creation or release of an authorization signature.
        atomic_write(directory / "state", {"phase": "RESERVED", "operation": op_hash}, mode=0o600)
        crash("after-authority-reserve", stop)
        message = directory / "operation"
        message.write_bytes(canonical_bytes(op))
        cp = directory / "operation.cp"
        policy = directory / "operation.policy"
        sig = directory / "operation.sig"
        tpm.cp_hash(message, cp)
        tpm.trial_policy(1, cp, policy, "integrated-authority")
        tpm.flush_all()
        run(["openssl", "dgst", "-sha256", "-sign", str(directory / "authority.private.pem"),
             "-out", str(sig), str(policy)])
        token = {"profile": PROFILE, "operation": op_hash, "identity": pins["identity"],
                 "counter": 1, "cp": cp.read_bytes().hex(), "policy": policy.read_bytes().hex(),
                 "signature": sig.read_bytes().hex()}
        atomic_write(directory / "state", {"phase": "ISSUED", "operation": op_hash, "token": token}, mode=0o600)
        return token

def check_receipt(base, receipt, op, directory):
    require(isinstance(receipt, dict) and set(receipt) == {
        "profile", "operation", "signature", "counter_after"}, "receipt schema")
    require(receipt["profile"] == PROFILE and receipt["operation"] == op
            and receipt["counter_after"] == 2, "receipt binding")
    with tempfile.TemporaryDirectory(dir=directory) as name:
        scratch = Path(name)
        message, sig = scratch / "message", scratch / "signature"
        message.write_bytes(canonical_bytes(op))
        sig.write_bytes(bytes.fromhex(receipt["signature"]))
        require(verify_with_openssl(base / "public" / "signer.pem", message, sig), "receipt signature")

def signer_worker(base, bundle, stop):
    directory = base / "signer"
    pins = read_json(base / "public" / "pins.json")
    with locked(directory):
        require(set(bundle) == {"operation", "token"}, "signer bundle")
        op, token = bundle["operation"], bundle["token"]
        op_hash = validate_op(op, pins)
        tpm = role_tpm(base, "signer")
        state = read_json(directory / "state")
        if state.get("phase") == "COMMITTED":
            receipt = state["receipt"]
            check_receipt(base, receipt, op, directory)
            require(tpm.key_name().hex() == pins["identity"] and tpm.read_counter() == 2, "rollback or identity mismatch")
            return {"receipt": receipt, "replayed": True}
        require(state == {"phase": "EMPTY"}, "uncertain prior signing")
        require(isinstance(token, dict) and set(token) == {"profile", "operation", "identity",
            "counter", "cp", "policy", "signature"}, "token schema")
        require(token["profile"] == PROFILE and token["operation"] == op_hash
                and token["identity"] == pins["identity"] and token["counter"] == 1, "token binding")
        require(tpm.key_name().hex() == pins["identity"] and tpm.read_counter() == 1, "TPM identity/counter")
        message = directory / "operation"
        message.write_bytes(canonical_bytes(op))
        cp, policy, sig = (directory / x for x in ("operation.cp", "operation.policy", "operation.sig"))
        tpm.cp_hash(message, cp)
        require(cp.read_bytes().hex() == token["cp"], "cpHash mismatch")
        tpm.trial_policy(1, cp, policy, "integrated-signer")
        require(policy.read_bytes().hex() == token["policy"], "policy digest mismatch")
        sig.write_bytes(bytes.fromhex(token["signature"]))
        crash("before-reserve", stop)
        atomic_write(directory / "state", {"phase": "RESERVED", "operation": op_hash}, mode=0o600)
        crash("after-reserve", stop)
        authority_ctx, authority_name, ticket = (directory / x for x in ("authority.ctx", "authority.name", "authority.ticket"))
        tpm.flush_all()
        tpm.tpm(["tpm2_loadexternal", "-C", "o", "-G", "rsa",
                 "-u", str(base / "public" / "authority.pem"), "-c", str(authority_ctx), "-n", str(authority_name)])
        require(authority_name.read_bytes().hex() == pins["authority_name"], "policy authority pin")
        tpm.tpm(["tpm2_verifysignature", "-c", str(authority_ctx), "-g", "sha256",
                 "-m", str(policy), "-s", str(sig), "-t", str(ticket), "-f", "rsassa"])
        tpm.flush_all()
        session = directory / "authorized.session"
        tpm.start_policy_session(counter=1, cp_hash=cp, approved_policy=policy,
                                 authority_name=authority_name, ticket=ticket, session=session)
        crash("after-policy", stop)
        signature = directory / "operation.signature"
        tpm.sign_with_session(message, session, signature)
        require(tpm.verify_with_tpm(message, signature)
                and verify_with_openssl(base / "public" / "signer.pem", message, signature), "signature verification")
        tpm.tpm(["tpm2_flushcontext", str(session)], check=False)
        crash("after-sign", stop)
        require(tpm.increment_counter() == 2, "counter advance")
        crash("after-increment", stop)
        receipt = {"profile": PROFILE, "operation": op,
                   "signature": signature.read_bytes().hex(), "counter_after": 2}
        atomic_write(directory / "state", {"phase": "COMMITTED", "receipt": receipt}, mode=0o600)
        crash("after-receipt", stop)
        return {"receipt": receipt, "replayed": False}

@contextlib.contextmanager
def fixture(bridge):
    with tempfile.TemporaryDirectory(prefix="ario2230-") as name:
        base = Path(name)
        base.chmod(0o711)
        public = base / "public"
        public.mkdir(mode=0o755)
        shutil.copy2(bridge, public / "bridge")
        (public / "bridge").chmod(0o755)
        code = public / "code"
        code.mkdir(mode=0o755)
        here = Path(__file__).resolve().parent
        shutil.copy2(here / "run_integrated.py", code / "run_integrated.py")
        shutil.copytree(here / "ario_r2230", code / "ario_r2230", ignore=shutil.ignore_patterns("__pycache__"))
        for role in ROLES:
            owned_dir(base / role, role)
        for role in ("signer", "policy"):
            owned_write(base / role / "state", {"phase": "EMPTY"}, role)
            owned_write(base / role / "lock", b"", role)
        for role in ("founder", "ario"):
            private = base / role / "key.pem"
            successful(as_role(role, ["openssl", "genpkey", "-algorithm", "ED25519", "-out", private]))
            pub = successful(as_role(role, ["openssl", "pkey", "-in", private, "-pubout"]))
            public_write(public / (role + ".pem"), pub)
        tpm = TpmLab(base / "tpm")
        try:
            authority_private = base / "policy" / "authority.private.pem"
            authority_public = base / "policy" / "authority.public.pem"
            info = provision(tpm, authority_private=authority_private, authority_public=authority_public,
                             run_as=(ROLES["policy"], ROLES["policy"], []))
            public_write(public / "authority.pem", authority_public.read_bytes())
            public_write(public / "signer.pem", Path(info["signer_public_pem"]).read_bytes())
            tpm.base.chmod(0o711)
            for p in (tpm.socket, tpm.ctrl):
                os.chown(p, 0, TPM_GROUP)
                p.chmod(0o660)
            genesis = sha256_hex(b"ARIO-R22.30 disposable genesis")
            pins = {"identity": info["key_name_hex"], "authority_name": info["authority_name_hex"], "genesis": genesis}
            public_write(public / "pins.json", pins)
            members = []
            for role in ("w1", "w2", "w3"):
                members.append(json.loads(successful(as_role(role, [public / "bridge", "init", base / role, role, genesis]))))
            public_write(public / "witnesses.json", {"Policy": {"Scope": "ario-r2230-test", "Epoch": 1,
                         "Threshold": 3, "Members": members}, "Genesis": genesis})
            yield base, pins
        finally:
            tpm.stop()

def operation(pins, payload):
    return {"profile": PROFILE, "identity": pins["identity"], "epoch": 1, "generation": 1,
            "previous": pins["genesis"], "request_id": "req-" + uuid.uuid4().hex,
            "payload_sha256": sha256_hex(payload)}

def approve(base, role, op, decision="APPROVE"):
    message = base / role / "approval.message"
    signature = base / role / "approval.signature"
    owned_write(message, approval_bytes(role, decision, hash_object(op)), role)
    successful(as_role(role, ["openssl", "pkeyutl", "-sign", "-rawin", "-inkey",
                               base / role / "key.pem", "-in", message, "-out", signature]))
    return {"role": role, "decision": decision, "signature": signature.read_bytes().hex()}

def reservations(base, op, *, expected=True):
    public = base / "public"
    results = [as_role(role, [public / "bridge", "reserve", base / role, public / "witnesses.json",
                            sha256_hex(op["request_id"].encode()), hash_object(op)]) for role in ("w1", "w2", "w3")]
    if not expected:
        require(all(r.returncode != 0 for r in results), "conflicting reservation unexpectedly succeeded")
        return []
    return [json.loads(successful(r)) for r in results]

def worker(base, role, bundle, stop="none"):
    return as_role(role, ["python3", base / "public" / "code" / "run_integrated.py",
                         "worker", base, role, stop], data=canonical_bytes(bundle), tpm=True)

def result(r):
    return json.loads(successful(r))

def denied(r, label):
    require(r.returncode == 2 and b"HOLD:" in r.stderr, f"{label}: expected explicit denial, got {r.returncode}: {r.stderr!r}")
    print("PASS", label, flush=True)

def bundle_for(base, op):
    approvals = [approve(base, role, op) for role in ("founder", "ario")]
    return {"operation": op, "approvals": approvals, "proofs": reservations(base, op)}

def run_conflicting_request_race(bridge):
    with fixture(bridge) as (base, pins):
        operations = [
            operation(pins, b"competing operation A"),
            operation(pins, b"competing operation B"),
        ]
        approvals = [
            [approve(base, role, op) for role in ("founder", "ario")]
            for op in operations
        ]
        roles = ("w1", "w2", "w3")
        jobs = [(index, role) for index in range(len(operations)) for role in roles]
        start = Barrier(len(jobs))

        def reserve(job):
            index, role = job
            start.wait(timeout=20)
            op = operations[index]
            return as_role(role, [
                base / "public" / "bridge", "reserve", base / role,
                base / "public" / "witnesses.json",
                sha256_hex(op["request_id"].encode()), hash_object(op),
            ])

        with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
            outcomes = list(pool.map(reserve, jobs))

        proofs = [[] for _ in operations]
        for (index, _role), outcome in zip(jobs, outcomes):
            if outcome.returncode == 0:
                proofs[index].append(json.loads(successful(outcome)))
        for role in roles:
            accepted = sum(
                outcome.returncode == 0
                for (index, candidate_role), outcome in zip(jobs, outcomes)
                if candidate_role == role
            )
            require(accepted == 1, f"{role} did not serialize competing reservations")
        require(sum(map(len, proofs)) == len(roles), "witness accepted duplicate or missing reservation")

        full_quorums = [index for index, candidate_proofs in enumerate(proofs)
                        if len(candidate_proofs) == len(roles)]
        require(len(full_quorums) <= 1, "conflicting requests both reached a full witness quorum")
        committed = []
        for index, op in enumerate(operations):
            bundle = {"operation": op, "approvals": approvals[index], "proofs": proofs[index]}
            if index not in full_quorums:
                denied(worker(base, "policy", bundle),
                       f"conflicting request {index + 1} without full quorum")
                continue
            token = result(worker(base, "policy", bundle))
            signed = result(worker(base, "signer", {"operation": op, "token": token}))
            check_receipt(base, signed["receipt"], op, base / "signer")
            committed.append(index)
        require(len(committed) <= 1, "conflicting requests both committed")
        print("PASS distinct concurrent requests serialized; full-quorum winners="
              + str(len(committed)), flush=True)

def run_matrix(bridge):
    with fixture(bridge) as (base, pins):
        op = operation(pins, b"synthetic approved operation")
        b = bundle_for(base, op)
        for role in ("founder", "ario"):
            denied(worker(base, "policy", dict(b, approvals=[a for a in b["approvals"] if a["role"] == role])),
                   role + "-only")
        denied(worker(base, "policy", dict(b, approvals=[b["approvals"][0], approve(base, "ario", op, "VETO")])), "Ario veto")
        denied(worker(base, "policy", dict(b, proofs=b["proofs"][:2])), "wrong quorum")
        denied(worker(base, "policy", dict(b, proofs=[b["proofs"][0]] * 3)), "duplicate witness")
        conflict = operation(pins, b"conflicting operation")
        reservations(base, conflict, expected=False)
        print("PASS conflicting witness reservations rejected", flush=True)
        denied(worker(base, "policy", dict(b, operation=conflict)), "substituted operation")
        token = result(worker(base, "policy", b))
        require(token == result(worker(base, "policy", b)), "authority exact retry")
        print("PASS same stored policy token returned", flush=True)
        s = {"operation": op, "token": token}
        # Two genuine competing OS processes; one logical commit, one exact retry.
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: result(worker(base, "signer", s)), range(2)))
        require(outcomes[0]["receipt"] == outcomes[1]["receipt"]
                and sorted(o["replayed"] for o in outcomes) == [False, True], "concurrency")
        check_receipt(base, outcomes[0]["receipt"], op, base)
        print("PASS end-to-end TPM receipt + independent verification + concurrent exact retry", flush=True)
        denied(worker(base, "signer", dict(s, operation=conflict)), "conflicting signing request")
        require(as_role("publisher", ["cat", base / "policy" / "authority.private.pem"]).returncode != 0, "publisher key access")
        require(as_role("publisher", ["tpm2_getrandom", "-T", f"swtpm:path={base / 'tpm' / 'tpm.sock'}", "8"]).returncode != 0, "publisher TPM access")
        print("PASS publisher denied authority private key and TPM socket", flush=True)
    with fixture(bridge) as (base, pins):
        op = operation(pins, b"authority crash")
        b = bundle_for(base, op)
        r = worker(base, "policy", b, "after-authority-reserve")
        require(r.returncode == -signal.SIGKILL, "authority crash did not occur")
        denied(worker(base, "policy", b), "authority crash after durable reservation")
    for point in ("before-reserve", "after-reserve", "after-policy", "after-sign", "after-increment", "after-receipt"):
        with fixture(bridge) as (base, pins):
            op = operation(pins, point.encode())
            b = bundle_for(base, op)
            token = result(worker(base, "policy", b))
            s = {"operation": op, "token": token}
            killed = worker(base, "signer", s, point)
            require(killed.returncode == -signal.SIGKILL, f"{point}: process not killed: {killed.stderr!r}")
            retry = worker(base, "signer", s)
            if point in ("before-reserve", "after-receipt"):
                recovered = result(retry)
                require(recovered["replayed"] == (point == "after-receipt"), "retry disposition")
                check_receipt(base, recovered["receipt"], op, base)
                print("PASS crash", point, "verified receipt recovered", flush=True)
            else:
                denied(retry, "crash " + point + " uncertain, no retry signing")
    run_conflicting_request_race(bridge)
    print("INTEGRATED_FIRST_GENERATION_COMPLETE", flush=True)

def main():
    if len(sys.argv) == 5 and sys.argv[1] == "worker":
        base, role, stop = Path(sys.argv[2]), sys.argv[3], sys.argv[4]
        try:
            require(os.getuid() == ROLES[role], "wrong worker UID")
            raw = sys.stdin.buffer.read((2 << 20) + 1)
            require(len(raw) <= 2 << 20, "oversized request")
            bundle = strict_loads(raw)
            fn = {"policy": policy_worker, "signer": signer_worker}[role]
            sys.stdout.buffer.write(canonical_bytes(fn(base, bundle, stop)))
            return 0
        except (LabError, ValueError, KeyError, TypeError, OSError) as exc:
            print("HOLD:", str(exc), file=sys.stderr)
            return 2
    if len(sys.argv) == 2:
        require(os.getuid() == 0, "disposable CI fixture requires root")
        run_matrix(Path(sys.argv[1]).resolve())
        return 0
    raise SystemExit("usage: run_integrated.py BRIDGE")

if __name__ == "__main__":
    raise SystemExit(main())
