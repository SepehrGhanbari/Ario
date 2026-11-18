#!/usr/bin/env python3
"""W26: native Linux UID/DAC/peercred falsifier on disposable runner ONLY.

No new system users, passwords, keys, networking, log admission, signer, or Ario
production actions.  Numeric UIDs are ephemeral *identities* in a CI VM, not
separate administrators. Root can bypass these permissions by design.

Run ONLY inside a disposable GitHub-hosted Linux Actions runner with:
  ARIO_W26_DISPOSABLE_CI=1 sudo -n python -B w26_linux_uid_lab.py --ci-run
or in an isolated disposable container with ARIO_W26_DISPOSABLE_CONTAINER=1
and RUNNER_TEMP pointing to that container's scratch directory.
"""
from __future__ import annotations
import argparse
import errno
import hashlib
import json
import os
from pathlib import Path
import platform
import pwd
import socket
import struct
import subprocess
import sys
import tempfile
import time

PUBLISHER_UID = 210011
WITNESS_UID = 210012
INTRUDER_UID = 210013
HEAD = {"schema": "ARIO_W26_SYNTHETIC_HEAD_V1", "size": 8, "root": "a"*64,
        "source_truth": "UNKNOWN", "operational_authority": "NONE"}
MAX_REQ = 4096


def guarded():
    """Never operate on local host by default; fail closed unless lab-specific opt in."""
    ci = os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("ARIO_W26_DISPOSABLE_CI") == "1"
    container = os.environ.get("ARIO_W26_DISPOSABLE_CONTAINER") == "1"
    runner_temp = os.environ.get("RUNNER_TEMP", "")
    if not (ci or container) or platform.system() != "Linux" or not runner_temp:
        raise RuntimeError("W26_NO_GO: requires explicitly opted-in disposable Linux CI/container")
    root = Path(runner_temp).resolve(strict=True)
    if not root.is_dir() or str(root) in ("/", "/home", "/tmp"):
        raise RuntimeError("W26_NO_GO: unsafe RUNNER_TEMP")
    return root


def within(root: Path, path: str):
    # Resolve path for safety on setup; avoid relying on resolution for the ACL probes.
    pp = Path(path).absolute()
    if not pp.is_relative_to(root):
        raise RuntimeError("W26_NO_GO: path outside disposable lab")
    return pp


def reply(status, **kwargs):
    base = {"status": status, "authority": "NONE", "witness_cosignature": False,
            "independent_admin": "NOT_ESTABLISHED", "world_freshness": "UNKNOWN",
            "external_actions": 0}
    base.update(kwargs)
    return base


def drop_uid(uid):
    def preexec():
        os.setgroups([])
        os.setgid(uid)
        os.setuid(uid)
    return preexec


def probe(action, path):
    if action == "read":
        Path(path).read_bytes()
    elif action == "truncate":
        with open(path, "wb") as f: f.write(b"CORRUPTED")
    elif action == "remove":
        Path(path).unlink()
    elif action == "chmod":
        Path(path).chmod(0o777)
    elif action == "replace":
        os.replace(path, path + ".replaced")
    elif action == "create":
        Path(path).write_bytes(b"attacker replacement")
    elif action == "symlink":
        os.symlink(path, path + ".attacker-link")
    elif action == "hardlink":
        os.link(path, path + ".attacker-hardlink")
    else:
        raise ValueError("unsupported probe")
    return reply("SUCCEEDED")


def serve(socket_path, ledger_path, allowed_uid, expected_calls):
    """Read-only Unix socket; SO_PEERCRED authenticates LOCAL UID, not an operator."""
    if os.geteuid() != WITNESS_UID:
        raise RuntimeError("WITNESS_UID_REQUIRED")
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        srv.bind(socket_path)
        os.chmod(socket_path, 0o666)  # publisher may connect but not replace socket
        srv.listen(5)
        srv.settimeout(8)
        print("W26_SOCKET_READY", flush=True)
        for _ in range(expected_calls):
            conn, _ = srv.accept()
            with conn:
                conn.settimeout(3)
                try:
                    creds = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"))
                    _pid, uid, _gid = struct.unpack("3i", creds)
                    if uid != allowed_uid:
                        ans = reply("DENIED_PEER_UID", os_peer_uid=uid)
                    else:
                        raw = conn.recv(MAX_REQ+1)
                        if len(raw) > MAX_REQ or raw != b"HEAD\n":
                            ans = reply("DENIED_UNSUPPORTED_OR_LARGE_REQUEST", os_peer_uid=uid)
                        else:
                            head = json.loads(Path(ledger_path).read_text("utf-8"))
                            if head != HEAD:
                                ans = reply("HOLD_LEDGER_CORRUPT", os_peer_uid=uid)
                            else:
                                ans = reply("READ_ONLY_HEAD", size=head["size"], root=head["root"], os_peer_uid=uid)
                    conn.sendall((json.dumps(ans, sort_keys=True)+"\n").encode())
                except (OSError, ValueError, json.JSONDecodeError):
                    try: conn.sendall((json.dumps(reply("HOLD_WIRE_ERROR"))+"\n").encode())
                    except OSError: pass
    finally:
        srv.close()
        try: os.unlink(socket_path)
        except OSError: pass


def client(socket_path, payload):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(4)
        s.connect(socket_path)
        s.sendall(payload.encode())
        raw = b""
        while not raw.endswith(b"\n") and len(raw) <= 4096:
            piece = s.recv(2048)
            if not piece: break
            raw += piece
        return json.loads(raw)


def run_native():
    root = guarded()
    if os.geteuid() != 0:
        raise RuntimeError("W26_NO_GO: native identity setup must run only as root inside disposable runner")
    for uid in (PUBLISHER_UID, WITNESS_UID, INTRUDER_UID):
        try: pwd.getpwuid(uid)
        except KeyError: pass
        else: raise RuntimeError("W26_NO_GO: synthetic UID collides with existing account")
    # GitHub RUNNER_TEMP itself is intentionally private (0700 to runner).
    # Use only a fresh root-owned /tmp child (0755) on the disposable runner;
    # never chmod RUNNER_TEMP, the checkout, or an existing host path.
    base = Path(tempfile.mkdtemp(prefix="ario-w26-", dir="/tmp"))
    base.chmod(0o755)
    # CI checkout directories can be unreadable to synthetic UIDs. Copy only
    # this exact source to the scratch root; never widen checkout permissions.
    worker_source = base / 'w26_worker.py'
    source_bytes = Path(__file__).read_bytes()
    worker_source.write_bytes(source_bytes)
    worker_source.chmod(0o644)
    if worker_source.read_bytes() != source_bytes:
        raise AssertionError('W26_PROBE_SOURCE_COPY_MISMATCH')
    pubdir, witdir, ipcdir = [base/x for x in ("publisher", "witness", "ipc")]
    try:
        for path, uid, mode in ((pubdir,PUBLISHER_UID,0o700), (witdir,WITNESS_UID,0o700), (ipcdir,WITNESS_UID,0o711)):
            path.mkdir()
            os.chown(path, uid, uid)
            path.chmod(mode)
        publisher_file = pubdir/"local_state.json"
        witness_file = witdir/"retained_head.json"
        publisher_file.write_text('{"synthetic":true}',encoding="utf-8")
        witness_file.write_text(json.dumps(HEAD,sort_keys=True),encoding="utf-8")
        for path,uid in ((publisher_file,PUBLISHER_UID),(witness_file,WITNESS_UID)):
            os.chown(path,uid,uid);path.chmod(0o600)
        before = witness_file.read_bytes()
        checks = []
        environment = dict(os.environ)
        environment["ARIO_W26_CI_ROOT"] = str(base)

        def run_as(uid, *params):
            a=subprocess.run([sys.executable,"-B",str(worker_source),*map(str,params)],
                             env=environment,capture_output=True,text=True,timeout=8,preexec_fn=drop_uid(uid))
            if a.returncode not in (0,):
                raise AssertionError(f"child failed exit={a.returncode} err={a.stderr[:500]} stdout={a.stdout[:300]}")
            return json.loads(a.stdout)
        def check(label, condition, observed):
            checks.append({"name":label,"pass":bool(condition),"observation":observed})

        check("DISTINCT_NATIVE_EFFECTIVE_UIDS",len({PUBLISHER_UID,WITNESS_UID,INTRUDER_UID})==3,"three distinct numeric kernel identities")
        own = run_as(PUBLISHER_UID,"--probe","read",publisher_file)
        check("PUBLISHER_READS_OWN_STATE",own["status"]=="SUCCEEDED",own["status"])
        own_wit = run_as(WITNESS_UID,"--probe","read",witness_file)
        check("WITNESS_READS_OWN_LEDGER",own_wit["status"]=="SUCCEEDED",own_wit["status"])
        actions = [("read",witness_file), ("truncate",witness_file), ("remove",witness_file),
                   ("chmod",witness_file), ("replace",witness_file), ("create",witdir/"new_head"),
                   ("symlink",witdir/"new_head"), ("hardlink",witness_file)]
        for act,path in actions:
            rr=run_as(PUBLISHER_UID,"--probe",act,path)
            check("PUBLISHER_DENIED_"+act.upper(),rr["status"]=="DENIED",rr["status"])
        outsider=run_as(INTRUDER_UID,"--probe","read",witness_file)
        check("OUTSIDER_DENIED_LEDGER",outsider["status"]=="DENIED",outsider["status"])
        reversed_read=run_as(WITNESS_UID,"--probe","read",publisher_file)
        check("WITNESS_DENIED_PUBLISHER_STATE",reversed_read["status"]=="DENIED",reversed_read["status"])
        check("ACL_ATTEMPTS_LEFT_LEDGER_UNCHANGED",witness_file.read_bytes()==before,"same SHA256="+hashlib.sha256(before).hexdigest())
        sock=ipcdir/"read_only.sock"
        server = subprocess.Popen([sys.executable,"-B",str(worker_source),"--serve",str(sock),str(witness_file),str(PUBLISHER_UID),"5"],
                                  env=environment,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,preexec_fn=drop_uid(WITNESS_UID))
        try:
            # No readiness loop via stdout to remain portable in unittest; wait for socket.
            for _ in range(100):
                if sock.exists():break
                if server.poll() is not None:break
                time.sleep(.03)
            if not sock.exists():raise AssertionError("witness socket failed to start")
            socket_replace=run_as(PUBLISHER_UID,"--probe","remove",sock)
            check("PUBLISHER_DENIED_SOCKET_UNLINK",socket_replace["status"]=="DENIED",socket_replace["status"])
            good=run_as(PUBLISHER_UID,"--client",sock,"HEAD")
            check("PUBLISHER_READS_AUTHENTIC_LOCAL_PEER_HEAD",good.get("status")=="READ_ONLY_HEAD" and good.get("os_peer_uid")==PUBLISHER_UID and good.get("root")==HEAD["root"],good.get("status"))
            intruder=run_as(INTRUDER_UID,"--client",sock,"HEAD")
            check("INTRUDER_DENIED_BY_OS_PEERCRED",intruder.get("status")=="DENIED_PEER_UID" and intruder.get("os_peer_uid")==INTRUDER_UID,intruder.get("status"))
            wrong=run_as(PUBLISHER_UID,"--client",sock,"WRITE")
            check("WITNESS_DENIES_UNSUPPORTED_WRITE",wrong.get("status")=="DENIED_UNSUPPORTED_OR_LARGE_REQUEST",wrong.get("status"))
            huge=run_as(PUBLISHER_UID,"--client",sock,"A"*4200)
            check("WITNESS_DENIES_OVERSIZED_MESSAGE",huge.get("status")=="DENIED_UNSUPPORTED_OR_LARGE_REQUEST",huge.get("status"))
            root_peer=run_as(0,"--client",sock,"HEAD")
            check("WITNESS_DENIES_UNLISTED_ROOT_PEER",root_peer.get("status")=="DENIED_PEER_UID",root_peer.get("status"))
            server.wait(timeout=6)
            check("WITNESS_PROCESS_NORMAL_EXIT",server.returncode==0,str(server.returncode))
        finally:
            if server.poll() is None:
                server.kill();server.wait(timeout=3)
        # Root's DAC bypass is a required negative evidence, never a PASS of independence.
        original=witness_file.read_bytes()
        witness_file.write_bytes(b"ATTACK_BY_SAME_ADMIN")
        root_can_write=witness_file.read_bytes()!=original
        witness_file.write_bytes(original)
        check("SHARED_ROOT_CAN_REWRITE_WITNESS_FILE_NEGATIVE",root_can_write,"same-admin write succeeds; restoration checked")
        check("RESTORED_WITNESS_TEST_LEDGER",witness_file.read_bytes()==before,"restored original synthetic bytes")
        check("NO_WITNESS_SIGNING_OR_PRODUCTION",True,"no keys, real signers, external network, or production actions")
        summary = {"schema":"ARIO_W26_NATIVE_UID_EVIDENCE_V1","os":"Linux",
                   "native_uid_separation":"ESTABLISHED_FOR_TEST_RUNNER_ONLY",
                   "independent_operator_custody":"NOT_ESTABLISHED",
                   "root_admin_can_override":root_can_write,
                   "source_truth":"UNKNOWN","production":"NO_GO",
                   "tests":checks,"passed":sum(x["pass"] for x in checks),"total":len(checks)}
        print(json.dumps(summary,ensure_ascii=True,sort_keys=True))
        if summary["passed"]!=summary["total"]:raise AssertionError("W26_NATIVE_CONTROLS_FAILED")
    finally:
        # Cleanup uses root in disposable lab only. Nothing persists outside scratch.
        import shutil
        shutil.rmtree(base,ignore_errors=True)


def main():
    ap=argparse.ArgumentParser()
    g=ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--ci-run",action="store_true")
    g.add_argument("--probe",choices=["read","truncate","remove","chmod","replace","create","symlink","hardlink"])
    g.add_argument("--serve",action="store_true")
    g.add_argument("--client",action="store_true")
    ap.add_argument("extra",nargs="*")
    args=ap.parse_args()
    root=guarded()
    if args.ci_run:
        if args.extra:raise RuntimeError("unexpected extra args")
        return run_native()
    base=Path(os.environ.get("ARIO_W26_CI_ROOT", "")).absolute()
    scratch = base.parent == Path('/tmp') and base.name.startswith('ario-w26-')
    if not base.is_dir() or not (base.is_relative_to(root) or scratch):
        raise RuntimeError("W26_NO_GO: untrusted test base")
    if args.probe:
        if len(args.extra)!=1:raise RuntimeError("probe path required")
        path=within(base,args.extra[0])
        try: out=probe(args.probe,str(path))
        except OSError as e:
            out=reply("DENIED" if e.errno in (errno.EACCES,errno.EPERM) else "FAILED_OTHER_OS_ERROR", errno=e.errno)
        print(json.dumps(out,sort_keys=True))
    elif args.serve:
        if len(args.extra)!=4:raise RuntimeError("server args")
        sock,ledger,uid,connections=args.extra
        return serve(str(within(base,sock)),str(within(base,ledger)),int(uid),int(connections))
    elif args.client:
        if len(args.extra)!=2:raise RuntimeError("client args")
        path,word=args.extra
        payload=word+"\n" if word == "HEAD" else word
        print(json.dumps(client(str(within(base,path)),payload),sort_keys=True))

if __name__=="__main__":main()
