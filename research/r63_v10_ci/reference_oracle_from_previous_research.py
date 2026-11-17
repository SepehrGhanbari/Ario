#!/usr/bin/env python3
"""Independent offline adversarial oracle for Ario R63 V10 research.

NEVER a native Windows CNG test. No credentials/keys and no Ario repo writes.
Actual subprocess RPC parent crash + fsync and socket duplicate-client race
exercise ONLY a deliberately tiny Python model. The V9 coverage-gap
comparison is based on read-only inspection of V9 WitnessHandler source.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time

DOMAIN = b"ARIO-R63/spend/v2\0"
VER = "ARIO_R63_SPEND_V2_RESEARCH"
ZERO = "0" * 64

def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
                      allow_nan=False).encode("ascii")
def h(b):
    return hashlib.sha256(b).hexdigest()
def snap(pairs):
    return h(canon(sorted([list(x) for x in pairs], key=lambda x: x[0])))
def fmt_pairs(pairs):
    return b"".join(canon(list(p)) + b"\n" for p in pairs)
def event_hash(body):
    return h(DOMAIN + canon(body))
class Hold(ValueError):
    pass

def review_v2(raw, anchor=None):
    if raw and not raw.endswith(b"\n"):
        raise Hold("v2 incomplete line")
    seq, prev, pairs = 0, ZERO, []
    found = anchor == (0, ZERO)
    for line in raw.splitlines():
        try:
            v = json.loads(line)
        except Exception as ex:
            raise Hold("v2 bad json") from ex
        if canon(v) != line or set(v) != {"version", "seq", "prev", "nonce", "id", "before", "after", "hash"}:
            raise Hold("v2 noncanonical")
        if v["version"] != VER or type(v["seq"]) is not int or v["seq"] != seq + 1 or v["prev"] != prev:
            raise Hold("v2 chain order")
        n, k = v["nonce"], v["id"]
        if not isinstance(n, str) or not isinstance(k, str) or len(n) != 64 or len(k) != 64:
            raise Hold("v2 malformed nonce")
        if any(n == nn or k == kk for nn, kk in pairs):
            raise Hold("v2 duplicate")
        after_pairs = pairs + [[n, k]]
        body = {x: y for x, y in v.items() if x != "hash"}
        if v["before"] != snap(pairs) or v["after"] != snap(after_pairs) or v["hash"] != event_hash(body):
            raise Hold("v2 content or event hash")
        seq, prev, pairs = seq+1, v["hash"], after_pairs
        if anchor is not None and seq == anchor[0]:
            if prev != anchor[1]:
                raise Hold("external anchor fork")
            found = True
    if anchor is not None and not found:
        raise Hold("external anchor requires missing prefix")
    return seq, prev, pairs

def append_v2(raw, nonce, identity):
    seq, prev, pairs = review_v2(raw)
    if any(nonce == n or identity == k for n, k in pairs):
        raise Hold("v2 reused nonce/id")
    body = {"version": VER, "seq": seq+1, "prev": prev, "nonce": nonce,
            "id": identity, "before": snap(pairs), "after": snap(pairs+[[nonce,identity]])}
    return raw + canon({**body, "hash": event_hash(body)}) + b"\n"

def legacy_pairs(raw):
    if raw and not raw.endswith(b"\n"):
        raise Hold("v1 partial line")
    out = []
    for line in raw.splitlines():
        try: obj = json.loads(line)
        except Exception as ex: raise Hold("v1 bad json") from ex
        if not isinstance(obj, list) or len(obj) != 2 or any(not isinstance(x, str) or len(x) != 64 for x in obj):
            raise Hold("v1 bad pair")
        if canon(obj) != line:
            raise Hold("v1 noncanonical")
        if any(obj[0] == x[0] or obj[1] == x[1] for x in out):
            raise Hold("v1 duplicate")
        out.append(obj)
    return out

def strict_guard(v1_path, v2_path, in_memory_pairs, broker_sorted_digest):
    if not v1_path.is_file() or not v2_path.is_file():
        raise Hold("missing durable journal")
    v1_raw, v2_raw = v1_path.read_bytes(), v2_path.read_bytes()
    v1 = legacy_pairs(v1_raw)
    _, head, v2 = review_v2(v2_raw)
    if v1 != in_memory_pairs or v1 != v2:
        raise Hold("V1_DISK_V2_DISK_MEMORY_DIVERGENCE")
    if snap(v1) != broker_sorted_digest:
        raise Hold("R60_SORTED_CONTENT_MISMATCH")
    return head

def observed_v9_guard_model(v2_path, in_memory_pairs, broker_sorted_digest):
    # Reflects V9's WitnessHandler spend path: ONLY parent.spends + V2 disk,
    # and no fresh read of the V1 disk bytes. This is NOT running native V9.
    if snap(in_memory_pairs) != broker_sorted_digest:
        raise Hold("broker sorted mismatch")
    _, head, v2 = review_v2(v2_path.read_bytes())
    if v2 != in_memory_pairs:
        raise Hold("v2 vs in-memory list mismatch")
    return head

def nonce(c):
    return c * 64

def initial_pairs():
    # Deliberately reverse the lexical order of append-vs-snapshot.
    return [[nonce("e"), nonce("1")], [nonce("1"), nonce("2")]]

def init_case(root):
    root.mkdir(parents=True, exist_ok=False)
    pairs = initial_pairs()
    v2 = b""
    for n, k in pairs:
        v2 = append_v2(v2, n, k)
    (root/"v1.jsonl").write_bytes(fmt_pairs(pairs))
    (root/"v2.jsonl").write_bytes(v2)
    return pairs

def fsync_append(path, data):
    with path.open("ab", buffering=0) as f:
        f.write(data)
        os.fsync(f.fileno())

def result_log(path, rec):
    with path.open("ab") as f:
        f.write(canon(rec)+b"\n")
        f.flush(); os.fsync(f.fileno())

class RpcServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

class CrashHandler(socketserver.BaseRequestHandler):
    def handle(self):
        raw = self.request.recv(256)
        if raw.strip() != b"CRASH_AFTER_V2_FSYNC":
            self.request.sendall(b"HOLD\n")
            return
        base = self.server.base
        old = (base/"v2.jsonl").read_bytes()
        new = append_v2(old, nonce("7"), nonce("3"))
        fsync_append(base/"v2.jsonl", new[len(old):])
        result_log(base/"rpc-parent-marker.jsonl", {"event":"V2_FSYNC_BEFORE_V1", "pid":os.getpid(), "scope":"PYTHON_MODEL_RPC_PARENT"})
        os._exit(73)

class RaceHandler(socketserver.BaseRequestHandler):
    def handle(self):
        raw = self.request.recv(256)
        if raw.strip() != b"EXACT_NONCE":
            self.request.sendall(b"HOLD\n")
            return
        with self.server.lock:
            base = self.server.base
            pairs = legacy_pairs((base/"v1.jsonl").read_bytes())
            _, _, v2_pairs = review_v2((base/"v2.jsonl").read_bytes())
            if pairs != v2_pairs:
                response = b"HOLD\n"
            elif [nonce("7"),nonce("3")] in pairs:
                response = b"ALREADY_COMMITTED_MODEL\n"
            else:
                old = (base/"v2.jsonl").read_bytes()
                new = append_v2(old, nonce("7"), nonce("3"))
                fsync_append(base/"v2.jsonl", new[len(old):])
                fsync_append(base/"v1.jsonl", canon([nonce("7"),nonce("3")])+b"\n")
                result_log(base/"model-use.jsonl", {"event":"MODEL_SIGNATURE", "nonce":nonce("7")})
                response = b"SIGNED_MODEL\n"
        self.request.sendall(response)

def server_main(kind, root):
    handler = CrashHandler if kind == "crash" else RaceHandler
    with RpcServer(("127.0.0.1", 0), handler) as server:
        server.base = root
        server.lock = threading.Lock()
        (root/"ready.port").write_text(str(server.server_address[1]),encoding="ascii")
        server.serve_forever()

def socket_request(port, payload):
    with socket.create_connection(("127.0.0.1",port),timeout=3) as sock:
        sock.settimeout(4)
        sock.sendall(payload+b"\n")
        return sock.recv(1024).strip().decode("ascii")

def wait_ready(path, child):
    for _ in range(100):
        if path.exists():return int(path.read_text())
        if child.poll() is not None:break
        time.sleep(.03)
    raise RuntimeError("server did not publish port")

def case_order_separation(root):
    p=init_case(root)
    raw=(root/"v2.jsonl").read_bytes()
    head=review_v2(raw)[1]
    other=b""
    for n,k in reversed(p):other=append_v2(other,n,k)
    assert head != review_v2(other)[1], "append order heads must differ"
    assert snap(p) == snap(list(reversed(p))), "R60 content snapshots must match"
    return {"case":"APPEND_ORDER_VS_SORTED_R60", "status":"PASS_MODEL", "event_head_distinct":True,"sorted_digest_equal":True}

def case_v1_disk_drift(root):
    p=init_case(root)
    v1=root/"v1.jsonl";v2=root/"v2.jsonl"
    broker=snap(p)
    assert strict_guard(v1,v2,p,broker)
    original=v1.read_bytes()
    cases={"deleted":None,"truncated":original.splitlines(keepends=True)[0],
           "noncanonical":original.replace(b'"',b'" ',1),"modified":fmt_pairs([[nonce("c"),nonce("1")],p[1]])}
    saw=[]
    for name, mutation in cases.items():
        if mutation is None:v1.unlink()
        else:v1.write_bytes(mutation)
        # The older check still passes as V1 disk is not reopened in this path.
        observed_v9_guard_model(v2,p,broker)
        try:strict_guard(v1,v2,p,broker)
        except Hold as ex:saw.append([name,str(ex)])
        else:raise AssertionError("new strict guard accepted V1 drift: "+name)
        v1.write_bytes(original)
    assert len(saw)==len(cases)
    return {"case":"V1_DISK_DRIFT_UNOBSERVED_BY_V9_MODEL", "status":"GAP_CONFIRMED_IN_SOURCE_MODEL", "mutations":saw,"native_exploit":"NOT_TESTED"}

def case_rpc_parent_crash(root, source):
    p=init_case(root)
    proc=subprocess.Popen([sys.executable,str(source),"--mode","server","--kind","crash","--root",str(root)],
                          stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        port=wait_ready(root/"ready.port",proc)
        answer=socket_request(port,b"CRASH_AFTER_V2_FSYNC")
        code=proc.wait(timeout=8)
        assert answer == "" and code==73, (answer,code)
    finally:
        if proc.poll() is None:proc.kill();proc.wait()
    assert len(legacy_pairs((root/"v1.jsonl").read_bytes()))==2
    assert len(review_v2((root/"v2.jsonl").read_bytes())[2])==3
    try:strict_guard(root/"v1.jsonl",root/"v2.jsonl",p,snap(p))
    except Hold as ex:hold=str(ex)
    else:raise AssertionError("crash gap did not HOLD")
    # No signature or CNG call exists in the model, intentionally.
    return {"case":"REAL_PYTHON_RPC_PARENT_CRASH", "status":"HOLD_MODEL", "process_exit":73,"v1_records":2,"v2_records":3,"next_request":"HOLD_UNCERTAIN_MODEL", "reason":hold,"native_CNG":"NOT_AVAILABLE"}

def case_concurrent_rpc(root,source):
    p=init_case(root)
    proc=subprocess.Popen([sys.executable,str(source),"--mode","server","--kind","race","--root",str(root)],
                          stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    try:
        port=wait_ready(root/"ready.port",proc)
        gate=threading.Barrier(16)
        def request(_):
            gate.wait(timeout=5)
            return socket_request(port,b"EXACT_NONCE")
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            results=list(pool.map(request,range(16)))
        assert results.count("SIGNED_MODEL")==1,results
        assert results.count("ALREADY_COMMITTED_MODEL")==15,results
        assert len(legacy_pairs((root/"v1.jsonl").read_bytes()))==3
        assert len(review_v2((root/"v2.jsonl").read_bytes())[2])==3
        assert len((root/"model-use.jsonl").read_bytes().splitlines())==1
    finally:
        proc.kill();proc.wait()
    return {"case":"RPC_DUPLICATE_NONCE_16_CLIENTS", "status":"PASS_MODEL", "signed_model":1,"replayed_model":15,"native_CNG":"NOT_AVAILABLE"}

def case_all_local_rollback(root):
    p=init_case(root)
    old_v1=(root/"v1.jsonl").read_bytes()
    old_v2=(root/"v2.jsonl").read_bytes()
    old_anchor=review_v2(old_v2)[:2]
    fsync_append(root/"v1.jsonl",canon([nonce("7"),nonce("3")])+b"\n")
    newer=append_v2(old_v2,nonce("7"),nonce("3"))
    fsync_append(root/"v2.jsonl",newer[len(old_v2):])
    new_anchor=review_v2((root/"v2.jsonl").read_bytes())[:2]
    assert new_anchor != old_anchor
    # Adversary with full local rollback replaces log+local pin coherently.
    (root/"v1.jsonl").write_bytes(old_v1)
    (root/"v2.jsonl").write_bytes(old_v2)
    local_pin=old_anchor
    strict_guard(root/"v1.jsonl",root/"v2.jsonl",p,snap(p))
    assert review_v2((root/"v2.jsonl").read_bytes(),anchor=local_pin)
    try:review_v2((root/"v2.jsonl").read_bytes(),anchor=new_anchor)
    except Hold:external_reject=True
    else:raise AssertionError("retained outside anchor failed to reject rollback")
    return {"case":"WHOLE_LOCAL_STATE_ROLLBACK", "status":"EXPECTED_COUNTEREXAMPLE_LOCAL_ACCEPT", "local_pin_accepts":True,"retained_external_anchor_rejects":external_reject,"independent_anchor_available":"NO"}

def run(out,source):
    out.mkdir(parents=True,exist_ok=False)
    results=[]
    cases=[(case_order_separation,False),(case_v1_disk_drift,False),(case_rpc_parent_crash,True),(case_concurrent_rpc,True),(case_all_local_rollback,False)]
    for idx,(case,needs_source) in enumerate(cases,1):
        case_root=out/f"case_{idx:02}"
        try:result=case(case_root,source) if needs_source else case(case_root)
        except Exception as ex:
            result={"case":case.__name__,"status":"FAIL_OR_INCONCLUSIVE","exception":type(ex).__name__,"reason":str(ex)[:300]}
        results.append(result)
        result_log(out/"cases.jsonl",result)
    data={"scope":"OFFLINE_PYTHON_MODEL_NOT_NATIVE_R63", "cases":results,
          "native_windows_signer":"NOT_EXECUTED", "production":"NO_GO", "trust_activation":"NO_GO", "independent_custody":"NOT_ESTABLISHED"}
    (out/"summary.json").write_bytes(canon(data)+b"\n")
    print(json.dumps(data,indent=2,ensure_ascii=False))
    return 1 if any(x["status"]=="FAIL_OR_INCONCLUSIVE" for x in results) else 0

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--mode",choices=["run","server"],default="run")
    parser.add_argument("--kind",choices=["crash","race"])
    parser.add_argument("--root",type=Path)
    parser.add_argument("--out",type=Path)
    a=parser.parse_args()
    if a.mode=="server":
        if not a.root or not a.kind:parser.error("server requires root and kind")
        server_main(a.kind,a.root)
        return 0
    if not a.out:parser.error("run requires --out")
    return run(a.out,Path(__file__).resolve())
if __name__=="__main__":
    raise SystemExit(main())
